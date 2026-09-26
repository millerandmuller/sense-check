#!/usr/bin/env python3
"""Render two umbilicus-centered crops per volume and z-level: a tight one at
native resolution (level 0, ~4mm across) and a wider one at the next pyramid
level (level 1, ~12mm across). This is the zoomed-in view the sense is
actually read from -- the wide axial-slice renders (render_axial_slices.py)
are context, not a reading aid.

Both levels are centered on the same interpolated umbilicus point used by
render_axial_slices.py (see umbilicus_data.py; real or estimated, all 23
eligible volumes have one). Only a small window around that point is read
from each pyramid level, so level 0 (native resolution) is cheap despite
being un-downsampled.

Requires zarr>=3, s3fs, matplotlib, numpy (uv run, see render_axial_slices.py
for the exact invocation).
"""
from __future__ import annotations

import argparse
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from catalog_client import ELIGIBLE_SAMPLES, FULL_CATALOG_URL, fetch_catalog  # noqa: E402
from umbilicus_data import interpolate, load_umbilicus  # noqa: E402
from volume_access import find_volume_path, open_group  # noqa: E402

CONVENTION_TEXT = (
    "Convention: villa spiral-fitting/README.md (f4570bf) documents that every "
    "catalog-conventional scroll shows the same spiral seen from its top, fixed "
    "by z_direction_is_top_to_bottom and left_handed_coordinates. The raw pixel "
    "axes below are the August entry's own convention (native array orientation, "
    "row=y col=x, no flip, viewed looking along +z) -- villa does not document "
    "pixel axes for a raw CT slice, only for exported grids."
)

# (pyramid level, physical width across the crop in mm)
CROP_SPECS = [(0, 4.0), (1, 12.0)]


def target_z_fullres(shape_z_native: int) -> list[int]:
    """Three interior z-levels, avoiding the noisy top/bottom margins.
    Matches render_axial_slices.py's choice so all three image kinds
    (wide render, zoomed crop, VC3D screenshot) line up at the same z."""
    return [round(shape_z_native * f) for f in (0.35, 0.55, 0.75)]


def crop_slice(arr, z_idx: int, cx: float, cy: float, half_px: int):
    shape_z, shape_y, shape_x = arr.shape
    y0, y1 = int(round(cy - half_px)), int(round(cy + half_px))
    x0, x1 = int(round(cx - half_px)), int(round(cx + half_px))
    y0c, y1c = max(0, y0), min(shape_y, y1)
    x0c, x1c = max(0, x0), min(shape_x, x1)
    raw = np.asarray(arr[z_idx, y0c:y1c, x0c:x1c])
    # Pad to the full requested window if we hit an edge, so every crop is
    # the same size and the umbilicus stays centered in the frame.
    out = np.zeros((y1 - y0, x1 - x0), dtype=raw.dtype)
    out[y0c - y0:y1c - y0, x0c - x0:x1c - x0] = raw
    return out


def render_crop(sample_id: str, z_full: int, level: int, width_mm: float,
                 arr, native_pixel_um: float, cx_full: float, cy_full: float,
                 is_estimated: bool, out_dir: Path) -> str:
    scale = 2 ** level
    z_idx = max(0, min(arr.shape[0] - 1, round(z_full / scale)))
    um_per_px = native_pixel_um * scale
    half_px = max(4, round((width_mm * 1000 / um_per_px) / 2))
    cx, cy = cx_full / scale, cy_full / scale

    slab = crop_slice(arr, z_idx, cx, cy, half_px)
    lo, hi = np.percentile(slab, [1, 99])
    disp = np.clip((slab.astype(np.float32) - lo) / max(hi - lo, 1), 0, 1)

    fig, ax = plt.subplots(figsize=(6, 6.6), dpi=150)
    ax.imshow(disp, cmap="gray", origin="upper")
    cx_local, cy_local = disp.shape[1] / 2, disp.shape[0] / 2
    color = "orange" if is_estimated else "red"
    ax.plot(cx_local, cy_local, marker="+", color=color, markersize=26, markeredgewidth=2.5)

    est_note = " (estimated)" if is_estimated else ""
    ax.set_title(
        f"{sample_id}  |  z={z_full}  |  level {level} (x{scale})  |  "
        f"~{width_mm:g} mm across  |  umbilicus{est_note} centered",
        fontsize=10,
    )
    ax.set_xlabel("x (right ->)")
    ax.set_ylabel("y (down v)")
    # physical scale bar, 1mm
    bar_px = 1000 / um_per_px
    bx0 = disp.shape[1] * 0.05
    by = disp.shape[0] * 0.95
    ax.plot([bx0, bx0 + bar_px], [by, by], color="lime", linewidth=3)
    ax.text(bx0, by - disp.shape[0] * 0.03, "1 mm", color="lime", fontsize=8)
    fig.text(0.02, 0.01, CONVENTION_TEXT, fontsize=6, wrap=True, va="bottom")
    fig.tight_layout(rect=[0, 0.09, 1, 1])

    out_path = out_dir / f"{sample_id}_z{z_full}_umbilicus_L{level}_{width_mm:g}mm.png"
    fig.savefig(out_path)
    plt.close(fig)
    return str(out_path)


def render_sample(sample_id: str, catalog: dict, out_dir: Path) -> list[str]:
    zarr_path, volume = find_volume_path(catalog, sample_id)
    volume_id = volume["id"]
    native_pixel_um = volume["properties"]["pixel_size_um"]
    umbilicus = load_umbilicus(sample_id)
    if umbilicus is None:
        raise SystemExit(f"error: no umbilicus (real or estimated) for {sample_id}")

    print(f"{sample_id}/{volume_id}: opening {zarr_path} ...")
    group = open_group(zarr_path)
    shape_z_native = group["0"].shape[0]

    saved = []
    for z_full in target_z_fullres(shape_z_native):
        cx_full, cy_full = interpolate(umbilicus.points, z_full)
        for level, width_mm in CROP_SPECS:
            arr = group[str(level)]
            print(f"  z={z_full} level={level} ({width_mm}mm) around "
                  f"x={cx_full:.0f} y={cy_full:.0f} ...")
            path = render_crop(sample_id, z_full, level, width_mm, arr,
                                native_pixel_um, cx_full, cy_full,
                                umbilicus.is_estimated, out_dir)
            saved.append(path)
            print(f"    saved {path}")
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
    print(f"\nRendered {total} crop images for {len(samples)} volume(s) into {out_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
