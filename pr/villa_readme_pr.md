<!--
Drafted for spiral-fitting/README.md at ScrollPrize/villa. Uses villa's own
pull_request_template.md structure verbatim. Not submitted; a draft for the
human maintainer of this repo to review and file.
-->

**In one sentence:** Add a short note after the `spiral_outward_sense`
fallbacks ("read off the CT data by a person in VC3D, or from an
already-fitted spiral") stating that the second fallback is circular — a
fitted spiral reports back the sense it was given — and that the catalog
data this whole chain starts from is incomplete for 5 of the 23 First
Letters eligible volumes.

**One real example:** Starting with `PHerc0490A` (a First Letters eligible
volume, `metadata.json`, fetched fresh from
`vesuvius-challenge-open-data.s3.amazonaws.com`), I looked up its catalog
entry and found `z_direction_is_top_to_bottom: null`, `left_handed_coordinates:
false` — `spiral_outward_sense` cannot be derived per the README's own
rule, exactly the case this note is about.

**Before:** The scroll-specification section says, without qualification,
that when the two catalog properties are absent `spiral_outward_sense` "is
required and is read off the CT data by a person in VC3D, or from an
already-fitted spiral" — implying both fallbacks are dependable.

**After this PR:** A short note directly under that bullet, stating
plainly that (1) a static single-crop read by an AI reader (Claude, from
the 12 mm/4 mm umbilicus crops, blind to the predicted sense; not
reviewed by a person) was inconclusive on 21 of 23 First Letters eligible
volumes in an independent test — this crop read did not exercise villa's
documented person-in-VC3D fallback, so this PR makes no claim about that
fallback's reliability, (2) fitting the spiral both ways and comparing
satisfaction does not discriminate the two senses either, confirmed at
1,500 and again at 30,000 steps on two independent scrolls, and (3) the
catalog properties this whole fallback chain starts from are null for 5
of the 23 eligible volumes in the full catalog (`metadata.min.json` omits
both for all 23, by design — it's the scrollprize.org Atlas's field
subset, not a bug).

**Proof:** `table/orientation.md` (all 23 volumes, catalog sense vs. CT
reading, reader disclosure) and `analysis/pherc0826/README.md` (four
equal-step fits, 1,500 and 30,000 steps, two scrolls, tie at every
checkpoint, with overlay images and the raw per-checkpoint numbers) at
`millerandmuller/sense-check`.

**Why / where this is useful:**
<!-- Lutfiya writes this paragraph herself before filing (CONTRIBUTING.md: human-written motivation) -->

- [ ] I personally verified that the example and proof above were
  produced by this PR on the stated data: `metadata.json` and
  `metadata.min.json` fetched directly from the S3 bucket and checked
  against all 23 eligible volumes' catalog records; the reading and
  fitting results are committed and reproducible in
  `millerandmuller/sense-check`.
  <!-- Lutfiya ticks this after running the example herself -->

## Details

**Target file:** `spiral-fitting/README.md`, "Scroll specification
(spiral-scroll.json)" section, at the current text (verified against
`ref=f4570bf`, the commit this whole investigation was pinned to,
itself PR #1899):

```markdown
- `spiral_outward_sense` — `"CW"` or `"ACW"` (case-insensitive). Derived from
  the two catalog properties when both are present, and then only needed as a
  cross-check (a mismatch is an error). Without them it is required and is
  read off the CT data by a person in VC3D, or from an already-fitted spiral.
```

**Proposed addition**, immediately after that bullet:

```markdown
  > A fitted spiral carries the sense it was fitted with; fitting both
  > senses and comparing `satisfied_tracks_fraction` did not discriminate
  > them in the tested configuration (tracks-only, two scrolls, 1,500 and
  > 30,000 steps). Five eligible First Letters volumes have no catalog
  > z-direction and need a person in VC3D.
```

**Not proposed here:** any change to `surface_orientation.py`'s derivation
rule, to `fit_spiral.py`, or to the catalog data itself — see the
companion issue draft (`villa_issue.md`) for the underlying findings this
note summarizes, including the two VC3D bugs encountered while gathering
this evidence.

Complements #1837 (gmDevi, tracks-only recipe), which does not touch this
bullet.
