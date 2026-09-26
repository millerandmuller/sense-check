#!/usr/bin/env python3
"""Parse a completed readings/READING_SHEET.md back into readings.json.

Fills sense/confidence/trusted_z_level/note into each volume's ct_reading,
and computes "agree" (sense == predicted_visual_sense) for the 18 derivable
volumes -- null for the 5 catalog-UNDERIVABLE volumes (no prediction to
compare against) and for an "unsure" reading (nothing to agree or disagree
with).

Refuses to write readings.json if any of the 23 rows still has no sense --
prints exactly which ones and exits nonzero without touching the file.

Usage:
    python3 fill_readings_from_sheet.py [--sheet readings/READING_SHEET.md]
                                         [--readings-json readings/readings.json]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

VALID_SENSES = {"CW", "ACW", "UNSURE"}
VALID_CONFIDENCE = {"HIGH", "MEDIUM", "LOW"}

SECTION_RE = re.compile(r"^## (?P<sample>\S+) — volume (?P<volume>\S+) — umbilicus: (?P<source>\S+)$",
                         re.MULTILINE)
FIELD_RE = re.compile(
    r"\*\*Sense \(CW / ACW / unsure\):\*\*\s*(?P<sense>.*?)\s*\n"
    r"\*\*Confidence \(high / medium / low\):\*\*\s*(?P<confidence>.*?)\s*\n"
    r"\*\*Z-level trusted:\*\*\s*(?P<trusted_z>.*?)\s*\n"
    r"\*\*Note:\*\*\s*(?P<note>.*?)\s*\n"
)


def parse_sheet(text: str) -> dict[str, dict]:
    sections = list(SECTION_RE.finditer(text))
    parsed = {}
    for i, m in enumerate(sections):
        start = m.end()
        end = sections[i + 1].start() if i + 1 < len(sections) else len(text)
        block = text[start:end]
        fm = FIELD_RE.search(block)
        if fm is None:
            raise SystemExit(f"error: could not find the entry fields for {m.group('sample')} "
                              f"-- sheet format may have been edited")
        parsed[m.group("sample")] = {
            "sense_raw": fm.group("sense").strip(),
            "confidence_raw": fm.group("confidence").strip(),
            "trusted_z": fm.group("trusted_z").strip(),
            "note": fm.group("note").strip(),
        }
    return parsed


def normalize_sense(raw: str) -> str:
    return raw.strip().upper()


def normalize_confidence(raw: str) -> str:
    return raw.strip().upper()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sheet", default="readings/READING_SHEET.md")
    parser.add_argument("--readings-json", default="readings/readings.json")
    parser.add_argument("--reader", default="LM",
                         help="Reader initials for every row")
    args = parser.parse_args()

    sheet_text = Path(args.sheet).read_text()
    parsed = parse_sheet(sheet_text)

    readings_path = Path(args.readings_json)
    records = json.loads(readings_path.read_text())

    missing = [r["scroll"] for r in records if not parsed.get(r["scroll"], {}).get("sense_raw")]
    if missing:
        print("REFUSING TO PUBLISH: the following volumes still have no reading "
              f"in {args.sheet}:")
        for s in missing:
            print(f"  - {s}")
        print(f"\n{readings_path} was NOT modified.")
        return 1

    bad_sense = []
    bad_confidence = []
    for sample, entry in parsed.items():
        sense = normalize_sense(entry["sense_raw"])
        if sense not in VALID_SENSES:
            bad_sense.append((sample, entry["sense_raw"]))
        if entry["confidence_raw"]:
            conf = normalize_confidence(entry["confidence_raw"])
            if conf not in VALID_CONFIDENCE:
                bad_confidence.append((sample, entry["confidence_raw"]))
    if bad_sense:
        print("REFUSING TO PUBLISH: sense must be CW, ACW, or unsure:")
        for s, v in bad_sense:
            print(f"  - {s}: {v!r}")
        return 1
    if bad_confidence:
        print("REFUSING TO PUBLISH: confidence must be high, medium, or low:")
        for s, v in bad_confidence:
            print(f"  - {s}: {v!r}")
        return 1

    n_agree = n_disagree = n_na = 0
    for r in records:
        sample = r["scroll"]
        entry = parsed[sample]
        sense = normalize_sense(entry["sense_raw"])
        sense_out = {"CW": "CW", "ACW": "ACW", "UNSURE": "unsure"}[sense]
        confidence_out = entry["confidence_raw"].strip().lower() or None

        r["ct_reading"]["sense"] = sense_out
        r["ct_reading"]["confidence"] = confidence_out
        r["ct_reading"]["reader"] = args.reader
        r["ct_reading"]["trusted_z_level"] = entry["trusted_z"] or None
        r["note"] = entry["note"] or None

        predicted = r["catalog"]["predicted_visual_sense"]
        if predicted is None or sense_out == "unsure":
            r["agree"] = None
            n_na += 1
        else:
            r["agree"] = (sense_out == predicted)
            if r["agree"]:
                n_agree += 1
            else:
                n_disagree += 1

    readings_path.write_text(json.dumps(records, indent=2) + "\n")
    print(f"Wrote {readings_path}: 23/23 readings filled. "
          f"Agreement vs. predicted_visual_sense: {n_agree} agree, {n_disagree} disagree, "
          f"{n_na} not applicable (underivable or unsure).")
    if n_disagree:
        print("\nDisagreements (worth a second look before F3):")
        for r in records:
            if r["agree"] is False:
                print(f"  - {r['scroll']}: catalog predicts {r['catalog']['predicted_visual_sense']}, "
                      f"read as {r['ct_reading']['sense']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
