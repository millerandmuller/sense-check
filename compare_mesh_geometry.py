#!/usr/bin/env python3
"""Compare two same-scroll, different-sense 30k-step fitted meshes as raw
point sets, testing the hypothesis that spiral_outward_sense changes only
the export parametrization (winding/U direction), not the fitted surface
geometry itself.

Two checks:
1. Symmetric nearest-neighbour distance between the two point clouds
   (median, 95th percentile, max, in voxels). Same surface within a voxel
   or two -> pure orientation/parametrization switch, not a different fit.
2. U-direction check: for a representative winding, does column index
   correlate with increasing or decreasing physical angle (theta) around
   the umbilicus? If this correlation sign differs between the two
   fits, the sense flips which way U runs even though the surface itself
   may be identical.

Run via: uv run --with tifffile --with numpy --with scipy python3 compare_mesh_geometry.py \\
    --meshes-a <dir-a>/meshes/fitted --meshes-b <dir-b>/meshes/fitted \\
    --label-a catalog --label-b contradicting --umbilicus-xy X,Y
"""
from __future__ import annotations

import argparse
import glob
from pathlib import Path

import numpy as np
import tifffile
from scipy.spatial import cKDTree


def list_windings(meshes_dir: Path) -> list[int]:
    dirs = [d for d in glob.glob(f"{meshes_dir}/w*") if "_spliced" not in d]
    return sorted(int(Path(d).name.lstrip("w")) for d in dirs)


def load_points(meshes_dir: Path, widx: int) -> np.ndarray:
    wdir = meshes_dir / f"w{widx:03d}"
    z = tifffile.imread(wdir / "z.tif").astype(np.float64)
    x = tifffile.imread(wdir / "x.tif").astype(np.float64)
    y = tifffile.imread(wdir / "y.tif").astype(np.float64)
    valid = z > -1
    return np.stack([x[valid], y[valid], z[valid]], axis=-1)


def load_all_points(meshes_dir: Path, windings: list[int], subsample: int) -> np.ndarray:
    parts = []
    for w in windings:
        pts = load_points(meshes_dir, w)
        if subsample > 1:
            pts = pts[::subsample]
        parts.append(pts)
    return np.concatenate(parts, axis=0)


def symmetric_nn_distance(a: np.ndarray, b: np.ndarray):
    tree_b = cKDTree(b)
    d_ab, _ = tree_b.query(a, k=1, workers=-1)
    tree_a = cKDTree(a)
    d_ba, _ = tree_a.query(b, k=1, workers=-1)
    d = np.concatenate([d_ab, d_ba])
    return {
        "median": float(np.median(d)),
        "p95": float(np.percentile(d, 95)),
        "max": float(np.max(d)),
        "n_a": int(a.shape[0]),
        "n_b": int(b.shape[0]),
    }


def u_direction_check(meshes_dir: Path, widx: int, ux: float, uy: float, target_z: float):
    """For one winding, at the row closest to target_z, does column index
    correlate with increasing or decreasing angle around (ux, uy)?"""
    wdir = meshes_dir / f"w{widx:03d}"
    z = tifffile.imread(wdir / "z.tif").astype(np.float64)
    x = tifffile.imread(wdir / "x.tif").astype(np.float64)
    y = tifffile.imread(wdir / "y.tif").astype(np.float64)
    n_cols = z.shape[1]
    cols, thetas = [], []
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
        xi = np.interp(target_z, zc_sorted, xc_sorted)
        yi = np.interp(target_z, zc_sorted, yc_sorted)
        theta = np.arctan2(yi - uy, xi - ux)
        cols.append(col)
        thetas.append(theta)
    cols = np.array(cols)
    thetas = np.unwrap(np.array(thetas))
    # Correlation sign between column index and unwrapped theta.
    corr = np.corrcoef(cols, thetas)[0, 1]
    return {"n_points": len(cols), "theta_col_correlation": float(corr),
            "direction": "increasing" if corr > 0 else "decreasing"}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--meshes-a", required=True)
    p.add_argument("--meshes-b", required=True)
    p.add_argument("--label-a", required=True)
    p.add_argument("--label-b", required=True)
    p.add_argument("--umbilicus-xy", required=True, help="X,Y for the U-direction check")
    p.add_argument("--target-z", type=float, required=True)
    p.add_argument("--subsample", type=int, default=4,
                   help="Take every Nth point per winding to bound point-cloud size")
    args = p.parse_args()

    ux, uy = (float(v) for v in args.umbilicus_xy.split(","))
    meshes_a, meshes_b = Path(args.meshes_a), Path(args.meshes_b)

    windings_a = list_windings(meshes_a)
    windings_b = list_windings(meshes_b)
    common = sorted(set(windings_a) & set(windings_b))
    print(f"windings: A={len(windings_a)} [{windings_a[0]}..{windings_a[-1]}], "
          f"B={len(windings_b)} [{windings_b[0]}..{windings_b[-1]}], common={len(common)}")

    pts_a = load_all_points(meshes_a, common, args.subsample)
    pts_b = load_all_points(meshes_b, common, args.subsample)
    print(f"point clouds: A={pts_a.shape[0]} points, B={pts_b.shape[0]} points (subsample={args.subsample})")

    nn = symmetric_nn_distance(pts_a, pts_b)
    print(f"symmetric nearest-neighbour distance (voxels): "
          f"median={nn['median']:.3f} p95={nn['p95']:.3f} max={nn['max']:.3f}")

    mid = common[len(common) // 2]
    u_a = u_direction_check(meshes_a, mid, ux, uy, args.target_z)
    u_b = u_direction_check(meshes_b, mid, ux, uy, args.target_z)
    print(f"U-direction check (winding w{mid:03d}, z={args.target_z}, umbilicus=({ux},{uy})):")
    print(f"  {args.label_a}: {u_a['n_points']} pts, corr={u_a['theta_col_correlation']:.4f}, "
          f"column index runs {u_a['direction']} theta")
    print(f"  {args.label_b}: {u_b['n_points']} pts, corr={u_b['theta_col_correlation']:.4f}, "
          f"column index runs {u_b['direction']} theta")
    same_dir = u_a["direction"] == u_b["direction"]
    print(f"  -> U direction is {'THE SAME' if same_dir else 'FLIPPED'} between {args.label_a} and {args.label_b}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
