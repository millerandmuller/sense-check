"""Shared catalog access for the Vesuvius Challenge open-data catalog.

Used by catalog_orientation.py, write_scroll_spec.py, and
render_axial_slices.py so all three read the catalog and pick the eligible
volume the same way.
"""
from __future__ import annotations

import gzip
import json
import urllib.error
import urllib.request
from typing import Any, Optional

FULL_CATALOG_URL = "https://vesuvius-challenge-open-data.s3.amazonaws.com/metadata.json"
MINIFIED_CATALOG_URL = "https://vesuvius-challenge-open-data.s3.amazonaws.com/metadata.min.json"

# The 23 First Letters eligible volumes.
# 18 have spiral tracks; the other 5 (PHerc1203, PHerc1218, PHerc1447,
# PHerc1545, PHerc0846B) have none and enter catalog-and-render only, but
# catalog lookup and orientation derivation apply to all 23 the same way.
ELIGIBLE_SAMPLES = [
    "PHerc0125", "PHerc0191", "PHerc0211", "PHerc0257", "PHerc0268", "PHerc0358",
    "PHerc0800", "PHerc0813", "PHerc0826", "PHerc0175A", "PHerc0175B", "PHerc0306B",
    "PHerc0343", "PHerc0483A", "PHerc0483B", "PHerc0490A", "PHerc0490B", "PHerc0846A",
    "PHerc1203", "PHerc1218", "PHerc1447", "PHerc1545", "PHerc0846B",
]

# The two eligible scan protocols for First Letters volumes. A handful of
# samples carry an extra, non-eligible high-resolution scan (2.403um/77keV)
# alongside the eligible one; pick_eligible_volume excludes those.
ELIGIBLE_PROTOCOLS = {(9.362, 113.0), (8.640, 116.0)}


def pick_eligible_volume(sample: dict[str, Any]) -> tuple[Optional[str], Optional[dict]]:
    """Return (volume_id, volume) for the First-Letters-eligible scan of a
    sample. Most samples have exactly one volume; a few carry an additional
    non-eligible high-resolution scan, excluded here by protocol."""
    volumes = sample.get("volumes", {})
    if len(volumes) == 1:
        ((vid, v),) = volumes.items()
        return vid, v
    for vid, v in volumes.items():
        p = v.get("properties", {})
        protocol = (round(p.get("pixel_size_um", 0.0), 3), p.get("energy_keV"))
        if protocol in ELIGIBLE_PROTOCOLS:
            return vid, v
    return None, None


def spiral_outward_sense_for(z_direction_is_top_to_bottom: Optional[bool],
                              left_handed_coordinates: Optional[bool]) -> Optional[str]:
    """villa's own rule (surface_orientation.py, f4570bf). Returns None
    (UNDERIVABLE) when either catalog key is missing."""
    if z_direction_is_top_to_bottom is None or left_handed_coordinates is None:
        return None
    return "ACW" if z_direction_is_top_to_bottom != left_handed_coordinates else "CW"


def fetch_raw(url: str) -> tuple[bytes, str, str]:
    """Fetch a URL and gunzip it if needed. Returns (bytes, etag, last_modified)."""
    try:
        with urllib.request.urlopen(url) as resp:  # noqa: S310 - fixed https S3 URL
            raw = resp.read()
            etag = resp.headers.get("ETag", "").strip('"')
            last_modified = resp.headers.get("Last-Modified", "")
    except (urllib.error.URLError, OSError) as e:
        # SystemExit, not RuntimeError, to match this codebase's error-handling
        # convention (see catalog_orientation.py / write_scroll_spec.py): a
        # clean one-line message, no raw traceback, exit code 1.
        raise SystemExit(f"error: could not reach {url} ({e}). Check network "
                          f"connectivity and try again.") from e
    try:
        raw = gzip.decompress(raw)
    except OSError:
        pass  # already plain JSON
    return raw, etag, last_modified


def fetch_catalog(url: str = FULL_CATALOG_URL) -> tuple[dict[str, Any], str, str]:
    raw, etag, last_modified = fetch_raw(url)
    return json.loads(raw), etag, last_modified
