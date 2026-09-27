#!/usr/bin/env python3
"""Annotate an existing render/crop PNG with a reading note's stated start
point and a schematic direction glyph, without inventing any coordinate the
note doesn't give.

A reading note sometimes gives one coordinate (where the reader started
following a sheet) plus a direction sequence in words ("up, then left,
then down"), not a traced polyline along the sheet. This script draws
exactly that: a ring at the one given point, and a small arrow glyph next
to it labelled with the direction sequence -- always prefixed "schematic"
so the image never reads as a traced path. It does not sample the CT
volume or compute anything; it only draws on top of an existing PNG.

Usage:
    python3 annotate_reading_path.py <input.png> <output.png> \\
        --point X Y --label "up -> left -> down = ACW on screen" \\
        --caption "Start of the path the reader followed; low confidence."
"""
from __future__ import annotations

import argparse
import warnings

warnings.filterwarnings("ignore")

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402


def annotate(image_path: str, out_path: str, x: float, y: float, label: str,
             caption: str) -> None:
    img = mpimg.imread(image_path)
    h, w = img.shape[0], img.shape[1]

    fig, ax = plt.subplots(figsize=(w / 150, h / 150), dpi=150)
    ax.imshow(img)
    ax.set_axis_off()

    ax.plot(x, y, marker="o", markersize=22, markerfacecolor="none",
            markeredgecolor="cyan", markeredgewidth=2.5)

    # Schematic direction glyph: a legend placed near the marker, not a
    # traced path along the sheet. The "schematic" prefix is added here,
    # not left to the caller, so the image can never read as a trace.
    glyph_x, glyph_y = x + w * 0.10, y - h * 0.08
    ax.annotate("", xy=(glyph_x + w * 0.06, glyph_y - h * 0.03),
                xytext=(glyph_x, glyph_y),
                arrowprops=dict(arrowstyle="-|>", color="cyan", lw=2))
    ax.text(glyph_x, glyph_y + h * 0.015, f"schematic -- {label}",
            color="cyan", fontsize=7, ha="left", va="bottom",
            bbox=dict(boxstyle="round", fc="black", ec="cyan", alpha=0.6))

    fig.text(0.02, 0.01, caption, fontsize=6, wrap=True, va="bottom")
    fig.tight_layout(rect=[0, 0.08, 1, 1])
    fig.savefig(out_path)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("image", help="Existing crop/render PNG to annotate")
    parser.add_argument("out", help="Output PNG path")
    parser.add_argument("--point", nargs=2, type=float, required=True, metavar=("X", "Y"),
                         help="The note's one given coordinate, in the input image's own pixels")
    parser.add_argument("--label", required=True,
                         help="Direction sequence from the note, e.g. 'up -> left -> down = ACW on screen'")
    parser.add_argument("--caption", required=True,
                         help="Caption line printed in the image margin")
    args = parser.parse_args()

    annotate(args.image, args.out, args.point[0], args.point[1], args.label, args.caption)
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
