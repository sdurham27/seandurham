"""
FastAPI backend — DJ Setlist AI
================================
Endpoints:
  GET  /api/library/status          — track counts, enrichment coverage
  POST /api/setlist/generate         — generate a setlist with Claude
  POST /api/setlist/export           — export setlist as rekordbox XML
  GET  /api/tracks                   — paginated, filterable track list
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

load_dotenv(Path(__file__).parent.parent.parent / ".env")

app = FastAPI(title="DJ Setlist AI", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_sb():
    from supabase import create_client
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def get_anthropic():
    import anthropic
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class SetlistRequest(BaseModel):
    duration_minutes: int = 60
    genre_focus: str = ""
    vibe_goal: str = ""
    time_of_night: str = "peak"       # warmup | peak | closing
    include_unvetted: bool = False
    track_count_hint: Optional[int] = None


class SetlistExportRequest(BaseModel):
    playlist_name: str
    tracks: list[dict]   # [{id, title, artist, ...}]


# ---------------------------------------------------------------------------
# Camelot compatibility
# ---------------------------------------------------------------------------

def camelot_compatible(key_a: Optional[str], key_b: Optional[str]) -> bool:
    """Return True if key_b is a compatible transition from key_a."""
    if not key_a or not key_b:
        return True  # unknown — allow
    try:
        num_a = int(key_a[:-1])
        letter_a = key_a[-1]
        num_b = int(key_b[:-1])
        letter_b = key_b[-1]
    except (ValueError, IndexError):
        return True

    # Same key = always compatible
    if key_a == key_b:
        return True
    # Adjacent number, same letter (e.g. 8A → 7A or 9A)
    if letter_a == letter_b and abs(num_a - num_b) == 1:
        return True
    # Wrap-around (1↔12)
    if letter_a == letter_b and {num_a, num_b} == {1, 12}:
        return True
    # Same number, different letter (relative major/minor e.g. 8A → 8B)
    if num_a == num_b and letter_a != letter_b:
        return True
    return False


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/library/status")
async def library_status():
    sb = get_sb()
    tracks_count = sb.table("tracks").select("id", count="exact").execute().count
    enriched_count = sb.table("track_features").select("track_id", count="exact").eq("matched", True).execute().count
    tagged_count = sb.table("track_vibes").select("track_id", count="exact").execute().count
    return {
        "total_tracks": tracks_count,
        "spotify_enriched": enriched_count,
        "ai_tagged": tagged_count,
    }


@app.get("/api/tracks")
async def list_tracks(
    page: int = 1,
    per_page: int = 50,
    genre: str = "",
    vetted_only: bool = False,
):
    sb = get_sb()
    offset = (page - 1) * per_page
    q = (
        sb.table("tracks")
        .select("*, track_features(*), track_vibes(*)")
        .range(offset, offset + per_page - 1)
    )
    if genre:
        q = q.ilike("genre", f"%{genre}%")
    resp = q.execute()
    tracks = resp.data

    if vetted_only:
        tracks = [t for t in tracks if (t.get("track_vibes") or [{}])[0].get("vetted", True)]

    return {"tracks": tracks, "page": page, "per_page": per_page}


@app.post("/api/setlist/generate")
async def generate_setlist(req: SetlistRequest):
    sb = get_sb()
    client = get_anthropic()

    # Estimate number of tracks: average ~6 min/track
    track_count = req.track_count_hint or max(5, req.duration_minutes // 6)

    # Fetch candidate tracks (joined with vibes + features)
    candidate_query = (
        sb.table("tracks")
        .select("id, title, artist, genre, bpm, camelot_key, rating, play_count, track_features(*), track_vibes(*)")
        .limit(600)
    )
    if req.genre_focus:
        candidate_query = candidate_query.ilike("genre", f"%{req.genre_focus}%")
    if not req.include_unvetted:
        # We'll filter client-side from vibes.vetted
        pass

    resp = candidate_query.execute()
    candidates = resp.data

    # Filter out unvetted if toggled off
    if not req.include_unvetted:
        def is_vetted(t):
            vibes = (t.get("track_vibes") or [{}])
            v = vibes[0] if vibes else {}
            return v.get("vetted", True)
        candidates = [t for t in candidates if is_vetted(t)]

    if len(candidates) < 5:
        raise HTTPException(status_code=400, detail="Not enough candidate tracks. Try enabling unvetted tracks or broadening genre.")

    # Build a compact candidate list for the prompt (keep token count manageable)
    def _candidate_summary(t: dict) -> dict:
        vibes = (t.get("track_vibes") or [{}])
        v = vibes[0] if vibes else {}
        feats = (t.get("track_features") or [{}])
        f = feats[0] if feats else {}
        return {
            "id": t["id"],
            "title": t["title"],
            "artist": t["artist"],
            "genre": t.get("genre", ""),
            "bpm": t.get("bpm"),
            "key": t.get("camelot_key"),
            "rating": t.get("rating", 0),
            "plays": t.get("play_count", 0),
            "energy_level": v.get("energy_level"),
            "mood": v.get("mood"),
            "vibe_tags": v.get("vibe_tags", []),
            "best_for": v.get("best_for", []),
            "vetted": v.get("vetted", True),
            "valence": f.get("valence"),
            "energy": f.get("energy"),
            "danceability": f.get("danceability"),
        }

    summaries = [_candidate_summary(t) for t in candidates]

    system_prompt = """You are an expert DJ curator. Given a pool of candidate tracks and an event
