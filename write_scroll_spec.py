#!/usr/bin/env python3
"""Write a spiral-scroll.json for one catalog volume.

For a derivable volume (both catalog orientation keys present), the spec
carries the catalog keys and the fitter derives the sense itself. For an
UNDERIVABLE volume, this script refuses to write a spec unless a human
reading is supplied via --sense and --reading-ref, and stores the reference
in the output for provenance (an unknown top-level key, ignored by
fit_session.parse_scroll_spec but readable by anyone checking the file).

Usage:
    python3 write_scroll_spec.py <scroll> <volume> [--sense CW|ACW --reading-ref TEXT]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

from catalog_client import FULL_CATALOG_URL, fetch_catalog

SCHEMA_VERSION = 1


def find_volume(catalog: dict[str, Any], scroll: str, volume: str) -> dict[str, Any]:
    sample = catalog["samples"].get(scroll)
    if sample is None:
        raise SystemExit(f"error: sample {scroll!r} not found in catalog")
    v = sample.get("volumes", {}).get(volume)
    if v is None:
        available = sorted(sample.get("volumes", {}))
        raise SystemExit(
            f"error: volume {volume!r} not found for {scroll!r}; available: {available}")
    return v


def spiral_outward_sense_for(z_direction_is_top_to_bottom: Optional[bool],
                              left_handed_coordinates: Optional[bool]) -> Optional[str]:
    if z_direction_is_top_to_bottom is None or left_handed_coordinates is None:
        return None
    return "ACW" if z_direction_is_top_to_bottom != left_handed_coordinates else "CW"


def build_spec(scroll: str, volume_id: str, props: dict[str, Any],
                sense_override: Optional[str], reading_ref: Optional[str]) -> dict[str, Any]:
    voxel_size_um = props.get("pixel_size_um")
    if voxel_size_um is None:
        raise SystemExit(f"error: {scroll}/{volume_id} has no pixel_size_um in the catalog")

    z_top = props.get("z_direction_is_top_to_bottom")
    left_handed = props.get("left_handed_coordinates")
    catalog_sense = spiral_outward_sense_for(z_top, left_handed)

    if catalog_sense is None:
        if sense_override is None or reading_ref is None:
            raise SystemExit(
                f"error: {scroll}/{volume_id} is UNDERIVABLE from the catalog "
                f"(z_direction_is_top_to_bottom={z_top}, left_handed_coordinates={left_handed}). "
                "Refusing to write a spec without a human reading: pass both "
                "--sense {CW,ACW} and --reading-ref <where the reading is recorded>."
            )
        sense = sense_override
    else:
        if sense_override is not None and sense_override != catalog_sense:
            raise SystemExit(
                f"error: --sense {sense_override} contradicts the catalog "
                f"(z_direction_is_top_to_bottom={z_top}, left_handed_coordinates={left_handed} "
                f"gives {catalog_sense})"
            )
        sense = catalog_sense

    spec: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "name": scroll,
        "voxel_size_um": voxel_size_um,
        "spiral_outward_sense": sense,
    }
    if z_top is not None:
        spec["z_direction_is_top_to_bottom"] = z_top
    if left_handed is not None:
        spec["left_handed_coordinates"] = left_handed
    if reading_ref is not None:
        spec["reading_reference"] = reading_ref
    return spec


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scroll", help="Sample id, e.g. PHerc0826")
    parser.add_argument("volume", help="Volume id, e.g. 20250821151701")
    parser.add_argument("--sense", choices=["CW", "ACW"], default=None,
                         help="Human reading, required for an UNDERIVABLE volume")
    parser.add_argument("--reading-ref", default=None,
                         help="Where the reading is recorded, e.g. readings/readings.json#PHerc0125"
                              " (required together with --sense for an UNDERIVABLE volume)")
    parser.add_argument("--catalog-url", default=FULL_CATALOG_URL)
    parser.add_argument("--out", default=None,
                         help="Output path (default: <scroll>_spiral-scroll.json)")
    args = parser.parse_args()

    if (args.sense is None) != (args.reading_ref is None):
        raise SystemExit("error: --sense and --reading-ref must be given together")

    print(f"Fetching catalog from {args.catalog_url} ...", file=sys.stderr)
    catalog, _, _ = fetch_catalog(args.catalog_url)
    volume = find_volume(catalog, args.scroll, args.volume)
    props = volume["properties"]

    spec = build_spec(args.scroll, args.volume, props, args.sense, args.reading_ref)

    out_path = Path(args.out) if args.out else Path(f"{args.scroll}_spiral-scroll.json")
    out_path.write_text(json.dumps(spec, indent=2) + "\n")
    print(f"Wrote {out_path}")
    print(json.dumps(spec, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
