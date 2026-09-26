"""Shared zarr access for eligible-volume renders (render_axial_slices.py,
render_umbilicus_crops.py): find a sample's ome-zarr path and open it
anonymously from the open-data S3 bucket.
"""
from __future__ import annotations

from typing import Any

from catalog_client import pick_eligible_volume

BUCKET = "vesuvius-challenge-open-data"


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


def open_group(zarr_path: str) -> Any:
    import s3fs
    import zarr
    fs = s3fs.S3FileSystem(anon=True)
    store = zarr.storage.FsspecStore(fs, path=f"{BUCKET}/{zarr_path}")
    return zarr.open_group(store=store, mode="r")
