# Sense hypothesis test: geometry + render comparison (2026-09-27)

Testing whether `spiral_outward_sense` changes only the export
parametrization (winding/U direction) rather than the fitted surface
itself, on both scrolls' 30,000-step catalog-vs-contradicting fit pairs.
See the project notes for the full writeup; this file is the raw numbers.

## Geometry (compare_mesh_geometry.py)

| Scroll | Symmetric NN distance (voxels): median / p95 / max | U-direction correlation (catalog / contradicting) | U-direction |
|---|---|---|---|
| PHerc0826 | 14.77 / 27.41 / 83.74 | +0.9993 / -0.9990 | flipped |
| PHerc0813 | 15.04 / 26.54 / 73.45 | -0.9995 / +0.9995 | flipped |

Voxel size 9.362 um, so ~15 voxels median = ~140 um. Not "within a voxel
or two," but small relative to the ~1500+ voxel z-window.

## Render (render_flattened_tifxyz.py + normalized cross-correlation)

Both 30k checkpoints per scroll flattened via villa's own
`flatten_spiral_checkpoint.py` (real Lasagna flatten optimization), then
rendered by sampling the real CT volume at each flattened grid point
(villa's `vc_render_tifxyz` could not be built here -- see script
docstring and the project notes for why -- this is a documented Python
substitute, not the original tool).

| Scroll | NCC as-is | NCC horizontal-flip | NCC vertical-flip | Mirrored? |
|---|---|---|---|---|
| PHerc0826 | 0.888 | 0.733 | 0.378 | No -- as-is wins |
| PHerc0813 | 0.928 | 0.768 | 0.472 | No -- as-is wins |

If sense only relabeled the same flattening, the horizontally-flipped
comparison should have scored highest. It didn't, on either scroll.
