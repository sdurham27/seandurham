"""
Phase 2 — Spotify Enrichment
==============================
For each un-enriched track in Supabase, search Spotify by title+artist and
pull audio features (valence, energy, danceability, acousticness,
instrumentalness, tempo) plus the Spotify track ID.

Handles:
  - Spotify rate limits (429) via exponential back-off
  - Unmatched tracks flagged with matched=false
  - Checkpointing: skips tracks already in track_features
  - Batched audio-feature lookups (Spotify allows up to 100 IDs per call)

Usage:
    python -m ingestion.spotify_enricher
    python -m ingestion.spotify_enricher --limit 500   # process first N tracks
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Title / artist parsing helpers
# ---------------------------------------------------------------------------

# Remix / edit / version suffixes in parentheses or brackets
_REMIX_RE = re.compile(
    r'\s*[\(\[]\s*[^\(\)\[\]]*?'
    r'(?:remix|rmx|mix|edit|rework|bootleg|mashup|flip|version|vip|dub|'
    r'instrumental|extended|radio\s+edit|original\s+mix|club\s+mix)'
    r'[^\(\)\[\]]*[\)\]]',
    re.IGNORECASE,
)

# feat./ft./featuring suffixes (inside or outside brackets)
_FEAT_RE = re.compile(
    r'\s*[\(\[]?(?:feat\.?|ft\.?|featuring)\s+[^\)\]]+[\)\]]?',
    re.IGNORECASE,
)

# Multi-artist separators in the artist field
_MULTI_ARTIST_RE = re.compile(
    r'\s*(?:feat\.?|ft\.?|featuring|&|,|vs\.?|\bx\b|w/)\s*',
    re.IGNORECASE,
)

# "Artist - Title" or "Artist – Title" separator embedded in the title field
_TITLE_SEP_RE = re.compile(r'\s+[-–—]\s+')


def _clean_title(title: str) -> str:
    """Strip remix/feat suffixes to get a bare track name for searching."""
    cleaned = _REMIX_RE.sub('', title)
    cleaned = _FEAT_RE.sub('', cleaned)
    return cleaned.strip() or title.strip()


def _primary_artist(artist: str) -> str:
    """Return only the first artist from a multi-artist / feat. string."""
    parts = _MULTI_ARTIST_RE.split(artist, maxsplit=1)
    return parts[0].strip()


def _extract_from_title(title: str) -> tuple[str, str]:
    """
    If title looks like "Artist - Track", extract and return (track, artist).
    Returns ("", "") if the pattern is not detected.
    """
    parts = _TITLE_SEP_RE.split(title, maxsplit=1)
    if len(parts) == 2:
        return parts[1].strip(), parts[0].strip()  # (title, artist)
    return "", ""


def _score_match(item: dict, want_title: str, want_artist: str) -> float:
    """
    Rough 0–1 similarity between a Spotify result and our target.
    Weights title more heavily than artist.
    """
    item_title = item.get("name", "").lower()
    item_artists = " ".join(a["name"] for a in item.get("artists", [])).lower()
    t_words = [w for w in want_title.lower().split() if len(w) > 2]
    a_words = [w for w in want_artist.lower().split() if len(w) > 2]

    t_hits = sum(1 for w in t_words if w in item_title)
    a_hits = sum(1 for w in a_words if w in item_artists)

    t_score = (t_hits / len(t_words)) if t_words else 0.0
    a_score = (a_hits / len(a_words)) if a_words else 0.5  # unknown artist = neutral

    return 0.65 * t_score + 0.35 * a_score


# ---------------------------------------------------------------------------
# Spotify helpers
# ---------------------------------------------------------------------------

def _build_spotify(client_id: str, client_secret: str):
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
    auth = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    return spotipy.Spotify(auth_manager=auth, requests_timeout=10, retries=3)


def _run_query(sp, query: str) -> Optional[dict]:
    """Execute a single Spotify search query, return top item or None."""
    try:
        results = sp.search(q=query, type="track", limit=3)
        items = results.get("tracks", {}).get("items", [])
        return items[0] if items else None
    except Exception as exc:
        print(f"  [spotify] query error ({query!r}): {exc}")
        return None


def _search_track(sp, title: str, artist: str) -> Optional[dict]:
    """
    Multi-strategy Spotify search with progressive fallback.

    Strategy order:
    1. Cleaned title + primary artist  (most common case)
    2. Original title + primary artist (if cleaning changed something)
    3. Artist extracted from title + cleaned track name  (embedded "Artist - Title")
    4. Cleaned title only  (when artist name differs significantly)
    5. Original title only (last resort)

    Picks the highest-scoring result across all attempts.
    Returns {spotify_id, name, artist} or None.
    """
    clean_t = _clean_title(title)
    primary_a = _primary_artist(artist)

    # Try to detect artist embedded inside the title field
    emb_title, emb_artist = _extract_from_title(title)
    clean_emb_t = _clean_title(emb_title) if emb_title else ""

    # Build ordered strategy list, deduplicating identical queries
    strategies: list[tuple[str, str, str]] = []  # (query, ref_title, ref_artist)

    def _add(q: str, ref_t: str, ref_a: str) -> None:
        if q and q not in {s[0] for s in strategies}:
            strategies.append((q, ref_t, ref_a))

    if clean_t and primary_a:
        _add(f'track:"{clean_t}" artist:"{primary_a}"', clean_t, primary_a)
    if title != clean_t and primary_a:
        _add(f'track:"{title}" artist:"{primary_a}"', title, primary_a)
    if emb_title and emb_artist:
        _add(f'track:"{clean_emb_t or emb_title}" artist:"{emb_artist}"', clean_emb_t or emb_title, emb_artist)
    if clean_t:
        _add(f'track:"{clean_t}"', clean_t, artist)
    if title != clean_t:
        _add(f'track:"{title}"', title, artist)

    best_item: Optional[dict] = None
    best_score = 0.0

    for query, ref_t, ref_a in strategies:
        item = _run_query(sp, query)
        time.sleep(0.05)
        if not item:
            continue
        score = _score_match(item, ref_t, ref_a)
        if score > best_score:
            best_score = score
            best_item = item
        if best_score >= 0.85:
            break  # good enough, stop early

    if best_item and best_score >= 0.35:
        return {
            "spotify_id": best_item["id"],
            "name": best_item["name"],
            "artist": best_item["artists"][0]["name"],
        }
    return None


def _get_audio_features_batch(sp, spotify_ids: list[str]) -> dict[str, dict]:
    """Fetch audio features for up to 100 IDs. Returns {spotify_id: features}."""
    BATCH = 100
    result: dict[str, dict] = {}
    for i in range(0, len(spotify_ids), BATCH):
        chunk = spotify_ids[i : i + BATCH]
        attempt = 0
        while attempt < 5:
            try:
                features_list = sp.audio_features(chunk)
                for f in features_list:
                    if f:
                        result[f["id"]] = f
                break
            except Exception as exc:
                wait = 2 ** attempt
                print(f"  [spotify] audio_features error (attempt {attempt+1}): {exc} — waiting {wait}s")
                time.sleep(wait)
                attempt += 1
    return result


# ---------------------------------------------------------------------------
# Main enrichment loop
# ---------------------------------------------------------------------------

def _fetch_unenriched_tracks(sb, limit: Optional[int]) -> list[dict]:
    """Return tracks that don't yet have a row in track_features."""
    # Supabase left join via !inner exclusion — we use a NOT IN subquery approach
    # by fetching enriched track_ids first then excluding them.
    enriched_resp = sb.table("track_features").select("track_id").execute()
    enriched_ids = {row["track_id"] for row in enriched_resp.data}

    q = sb.table("tracks").select("id,title,artist,file_path")
    if limit:
        q = q.limit(limit)
    resp = q.execute()
    tracks = resp.data

    return [t for t in tracks if t["id"] not in enriched_ids]


