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
import sys
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Spotify helpers
# ---------------------------------------------------------------------------

def _build_spotify(client_id: str, client_secret: str):
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
    auth = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    return spotipy.Spotify(auth_manager=auth, requests_timeout=10, retries=3)


def _search_track(sp, title: str, artist: str) -> Optional[dict]:
    """
    Search Spotify for the best matching track.
    Returns a dict with {spotify_id, name, artist} or None if no match.
    """
    query = f"track:{title} artist:{artist}"
    try:
        results = sp.search(q=query, type="track", limit=1)
    except Exception as exc:
        print(f"  [spotify] search error for '{title}' by '{artist}': {exc}")
        return None

    items = results.get("tracks", {}).get("items", [])
    if not items:
        # Retry with just title (artist name sometimes differs)
        try:
            results = sp.search(q=f"track:{title}", type="track", limit=3)
            items = results.get("tracks", {}).get("items", [])
        except Exception:
            return None
        if not items:
            return None
        # Pick closest artist match
        artist_lower = artist.lower()
        for item in items:
            item_artists = " ".join(a["name"] for a in item["artists"]).lower()
            if any(word in item_artists for word in artist_lower.split()):
                return {"spotify_id": item["id"], "name": item["name"], "artist": item["artists"][0]["name"]}
        return None

    item = items[0]
    return {"spotify_id": item["id"], "name": item["name"], "artist": item["artists"][0]["name"]}


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

    q = sb.table("tracks").select("id,title,artist")
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
        result = _search_track(sp, track["title"], track["artist"])
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
