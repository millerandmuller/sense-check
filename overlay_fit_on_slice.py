#!/usr/bin/env python3
"""Overlay an A1/A1b spiral-fit's mesh cross-section on the real CT slice at a
target z, one image per fit run (e.g. catalog sense vs. the explicit
contradicting sense), so the visible papyrus wraps can be checked against
each fit's actual output geometry directly -- not a loss number, not a
random-hue track scatter.

Adapted from the August entry's overlay_mesh_on_slice.py
(millerandmuller/first-light-pherc0826) to run over any sample/z/run set
instead of one hardcoded scroll, and to reuse this repo's own catalog/volume/
umbilicus access (catalog_client, volume_access, umbilicus_data,
render_axial_slices.pick_level) instead of re-deriving them, since those are
already read against the real villa/catalog source and verified.

Requires zarr>=3, s3fs, matplotlib, numpy, tifffile -- run via uv so it gets
the right versions without touching system packages:

    uv run --python 3.13 --with "zarr>=3" --with s3fs --with matplotlib \\
        --with numpy --with tifffile python3 overlay_fit_on_slice.py \\
        --sample PHerc0826 --target-z 5922 \\
        --run catalog_ACW=analysis/pherc0826/catalog_ACW/2026-09-26_PHerc0826_slice-5200-6700_0-patch/meshes/fitted \\
        --run contradicting_CW=analysis/pherc0826/contradicting_CW/2026-09-26_PHerc0826_slice-5200-6700_0-patch/meshes/fitted \\
        --out-dir analysis/pherc0826
"""
from __future__ import annotations

import argparse
import glob
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
from umbilicus_data import interpolate, load_umbilicus  # noqa: E402
from volume_access import find_volume_path, open_group  # noqa: E402

CONVENTION_TEXT = (
    "Convention: native array orientation, row=y col=x, no flip, viewed looking "
    "along +z (same convention as render_axial_slices.py). Curve = fitted spiral "
    "mesh's cross-section at the target z, colour = winding index. Umbilicus is "
    "the measured/estimated control-point interpolation (umbilicus_data.py), not "
    "re-derived here."
)


def mesh_curve_at_z(meshes_dir: Path, target_z: float) -> np.ndarray:
    """Per-winding mesh output (w<NNN>/{x,y,z}.tif) -> (x, y, winding_idx)
    points whose z-column brackets target_z, linearly interpolated to it."""
    winding_dirs = sorted(
        d for d in glob.glob(f"{meshes_dir}/w*") if "_spliced" not in d
    )
    points = []
    for wdir in winding_dirs:
        widx = int(Path(wdir).name.lstrip("w"))
        z = tifffile.imread(f"{wdir}/z.tif")
        x = tifffile.imread(f"{wdir}/x.tif")
        y = tifffile.imread(f"{wdir}/y.tif")
        for col in range(z.shape[1]):
            zc = z[:, col]
            valid = zc > -1
            if valid.sum() < 2:
                continue
            zc_v = zc[valid]
            order = np.argsort(zc_v)
            zc_sorted = zc_v[order]
            if not (zc_sorted[0] <= target_z <= zc_sorted[-1]):
                continue
            xc_sorted = x[:, col][valid][order]
            yc_sorted = y[:, col][valid][order]
            xi = np.interp(target_z, zc_sorted, xc_sorted)
            yi = np.interp(target_z, zc_sorted, yc_sorted)
            points.append((xi, yi, widx))
    return np.array(points) if points else np.empty((0, 3))


def render_base_slice(sample_id: str, catalog: dict, target_z_full: int):
    zarr_path, _ = find_volume_path(catalog, sample_id)
    print(f"{sample_id}: opening {zarr_path} ...")
    group = open_group(zarr_path)
    level, scale = pick_level(group)
    arr = group[level]
    z_idx = max(0, min(arr.shape[0] - 1, round(target_z_full / scale)))
    print(f"  level {level} shape={arr.shape} scale={scale}x z_idx={z_idx}")
    slab = np.asarray(arr[z_idx, :, :])
    lo, hi = np.percentile(slab, [1, 99])
    disp = np.clip((slab.astype(np.float32) - lo) / max(hi - lo, 1), 0, 1)
    return disp, scale, level


