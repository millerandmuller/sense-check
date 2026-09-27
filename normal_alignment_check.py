#!/usr/bin/env python3
"""Sample the fitted spiral surface's local normal direction against the
real lasagna nx/ny normal field, along one full winding at the fit window's
middle z, and report the mean and minimum cosine alignment.

This is an independent geometric check, run on the FINAL fitted mesh output
(not during training): a wrong-handed spiral pays for it once per turn at a
sheet jump, which shows up as a periodic dip in this alignment as theta goes
around the ring -- something an eyeballed overlay cannot show.

Simplification, stated explicitly: villa's own training-time `dense_normals`
loss (spiral-fitting/losses.py, iter_lasagna_losses) compares a full 3D
scroll-space radial covector (pulled back through the fit's differentiable
transform) against the real 3D decoded normal (nz, ny, nx), using an
epsilon finite difference. This script does not have access to that live
transform object -- it only has the exported per-winding mesh grids
(w<NNN>/{x,y,z}.tif). It approximates the same radial covector by the
finite difference between the SAME theta-column of two adjacent windings'
meshes at the same z (a one-winding-step secant instead of an infinitesimal
one), and compares only the in-plane (x, y) component of both the fitted
and the real normal (dropping z-tilt on both sides for a fair comparison).
This is coarser than villa's own loss but uses the same decode convention
(losses.py:_decode_uint8_normal) and the same undirected |cos| comparison,
and is expected to catch the same class of handedness/sheet-jump error.

Run with the villa venv (has zarr + tifffile already):
    /workspace/villa/spiral-fitting/.venv/bin/python normal_alignment_check.py \\
        --meshes-dir /workspace/out/PHerc0826_ACW_30k/.../meshes/fitted \\
        --dataset-root /workspace/data/PHerc0826 \\
        --nx-path lasagna_inputs/PHerc0826_nx.ome.zarr \\
        --ny-path lasagna_inputs/PHerc0826_ny.ome.zarr \\
        --lasagna-scale 4 --normal-zarr-group 2 \\
        --z-mid 5950 --label "PHerc0826 ACW 30k" \\
        --out-csv analysis_normal_check_PHerc0826_ACW.csv
"""
from __future__ import annotations

import argparse
import glob
from pathlib import Path

import numpy as np
import tifffile
import zarr


def decode_uint8_normal_xy(nx_u8: np.ndarray, ny_u8: np.ndarray):
    """losses.py:_decode_uint8_normal, in-plane (x, y) component only."""
    valid = (nx_u8 != 0) | (ny_u8 != 0)
    nx = (nx_u8.astype(np.float64) - 128.0) / 127.0
    ny = (ny_u8.astype(np.float64) - 128.0) / 127.0
    return nx, ny, valid


def list_windings(meshes_dir: Path) -> list[int]:
    dirs = [d for d in glob.glob(f"{meshes_dir}/w*") if "_spliced" not in d]
    indices = sorted(int(Path(d).name.lstrip("w")) for d in dirs)
    return indices


def curve_xy_at_z(meshes_dir: Path, widx: int, target_z: float):
    """Per-column (x, y) at target_z for one winding, matching
    overlay_fit_on_slice.py's mesh_curve_at_z column-interpolation, but
    keeping every column's result indexed (None where z doesn't bracket)."""
    wdir = meshes_dir / f"w{widx:03d}"
    z = tifffile.imread(wdir / "z.tif")
    x = tifffile.imread(wdir / "x.tif")
    y = tifffile.imread(wdir / "y.tif")
    n_cols = z.shape[1]
    xs = np.full(n_cols, np.nan)
    ys = np.full(n_cols, np.nan)
    for col in range(n_cols):
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
        xs[col] = np.interp(target_z, zc_sorted, xc_sorted)
        ys[col] = np.interp(target_z, zc_sorted, yc_sorted)
    return xs, ys


