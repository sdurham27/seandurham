"""
Phase 3 — AI Vibe Tagging
===========================
For each un-tagged track, call the Anthropic API with a prompt that includes
all known metadata and asks for structured JSON vibe tags.

Designed to be resumable: skips tracks already present in track_vibes.
Run in chunks to avoid hitting API rate limits.

Output schema per track:
  vibe_tags:    string[]  e.g. ["dark", "hypnotic", "late night"]
  energy_level: int 1–10
  mood:         string    e.g. "euphoric"
  best_for:     string[]  e.g. ["closing set", "peak hour"]
  vetted:       bool      false if play_count==0 and rating==0

Usage:
    python -m ingestion.ai_tagger
    python -m ingestion.ai_tagger --chunk 100 --offset 0
    python -m ingestion.ai_tagger --chunk 100 --offset 100
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an expert DJ and music analyst. Given track metadata and audio features,
return a JSON object describing the track's vibe for DJ use.

Respond ONLY with valid JSON — no markdown fences, no explanation.
Required fields:
  "vibe_tags":    array of 3–6 lowercase string tags (e.g. "dark", "hypnotic", "peak floor")
  "energy_level": integer 1 (lowest) to 10 (highest)
  "mood":         single lowercase string (e.g. "euphoric", "melancholy", "groovy")
  "best_for":     array of 1–3 context strings from: ["warmup", "peak hour", "closing set",
                  "after hours", "daytime", "sunrise", "crowd builder", "dancefloor filler"]
  "vetted":       boolean — true if the track has plays OR a star rating, false otherwise
"""


def _build_user_message(track: dict, features: Optional[dict]) -> str:
    parts = [
        f"Title: {track.get('title', 'Unknown')}",
        f"Artist: {track.get('artist', 'Unknown')}",
        f"Album: {track.get('album', '') or 'Unknown'}",
        f"Genre: {track.get('genre', '') or 'Unknown'}",
        f"BPM: {track.get('bpm', 'Unknown')}",
        f"Key (Camelot): {track.get('camelot_key', 'Unknown')}",
        f"Play count: {track.get('play_count', 0)}",
        f"Star rating: {track.get('rating', 0)}/5",
    ]
    if features and features.get("matched"):
        parts += [
            f"Valence (happiness): {features.get('valence', 'N/A')}",
            f"Energy: {features.get('energy', 'N/A')}",
            f"Danceability: {features.get('danceability', 'N/A')}",
            f"Acousticness: {features.get('acousticness', 'N/A')}",
            f"Instrumentalness: {features.get('instrumentalness', 'N/A')}",
            f"Spotify tempo: {features.get('tempo', 'N/A')}",
        ]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Anthropic call with retry
# ---------------------------------------------------------------------------

@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=2, min=2, max=30))
def _call_claude(client, track: dict, features: Optional[dict]) -> dict:
    user_msg = _build_user_message(track, features)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = response.content[0].text.strip()
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def _fetch_untagged_tracks(sb, chunk: int, offset: int) -> list[dict]:
    """Tracks that exist in `tracks` but not yet in `track_vibes`."""
    tagged_resp = sb.table("track_vibes").select("track_id").execute()
    tagged_ids = {r["track_id"] for r in tagged_resp.data}

    resp = (
        sb.table("tracks")
        .select("id,title,artist,album,genre,bpm,camelot_key,play_count,rating")
        .range(offset, offset + chunk - 1)
        .execute()
    )
    return [t for t in resp.data if t["id"] not in tagged_ids]


def _fetch_features_for(sb, track_ids: list[str]) -> dict[str, dict]:
    """Return {track_id: features_row} for the given track IDs."""
    resp = sb.table("track_features").select("*").in_("track_id", track_ids).execute()
    return {r["track_id"]: r for r in resp.data}


def tag(chunk: int = 50, offset: int = 0) -> None:
    load_dotenv(Path(__file__).parent.parent.parent / ".env")

    import anthropic
    from supabase import create_client

    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    tracks = _fetch_untagged_tracks(sb, chunk, offset)
    if not tracks:
        print("[ai_tagger] No untagged tracks in this range.")
        return

    track_ids = [t["id"] for t in tracks]
    features_map = _fetch_features_for(sb, track_ids)

    print(f"[ai_tagger] Tagging {len(tracks)} tracks (offset={offset})…")

    rows_to_insert: list[dict] = []
    errors: list[str] = []

    for idx, track in enumerate(tracks):
        features = features_map.get(track["id"])
        try:
            result = _call_claude(client, track, features)
            # Validate / sanitise
            vibe_tags = result.get("vibe_tags", [])
            energy_level = max(1, min(10, int(result.get("energy_level", 5))))
            mood = str(result.get("mood", "unknown"))
            best_for = result.get("best_for", [])
            vetted = bool(result.get("vetted", track.get("play_count", 0) > 0 or track.get("rating", 0) > 0))

            rows_to_insert.append({
                "track_id": track["id"],
                "vibe_tags": vibe_tags,
                "energy_level": energy_level,
                "mood": mood,
                "best_for": best_for,
                "vetted": vetted,
            })
        except json.JSONDecodeError as exc:
            errors.append(track["id"])
            print(f"  [warn] JSON parse failed for track {track['id']} ({track['title']}): {exc}")
        except Exception as exc:
            errors.append(track["id"])
            print(f"  [warn] Claude error for track {track['id']} ({track['title']}): {exc}")

        if (idx + 1) % 10 == 0:
            print(f"  tagged {idx+1}/{len(tracks)}")

        # Rate-limit courtesy sleep (~3 req/s to stay within Anthropic limits)
        time.sleep(0.35)

    # Upsert results
    BATCH = 100
    for i in range(0, len(rows_to_insert), BATCH):
        sb.table("track_vibes").upsert(rows_to_insert[i:i+BATCH], on_conflict="track_id").execute()
        print(f"  upserted track_vibes {min(i+BATCH, len(rows_to_insert))}/{len(rows_to_insert)}")

    print(f"[ai_tagger] Done. Tagged {len(rows_to_insert)}, errors {len(errors)}.")
    if errors:
        print(f"  Failed track IDs: {errors[:20]}{'…' if len(errors)>20 else ''}")


def main() -> None:
    parser = argparse.ArgumentParser(description="AI vibe-tag tracks via Claude")
    parser.add_argument("--chunk", type=int, default=50, help="Tracks per run (default 50)")
    parser.add_argument("--offset", type=int, default=0, help="Skip first N tracks")
    args = parser.parse_args()
    tag(chunk=args.chunk, offset=args.offset)


if __name__ == "__main__":
    main()
