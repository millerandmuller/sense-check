# Umbilicus sources

All 23 eligible volumes now have an umbilicus, real or estimated; every
image and `readings.json` row says which (`umbilicus_source`).

## Measured (11, this directory)

Community hand-annotated polylines for 10 volumes, copied from
[herculaneum-umbilici](https://github.com/AlexeyDrobkovStrikesBack/herculaneum-umbilici)
(MIT License, Copyright (c) 2026 Alexey Drobkov):

PHerc0191, PHerc0257, PHerc0268, PHerc0358, PHerc0800, PHerc0813, PHerc1203,
PHerc1218, PHerc1447, PHerc1545.

PHerc0826's umbilicus is our own, verified during the August 2026 entry
([first-light-pherc0826](https://github.com/millerandmuller/first-light-pherc0826)).

## Estimated (12, `estimated/`)

From the organizers' surface prediction via `estimate_umbilicus.py`
(max distance-to-boundary of the largest sheet-mask component, per z):
10 fetched directly from
[gmDevi/vc-windows-tools](https://github.com/gmDevi/vc-windows-tools)
`results/umbilici/` (MIT License, Copyright (c) 2026 Gennaro Marco
Devincenzis and contributors; the script and results originate from villa
PR [#1736](https://github.com/ScrollPrize/villa/pull/1736), closed but not
merged) — PHerc0125, PHerc0175A, PHerc0175B, PHerc0306B, PHerc0343,
PHerc0483A, PHerc0483B, PHerc0490A, PHerc0490B, PHerc0846A. The other 2,
PHerc0211 and PHerc0846B, were not in that repo's results and were run
fresh with the same script (`tools/estimate_umbilicus.py`) against those
volumes' own surface predictions.

Per [C-11], PHerc0125 and PHerc0211 also have an approximate umbilicus
bruniss posted in the Vesuvius Discord `#general` on 2026-08-08; this repo
does not have a copy of that one and uses the estimated one instead.

## Format

`{"control_points": [{"x": int, "y": int, "z": int, "score": int}, ...],
"metadata": {...}}`, roughly one point every 100-1500 z depending on
source, interpolated linearly between points.
