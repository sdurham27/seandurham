"""
Phase 1 — Library Ingestion
=============================
Reads the rekordbox library (via pyrekordbox or XML fallback) and upserts
tracks into the Supabase `tracks` table.

Usage:
    python -m ingestion.ingest              # full sync
    python -m ingestion.ingest --diff-only  # only new/changed tracks
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Allow running as a script from backend/
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.rekordbox_reader import LibrarySource, Track


def get_supabase_client():
    from supabase import create_client
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)


def fetch_known_source_ids(sb) -> set[str]:
    """Return all source_ids already in the tracks table."""
    resp = sb.table("tracks").select("source_id").execute()
    return {row["source_id"] for row in resp.data if row.get("source_id")}


def upsert_tracks(sb, tracks: list[Track]) -> None:
    """Upsert a list of tracks into Supabase in batches."""
    BATCH = 200
    total = len(tracks)
    for i in range(0, total, BATCH):
        batch = tracks[i : i + BATCH]
        rows = [t.as_dict() for t in batch]
        sb.table("tracks").upsert(rows, on_conflict="source_id").execute()
        print(f"  upserted {min(i + BATCH, total)}/{total}")


def main() -> None:
    load_dotenv(Path(__file__).parent.parent.parent / ".env")

    parser = argparse.ArgumentParser(description="Ingest rekordbox library into Supabase")
    parser.add_argument("--diff-only", action="store_true", help="Only ingest new/changed tracks")
    parser.add_argument("--db-path", help="Override rekordbox master.db path")
    parser.add_argument("--xml-path", help="Override rekordbox XML export path")
    args = parser.parse_args()

    sb = get_supabase_client()
    src = LibrarySource(db_path=args.db_path, xml_path=args.xml_path)

    if args.diff_only:
        known = fetch_known_source_ids(sb)
        tracks = src.diff(known)
    else:
        tracks = src.load()

    if not tracks:
        print("[ingest] Nothing to ingest.")
        return

    print(f"[ingest] Upserting {len(tracks)} tracks…")
    upsert_tracks(sb, tracks)
    print("[ingest] Done.")


if __name__ == "__main__":
    main()
