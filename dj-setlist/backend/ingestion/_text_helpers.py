"""
Shared text-parsing helpers for title/artist normalisation and search scoring.
Used by soundcloud_enricher and rekordbox_reader.
"""

from __future__ import annotations

import re

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