def overlay_one(sample_id, sense, meshes_dir, target_z_full, base, scale, level, umbilicus, out_path):
    pts = mesh_curve_at_z(Path(meshes_dir), target_z_full)
    print(f"{sample_id} [{sense}]: {len(pts)} curve points from mesh at z={target_z_full}")

    fig, ax = plt.subplots(figsize=(9, 10.5), dpi=150)
    ax.imshow(base, cmap="gray", origin="upper")
    if len(pts):
        xs, ys, widx = pts[:, 0] / scale, pts[:, 1] / scale, pts[:, 2]
        sc = ax.scatter(xs, ys, c=widx, cmap="hsv", s=3, linewidths=0)
        cbar = fig.colorbar(sc, ax=ax, fraction=0.03, pad=0.02)
        cbar.set_label("winding index")
    else:
        ax.text(0.02, 0.94, "WARNING: no mesh curve intersects this z",
                 transform=ax.transAxes, color="red", fontsize=10, va="top",
                 bbox=dict(facecolor="black", alpha=0.6, pad=3))

    if umbilicus is not None:
        ux_full, uy_full = interpolate(umbilicus.points, target_z_full)
        ux, uy = ux_full / scale, uy_full / scale
        color = "orange" if umbilicus.is_estimated else "red"
        ax.plot(ux, uy, marker="o", color=color, markersize=14,
                 markerfacecolor="none", markeredgewidth=2)
        for dx0, dx1 in ((-25, -12), (12, 25)):
            ax.plot([ux + dx0, ux + dx1], [uy, uy], color=color, linewidth=1.5)
        for dy0, dy1 in ((-25, -12), (12, 25)):
            ax.plot([ux, ux], [uy + dy0, uy + dy1], color=color, linewidth=1.5)

    ax.set_title(
        f"{sample_id}  |  z={target_z_full}  |  spiral_outward_sense = {sense}  |  "
        f"fitted mesh cross-section over real slice (level {level}, x{scale})",
        fontsize=11,
    )
    ax.set_xlabel("x (right ->)")
    ax.set_ylabel("y (down v)")
    fig.text(0.02, 0.01, CONVENTION_TEXT, fontsize=6.5, wrap=True, va="bottom")
    fig.tight_layout(rect=[0, 0.05, 1, 1])
    fig.savefig(out_path)
    plt.close(fig)
    print(f"saved {out_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sample", required=True, help="e.g. PHerc0826")
    parser.add_argument("--target-z", type=int, required=True,
                         help="Full-resolution z, must fall inside every --run's fit window.")
    parser.add_argument("--run", action="append", required=True, dest="runs",
                         metavar="SENSE=MESHES_DIR",
                         help="Repeatable. SENSE is a label (e.g. catalog_ACW); "
                              "MESHES_DIR is that fit's meshes/fitted directory.")
    parser.add_argument("--out-dir", default=".")
    parser.add_argument("--catalog-url", default=FULL_CATALOG_URL)
    args = parser.parse_args()

    runs = dict(r.split("=", 1) for r in args.runs)

    print(f"Fetching catalog from {args.catalog_url} ...")
    catalog, _, _ = fetch_catalog(args.catalog_url)
    umbilicus = load_umbilicus(args.sample)
    if umbilicus is None:
        print(f"WARNING: no umbilicus file for {args.sample}; overlay will omit the marker.")

    base, scale, level = render_base_slice(args.sample, catalog, args.target_z)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for sense, meshes_dir in runs.items():
        out_path = out_dir / f"{args.sample}_z{args.target_z}_{sense}.png"
        overlay_one(args.sample, sense, meshes_dir, args.target_z, base, scale, level, umbilicus, out_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