def resample_by_theta_fraction(xs: np.ndarray, ys: np.ndarray, n_samples: int):
    """Different windings discretize theta with different column counts (an
    outer winding's mesh has more columns than an inner one), so column index
    isn't a shared ordinate. Reindex both by fraction-of-full-turn (assumes
    each winding's own columns are uniformly spaced in theta, which is the
    export convention) onto a common grid of n_samples fractions."""
    n_cols = xs.shape[0]
    col_frac = np.arange(n_cols) / n_cols
    valid = np.isfinite(xs) & np.isfinite(ys)
    if valid.sum() < 2:
        return np.full(n_samples, np.nan), np.full(n_samples, np.nan)
    target_frac = np.arange(n_samples) / n_samples
    # Wrap-around interpolation: a full turn is periodic in theta.
    xs_p = np.interp(target_frac, col_frac[valid], xs[valid], period=1.0)
    ys_p = np.interp(target_frac, col_frac[valid], ys[valid], period=1.0)
    return xs_p, ys_p


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--meshes-dir", required=True)
    p.add_argument("--dataset-root", required=True)
    p.add_argument("--nx-path", required=True, help="relative to dataset-root")
    p.add_argument("--ny-path", required=True, help="relative to dataset-root")
    p.add_argument("--lasagna-scale", type=float, required=True)
    p.add_argument("--normal-zarr-group", default="2")
    p.add_argument("--z-mid", type=float, required=True)
    p.add_argument("--label", required=True)
    p.add_argument("--out-csv", required=True)
    p.add_argument("--num-theta-samples", type=int, default=360)
    args = p.parse_args()

    meshes_dir = Path(args.meshes_dir)
    windings = list_windings(meshes_dir)
    if len(windings) < 2:
        raise SystemExit(f"error: fewer than 2 windings found in {meshes_dir}")
    mid_pos = len(windings) // 2
    k = windings[mid_pos]
    k_next = windings[mid_pos + 1] if mid_pos + 1 < len(windings) else windings[mid_pos - 1]
    print(f"{args.label}: using winding pair w{k:03d} / w{k_next:03d} out of "
          f"{len(windings)} windings [{windings[0]}..{windings[-1]}] at z={args.z_mid}")

    x1_raw, y1_raw = curve_xy_at_z(meshes_dir, k, args.z_mid)
    x2_raw, y2_raw = curve_xy_at_z(meshes_dir, k_next, args.z_mid)
    x1, y1 = resample_by_theta_fraction(x1_raw, y1_raw, args.num_theta_samples)
    x2, y2 = resample_by_theta_fraction(x2_raw, y2_raw, args.num_theta_samples)

    # Only the numbered pyramid level was mirrored (no root .zgroup for the
    # multiscale group), so open that level's array directly rather than
    # opening the parent as a group and indexing into it.
    nx_group = zarr.open_array(f"{args.dataset_root}/{args.nx_path}/{args.normal_zarr_group}", mode="r")
    ny_group = zarr.open_array(f"{args.dataset_root}/{args.ny_path}/{args.normal_zarr_group}", mode="r")
    shape = nx_group.shape

    rows = []
    for col in range(x1.shape[0]):
        if not (np.isfinite(x1[col]) and np.isfinite(x2[col])):
            continue
        dx, dy = x2[col] - x1[col], y2[col] - y1[col]
        norm = np.hypot(dx, dy)
        if norm < 1e-6:
            continue
        fit_nx, fit_ny = dx / norm, dy / norm

        mid_x, mid_y = (x1[col] + x2[col]) / 2, (y1[col] + y2[col]) / 2
        zi = int(round(args.z_mid / args.lasagna_scale))
        yi = int(round(mid_y / args.lasagna_scale))
        xi = int(round(mid_x / args.lasagna_scale))
        if not (0 <= zi < shape[0] and 0 <= yi < shape[1] and 0 <= xi < shape[2]):
            continue
        nx_u8 = int(nx_group[zi, yi, xi])
        ny_u8 = int(ny_group[zi, yi, xi])
        real_nx, real_ny, valid = decode_uint8_normal_xy(
            np.array(nx_u8), np.array(ny_u8))
        if not valid:
            continue
        real_norm = np.hypot(real_nx, real_ny)
        if real_norm < 1e-6:
            continue
        real_nx, real_ny = real_nx / real_norm, real_ny / real_norm

        cosine = abs(fit_nx * real_nx + fit_ny * real_ny)
        rows.append((col, mid_x, mid_y, cosine))

    if not rows:
        raise SystemExit("error: no valid samples along this ring -- nothing to report")

    cosines = np.array([r[3] for r in rows])
    print(f"{args.label}: {len(rows)}/{x1.shape[0]} columns valid; "
          f"mean cosine={cosines.mean():.4f}  min cosine={cosines.min():.4f}  "
          f"(dip threshold reference: <0.5 ~ 60deg+ misalignment)")

    with open(args.out_csv, "w") as f:
        f.write("col,mid_x,mid_y,cosine\n")
        for col, mx, my, c in rows:
            f.write(f"{col},{mx:.2f},{my:.2f},{c:.4f}\n")
    print(f"saved {args.out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
