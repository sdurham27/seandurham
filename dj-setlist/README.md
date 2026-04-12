# DJ Setlist AI

AI-powered setlist generator for rekordbox libraries. Enriches your library with Spotify audio features and Claude vibe tags, then generates intelligent, harmonically-sequenced setlists for any event.

---

## Architecture

```
dj-setlist/
├── backend/
│   ├── ingestion/
│   │   ├── rekordbox_reader.py  # Phase 0: pyrekordbox + XML fallback + diff sync
│   │   ├── ingest.py            # Phase 1: library → Supabase
│   │   ├── spotify_enricher.py  # Phase 2: Spotify audio features
│   │   └── ai_tagger.py         # Phase 3: Claude vibe tags
│   ├── api/
│   │   └── main.py              # FastAPI server (setlist generator + export)
│   ├── migrations/
│   │   └── 001_initial_schema.sql
│   └── requirements.txt
├── frontend/                    # React + Vite
│   └── src/
│       ├── App.tsx
│       ├── components/
│       └── lib/api.ts
└── .env.example
```

---

## Setup

### 1. Copy `.env`

```bash
cp .env.example .env
# Fill in: SUPABASE_URL, SUPABASE_SERVICE_KEY, SPOTIFY_CLIENT_ID,
#          SPOTIFY_CLIENT_SECRET, ANTHROPIC_API_KEY
```

### 2. Supabase schema

Run `backend/migrations/001_initial_schema.sql` in your Supabase SQL editor.

### 3. Python backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Run ingestion pipeline

```bash
# Phase 0 + 1: ingest library
python -m ingestion.ingest

# If pyrekordbox can't open master.db, export from rekordbox:
#   File → Export Collection in xml format
# Then:
REKORDBOX_XML_PATH=/path/to/collection.xml python -m ingestion.ingest

# Phase 2: Spotify enrichment (batched, resumable)
python -m ingestion.spotify_enricher

# Phase 3: AI vibe tagging (run in chunks of 50)
python -m ingestion.ai_tagger --chunk 50 --offset 0
python -m ingestion.ai_tagger --chunk 50 --offset 50
# ...repeat until done
```

### 5. Start the API server

```bash
uvicorn api.main:app --reload --port 8000
```

### 6. Start the frontend

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

---

## Data model

| Table | Description |
|-------|-------------|
| `tracks` | Core library: title, artist, BPM, Camelot key, rating, etc. |
| `track_features` | Spotify: valence, energy, danceability, acousticness, instrumentalness, tempo |
| `track_vibes` | Claude: vibe_tags[], energy_level 1-10, mood, best_for[], vetted |

---

## Camelot wheel compatibility

Transitions are flagged as compatible if:
- Same key (e.g. 8A → 8A)
- Same number, adjacent letter (e.g. 8A → 8B, relative major/minor)
- Same letter, adjacent number (e.g. 8A → 7A or 9A)
- Wrap-around: 1A ↔ 12A (or B)

---

## Vetted vs unvetted

Tracks with **0 plays and 0 star rating** are marked `vetted=false`. The setlist generator excludes them by default and surfaces 2-3 as "wildcards" when the vibe profile matches high-rated tracks.

> Note: play counts are not used as a quality signal — many high-quality tracks were imported but never played in rekordbox.
