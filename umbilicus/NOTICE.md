# Umbilicus sources

Community hand-annotated umbilicus polylines for 10 of the 23 eligible volumes,
copied from [herculaneum-umbilici](https://github.com/AlexeyDrobkovStrikesBack/herculaneum-umbilici)
(MIT License, Copyright (c) 2026 Alexey Drobkov):

PHerc0191, PHerc0257, PHerc0268, PHerc0358, PHerc0800, PHerc0813, PHerc1203,
PHerc1218, PHerc1447, PHerc1545.

PHerc0826's umbilicus is our own, verified during the August 2026 entry
([first-light-pherc0826](https://github.com/millerandmuller/first-light-pherc0826)).

The remaining 12 eligible volumes (PHerc0125, PHerc0211, PHerc0175A, PHerc0175B,
PHerc0306B, PHerc0343, PHerc0483A, PHerc0483B, PHerc0490A, PHerc0490B, PHerc0846A,
PHerc0846B) have no umbilicus file here. `render_axial_slices.py` renders their
slices without a marked umbilicus and says so on the image; per
[C-11], PHerc0125 and PHerc0211 have an approximate umbilicus bruniss posted
in the Vesuvius Discord `#general` on 2026-08-08 that this repo does not have
a copy of.

Format: `{"control_points": [{"x": int, "y": int, "z": int, "score": int}, ...]}`,
one point roughly every 100-200 z, interpolated linearly between points.
