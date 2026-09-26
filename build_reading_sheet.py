#!/usr/bin/env python3
"""Build readings/READING_SHEET.md: a blind reading form for the 23 volumes.

Order: the 5 catalog-UNDERIVABLE volumes first (no cross-check available, so
their reading is the only source of truth for those rows), then the 18
derivable volumes in catalog order. Per volume: the three 12mm/level-1 crops
inline (this is the reading evidence), the three 4mm/level-0 crops collapsed
below (detail, not usually needed), the umbilicus source, and a blank entry
block for sense/confidence/trusted z-level/note.

Deliberately does NOT show predicted_visual_sense -- the reading must not be
anchored by the theoretical prediction. That comparison happens after the
sheet is filled in and handed back (fill_readings_from_sheet.py).

Usage:
    python3 build_reading_sheet.py [--renders-dir readings/renders] [--out readings/READING_SHEET.md]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from catalog_client import ELIGIBLE_SAMPLES

UNDERIVABLE_FIRST = ["PHerc0125", "PHerc1203", "PHerc0490A", "PHerc0490B", "PHerc0846A"]

ENTRY_TEMPLATE = """\
**Sense (CW / ACW / unsure):**
**Confidence (high / medium / low):**
**Z-level trusted:**
**Note:**
"""


def ordered_samples() -> list[str]:
    rest = [s for s in ELIGIBLE_SAMPLES if s not in UNDERIVABLE_FIRST]
    return UNDERIVABLE_FIRST + rest


def volume_section(record: dict) -> str:
    sample = record["scroll"]
    ct = record["ct_reading"]
    source = ct["umbilicus_source"] or "none"

    def crop_pairs(level_tag: str) -> list[tuple[int, str]]:
        pattern = re.compile(rf"_z(\d+)_umbilicus_{level_tag}_")
        pairs = []
        for p in ct["umbilicus_crops"]:
            m = pattern.search(p)
            if m:
                pairs.append((int(m.group(1)), p))
        return sorted(pairs)

    l1_crops = crop_pairs("L1")
    l0_crops = crop_pairs("L0")

    def rel(path: str) -> str:
        # readings/READING_SHEET.md lives in readings/; crops are readings/renders/...
        return path.split("readings/", 1)[-1]

    lines = [
        f"## {sample} — volume {record['volume']} — umbilicus: {source}",
        "",
        "### 12 mm crops (level 1) -- read from these",
        "",
    ]
    for z, p in l1_crops:
        lines.append(f"z={z}")
        lines.append(f"![{sample} z={z} 12mm]({rel(p)})")
        lines.append("")

    lines += [
        "<details>",
        "<summary>4 mm crops (level 0, detail)</summary>",
        "",
    ]
    for z, p in l0_crops:
        lines.append(f"z={z}")
        lines.append(f"![{sample} z={z} 4mm]({rel(p)})")
        lines.append("")
    lines += ["</details>", ""]

    lines += [ENTRY_TEMPLATE, "---", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--readings-json", default="readings/readings.json")
    parser.add_argument("--out", default="readings/READING_SHEET.md")
    args = parser.parse_args()

    records = {r["scroll"]: r for r in json.loads(Path(args.readings_json).read_text())}

    samples = ordered_samples()
    missing = [s for s in samples if s not in records]
    if missing:
        raise SystemExit(f"error: missing from readings.json: {missing}")

    header = """\
# Reading sheet -- Sense Check

Blind reading form. Fill in Sense / Confidence / Z-level trusted / Note for
each volume from the 12 mm crops (the 4 mm crops are supporting detail).
The catalog's predicted sense is deliberately not shown here -- it lives
only in readings.json, so this reading isn't anchored by it.

Order: the 5 volumes the catalog cannot derive a sense for (no cross-check
available for these) come first, then the 18 derivable volumes.

"""
    body = "\n".join(volume_section(records[s]) for s in samples)

    out_path = Path(args.out)
    out_path.write_text(header + body)
    print(f"Wrote {out_path}: {len(samples)} volumes "
          f"({len(UNDERIVABLE_FIRST)} underivable first, {len(samples) - len(UNDERIVABLE_FIRST)} derivable).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
