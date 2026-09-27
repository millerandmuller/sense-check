**In one sentence:** For the 23 First Letters eligible volumes, the catalog
is missing the fields `spiral_outward_sense` is derived from on 5 of them
(and on all of them via the minified catalog); a static single-crop AI
read — descriptions checked against the images by Chris Müller — settled
none of the 23; and fitting the spiral both ways and comparing
satisfaction does not discriminate it either, on the two scrolls tested —
a fitted spiral reports back the sense it was given, not an independent
signal.

**I was trying to:** Determine `spiral_outward_sense` for all 23 First
Letters eligible volumes, to write correct `spiral-scroll.json` files for
each and, for one of them (PHerc0826), resolve a disagreement with an
existing (August 2026) community fit that had settled on the opposite
sense from the catalog's own derivation.

**Using:** villa at commit `f4570bf` (PR #1899, "Spiral orientation"),
`surface_orientation.py`'s `spiral_outward_sense_for` rule, the open-data
catalog (`metadata.json` and `metadata.min.json`, fetched directly from
`vesuvius-challenge-open-data.s3.amazonaws.com`), and `fit_spiral.py`
re-fit both senses of PHerc0826 and PHerc0813 at 1,500 and 30,000 steps
each (tracks-only, patches and outer-shell disabled, RTX 3090).

**What happened:**
1. **Catalog:** 5 of the 23 eligible volumes (`PHerc0125`, `PHerc0490A`,
   `PHerc0490B`, `PHerc0846A`, `PHerc1203`) have
   `z_direction_is_top_to_bottom: null` in the full catalog, so
   `spiral_outward_sense_for` returns `None` (UNDERIVABLE) for them.
   Checked separately: `metadata.min.json` omits both
   `z_direction_is_top_to_bottom` and `left_handed_coordinates` from every
   sample's volume properties, for all 23, not just those 5 — anyone
   working from the minified catalog alone cannot derive sense for any
   First Letters eligible volume.
2. **Reading:** a static single-crop read (12mm/4mm umbilicus crops, one
   AI reader; descriptions checked against the images by Chris Müller)
   settled none of the 23 volumes. Umbilicus crops for the 5
   catalog-UNDERIVABLE volumes, the ones this issue is mainly about:
   [`PHerc0125`](https://github.com/millerandmuller/sense-check/blob/main/readings/renders/PHerc0125_z11462_umbilicus_L1_12mm.png) ·
   [`PHerc0490A`](https://github.com/millerandmuller/sense-check/blob/main/readings/renders/PHerc0490A_z8774_umbilicus_L1_12mm.png) ·
   [`PHerc0490B`](https://github.com/millerandmuller/sense-check/blob/main/readings/renders/PHerc0490B_z7986_umbilicus_L1_12mm.png) ·
   [`PHerc0846A`](https://github.com/millerandmuller/sense-check/blob/main/readings/renders/PHerc0846A_z10514_umbilicus_L1_12mm.png) ·
   [`PHerc1203`](https://github.com/millerandmuller/sense-check/blob/main/readings/renders/PHerc1203_z10437_umbilicus_L1_12mm.png)
   (full set, all z-levels, both crop sizes, in `readings/renders/` at
   `millerandmuller/sense-check`).
3. **Fitting:** re-fit both senses of PHerc0826 (catalog ACW vs. explicit
   CW) and PHerc0813 (catalog CW vs. explicit ACW) at 1,500 steps, then
   again at 30,000 steps via staged checkpoint-resume (same optimizer/LR
   state carried through, not restarted). `satisfied_tracks_fraction`
   ties on both scrolls at both step counts, and the small gap between
   senses **flips direction** between 1,500 and 30,000 steps on both
   scrolls (PHerc0826: catalog leads by 0.07pp at 1.5k, contradicting
   leads by 0.11pp at 30k; PHerc0813: same pattern, opposite starting
   leader). A companion check comparing the two senses' fitted point
   clouds directly found them close (~15 voxel median separation, ~140
   µm) but not identical, with the winding parametrization's direction of
   travel cleanly reversed between senses — consistent with
   `spiral_outward_sense` doing real work, just not work that this
   fitting/reading combination can use to tell which value is correct.

**What I expected or needed:** Some reliable way to determine sense for a
First Letters eligible volume when the catalog's own two fields are
absent, given the README's stated fallbacks ("read off the CT data by a
person in VC3D, or from an already-fitted spiral"). The already-fitted-
spiral fallback did not hold up in this test; the person-in-VC3D fallback
was not tested here.

**Evidence / reproduction:** `table/orientation.md` (all 23 volumes,
catalog sense vs. CT reading, reader disclosure) and
`analysis/pherc0826/README.md` (the PHerc0826 case in full: four
equal-step fits, geometry and render comparison, with overlay images),
both at `millerandmuller/sense-check` (this month's independent
submission repo; public data and reproducible methodology, cited here
rather than embedded, since the repo itself is project-specific).

- [x] I personally encountered or reproduced this using the version and
  data stated above.

## Details

This does not claim `surface_orientation.py`'s rule, the catalog data, or
any specific reading is wrong — three separate hypotheses for PHerc0826's
specific catalog-vs-community-fit disagreement remain open (reading
wrong, catalog flag wrong, or the rule's own convention wrong;
see `analysis/pherc0826/README.md` in the repo above for the full
treatment, including a fourth hypothesis — that sense changes only the
export parametrization, not the fitted geometry — which is itself only
half-confirmed). This issue is about the practical gap: for roughly a
fifth of the First Letters eligible set, and for a real, tested example
of the disagreement, none of the documented ways to determine sense
actually resolve it. A documentation PR addressing the README's wording
around this is drafted separately (`villa_readme_pr.md` in the same
repo).
