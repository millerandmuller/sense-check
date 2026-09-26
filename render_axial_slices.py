#!/usr/bin/env python3
"""Render three labeled axial slices per eligible volume for a CW/ACW
spiral-winding read, adapted from the August entry's render_cw_acw_slices.py
(millerandmuller/first-light-pherc0826) to run over any of the 23 First
Letters eligible volumes instead of one hardcoded scroll.

Reads the volume zarr directly from the open-data S3 bucket (anonymous, via
s3fs) at a downsampled pyramid level, marks the umbilicus when a control-point
file is available in umbilicus/ (see umbilicus/NOTICE.md for sources; 11 of
23 volumes have one), and prints the viewing convention directly on the image
so the convention is never separated from the picture it was read against.
A volume with no umbilicus file is rendered anyway, with a note that it has
none, instead of guessing a location.

This intentionally does not decide CW or ACW -- that reading is a human's
call in front of the image.

Requires zarr>=3, s3fs, matplotlib, numpy -- not in system Python (which has
zarr 2.x). Run it via uv so it gets the right versions without touching
system packages:

    uv run --python 3.13 --with "zarr>=3" --with s3fs --with matplotlib \\
        --with numpy python3 render_axial_slices.py [--sample PHerc0826] [--out-dir readings/renders]
"""
from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path
from typing import Optional

warnings.filterwarnings("ignore")

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import s3fs  # noqa: E402
import zarr  # noqa: E402

from catalog_client import ELIGIBLE_SAMPLES, FULL_CATALOG_URL, fetch_catalog, pick_eligible_volume  # noqa: E402

BUCKET = "vesuvius-challenge-open-data"
UMBILICUS_DIR = Path(__file__).parent / "umbilicus"
TARGET_IN_PLANE_PX = 2200  # aim the pyramid level choice at roughly this size

CONVENTION_TEXT = (
    "Convention: villa spiral-fitting/README.md (f4570bf) documents that every "
    "catalog-conventional scroll shows the same spiral seen from its top, fixed "
    "by z_direction_is_top_to_bottom and left_handed_coordinates. The raw pixel "
    "axes below are the August entry's own convention (native array orientation, "
    "row=y col=x, no flip, viewed looking along +z) -- villa does not document "
    "pixel axes for a raw CT slice, only for exported grids."
)


def find_volume_path(catalog: dict, sample_id: str) -> tuple[str, dict]:
    sample = catalog["samples"].get(sample_id)
    if sample is None:
        raise SystemExit(f"error: sample {sample_id!r} not found in catalog")
    vid, v = pick_eligible_volume(sample)
    if vid is None:
        raise SystemExit(f"error: no eligible-protocol volume found for {sample_id!r}")
    data = v.get("data", [])
    path = next((d["origins"][0]["path"] for d in data if d.get("type") == "ome-zarr"), None)
    if path is None:
        raise SystemExit(f"error: no ome-zarr data entry for {sample_id}/{vid}")
    return path.rstrip("/"), v


def open_group(zarr_path: str):
    fs = s3fs.S3FileSystem(anon=True)
    store = zarr.storage.FsspecStore(fs, path=f"{BUCKET}/{zarr_path}")
    return zarr.open_group(store=store, mode="r")


def pick_level(group) -> tuple[str, int]:
    """Pick the smallest-scale pyramid level whose in-plane size is at or
    below TARGET_IN_PLANE_PX, falling back to the coarsest level available."""
    candidates = []
    for level in map(str, range(8)):
        if level not in group:
            break
        shape = group[level].shape
        candidates.append((level, shape))
    if not candidates:
        raise SystemExit("error: no pyramid levels found in this zarr group")
    for level, shape in candidates:
        if shape[1] <= TARGET_IN_PLANE_PX and shape[2] <= TARGET_IN_PLANE_PX:
            return level, 2 ** int(level)
    level, _ = candidates[-1]
    return level, 2 ** int(level)


def target_z_fullres(shape_z: int) -> list[int]:
    """Three interior z-levels, avoiding the noisy top/bottom margins."""
    return [round(shape_z * f) for f in (0.35, 0.55, 0.75)]


def load_umbilicus(sample_id: str) -> Optional[list[dict]]:
    path = UMBILICUS_DIR / f"{sample_id}_umbilicus.json"
    if not path.exists():
        return None
    doc = json.loads(path.read_text())
    return sorted(doc["control_points"], key=lambda p: p["z"])


