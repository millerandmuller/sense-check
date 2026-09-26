"""Predict what a catalog-derived CW/ACW sense should look like in our own
render's pixel convention (row = y, increasing down; col = x, increasing
right; viewed looking along +z), so a reading is a direct visual comparison
instead of a mental rotation.

Derivation, from villa's own source at f4570bf:

1. spiral-fitting/surface_orientation.py, spiral_outward_sense_for docstring:
   "in a right-handed, top-to-bottom volume the spiral winds outwards against
   atan2(y, x), the mirror of the fit's canonical spiral (CW, radius growing
   with atan2(y, x))". So the fit's own canonical convention defines CW as:
   radius grows as atan2(y, x) increases, in the fit's "slice space" (y, x).

2. spiral-fitting/transforms.py, SpiralAndTransform._get_transform_parts:

       if self.spiral_outward_sense == 'CW':
           maybe_flip = []
       else:
           assert self.spiral_outward_sense == 'ACW'
           # To make spiral go anticlockwise in slice space (going outwards
           # from the centre), flip it horizontally
           maybe_flip = [AffineTransform(scale=[1., 1., -1.])]  # zyx -> flips x

   So spiral_outward_sense is applied as a single flip of x in slice space;
   z and y are untouched. CW is the unflipped, canonical case.

3. gmDevi/vc-windows-tools tools/spiral_sense.py (MIT, independent) states the
   same fit convention in explicit screen terms: "visual clockwise =
   atan2(y-cy, x-cx) increasing, y down" -- i.e. the fit's (y, x) in point 1
   is screen/array (row, col) with row down, exactly our render's convention.

Putting these together: spiral_outward_sense's CW/ACW *is* the visual
CW/ACW of a slice rendered with row=y-down, col=x-right, viewed along +z --
no rotation or extra mirroring needed. predicted_visual_sense(derived_sense)
is therefore the identity.

CAVEAT (the part that could be the README PR finding): step 3 establishes
that gmDevi read the fit's "slice space" the same way we do, but neither
surface_orientation.py nor transforms.py itself says outright that "slice
space" is pixel-identical to the raw zarr array's own (z, y, x) indexing (no
axis permutation, no flip) -- that identity is inferred from how the fit
consumes/exports slices, not stated as a contract. An empirical spot-check
(gmDevi's spiral_sense.py, run against our own umbilicus, PHerc0826, three
z-levels) came back ACW/CW/CW rather than ACW/ACW/ACW -- inconsistent with
itself, not just with the prediction. That is consistent with the tool's own
documented weakness (structure-tensor estimate on a partial sheet mask,
noisy per-slice) rather than evidence against the mapping above, but it
means this session could not get a clean three-for-three empirical
confirmation. Treat the identity mapping as well-sourced but not
independently proven; a maintainer confirming or correcting it would itself
be a useful documentation contribution.
"""
from __future__ import annotations

from typing import Optional


def predicted_visual_sense(derived_sense: Optional[str]) -> Optional[str]:
    """derived_sense is the catalog's spiral_outward_sense_for() output
    ("CW", "ACW", or None for UNDERIVABLE). Returns the sense a reader should
    see, in our own render/screenshot pixel convention, or None if
    undefined."""
    if derived_sense not in ("CW", "ACW"):
        return None
    return derived_sense


VISUAL_CONVENTION_NOTE = (
    "Predicted visual sense assumes slice-space (villa transforms.py, "
    "surface_orientation.py) is pixel-identical to this render/screenshot's "
    "own axes (row=y down, col=x right, viewed along +z) -- inferred, not "
    "villa-confirmed; see predicted_sense.py docstring for the derivation "
    "and an inconclusive empirical spot-check."
)
