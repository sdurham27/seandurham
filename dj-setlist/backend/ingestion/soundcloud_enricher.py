"""
SoundCloud Enrichment
======================
Searches SoundCloud for tracks that Spotify could not match. Because SC is home
to DJ edits, bootlegs, label promos, and unreleased tracks, it catches exactly
the gap in Spotify's catalog.

Uses SoundCloud's internal v2 API (api-v2.soundcloud.com) — the same API that
powers soundcloud.com. No official developer account required, but a client_id
IS required. Two ways to obtain it:

  1. Automatic: this script will fetch soundcloud.com and parse a client_id
     from the embedded JS bundles. This works until SoundCloud rotates the key.
  2. Manual: inspect network requests on soundcloud.com (search for a track,
     find a request to api-v2.soundcloud.com, copy the client_id query param)
     and set SOUNDCLOUD_CLIENT_ID in your .env file.

What we store (added to track_features):
  soundcloud_id       text    — numeric track ID as string
  soundcloud_matched  bool    — true if SC found the track

Note: SoundCloud does not expose audio features (valence, energy etc.) via its
API, so this enrichment only confirms track identity and updates the vetted flag.

Usage:
    python -m ingestion.soundcloud_enricher                  # unmatched tracks only
    python -m ingestion.soundcloud_enricher --all            # re-check every track
    python -m ingestion.soundcloud_enricher --limit 200
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.spotify_enricher import (  # reuse the same helpers
    _clean_title,
    _primary_artist,
    _extract_from_title,
)


# ---------------------------------------------------------------------------
# SoundCloud client_id resolution
# ---------------------------------------------------------------------------

_SC_CLIENT_ID_RE = re.compile(r'client_id:"([a-zA-Z0-9]{20,40})"')
_SC_SCRIPT_RE = re.compile(
    r'<script[^>]+src="(https://a-v2\.sndcdn\.com/assets/[^"]+\.js)"'
)

_cached_client_id: Optional[str] = None


def _fetch_client_id_from_web() -> Optional[str]:
    """
    Parse the SoundCloud web app JS bundles and extract the client_id.
    Checks the last 8 script bundles (the app bundle is usually near the end).
    """
    try:
        resp = httpx.get(
            "https://soundcloud.com",
            headers={"User-Agent": "Mozilla/5.0"},
            follow_redirects=True,
            timeout=15,
        )
        script_urls = _SC_SCRIPT_RE.findall(resp.text)
    except Exception as exc:
        print(f"[soundcloud] Could not fetch soundcloud.com: {exc}")
        return None

    for url in reversed(script_urls[-10:]):
        try:
            js = httpx.get(url, timeout=15).text
            m = _SC_CLIENT_ID_RE.search(js)
            if m:
                return m.group(1)
        except Exception:
            continue

    return None


def get_client_id() -> str:
    """Return a valid SoundCloud client_id, raising RuntimeError if none found."""
    global _cached_client_id

    # 1. Env var — highest priority, never stale
    env_id = os.environ.get("SOUNDCLOUD_CLIENT_ID", "").strip()
    if env_id:
        return env_id

    # 2. In-process cache
    if _cached_client_id:
        return _cached_client_id

    # 3. Auto-fetch from SC JS
    print("[soundcloud] Fetching client_id from soundcloud.com…")
    client_id = _fetch_client_id_from_web()
    if client_id:
        _cached_client_id = client_id
        print(f"[soundcloud] Got client_id: {client_id[:8]}…")
        return client_id

    raise RuntimeError(
        "Could not obtain a SoundCloud client_id automatically.\n"
        "Get one manually:\n"
        "  1. Open soundcloud.com in Chrome, open DevTools → Network\n"
        "  2. Search for any track\n"
        "  3. Find a request to api-v2.soundcloud.com\n"
        "  4. Copy the client_id query parameter\n"
        "Then set SOUNDCLOUD_CLIENT_ID=<value> in your .env file."
    )


# ---------------------------------------------------------------------------
# Search helpers
# ---------------------------------------------------------------------------

def _score_sc_match(item: dict, want_title: str, want_artist: str) -> float:
    """
    Score a SoundCloud search result against our target title/artist.
    Returns 0–1.
    """
    sc_title = item.get("title", "").lower()
    sc_user = (item.get("user") or {}).get("username", "").lower()
    sc_publisher = ((item.get("publisher_metadata") or {}).get("artist") or "").lower()
    sc_artist = sc_publisher or sc_user

    t_words = [w for w in want_title.lower().split() if len(w) > 2]
    a_words = [w for w in want_artist.lower().split() if len(w) > 2]

    t_hits = sum(1 for w in t_words if w in sc_title)
    a_hits = sum(1 for w in a_words if w in sc_artist)

    t_score = (t_hits / len(t_words)) if t_words else 0.0
    a_score = (a_hits / len(a_words)) if a_words else 0.5

    return 0.65 * t_score + 0.35 * a_score


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=1, max=10))
def _sc_search(client_id: str, query: str) -> list[dict]:
    """Hit the SoundCloud v2 search endpoint. Returns up to 5 results."""
    resp = httpx.get(
        "https://api-v2.soundcloud.com/search/tracks",
        params={"q": query, "client_id": client_id, "limit": 5},
        headers={"Accept": "application/json; charset=utf-8"},
        timeout=12,
    )
    if resp.status_code == 401:
        # client_id expired — clear cache so next call re-fetches
        global _cached_client_id
        _cached_client_id = None
        raise RuntimeError("SoundCloud client_id expired. Re-run to auto-refresh, or set SOUNDCLOUD_CLIENT_ID.")
    resp.raise_for_status()
    return resp.json().get("collection", [])


def search_soundcloud(client_id: str, title: str, artist: str) -> Optional[dict]:
    """
    Multi-query SoundCloud search with scoring, mirroring the Spotify approach.

    Returns {soundcloud_id, permalink_url, sc_title, sc_artist} or None.
    """
    clean_t = _clean_title(title)
    primary_a = _primary_artist(artist)
    emb_title, emb_artist = _extract_from_title(title)

    queries: list[tuple[str, str, str]] = []  # (query_str, ref_title, ref_artist)

    def _add(q: str, rt: str, ra: str) -> None:
        if q and q not in {s[0] for s in queries}:
            queries.append((q, rt, ra))

    _add(f"{primary_a} {clean_t}", clean_t, primary_a)
    if title != clean_t:
        _add(f"{primary_a} {title}", title, primary_a)
    if emb_title and emb_artist:
        _add(f"{emb_artist} {_clean_title(emb_title)}", _clean_title(emb_title), emb_artist)
    _add(f"{clean_t}", clean_t, artist)

    best_item: Optional[dict] = None
    best_score = 0.0

    for query, ref_t, ref_a in queries:
        try:
            items = _sc_search(client_id, query)
        except Exception as exc:
            print(f"  [soundcloud] search error ({query!r}): {exc}")
            time.sleep(1)
            continue

        for item in items:
            score = _score_sc_match(item, ref_t, ref_a)
            if score > best_score:
                best_score = score
                best_item = item

        if best_score >= 0.85:
            break

        time.sleep(0.2)

    if best_item and best_score >= 0.4:
        user = best_item.get("user") or {}
        publisher = best_item.get("publisher_metadata") or {}
        return {
            "soundcloud_id": str(best_item["id"]),
            "permalink_url": best_item.get("permalink_url", ""),
            "sc_title": best_item.get("title", ""),
            "sc_artist": publisher.get("artist") or user.get("username", ""),
        }

    return None


# ---------------------------------------------------------------------------
# Main enrichment loop
# ---------------------------------------------------------------------------

def _fetch_target_tracks(sb, only_unmatched: bool, limit: Optional[int]) -> list[dict]:
    """
    Return tracks to check on SoundCloud.
    - only_unmatched=True  → tracks where spotify matched=false (the useful case)
    - only_unmatched=False → all tracks that don't yet have soundcloud_matched=true
    """
    q = sb.table("track_features").select("track_id,matched,soundcloud_matched")
    if only_unmatched:
        q = q.eq("matched", False)
    resp = q.execute()
    features = resp.data

    # Filter to those not yet SC-matched
    needs_sc = [
        f["track_id"] for f in features
        if not f.get("soundcloud_matched")
    ]

    if not needs_sc:
        return []

    # Fetch title/artist for these track_ids
    track_resp = (
        sb.table("tracks")
        .select("id,title,artist")
        .in_("id", needs_sc)
    )
    if limit:
        track_resp = track_resp.limit(limit)
    return track_resp.execute().data


def enrich_soundcloud(only_unmatched: bool = True, limit: Optional[int] = None) -> None:
    load_dotenv(Path(__file__).parent.parent.parent / ".env")

    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

    client_id = get_client_id()

    tracks = _fetch_target_tracks(sb, only_unmatched, limit)
    total = len(tracks)

    if not total:
        print("[soundcloud] No tracks to check.")
        return

    print(f"[soundcloud] Checking {total} tracks on SoundCloud…")

    sc_matched: list[dict] = []
    sc_missed: list[str] = []

    for idx, track in enumerate(tracks):
        result = search_soundcloud(client_id, track["title"], track["artist"])
        if result:
            sc_matched.append({
                "track_id": track["id"],
                "soundcloud_id": result["soundcloud_id"],
                "soundcloud_matched": True,
            })
        else:
            sc_missed.append(track["id"])

        if (idx + 1) % 25 == 0:
            print(f"  checked {idx+1}/{total} (sc_matched {len(sc_matched)}, missed {len(sc_missed)})")

        time.sleep(0.25)  # ~4 req/s — polite

    print(f"[soundcloud] SC matched {len(sc_matched)}, still unmatched {len(sc_missed)}")

    # Upsert soundcloud_id + soundcloud_matched into track_features
    BATCH = 200
    updates = [
        {"track_id": m["track_id"], "soundcloud_id": m["soundcloud_id"], "soundcloud_matched": True}
        for m in sc_matched
    ] + [
        {"track_id": tid, "soundcloud_matched": False}
        for tid in sc_missed
    ]

    for i in range(0, len(updates), BATCH):
        sb.table("track_features").upsert(updates[i:i+BATCH], on_conflict="track_id").execute()
        print(f"  updated track_features {min(i+BATCH, len(updates))}/{len(updates)}")

    print("[soundcloud] Done.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich unmatched tracks via SoundCloud")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Check all tracks, not just Spotify-unmatched ones",
    )
    parser.add_argument("--limit", type=int, default=None, help="Max tracks to check")
    args = parser.parse_args()
    enrich_soundcloud(only_unmatched=not args.all, limit=args.limit)


if __name__ == "__main__":
    main()
