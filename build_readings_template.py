#!/usr/bin/env python3
"""Assemble readings/readings.json from the catalog and the rendered images,
leaving the human fields (sense, confidence, reader) blank.

Matches the record shape from the project plan:

    {"scroll": ..., "volume": ..., "um": ..., "keV": ...,
     "catalog": {"z_direction_is_top_to_bottom": ..., "left_handed_coordinates": ...,
                 "derived_sense": ...},
     "ct_reading": {"sense": null, "confidence": null, "reader": null,
                     "z_levels": [...], "convention": "...",
                     "renders": [...], "vc3d_screenshots": [...]},
     "agree": null, "note": null}

Re-run after new renders or VC3D screenshots land; it only fills fields it
can derive itself and never overwrites an existing human reading (sense,
confidence, reader, note) already present in readings/readings.json.

Usage:
    python3 build_readings_template.py [--renders-dir readings/renders]
                                        [--screenshots-dir readings/vc3d_screenshots]
                                        [--out readings/readings.json]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from catalog_client import (
    ELIGIBLE_SAMPLES,
    FULL_CATALOG_URL,
    fetch_catalog,
    pick_eligible_volume,
    spiral_outward_sense_for,
)

CONVENTION = (
    "villa spiral-fitting/README.md (f4570bf): every catalog-conventional scroll "
    "shows the same spiral seen from its top, fixed by z_direction_is_top_to_bottom "
    "and left_handed_coordinates. Raw pixel axes are the August entry's own "
    "convention (native array orientation, row=y col=x, no flip, viewed looking "
    "along +z) -- villa does not document pixel axes for a raw CT slice."
)

RENDER_RE = re.compile(r"^(?P<sample>.+)_z(?P<z>\d+)_level\d+\.png$")
SCREENSHOT_RE = re.compile(r"^(?P<sample>.+)_z(?P<z>\d+)\.png$")


def collect_images(directory: Path, pattern: re.Pattern) -> dict[str, list[tuple[int, str]]]:
    by_sample: dict[str, list[tuple[int, str]]] = {}
    if not directory.exists():
        return by_sample
    for f in sorted(directory.iterdir()):
        m = pattern.match(f.name)
        if not m:
            continue
        by_sample.setdefault(m.group("sample"), []).append((int(m.group("z")), str(f)))
    for sample in by_sample:
        by_sample[sample].sort()
    return by_sample


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--renders-dir", default="readings/renders")
    parser.add_argument("--screenshots-dir", default="readings/vc3d_screenshots")
    parser.add_argument("--out", default="readings/readings.json")
    parser.add_argument("--catalog-url", default=FULL_CATALOG_URL)
    args = parser.parse_args()

    out_path = Path(args.out)
    existing: dict[str, dict[str, Any]] = {}
    if out_path.exists():
        for rec in json.loads(out_path.read_text()):
            existing[rec["scroll"]] = rec

    renders = collect_images(Path(args.renders_dir), RENDER_RE)
    screenshots = collect_images(Path(args.screenshots_dir), SCREENSHOT_RE)

    print(f"Fetching catalog from {args.catalog_url} ...")
    catalog, _, _ = fetch_catalog(args.catalog_url)

    records = []
    for sample_id in ELIGIBLE_SAMPLES:
        sample = catalog["samples"][sample_id]
        vid, v = pick_eligible_volume(sample)
        p = v["properties"]
        z_top = p.get("z_direction_is_top_to_bottom")
        left_handed = p.get("left_handed_coordinates")
        derived_sense = spiral_outward_sense_for(z_top, left_handed)

        prior = existing.get(sample_id, {})
        prior_reading = prior.get("ct_reading", {})
        z_levels = sorted({z for z, _ in renders.get(sample_id, [])} |
                           {z for z, _ in screenshots.get(sample_id, [])}) or \
            prior_reading.get("z_levels", [])

        record = {
            "scroll": sample_id,
            "volume": vid,
            "um": p.get("pixel_size_um"),
            "keV": p.get("energy_keV"),
            "catalog": {
                "z_direction_is_top_to_bottom": z_top,
                "left_handed_coordinates": left_handed,
                "derived_sense": derived_sense,
            },
            "ct_reading": {
                "sense": prior_reading.get("sense"),
                "confidence": prior_reading.get("confidence"),
                "reader": prior_reading.get("reader"),
                "z_levels": z_levels,
                "convention": CONVENTION,
                "renders": [path for _, path in renders.get(sample_id, [])],
                "vc3d_screenshots": [path for _, path in screenshots.get(sample_id, [])],
            },
            "agree": prior.get("agree"),
            "note": prior.get("note"),
        }
        records.append(record)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(records, indent=2) + "\n")

    with_renders = sum(1 for r in records if r["ct_reading"]["renders"])
    with_screenshots = sum(1 for r in records if r["ct_reading"]["vc3d_screenshots"])
    with_reading = sum(1 for r in records if r["ct_reading"]["sense"])
    print(f"Wrote {out_path}: {len(records)} volumes, "
          f"{with_renders} with renders, {with_screenshots} with VC3D screenshots, "
          f"{with_reading} with a human reading.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
