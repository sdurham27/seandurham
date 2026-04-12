"""
Spotify enrichment has been removed.
Spotify's Web API now requires a Premium account, which isn't practical
for this use case. Track verification is handled by soundcloud_enricher.py.
"""

raise SystemExit(
    "Spotify enrichment is disabled. Run soundcloud_enricher instead:\n"
    "  python -m ingestion.soundcloud_enricher"
)
