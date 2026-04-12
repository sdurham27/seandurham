"""
Phase 0 — rekordbox Library Access
===================================
Primary:  pyrekordbox (reads the encrypted master.db directly)
Fallback: XML export (File → Export Collection in rekordbox)

Also handles diff-based sync — only re-ingest tracks that are new or changed.
"""

from __future__ import annotations

import os
import platform
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Optional


# ---------------------------------------------------------------------------
# Title / artist normalisation
# ---------------------------------------------------------------------------

# Matches common "Artist - Title" separators (hyphen, en-dash, em-dash)
_TITLE_SEP_RE = re.compile(r'\s+[-–—]\s+')

# Matches feat./ft./featuring suffixes inside title or artist strings
_FEAT_RE = re.compile(
    r'\s*[\(\[]?(?:feat\.?|ft\.?|featuring)\s+[^\)\]]+[\)\]]?',
    re.IGNORECASE,
)


def _parse_artist_title(raw_title: str, raw_artist: str) -> tuple[str, str]:
    """
    Normalise title and artist fields from rekordbox metadata.

    Handles cases where:
    - The artist is embedded in the title as "Artist - Track Title"
    - The title contains feat./ft. guest artist info
    - Artist field is duplicated in the title ("Artist - Track", artist="Artist")

    Returns (clean_title, clean_artist). Does NOT split multi-artist strings —
    those are preserved as-is for Spotify search to handle.
    """
    title = raw_title.strip()
    artist = raw_artist.strip()

    # Case 1: artist field is blank and title contains "Something - Something"
    # → treat left side as artist, right side as title
    if not artist and _TITLE_SEP_RE.search(title):
        parts = _TITLE_SEP_RE.split(title, maxsplit=1)
        if len(parts) == 2:
            artist = parts[0].strip()
            title = parts[1].strip()

    # Case 2: artist IS set but the title also starts with the artist name
    # e.g. title="DJ Koze - Track Name", artist="DJ Koze"
    # Strip the leading "Artist - " prefix from the title
    elif artist and _TITLE_SEP_RE.search(title):
        parts = _TITLE_SEP_RE.split(title, maxsplit=1)
        if len(parts) == 2:
            left = parts[0].strip()
            # Only strip if the left segment matches the artist (or is contained in it)
            if (left.lower() == artist.lower()
                    or left.lower() in artist.lower()
                    or artist.lower() in left.lower()):
                title = parts[1].strip()

    return title, artist


# ---------------------------------------------------------------------------
# Camelot wheel conversion
# ---------------------------------------------------------------------------

# rekordbox stores keys as e.g. "1A", "7B" — this maps the raw key string to
# Camelot notation (they already match).  Rekordbox numeric keys (0–23) also
# need mapping.
_MUSICAL_KEY_TO_CAMELOT: dict[str, str] = {
    # Majors
    "Cmaj": "8B",  "C major": "8B",
    "Dbmaj": "3B", "C#maj": "3B", "Db major": "3B", "C# major": "3B",
    "Dmaj": "10B", "D major": "10B",
    "Ebmaj": "5B", "D#maj": "5B", "Eb major": "5B", "D# major": "5B",
    "Emaj": "12B", "E major": "12B",
    "Fmaj": "7B",  "F major": "7B",
    "F#maj": "2B", "Gbmaj": "2B", "F# major": "2B", "Gb major": "2B",
    "Gmaj": "9B",  "G major": "9B",
    "Abmaj": "4B", "G#maj": "4B", "Ab major": "4B", "G# major": "4B",
    "Amaj": "11B", "A major": "11B",
    "Bbmaj": "6B", "A#maj": "6B", "Bb major": "6B", "A# major": "6B",
    "Bmaj": "1B",  "B major": "1B",
    # Minors
    "Amin": "8A",  "A minor": "8A",
    "Bmin": "3A",  "B minor": "3A",
    "Bbmin": "6A", "A#min": "6A", "Bb minor": "6A", "A# minor": "6A",
    "Cmin": "5A",  "C minor": "5A",
    "C#min": "12A","Dbmin": "12A", "C# minor": "12A", "Db minor": "12A",
    "Dmin": "7A",  "D minor": "7A",
    "D#min": "2A", "Ebmin": "2A", "D# minor": "2A", "Eb minor": "2A",
    "Emin": "9A",  "E minor": "9A",
    "Fmin": "4A",  "F minor": "4A",
    "F#min": "11A","Gbmin": "11A", "F# minor": "11A", "Gb minor": "11A",
    "Gmin": "6A",  "G minor": "6A",  # note: same number, distinct letter
    "G#min": "1A", "Abmin": "1A", "G# minor": "1A", "Ab minor": "1A",
}

