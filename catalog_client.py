"""Shared fetch helper for the Vesuvius Challenge open-data catalog.

Used by catalog_orientation.py and write_scroll_spec.py so both read the
same catalog the same way.
"""
from __future__ import annotations

import gzip
import json
import urllib.request
from typing import Any

FULL_CATALOG_URL = "https://vesuvius-challenge-open-data.s3.amazonaws.com/metadata.json"
MINIFIED_CATALOG_URL = "https://vesuvius-challenge-open-data.s3.amazonaws.com/metadata.min.json"


def fetch_raw(url: str) -> tuple[bytes, str, str]:
    """Fetch a URL and gunzip it if needed. Returns (bytes, etag, last_modified)."""
    with urllib.request.urlopen(url) as resp:  # noqa: S310 - fixed https S3 URL
        raw = resp.read()
        etag = resp.headers.get("ETag", "").strip('"')
        last_modified = resp.headers.get("Last-Modified", "")
    try:
        raw = gzip.decompress(raw)
    except OSError:
        pass  # already plain JSON
    return raw, etag, last_modified


def fetch_catalog(url: str = FULL_CATALOG_URL) -> tuple[dict[str, Any], str, str]:
    raw, etag, last_modified = fetch_raw(url)
    return json.loads(raw), etag, last_modified