def enrich(limit: Optional[int] = None) -> None:
    load_dotenv(Path(__file__).parent.parent.parent / ".env")

    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

    sp = _build_spotify(
        os.environ["SPOTIFY_CLIENT_ID"],
        os.environ["SPOTIFY_CLIENT_SECRET"],
    )

    tracks = _fetch_unenriched_tracks(sb, limit)
    total = len(tracks)
    print(f"[spotify] {total} tracks to enrich")

    if not total:
        print("[spotify] All tracks already enriched.")
        return

    # Phase A: search Spotify for each track to get spotify_id
    matched: list[dict] = []    # {track_id, spotify_id}
    unmatched: list[str] = []   # track_ids with no Spotify match

    for idx, track in enumerate(tracks):
        # If artist field is blank, try to get it from the file name
        # e.g. "04 - Track Name.mp3" → strip track number and extension
        artist = track["artist"] or ""
        if not artist and track.get("file_path"):
            stem = Path(track["file_path"]).stem
            # Remove leading track numbers like "01 - " or "01. "
            stem = re.sub(r'^\d+[\s\-\.]+', '', stem).strip()
            # If stem still has " - ", treat left part as artist
            if ' - ' in stem:
                artist = stem.split(' - ', 1)[0].strip()

        result = _search_track(sp, track["title"], artist)
        if result:
            matched.append({"track_id": track["id"], "spotify_id": result["spotify_id"]})
        else:
            unmatched.append(track["id"])

        if (idx + 1) % 50 == 0:
            print(f"  searched {idx+1}/{total} (matched {len(matched)}, unmatched {len(unmatched)})")

        # Spotify search rate limit: ~30 req/s; sleep slightly to stay safe
        time.sleep(0.1)

    print(f"[spotify] Matched {len(matched)}, unmatched {len(unmatched)}")

    # Phase B: fetch audio features in batches
    spotify_ids = [m["spotify_id"] for m in matched]
    features_by_id = _get_audio_features_batch(sp, spotify_ids)
    print(f"[spotify] Got audio features for {len(features_by_id)} tracks")

    # Phase C: upsert into track_features
    KEYS = ["valence", "energy", "danceability", "acousticness", "instrumentalness", "tempo"]
    rows_to_insert: list[dict] = []
    for m in matched:
        f = features_by_id.get(m["spotify_id"], {})
        row = {
            "track_id": m["track_id"],
            "spotify_id": m["spotify_id"],
            "matched": True,
            **{k: f.get(k) for k in KEYS},
        }
        rows_to_insert.append(row)

    # Unmatched tracks — insert with matched=false so they're flagged
    for track_id in unmatched:
        rows_to_insert.append({"track_id": track_id, "matched": False, "spotify_id": None})

    BATCH = 200
    for i in range(0, len(rows_to_insert), BATCH):
        sb.table("track_features").upsert(rows_to_insert[i:i+BATCH], on_conflict="track_id").execute()
        print(f"  upserted track_features {min(i+BATCH, len(rows_to_insert))}/{len(rows_to_insert)}")

    print("[spotify] Enrichment complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich tracks with Spotify audio features")
    parser.add_argument("--limit", type=int, default=None, help="Max tracks to process")
    args = parser.parse_args()
    enrich(limit=args.limit)


if __name__ == "__main__":
    main()