# rekordbox IDKey values (0-based numeric) → Camelot
_ID_KEY_MAP: list[str] = [
    "8B", "3B", "10B", "5B", "12B", "7B", "2B", "9B", "4B", "11B", "6B", "1B",
    "8A", "3A", "10A", "5A", "12A", "7A", "2A", "9A", "4A", "11A", "6A", "1A",
]


def to_camelot(raw_key: str | int | None) -> Optional[str]:
    """Convert a rekordbox key value to Camelot wheel notation."""
    if raw_key is None:
        return None
    if isinstance(raw_key, int):
        if 0 <= raw_key < len(_ID_KEY_MAP):
            return _ID_KEY_MAP[raw_key]
        return None
    raw = str(raw_key).strip()
    # Already in Camelot format (e.g. "8A", "12B")
    if re.match(r"^(1[0-2]|[1-9])[AB]$", raw):
        return raw
    return _MUSICAL_KEY_TO_CAMELOT.get(raw)


# ---------------------------------------------------------------------------
# Track dataclass — normalised representation used by all phases
# ---------------------------------------------------------------------------

@dataclass
class Track:
    title: str
    artist: str
    album: str = ""
    genre: str = ""
    bpm: Optional[float] = None
    camelot_key: Optional[str] = None
    play_count: int = 0
    date_added: Optional[str] = None   # ISO date string
    rating: int = 0                    # 0–255 in rekordbox; normalise 0–5
    file_path: str = ""
    # populated by enrichment phases
    source_id: Optional[str] = None    # rekordbox internal ID (str)

    # helper so dicts work as DB rows
    def as_dict(self) -> dict:
        return {
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "genre": self.genre,
            "bpm": self.bpm,
            "camelot_key": self.camelot_key,
            "play_count": self.play_count,
            "date_added": self.date_added,
            "rating": self.rating,
            "file_path": self.file_path,
            "source_id": self.source_id,
        }


# ---------------------------------------------------------------------------
# Auto-detect master.db path
# ---------------------------------------------------------------------------

def _detect_masterdb_path() -> Optional[Path]:
    """Return the path to rekordbox master.db, or None if not found."""
    system = platform.system()
    candidates: list[Path] = []

    if system == "Darwin":  # macOS
        home = Path.home()
        candidates = [
            home / "Library/Pioneer/rekordbox/master.db",
            home / "Library/Application Support/Pioneer/rekordbox/master.db",
            home / "Library/Pioneer/rekordbox6/master.db",
        ]
    elif system == "Windows":
        appdata = Path(os.environ.get("APPDATA", "C:/Users/Public/AppData/Roaming"))
        localappdata = Path(os.environ.get("LOCALAPPDATA", "C:/Users/Public/AppData/Local"))
        candidates = [
            appdata / "Pioneer/rekordbox/master.db",
            localappdata / "Pioneer/rekordbox/master.db",
            Path("C:/Users") / os.environ.get("USERNAME", "user") / "AppData/Roaming/Pioneer/rekordbox/master.db",
        ]
    else:
        # Linux (rare but possible via Wine)
        home = Path.home()
        candidates = [
            home / ".wine/drive_c/users" / os.environ.get("USER", "user") / "AppData/Roaming/Pioneer/rekordbox/master.db",
        ]

    for path in candidates:
        if path.exists():
            return path
    return None


# ---------------------------------------------------------------------------
# Primary reader: pyrekordbox
# ---------------------------------------------------------------------------

def _normalise_rating(raw: int | None) -> int:
    """Convert rekordbox 0-255 rating to 0-5 stars."""
    if not raw:
        return 0
    if raw >= 204:
        return 5
    if raw >= 153:
        return 4
    if raw >= 102:
        return 3
    if raw >= 51:
        return 2
    if raw > 0:
        return 1
    return 0


def read_via_pyrekordbox(db_path: Optional[str] = None) -> list[Track]:
    """
    Open the rekordbox library via pyrekordbox and return a list of Tracks.
    Raises ImportError if pyrekordbox is not installed, or Exception if the
    DB cannot be opened (locked, missing, wrong version).
    """
    import pyrekordbox  # noqa: F401 — let ImportError propagate naturally
    from pyrekordbox import Rekordbox6Database

    if db_path:
        db = Rekordbox6Database(db_path)
    else:
        detected = _detect_masterdb_path()
        if detected:
            db = Rekordbox6Database(str(detected))
        else:
            db = Rekordbox6Database()  # let pyrekordbox auto-detect

    tracks: list[Track] = []
    for content in db.get_content():
        try:
            artist_name = ""
            if hasattr(content, "Artist") and content.Artist:
                artist_name = content.Artist.Name or ""

            album_name = ""
            if hasattr(content, "Album") and content.Album:
                album_name = content.Album.Name or ""

            genre_name = ""
            if hasattr(content, "Genre") and content.Genre:
                genre_name = content.Genre.Name or ""

            raw_key = getattr(content, "IDKey", None) or getattr(content, "Tonality", None)
            camelot = to_camelot(raw_key)

            bpm_val = getattr(content, "BPM", None)
            if bpm_val is not None:
                # pyrekordbox sometimes stores BPM * 100
                if bpm_val > 500:
                    bpm_val = round(bpm_val / 100, 2)
                else:
                    bpm_val = round(float(bpm_val), 2)

            date_added = None
            raw_date = getattr(content, "DateAdded", None) or getattr(content, "StockDate", None)
            if raw_date:
                date_added = str(raw_date)[:10]  # keep YYYY-MM-DD

            title, artist_name = _parse_artist_title(content.Title or "", artist_name)

            tracks.append(Track(
                title=title,
                artist=artist_name,
                album=album_name,
                genre=genre_name,
                bpm=bpm_val,
                camelot_key=camelot,
                play_count=int(getattr(content, "PlayCount", 0) or 0),
                date_added=date_added,
                rating=_normalise_rating(getattr(content, "Rating", 0)),
                file_path=getattr(content, "FolderPath", "") or getattr(content, "FilePath", "") or "",
                source_id=str(content.ID) if hasattr(content, "ID") else None,
            ))
        except Exception as exc:
            print(f"[warn] skipping track (parse error): {exc}")
            continue

    return tracks


