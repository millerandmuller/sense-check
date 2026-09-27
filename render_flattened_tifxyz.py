#!/usr/bin/env python3
"""Render a flattened TIFXYZ (from villa's flatten_spiral_checkpoint.py) by
sampling the real CT volume at each flattened grid point.

Substitutes for villa's vc_render_tifxyz (volume-cartographer/apps/src/
vc_render_tifxyz.cpp), which could not be built here: the top-level CMake
configure requires Qt6 unconditionally (even though this tool itself is a
CLI, not the GUI app), Qt6 is not installed, and installing it plus
whatever else the full VC3D dependency graph pulls in was judged too
open-ended for the pod-hour budget on this task. This script does the same
core job vc_render_tifxyz would for our purpose -- turn a flattened tifxyz's
per-pixel (x, y, z) scroll-space coordinates into a 2D image of the real CT
intensity at those points -- using nearest-voxel lookup into a coarse
pyramid level (matching this repo's convention in render_axial_slices.py /
overlay_fit_on_slice.py), not vc_render_tifxyz's own (fancier, sub-pixel)
resampling. Good enough to see whether two flattened renders are mirror
images of each other; not a claim of pixel-identical output to the real
tool.

Usage:
    uv run --python 3.13 --with "zarr>=3" --with s3fs --with matplotlib \\
        --with numpy --with tifffile python3 render_flattened_tifxyz.py \\
        --sample PHerc0826 --tifxyz analysis/pherc0826/flatten/PHerc0826_catalog_ACW_30k.tifxyz \\
        --label catalog_ACW --out analysis/pherc0826/flatten/PHerc0826_catalog_ACW_30k_render.png \\
        --col-subsample 6
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
import tifffile  # noqa: E402

from catalog_client import FULL_CATALOG_URL, fetch_catalog  # noqa: E402
from render_axial_slices import pick_level  # noqa: E402
from volume_access import find_volume_path, open_group  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sample", required=True)
    p.add_argument("--tifxyz", required=True, help="flattened tifxyz directory (has x.tif/y.tif/z.tif)")
    p.add_argument("--label", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--col-subsample", type=int, default=6,
                   help="take every Nth column of the flattened grid to bound sample count")
    p.add_argument("--catalog-url", default=FULL_CATALOG_URL)
    args = p.parse_args()

    tifxyz_dir = Path(args.tifxyz)
    x = tifffile.imread(tifxyz_dir / "x.tif").astype(np.float64)
    y = tifffile.imread(tifxyz_dir / "y.tif").astype(np.float64)
    z = tifffile.imread(tifxyz_dir / "z.tif").astype(np.float64)
    valid = z > -1
    print(f"{args.label}: flattened grid {z.shape}, {int(valid.sum())} valid cells")

    x = x[:, ::args.col_subsample]
    y = y[:, ::args.col_subsample]
    z = z[:, ::args.col_subsample]
    valid = valid[:, ::args.col_subsample]
    print(f"{args.label}: after column subsample -> {z.shape}, {int(valid.sum())} valid cells")

    print(f"Fetching catalog from {args.catalog_url} ...")
    catalog, _, _ = fetch_catalog(args.catalog_url)
    zarr_path, _ = find_volume_path(catalog, args.sample)
    print(f"{args.sample}: opening {zarr_path} ...")
    group = open_group(zarr_path)
    level, scale = pick_level(group)
    arr = group[level]
    print(f"  level {level} shape={arr.shape} scale={scale}x")

    zi = np.clip(np.round(z / scale).astype(np.int64), 0, arr.shape[0] - 1)
    yi = np.clip(np.round(y / scale).astype(np.int64), 0, arr.shape[1] - 1)
    xi = np.clip(np.round(x / scale).astype(np.int64), 0, arr.shape[2] - 1)

    image = np.zeros(z.shape, dtype=np.float32)
    rows, cols = np.where(valid)
    print(f"{args.label}: sampling {len(rows)} points from the volume ...")
    # Batch the fancy-index gather in chunks so a single huge vindex call
    # doesn't blow up memory or time out the s3fs session.
    batch = 20000
    values = np.empty(len(rows), dtype=np.float32)
    for start in range(0, len(rows), batch):
        end = min(start + batch, len(rows))
        sel = (zi[rows[start:end], cols[start:end]],
               yi[rows[start:end], cols[start:end]],
               xi[rows[start:end], cols[start:end]])
        values[start:end] = np.asarray(arr.vindex[sel])
        if start % (batch * 5) == 0:
            print(f"  {end}/{len(rows)}", flush=True)
    image[rows, cols] = values

    lo, hi = np.percentile(values, [1, 99])
    disp = np.clip((image - lo) / max(hi - lo, 1), 0, 1)
    disp[~valid] = 0

    fig, ax = plt.subplots(figsize=(18, 4), dpi=150)
    ax.imshow(disp, cmap="gray", aspect="auto", origin="upper")
    ax.set_title(f"{args.sample} flattened render (substitute for vc_render_tifxyz) -- {args.label}", fontsize=10)
    ax.set_xlabel(f"unrolled arc-length (col, subsample={args.col_subsample})")
    ax.set_ylabel("z-height (row)")
    fig.tight_layout()
    fig.savefig(args.out)
    print(f"saved {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
