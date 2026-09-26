# Findings for the villa README PR and issue

Two observations from this build, stated as observations with no verdict --
neither is a claim that villa's code is wrong. Kept here so F4 (README PR)
and F5 (issue) can cite them with evidence rather than re-deriving them.

## Finding A: re-opening an already-opened catalog sample renders blank

**Observed:** `vc3d_open_catalog_sample` on a sample already opened earlier
in the same VC3D session returns success (`"opened": true`, correct scale
label, correct crosshair position at high zoom) but the viewport shows no
volume content, at any zoom including the exact default that rendered it
correctly the first time. The bridge itself stays healthy throughout (pings
respond normally); this is not a crash.

**Evidence:**
- `PHerc0826`: first open + screenshot at scale 0.05 -- content visible
  (`readings/vc3d_screenshots/PHerc0826_z9306.png`, committed earlier in
  this build). Re-opened later in the same session, same scale 0.05, same
  region -- blank (`analysis/vc3d-crash/reopen-blank-evidence/PHerc0826_reopened_blank_scale0.05.png`).
- `PHerc0813`: same pattern on a second, independent sample
  (`analysis/vc3d-crash/reopen-blank-evidence/PHerc0813_reopened_blank_scale0.05.png`),
  ruling out a PHerc0826-specific cause.
- The `open_catalog_sample` response itself is the tell: a first-time open
  reports `"attached": {"volumes": 1, ...}`; a repeat open of the same
  sample reports `"attached": {"volumes": 0, ...}` with a message
  `"Skipped <volume> (ome-zarr): already attached"`.

**Not established:** the exact internal cause (a stale reference to a
GPU-side resource evicted when a later sample was opened is a plausible
guess, not verified). No workaround short of a full VC3D relaunch was
found in this session.

## Finding B: villa's own convention and an independent estimator disagree on PHerc0826, and the estimator disagrees with itself

**Observed:** Two ways of predicting what PHerc0826's catalog-derived sense
(ACW) should look like on screen do not agree, and one of them is not even
internally consistent across the volume's own z-levels.

1. **Theoretical, from villa's own source** (`surface_orientation.py`'s
   `spiral_outward_sense_for` docstring + `transforms.py`'s
   `SpiralAndTransform._get_transform_parts`, which flips only x for ACW):
   predicts ACW should appear visually anticlockwise-outward at every
   z-level, in the convention row=y-down, col=x-right, viewed along +z.
   Derivation: `predicted_sense.py`.

2. **Independent, empirical** (`gmDevi/vc-windows-tools` `spiral_sense.py`,
   a structure-tensor estimate on the organizers' surface prediction, same
   stated convention: "visual clockwise = atan2(y-cy, x-cx) increasing, y
   down"): run against PHerc0826 at the same three z-levels used throughout
   this build --
   - z=5922: **CW** (disagrees with the ACW prediction)
   - z=9306: **ACW** (agrees)
   - z=12690: **CW** (disagrees)

**Evidence (images, our own umbilicus, same convention):**
- `readings/renders/PHerc0826_z5922_umbilicus_L1_12mm.png`
- `readings/renders/PHerc0826_z9306_umbilicus_L1_12mm.png`
- `readings/renders/PHerc0826_z12690_umbilicus_L1_12mm.png`

**Not established:** which of the two methods, if either, is right at any
given z-level; whether the estimator's own inconsistency is noise (a
structure-tensor estimate on a partial, imperfect sheet mask is expected to
be noisy per the tool's own documentation) or points to something real
about how the sense should be read near the ends of a volume versus its
middle. Both are stated as observations for a maintainer to weigh in on,
not as a claim that either transforms.py or spiral_sense.py is wrong.

## Anticipated, to confirm once the human readings are in: the #1736 estimator can land inside the sheet pack, not at the true core

**Not yet a finding -- a specific prediction being recorded before reading,
so it isn't a post-hoc rationalization if it happens.** `estimate_umbilicus.py`
(villa PR #1736, closed but not merged) takes the point of maximum
distance-to-boundary in the largest connected sheet-mask component as the
core. On a scroll crushed enough that the windings press together, that
point can fall inside the winding pack itself rather than at the true
central core, giving a plausible-looking but wrong center.

**Example to watch:** `PHerc0125` (a 2025-2026, tracks-only volume with no
published umbilicus), z=11462 --
`readings/renders/PHerc0125_z11462_umbilicus_L1_12mm.png`. The estimated
umbilicus crosshair does not sit at an obviously converging center; the
surrounding fiber pattern looks locally dense and directionless rather than
showing clean radial convergence.

If the reading pass comes back with several "unsure, core not resolvable
at this scale" among the 12 estimated-umbilicus volumes, that is the
predicted outcome landing, not a gap in this build's method -- worth a
line in the README PR (F4) about the estimator's known limitation on
crushed scrolls, citing this image.
