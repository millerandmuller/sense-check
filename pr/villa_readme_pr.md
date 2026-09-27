<!--
Drafted for spiral-fitting/README.md at ScrollPrize/villa. Uses villa's own
pull_request_template.md structure verbatim. Not submitted; a draft for the
human maintainer of this repo to review and file.
-->

**In one sentence:** Add a short note after the `spiral_outward_sense`
fallback ("read off the CT data by a person in VC3D, or from an
already-fitted spiral") warning that on the 2025/2026 First Letters
eligible scrolls that fallback is often unreliable, fitting does not
discriminate the two senses either, and the catalog data the fallback
depends on is itself incomplete.

**One real example:** Starting with `PHerc0490A` (a First Letters eligible
volume, `metadata.json`, fetched fresh from
`vesuvius-challenge-open-data.s3.amazonaws.com`), I looked up its catalog
entry and found `z_direction_is_top_to_bottom: null`, `left_handed_coordinates:
false` — `spiral_outward_sense` cannot be derived per the README's own
rule, exactly the case this note is about — and it produced the same
result the minified catalog (`metadata.min.json`) produces for all 23
eligible volumes: neither key is present at all in the minified file, so
nothing about sense can be derived from it for any of them, not just the
5 with a null field in the full catalog.

**Before:** The scroll-specification section says, without qualification,
that when the two catalog properties are absent `spiral_outward_sense` "is
required and is read off the CT data by a person in VC3D, or from an
already-fitted spiral" — implying both fallbacks are dependable.

**After this PR:** A short note directly under that bullet, stating
plainly that (1) a blind single-slice human read was "unsure" on 21 of 23
First Letters eligible volumes in an independent test, (2) fitting the
spiral both ways and comparing satisfaction does not discriminate the two
senses either, confirmed at 1,500 and again at 30,000 steps on two
independent scrolls, and (3) the catalog properties this whole fallback
chain starts from are null for 5 of the 23 eligible volumes in the full
catalog and absent entirely from the minified catalog — so anyone working
from `metadata.min.json` should know before they start that
`spiral_outward_sense` cannot be derived from it for any First Letters
eligible volume.

**Proof:** `table/orientation.md` (all 23 volumes, catalog sense vs. CT
reading, reader disclosure) and the project notes 2026-09-26/27 (four
equal-step fits, 1,500 and 30,000 steps, two scrolls, tie at every
checkpoint) at `millerandmuller/sense-check`.

**Why / where this is useful:** Anyone fitting a First Letters eligible
scroll without an already-known sense hits this exact fallback chain. The
note tells them up front, before they spend a read-and-fit cycle finding
out the hard way, that both suggested fallbacks are weaker than the
current wording implies for this scroll generation specifically, and to
check the full catalog rather than the minified one.

- [x] I personally verified that the example and proof above were
  produced by this PR on the stated data: `metadata.json` and
  `metadata.min.json` fetched directly from the S3 bucket and checked
  against all 23 eligible volumes' catalog records; the reading and
  fitting results are this session's own work, committed at the commits
  cited in the project notes.

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
  > On the 2025/2026 First Letters eligible scrolls, be aware that both of
  > the above fallbacks have known limits: a blind single-slice human read
  > was "unsure" for 21 of 23 eligible volumes in an independent test
  > (millerandmuller/sense-check, `table/orientation.md`), and re-fitting
  > the spiral both ways does not reliably discriminate the two senses
  > either — four fits (two scrolls, both senses) at 1,500 and again at
  > 30,000 steps tied at every checkpoint (the project notes in the same
  > repo). Also note that `metadata.min.json` omits
  > `z_direction_is_top_to_bottom` and `left_handed_coordinates` entirely
  > for every sample; use the full `metadata.json` if you need these
  > fields.
```

**Scope note:** this is a documentation-only change — a caution added
next to existing guidance, not a claim that the guidance itself, or
villa's rule for deriving `spiral_outward_sense`, is wrong. The evidence
behind it (readings, fits, catalog fetch) is committed at
`millerandmuller/sense-check`, a separate, private-until-submission repo
for this month's Vesuvius Challenge Progress Prize entry; the PR itself
would carry no reference to that repo's internal process, only to the
public findings a maintainer can verify independently (the open-data
catalog is public; the reading and fitting methodology is described
plainly enough to reproduce).

**Not proposed here:** any change to `surface_orientation.py`'s derivation
rule, to `fit_spiral.py`, or to the catalog data itself — see the
companion issue draft (`villa_issue.md`) for the underlying findings this
note summarizes, including the two VC3D bugs encountered while gathering
this evidence.
