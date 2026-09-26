"""Load umbilicus control points for a sample, real or estimated.

umbilicus/<sample>_umbilicus.json       -- measured (herculaneum-umbilici, MIT,
                                            or our own August PHerc0826 data)
umbilicus/estimated/<sample>_est.json   -- estimated (gmDevi/vc-windows-tools,
                                            MIT, from villa PR #1736; PHerc0211
                                            and PHerc0846B run fresh with the
                                            same estimate_umbilicus.py script)

See umbilicus/NOTICE.md for exact sources per volume.
"""
from __future__ import annotations

from pathlib import Path
from typing import NamedTuple, Optional

UMBILICUS_DIR = Path(__file__).parent / "umbilicus"
ESTIMATED_DIR = UMBILICUS_DIR / "estimated"


class Umbilicus(NamedTuple):
    points: list[dict]  # sorted by z, each {"x", "y", "z", "score"}
    is_estimated: bool


def load_umbilicus(sample_id: str) -> Optional[Umbilicus]:
    real_path = UMBILICUS_DIR / f"{sample_id}_umbilicus.json"
    est_path = ESTIMATED_DIR / f"{sample_id}_est.json"
    if real_path.exists():
        path, is_estimated = real_path, False
    elif est_path.exists():
        path, is_estimated = est_path, True
    else:
        return None
    import json
    doc = json.loads(path.read_text())
    points = sorted(doc["control_points"], key=lambda p: p["z"])
    return Umbilicus(points=points, is_estimated=is_estimated)


def interpolate(points: list[dict], z_target: float) -> tuple[float, float]:
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