# ---------------------------------------------------------------------------
# Fallback reader: XML export
# ---------------------------------------------------------------------------

def read_via_xml(xml_path: str) -> list[Track]:
    """
    Parse a rekordbox XML collection export.
    The format is: <DJ_PLAYLISTS><COLLECTION><TRACK .../></COLLECTION></DJ_PLAYLISTS>
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    collection = root.find("COLLECTION")
    if collection is None:
        raise ValueError(f"No <COLLECTION> element found in {xml_path}")

    tracks: list[Track] = []
    for elem in collection.findall("TRACK"):
        raw_key = elem.get("Tonality") or elem.get("KeyID")
        camelot = to_camelot(int(raw_key) if raw_key and raw_key.isdigit() else raw_key)

        bpm_str = elem.get("AverageBpm") or elem.get("Bpm")
        bpm_val = round(float(bpm_str), 2) if bpm_str else None

        rating_raw = int(elem.get("Rating", 0) or 0)
        # XML rating is 0-255
        rating = _normalise_rating(rating_raw)

        date_added = elem.get("DateAdded") or elem.get("StockDate")
        if date_added:
            date_added = date_added[:10]

        raw_title = elem.get("Name", "")
        raw_artist = elem.get("Artist", "")
        title, artist = _parse_artist_title(raw_title, raw_artist)

        tracks.append(Track(
            title=title,
            artist=artist,
            album=elem.get("Album", ""),
            genre=elem.get("Genre", ""),
            bpm=bpm_val,
            camelot_key=camelot,
            play_count=int(elem.get("PlayCount", 0) or 0),
            date_added=date_added,
            rating=rating,
            file_path=elem.get("Location", "").replace("file://localhost", ""),
            source_id=elem.get("TrackID"),
        ))

    return tracks


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

class LibrarySource:
    """
    Manages library access with automatic fallback and diff-based sync.
    Usage:
        src = LibrarySource()
        tracks = src.load()          # all tracks
        new_ids = src.diff(known)    # source_ids not yet in `known`
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        xml_path: Optional[str] = None,
    ):
        self.db_path = db_path or os.environ.get("REKORDBOX_DB_PATH") or None
        self.xml_path = xml_path or os.environ.get("REKORDBOX_XML_PATH") or None
        self._mode: Optional[str] = None  # "db" or "xml"

    def load(self) -> list[Track]:
        """Load all tracks from the best available source."""
        # 1. Try pyrekordbox
        try:
            tracks = read_via_pyrekordbox(self.db_path)
            self._mode = "db"
            print(f"[rekordbox] Loaded {len(tracks)} tracks via pyrekordbox (master.db)")
            return tracks
        except ImportError:
            print("[rekordbox] pyrekordbox not installed — falling back to XML")
        except Exception as exc:
            print(f"[rekordbox] master.db unavailable ({exc}) — falling back to XML")

        # 2. Fallback: XML
        xml = self.xml_path
        if not xml:
            raise RuntimeError(
                "Could not open rekordbox master.db.\n"
                "Please export your collection from rekordbox:\n"
                "  File → Export Collection in xml format\n"
                "Then set REKORDBOX_XML_PATH in your .env file."
            )
        tracks = read_via_xml(xml)
        self._mode = "xml"
        print(f"[rekordbox] Loaded {len(tracks)} tracks via XML export")
        return tracks

    def diff(self, known_source_ids: set[str]) -> list[Track]:
        """Return only tracks whose source_id is not in known_source_ids."""
        all_tracks = self.load()
        new = [t for t in all_tracks if t.source_id not in known_source_ids]
        print(f"[sync] {len(new)} new / changed tracks to ingest (total {len(all_tracks)})")
        return new