def interpolate_umbilicus(points: list[dict], z_target: int) -> tuple[float, float]:
    zs = [p["z"] for p in points]
    if z_target <= zs[0]:
        p = points[0]
        return p["x"], p["y"]
    if z_target >= zs[-1]:
        p = points[-1]
        return p["x"], p["y"]
    for i in range(len(points) - 1):
        z0, z1 = points[i]["z"], points[i + 1]["z"]
        if z0 <= z_target <= z1:
            t = (z_target - z0) / (z1 - z0) if z1 != z0 else 0.0
            x = points[i]["x"] + t * (points[i + 1]["x"] - points[i]["x"])
            y = points[i]["y"] + t * (points[i + 1]["y"] - points[i]["y"])
            return x, y
    raise RuntimeError(f"z={z_target} not bracketed (range {zs[0]}-{zs[-1]})")


def render_sample(sample_id: str, catalog: dict, out_dir: Path) -> list[str]:
    zarr_path, volume = find_volume_path(catalog, sample_id)
    volume_id = volume["id"]
    print(f"{sample_id}/{volume_id}: opening {zarr_path} ...")
    group = open_group(zarr_path)
    level, scale = pick_level(group)
    arr = group[level]
    shape_z = arr.shape[0]
    print(f"  level {level} shape={arr.shape} scale={scale}x")

    umbilicus_points = load_umbilicus(sample_id)
    has_umbilicus = umbilicus_points is not None

    saved = []
    for z_full in target_z_fullres(shape_z * scale):
        z_idx = max(0, min(arr.shape[0] - 1, round(z_full / scale)))
        print(f"  reading z_full={z_full} -> level{level} z_idx={z_idx} ...")
        slab = np.asarray(arr[z_idx, :, :])

        lo, hi = np.percentile(slab, [1, 99])
        disp = np.clip((slab.astype(np.float32) - lo) / max(hi - lo, 1), 0, 1)

        fig, ax = plt.subplots(figsize=(9, 10.5), dpi=150)
        ax.imshow(disp, cmap="gray", origin="upper")

        if has_umbilicus:
            ux_full, uy_full = interpolate_umbilicus(umbilicus_points, z_full)
            ux, uy = ux_full / scale, uy_full / scale
            ax.plot(ux, uy, marker="+", color="red", markersize=22, markeredgewidth=2.5)
            ax.plot(ux, uy, marker="o", color="red", markersize=10,
                     markerfacecolor="none", markeredgewidth=2)
            ax.annotate(
                f"umbilicus (interpolated)\nz_full={z_full}  x={ux_full:.0f} y={uy_full:.0f}",
                xy=(ux, uy), xytext=(ux + 60, uy - 60), color="red", fontsize=9,
                arrowprops=dict(arrowstyle="->", color="red"),
            )
        else:
            ax.text(0.02, 0.98, "umbilicus: not available for this volume (see umbilicus/NOTICE.md)",
                     transform=ax.transAxes, color="orange", fontsize=9, va="top",
                     bbox=dict(facecolor="black", alpha=0.6, pad=3))

        ax.set_title(
            f"{sample_id}  |  full-res z={z_full}  |  level {level} "
            f"(x{scale} downsample)  |  z_idx={z_idx}",
            fontsize=11,
        )
        ax.set_xlabel("x (right ->)")
        ax.set_ylabel("y (down v)")
        fig.text(0.02, 0.01, CONVENTION_TEXT, fontsize=7, wrap=True, va="bottom")
        fig.tight_layout(rect=[0, 0.06, 1, 1])

        out_path = out_dir / f"{sample_id}_z{z_full}_level{level}.png"
        fig.savefig(out_path)
        plt.close(fig)
        saved.append(str(out_path))
        print(f"  saved {out_path}")
    return saved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sample", action="append", dest="samples", default=None,
                         help="Sample id to render (repeatable). Default: all 23 eligible.")
    parser.add_argument("--out-dir", default="readings/renders")
    parser.add_argument("--catalog-url", default=FULL_CATALOG_URL)
    args = parser.parse_args()

    samples = args.samples or ELIGIBLE_SAMPLES
    unknown = [s for s in samples if s not in ELIGIBLE_SAMPLES]
    if unknown:
        raise SystemExit(f"error: not eligible: {unknown}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Fetching catalog from {args.catalog_url} ...")
    catalog, _, _ = fetch_catalog(args.catalog_url)

    all_saved = {}
    for sample_id in samples:
        all_saved[sample_id] = render_sample(sample_id, catalog, out_dir)

    total = sum(len(v) for v in all_saved.values())
    print(f"\nRendered {total} images for {len(samples)} volume(s) into {out_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
