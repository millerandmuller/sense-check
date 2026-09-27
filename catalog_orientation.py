#!/usr/bin/env python3
"""Derive spiral winding sense from the Vesuvius Challenge open-data catalog
for the 23 First Letters eligible volumes, and measure how many of the 71
cataloged volumes the rule covers at all.

Rule (villa spiral-fitting/surface_orientation.py, spiral_outward_sense_for,
commit f4570bf):

    "ACW" if z_direction_is_top_to_bottom != left_handed_coordinates else "CW"

Usage:
    python3 catalog_orientation.py [--catalog-url URL] [--out-dir table]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from catalog_client import (
    ELIGIBLE_SAMPLES,
    FULL_CATALOG_URL,
    MINIFIED_CATALOG_URL,
    fetch_catalog,
    fetch_raw,
    pick_eligible_volume,
    spiral_outward_sense_for,
)


@dataclass
class Row:
    sample_id: str
    volume_id: str
    pixel_size_um: float
    energy_keV: float
    z_direction_is_top_to_bottom: Optional[bool]
    left_handed_coordinates: Optional[bool]
    derived_sense: Optional[str]

    @property
    def status(self) -> str:
        return self.derived_sense if self.derived_sense else "UNDERIVABLE"


def build_rows(catalog: dict[str, Any]) -> list[Row]:
    samples = catalog["samples"]
    rows = []
    for sample_id in ELIGIBLE_SAMPLES:
        sample = samples.get(sample_id)
        if sample is None:
            raise SystemExit(f"eligible sample {sample_id} not found in catalog")
        vid, v = pick_eligible_volume(sample)
        if vid is None:
            raise SystemExit(f"no eligible-protocol volume found for {sample_id}")
        p = v["properties"]
        z_top = p.get("z_direction_is_top_to_bottom")
        left_handed = p.get("left_handed_coordinates")
        rows.append(Row(
            sample_id=sample_id,
            volume_id=vid,
            pixel_size_um=p.get("pixel_size_um"),
            energy_keV=p.get("energy_keV"),
            z_direction_is_top_to_bottom=z_top,
            left_handed_coordinates=left_handed,
            derived_sense=spiral_outward_sense_for(z_top, left_handed),
        ))
    return rows


def full_catalog_coverage(catalog: dict[str, Any]) -> tuple[int, int]:
    """(total_volumes, volumes_with_both_keys) across every sample in the
    catalog, not just the 23 eligible ones."""
    total = 0
    covered = 0
    for sample in catalog["samples"].values():
        for v in sample.get("volumes", {}).values():
            total += 1
            p = v.get("properties", {})
            if p.get("z_direction_is_top_to_bottom") is not None and \
               p.get("left_handed_coordinates") is not None:
                covered += 1
    return total, covered


def prove_minified_catalog_lacks_keys(minified_raw: bytes) -> bool:
    """Returns True if the minified catalog carries neither orientation key
    anywhere (proof for the README's one-command claim)."""
    text = minified_raw.decode("utf-8", errors="replace")
    return "z_direction_is_top_to_bottom" not in text and "left_handed_coordinates" not in text


def write_provenance(path: Path, catalog_url: str, etag: str, last_modified: str,
                      fetched_at: str) -> None:
    """Record the real catalog fetch (not the publish time) so publish_table.py
    can print it instead of mislabelling its own publish time as 'Fetched'."""
    path.write_text(json.dumps({
        "catalog_url": catalog_url,
        "etag": etag,
        "last_modified": last_modified,
        "fetched_at": fetched_at,
    }, indent=2) + "\n")


def write_csv(rows: list[Row], path: Path) -> None:
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sample_id", "volume_id", "pixel_size_um", "energy_keV",
                    "z_direction_is_top_to_bottom", "left_handed_coordinates", "derived_sense"])
        for r in rows:
            w.writerow([r.sample_id, r.volume_id, r.pixel_size_um, r.energy_keV,
                        r.z_direction_is_top_to_bottom, r.left_handed_coordinates, r.status])


def write_markdown(rows: list[Row], path: Path, total_vols: int, covered_vols: int,
                    etag: str, last_modified: str, fetched_at: str) -> None:
    derivable = sum(1 for r in rows if r.derived_sense is not None)
    underivable = len(rows) - derivable
    lines = [
        "# Catalog orientation — 23 First Letters eligible volumes",
        "",
        f"Catalog: `metadata.json`, ETag `{etag}`, Last-Modified `{last_modified}`, "
        f"fetched {fetched_at}.",
        "",
        f"Coverage across the full catalog: **{covered_vols} of {total_vols}** volumes carry both "
        "orientation keys. Within the 23 eligible: "
        f"**{derivable} derivable, {underivable} UNDERIVABLE**.",
        "",
        "| Sample | Volume | µm | keV | z_top_to_bottom | left_handed | Derived sense |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r.sample_id} | {r.volume_id} | {r.pixel_size_um} | {r.energy_keV} | "
            f"{r.z_direction_is_top_to_bottom} | {r.left_handed_coordinates} | **{r.status}** |"
        )
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog-url", default=FULL_CATALOG_URL)
    parser.add_argument("--minified-url", default=MINIFIED_CATALOG_URL)
    parser.add_argument("--out-dir", default="table")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Fetching full catalog from {args.catalog_url} ...", file=sys.stderr)
    catalog, etag, last_modified = fetch_catalog(args.catalog_url)
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    rows = build_rows(catalog)
    total_vols, covered_vols = full_catalog_coverage(catalog)

    write_provenance(out_dir / "catalog_provenance.json", args.catalog_url, etag,
                      last_modified, fetched_at)
    write_csv(rows, out_dir / "orientation.csv")
    write_markdown(rows, out_dir / "orientation.md", total_vols, covered_vols, etag,
                    last_modified, fetched_at)

    # If readings already exist, publish_table.py's richer table (CT reading,
    # confidence, agree, reader disclosure) supersedes what was just written
    # above. Re-run it now so this script's own "one-command proof" never
    # leaves the published table downgraded to the catalog-only draft.
    readings_path = Path("readings/readings.json")
    if out_dir == Path("table") and readings_path.exists():
        import publish_table
        print(f"{readings_path} exists -- re-publishing the richer table "
              f"(catalog-only draft above would otherwise stay in place)...",
              file=sys.stderr)
        if publish_table.main([]) != 0:
            print("WARNING: re-publish failed (see above) -- "
                  f"{out_dir / 'orientation.md'} is now the catalog-only draft, "
                  "not the published table. Run publish_table.py once readings "
                  "are complete.", file=sys.stderr)

    print(f"Fetching minified catalog from {args.minified_url} ...", file=sys.stderr)
    minified_raw, _, _ = fetch_raw(args.minified_url)
    minified_lacks_keys = prove_minified_catalog_lacks_keys(minified_raw)

    derivable = sum(1 for r in rows if r.derived_sense is not None)
    underivable = len(rows) - derivable

    print(f"Eligible volumes: {len(rows)}  derivable: {derivable}  UNDERIVABLE: {underivable}")
    print(f"Full catalog coverage: {covered_vols} of {total_vols}")
    print(f"Minified catalog lacks both orientation keys: {minified_lacks_keys}")
    print(f"Wrote {out_dir / 'orientation.csv'} and {out_dir / 'orientation.md'}")

    if not minified_lacks_keys:
        print("WARNING: minified catalog now carries orientation keys; update the README claim.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
