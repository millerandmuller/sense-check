#!/usr/bin/env python3
"""Publish the final table/orientation.md from readings.json: catalog sense,
CT reading, agreement, and the reader disclosure -- supersedes
catalog_orientation.py's catalog-only draft once readings exist.

Refuses to publish if any of the 23 rows still has no reading (ct_reading.sense
is null), same contract as fill_readings_from_sheet.py, kept here too since
this can be re-run independently later.

Usage:
    python3 publish_table.py [--readings-json readings/readings.json] [--out table/orientation.md]
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--readings-json", default="readings/readings.json")
    parser.add_argument("--out", default="table/orientation.md")
    parser.add_argument("--provenance", default=None,
                         help="catalog_provenance.json written by catalog_orientation.py "
                              "(default: catalog_provenance.json next to --out)")
    args = parser.parse_args(argv)

    out_path = Path(args.out)
    provenance_path = Path(args.provenance) if args.provenance else out_path.parent / "catalog_provenance.json"
    if not provenance_path.exists():
        print(f"REFUSING TO PUBLISH: {provenance_path} is missing -- "
              "run catalog_orientation.py first.")
        return 1
    provenance = json.loads(provenance_path.read_text())

    records = json.loads(Path(args.readings_json).read_text())

    missing = [r["scroll"] for r in records if not r["ct_reading"]["sense"]]
    if missing:
        print("REFUSING TO PUBLISH: the following volumes still have no reading:")
        for s in missing:
            print(f"  - {s}")
        return 1

    reader_disclosures = {r["ct_reading"]["reader"] for r in records}
    if len(reader_disclosures) != 1:
        print(f"REFUSING TO PUBLISH: expected one consistent reader disclosure, found "
              f"{len(reader_disclosures)}: {reader_disclosures}")
        return 1
    reader = reader_disclosures.pop()

    derivable = [r for r in records if r["catalog"]["derived_sense"] is not None]
    underivable = [r for r in records if r["catalog"]["derived_sense"] is None]
    unsure = [r for r in records if r["ct_reading"]["sense"] == "unsure"]
    agree = [r for r in records if r["agree"] is True]
    disagree = [r for r in records if r["agree"] is False]

    catalog_name = Path(provenance["catalog_url"]).name
    lines = [
        "# Catalog orientation vs. CT reading -- 23 First Letters eligible volumes",
        "",
        f"> **Reader:** {reader}",
        "",
        f"Catalog: `{catalog_name}`, ETag `{provenance['etag']}`, "
        f"Last-Modified `{provenance['last_modified']}`, fetched {provenance['fetched_at']}.",
        f"Published {datetime.now(timezone.utc).isoformat(timespec='seconds')}.",
        "",
        f"{len(derivable)} volumes derivable from the catalog, {len(underivable)} UNDERIVABLE. "
        f"Of the 23 readings: {len(unsure)} unsure, {len(agree)} agree with the catalog's "
        f"predicted visual sense, {len(disagree)} disagree.",
        "",
        "| Sample | Volume | µm | Catalog sense | CT reading | Confidence | Agree | Umbilicus | Note |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in records:
        catalog_sense = r["catalog"]["derived_sense"] or "UNDERIVABLE"
        ct = r["ct_reading"]
        sense = ct["sense"]
        sense_disp = f"**{sense}**" if sense != "unsure" else "unsure"
        agree_val = r["agree"]
        agree_disp = "n/a" if agree_val is None else ("✅ agree" if agree_val else "❌ **disagree**")
        note = (r["note"] or "").replace("|", "\\|")
        note_short = note if len(note) <= 100 else note[:97] + "..."
        lines.append(
            f"| {r['scroll']} | {r['volume']} | {r['um']} | {catalog_sense} | {sense_disp} | "
            f"{ct['confidence'] or '-'} | {agree_disp} | {ct['umbilicus_source']} | {note_short} |"
        )

    if disagree:
        lines += ["", "## Disagreements (catalog vs. CT reading)", ""]
        for r in disagree:
            lines.append(f"- **{r['scroll']}**: catalog predicts "
                          f"{r['catalog']['predicted_visual_sense']}, read as {r['ct_reading']['sense']} "
                          f"(confidence {r['ct_reading']['confidence']}). {r['note']}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n")
    print(f"Published {out_path}: {len(records)} rows, {len(agree)} agree, {len(disagree)} disagree, "
          f"{len(unsure)} unsure.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