description, select and sequence a setlist.

Rules:
1. Match the vibe/mood goal described by the user
2. Follow a logical energy arc appropriate for the set type (warmup=gradual build,
   peak=sustained high energy, closing=build then wind down)
3. Sequence tracks for harmonic compatibility using Camelot wheel logic:
   compatible transitions = same number adjacent letter, same letter adjacent number,
   same number different letter (relative major/minor), or wrap 1↔12
4. Avoid placing more than 2 unvetted tracks in a row
5. Include 2-3 "wildcard" picks — tracks with low play_count but strong features/tags
   that are stylistically similar to high-rated tracks

Respond ONLY with valid JSON (no markdown):
{
  "tracks": [
    { "id": "<track_id>", "reason": "<1 sentence why this track fits here>" }
  ],
  "arc_description": "<2 sentence description of the energy arc>"
}
"""

    user_msg = f"""Event details:
- Set duration: {req.duration_minutes} minutes (~{track_count} tracks)
- Genre focus: {req.genre_focus or 'open format'}
- Vibe/mood goal: {req.vibe_goal or 'not specified'}
- Time of night: {req.time_of_night}
- Include unvetted tracks: {req.include_unvetted}

Please select and sequence exactly {track_count} tracks from the candidates below.

Candidate tracks (JSON):
{summaries[:300]}
"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_msg}],
    )

    import json
    raw = response.content[0].text.strip()
    result = json.loads(raw)

    # Hydrate with full track data
    id_to_track = {t["id"]: t for t in candidates}
    setlist = []
    for item in result.get("tracks", []):
        track = id_to_track.get(item["id"])
        if track:
            vibes = (track.get("track_vibes") or [{}])
            v = vibes[0] if vibes else {}
            feats = (track.get("track_features") or [{}])
            f = feats[0] if feats else {}
            setlist.append({
                **{k: track[k] for k in ["id", "title", "artist", "genre", "bpm", "camelot_key", "rating", "play_count"]},
                "energy_level": v.get("energy_level"),
                "mood": v.get("mood"),
                "vibe_tags": v.get("vibe_tags", []),
                "best_for": v.get("best_for", []),
                "vetted": v.get("vetted", True),
                "valence": f.get("valence"),
                "energy": f.get("energy"),
                "reason": item.get("reason", ""),
            })

    return {
        "setlist": setlist,
        "arc_description": result.get("arc_description", ""),
        "duration_minutes": req.duration_minutes,
        "event": {
            "genre_focus": req.genre_focus,
            "vibe_goal": req.vibe_goal,
            "time_of_night": req.time_of_night,
        },
    }


@app.post("/api/setlist/export")
async def export_setlist(req: SetlistExportRequest):
    """Generate a rekordbox-importable XML playlist."""
    root = ET.Element("DJ_PLAYLISTS", Version="1.0.0")
    product = ET.SubElement(root, "PRODUCT", Name="rekordbox", Version="6.0.0", Company="AlphaTheta")

    collection = ET.SubElement(root, "COLLECTION", Entries=str(len(req.tracks)))
    for i, track in enumerate(req.tracks):
        ET.SubElement(collection, "TRACK",
            TrackID=str(track.get("id", i + 1)),
            Name=track.get("title", ""),
            Artist=track.get("artist", ""),
            Genre=track.get("genre", ""),
            AverageBpm=str(track.get("bpm") or ""),
            Tonality=track.get("camelot_key", ""),
        )

    playlists = ET.SubElement(root, "PLAYLISTS")
    root_node = ET.SubElement(playlists, "NODE", Type="0", Name="ROOT", Count="1")
    playlist_node = ET.SubElement(root_node, "NODE",
        Name=req.playlist_name,
        Type="1",
        KeyType="0",
        Entries=str(len(req.tracks)),
    )
    for i, track in enumerate(req.tracks):
        ET.SubElement(playlist_node, "TRACK", Key=str(track.get("id", i + 1)))

    ET.indent(root)
    xml_bytes = b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode").encode()

    filename = req.playlist_name.replace(" ", "_") + ".xml"
    return Response(
        content=xml_bytes,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
