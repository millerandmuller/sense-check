# Sense Check

**Which way does each scroll turn — and can that even be determined —
for the 23 First Letters eligible volumes in the Vesuvius Challenge open
data?**

**A fitted spiral reports back the sense it was given — villa's
"already-fitted spiral" fallback is circular.** Tested on two scrolls,
tracks-only (patches and outer shell disabled), 1.5k and 30k steps; the
two senses' point clouds sit ~15 voxels apart, not identical.

## The 23 volumes

Of 23 readings: **23 unsure, 0 disagree, 0 agree.**

| Sample | Catalog | CT reading | Agree |
|---|---|---|---|
| PHerc0125 | UNDERIVABLE | unsure | n/a |
| PHerc0191 | CW | unsure | n/a |
| PHerc0211 | ACW | unsure | n/a |
| PHerc0257 | CW | unsure | n/a |
| PHerc0268 | CW | unsure | n/a |
| PHerc0358 | ACW | unsure | n/a |
| PHerc0800 | CW | unsure | n/a |
| PHerc0813 | CW | unsure | n/a |
| PHerc0826 | ACW | unsure | n/a |
| PHerc0175A | ACW | unsure | n/a |
| PHerc0175B | ACW | unsure | n/a |
| PHerc0306B | ACW | unsure | n/a |
| PHerc0343 | CW | unsure | n/a |
| PHerc0483A | ACW | unsure | n/a |
| PHerc0483B | CW | unsure | n/a |
| PHerc0490A | UNDERIVABLE | unsure | n/a |
| PHerc0490B | UNDERIVABLE | unsure | n/a |
| PHerc0846A | UNDERIVABLE | unsure | n/a |
| PHerc1203 | UNDERIVABLE | unsure | n/a |
| PHerc1218 | CW | unsure | n/a |
| PHerc1447 | ACW | unsure | n/a |
| PHerc1545 | ACW | unsure | n/a |
| PHerc0846B | CW | unsure | n/a |

> Reader: Readings by one AI reader (Claude), blind to the catalog's
> predicted sense; Chris Müller checked each row's description against
> its image, and the two direction claims that did not hold up were
> withdrawn.

Full table: `table/orientation.md`.

## Findings

**(i) 5 of 23 eligible volumes have no z-direction in the catalog.**
18/23 eligible (41/71 total) have both catalog fields sense needs; 5
don't — proof: `python3 catalog_orientation.py`. `metadata.min.json` is
the scrollprize.org Atlas's field subset of `metadata.json`
(`scrollprize.org/src/components/atlas/useAtlasData.js`), with no volume
properties; use `metadata.json`.

**(ii) A static single-crop AI read settled none of the 23**
(`analysis/readme_pr_findings.md` Finding D) — not a person-in-VC3D test.

**(iii) The equal-step retest retracts the August CW conclusion for
PHerc0826** (`analysis/pherc0826/README.md`).

| Fit | 1,500 steps | 30,000 steps |
|---|---|---|
| 0826 catalog (ACW) | 0.09691 | 0.09684 |
| 0826 contradicting (CW) | 0.09623 | 0.09791 |
| 0813 catalog (CW) | 0.16338 | 0.16317 |
| 0813 contradicting (ACW) | 0.16561 | 0.16207 |

Both scrolls tie at every checkpoint; the gap flips sign between 1.5k and
30k — noise, not signal.

### Found on the way

Two VC3D bugs. `stable` (`fc25b4d`) crashes opening a sample whose
lasagna representation triggers `resolveLasagnaForVolume`; fixed (PR
#1225) in `latest`, not yet in `stable`. Separately, re-opening a sample
renders blank:

![Re-opening PHerc0826 renders blank](analysis/vc3d-crash/reopen-blank-evidence/PHerc0826_reopened_blank_scale0.05.png)

Details: `analysis/vc3d-crash/README.md`, `pr/villa_issue.md`.

## Writing a scroll spec

villa's README says the two keys are hand-copied ("not covered by
scrollprize.org/tutorial_spiral"); this script does that and refuses when
it can't.

```
python3 write_scroll_spec.py <scroll> <volume>
python3 write_scroll_spec.py <scroll> <volume> --sense CW|ACW --reading-ref "<how you know>"
```

First form: the 18 derivable volumes. Second: required for the 5
UNDERIVABLE ones.

## Filed upstream

Drafts: `pr/villa_readme_pr.md` (PR), `pr/villa_issue.md` (issue) — not
yet opened.

## Limitations

- Readings by one AI reader; descriptions checked against the images by
  Chris Müller.
- Renders sample the CT in Python (`render_flattened_tifxyz.py`), not
  villa's `vc_render_tifxyz` (Qt6 unavailable).
- Not tested: what sense affects downstream (normal direction, recto/verso).
- PHerc0125 has a published umbilicus (used in villa #1837); our crops
  used an estimated one.

## Cost

~$8.84 — one RunPod RTX 3090, ~17 pod-hours at $0.52/h.

## AI-use disclosure

Code, fits, and this document were produced with AI assistance, directed
by Lutfiya Miller and Chris Müller. Readings by one AI reader;
descriptions checked against the images by Chris Müller.

## License

MIT. See `LICENSE`.
