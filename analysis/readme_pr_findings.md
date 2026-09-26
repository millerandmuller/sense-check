# Findings for the villa README PR and issue

Four observations from this build, stated as observations with no verdict --
none is a claim that villa's code, or anyone's tool, is wrong. Kept here so
F4 (README PR) and F5 (issue) can cite them with evidence rather than
re-deriving them.

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

## Finding C: the #1736 estimator lands 2-3mm off the visible core on at least 3 of the 12 estimated-umbilicus volumes

**This was a pre-registered prediction, now confirmed by the reading pass**
(the prediction, made before reading, is preserved below for the record).
`estimate_umbilicus.py` (villa PR #1736, closed but not merged) takes the
point of maximum distance-to-boundary in the largest connected sheet-mask
component as the core. On a scroll crushed enough that the windings press
together, or where the true core sits off that maximum, the estimate can
land beside the real center rather than on it.

**Observed, with a visible correct core beside the estimate:**
- `PHerc0175A`, z=4462: a clear spiral centre is visible off-target by
  ~2.5mm (`readings/renders/PHerc0175A_z4462_umbilicus_L1_12mm.png`).
- `PHerc0343`, z=9899 and z=13498: a crumpled centre and a clean spiral core
  with a hooked innermost sheet, both ~2-3mm right of the mark
  (`readings/renders/PHerc0343_z13498_umbilicus_L1_12mm.png`).
- `PHerc0846B`, z=4874: a large crumpled swirl visible ~2.5mm off the mark
  (`readings/renders/PHerc0846B_z4874_umbilicus_L1_12mm.png`).

Distinct from the other 8 estimated-umbilicus volumes (PHerc0125, 0490A,
0490B, 0846A, 0175B, 0306B, 0483A, 0483B), where no core was visible at all
near the estimate, on-target or not -- those may be genuinely crushed past
what a single slice can resolve, rather than a mislocated estimate.

**Not established:** whether the ~2-3mm offset pattern generalizes beyond
these three, or what in the sheet-mask geometry predicts it.

## Finding D: on these eligible scrolls, a single-slice visual read does not usually determine the sense

**Observed:** Of the 23 volumes read (one reader, blind to the catalog
prediction, from the 12mm/4mm umbilicus crops only -- see `readings/READING_SHEET.md`
disclosure and `table/orientation.md`), 21 came back "unsure." The common
reasons, by volume: the core is filled with debris rather than showing a
free inner terminus (e.g. PHerc0826, PHerc1218, PHerc1545), the innermost
material is crumpled fragments rather than one continuous wrap (PHerc0191,
PHerc0257, PHerc0358), or no core is visible at all near the umbilicus
(most of the 12 estimated-umbilicus volumes; see Finding C). Only 2 volumes
got a sense: `PHerc1203` (ACW, its only evidence, since the catalog cannot
derive one) and `PHerc0813` (ACW, low confidence) -- which disagrees with
PHerc0813's catalog-derived prediction of CW.

**Update after running the comparison (A1/A1b, see `analysis/pherc0826/` and
`analysis/pherc0813/`):** a single-slice visual read clearly does not
determine the sense on these scrolls (above), but the CW-vs-ACW overlay-fit
comparison this build tried as the presumed discriminator did not resolve
it either. Both PHerc0826 (catalog-ACW vs. explicit CW) and PHerc0813
(catalog-CW vs. explicit ACW) were re-fit both ways -- tracks-only, 1500
steps, patches/outer-shell disabled -- and on both scrolls the two fits are
visually indistinguishable and near-tied on `satisfied_tracks_fraction`,
with no consistent winner (catalog wins on PHerc0826 by 0.07pp; the
contradicting sense wins on PHerc0813 by 0.22pp, the opposite direction).
`spiral_outward_sense` is genuinely consumed in villa's fitting code
(`transforms.py`), so this is not a no-op config value; a single
from-scratch reduced fit over one z-window per hypothesis appears to be
under-constrained to separate the two senses either geometrically or by
this metric. See the project notes 2026-09-26 for the full comparison and
the options being weighed (longer fits, re-enabling outer-shell/patches
terms, a wider z-window) before either scroll's sense can be claimed
resolved by this method.

**Not established:** whether a different reader, a different z-level
choice, or VC3D's own interactive rotation (rather than a fixed axial
slice) would resolve more of the 21 unsure cases; this build only tested
fixed-axial-slice, single-reader reading.
