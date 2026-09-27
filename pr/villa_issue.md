<!--
Two drafts for ScrollPrize/villa, using villa's own .github/ISSUE_TEMPLATE/issue.md
verbatim for each. Kept in one file for this project's own record; would be
filed as two separate GitHub issues (different problems, different areas of
the codebase) by the human maintainer of this repo.
-->

# Issue draft 1 of 2: sense (spiral_outward_sense) is unreliable to derive on 2025/2026 First Letters eligible scrolls

**In one sentence:** For the 23 First Letters eligible volumes, the catalog
is missing the fields `spiral_outward_sense` is derived from on 5 of them
(and on all of them via the minified catalog); a static single-crop AI
read, not reviewed by a person, was inconclusive on 21 of 23; and fitting
the spiral both ways and comparing satisfaction does not discriminate it
either, on the two scrolls tested — a fitted spiral reports back the
sense it was given, not an independent signal.

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
   AI reader, not reviewed by a person) came back "unsure" for 21 of the 23
   volumes; the two that got a definite reading were `PHerc1203` (ACW,
   catalog-underivable, so uncorroborated) and `PHerc0813` (ACW, low
   confidence, disagreeing with the catalog's derived CW). Umbilicus crops
   for the 5 catalog-UNDERIVABLE volumes, the ones this issue is mainly
   about:
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

---

# Issue draft 2 of 2: two VC3D bugs found while reading First Letters eligible volumes (crash on `resolveLasagnaForVolume`, fixed on `latest` but not in `stable`; blank re-open)

**In one sentence:** Two separate VC3D bugs surfaced while reading 23
scrolls via the Agent Bridge: `stable` (`fc25b4d`, 2026-07-31) crashes
opening a catalog sample whose lasagna representation triggers
`resolveLasagnaForVolume` to throw (fixed by PR #1225, present in
`latest` but not yet in a `stable` release), and re-opening an
already-opened sample renders a blank viewport with no error.

**I was trying to:** Screenshot 23 catalog samples via the VC3D Agent
Bridge for a reading task (open each sample, capture a view at three
z-levels).

**Using:** VC3D `stable` build `fc25b4d` (2026-07-31) for the crash;
reproduced the second bug on both `stable` and after switching to
`latest` build `6e3816c` (2026-09-25). macOS 26.5 (25F71), Apple Silicon.
Agent Bridge, `vc3d_open_catalog_sample` / `vc3d_describe_catalog_sample`.

**What happened:**

*Bug 1 — crash on open, `stable` build only.* Opening `PHerc0826` via
`vc3d_open_catalog_sample` crashed VC3D within the same second, twice in a
row (reproduced 2/2), including once when the request explicitly asked
for no representation kinds to be attached (`resources={"kinds": []}`) —
`resolveLasagnaForVolume` throws regardless of what the client requests,
so the bug is in opening this sample, not in what gets attached.
Redacted excerpt (`app_version`, symbol names, and signal only; user IDs,
device identifiers, and local process/coalition names removed):

```
"build_version": "fc25b4d-2026-07-31"
"exception": {"type": "EXC_CRASH", "signal": "SIGABRT"}
"termination": {"code": 6, "indicator": "Abort trap: 6"}

faulting thread, top frames:
  __pthread_kill
  pthread_kill
  abort
  __abort_message
  demangling_terminate_handler()
  _objc_terminate()
  std::__terminate(void (*)())
  __cxxabiv1::failed_throw(__cxxabiv1::__cxa_exception*)
  __cxa_throw
  vc3d::opendata::resolveLasagnaForVolume(VolumePkg const&, std::string const&)
```

Root cause, confirmed independently: PR #1225 (merged 2026-08-17) fixes an
exception-handling bug where `resolveLasagnaForVolume` throws as designed,
but on `lld`-linked macOS executables the surrounding `catch` loses its
unwind info and the throw always escalates to `std::terminate`/`SIGABRT`
instead of being handled. `stable` (`fc25b4d`, built 2026-07-31) predates
the fix; `latest` (`6e3816c`, built 2026-09-25) carries it. Switching
`.mcp.json` to the `latest` build resolved the crash; all 23 volumes then
opened and screenshotted cleanly.

**Ask:** cut a `stable` release that includes #1225, or otherwise flag in
the README that `stable` currently lacks a crash fix that affects opening
at least some catalog samples with a lasagna representation.

*Bug 2 — re-opening an already-opened sample renders blank, not a crash,
reproduced on `latest`.* Re-opening a catalog sample already opened
earlier in the same VC3D session returns success
(`"opened": true`, correct scale label, correct crosshair position at
high zoom) but the viewport shows no volume content, at every zoom level
including the exact default that rendered it correctly the first time.
The bridge itself stays healthy (pings respond normally) — this is not a
crash. Reproduced on two independent samples (`PHerc0826`, `PHerc0813`).
The response itself is the tell: a first-time open reports
`"attached": {"volumes": 1, ...}`; a repeat open of the same sample
reports `"attached": {"volumes": 0, ...}` with `"Skipped <volume>
(ome-zarr): already attached"` — the bridge believes the resource is
still attached and skips re-attaching it, but whatever GPU-side resource
backed the earlier texture appears to have been evicted (only one volume
resident at a time) once a different sample was opened in between,
leaving a dangling reference. `vc3d_select_volume` on the same,
already-current volume does not fix it; no workaround short of a full
VC3D relaunch was found. Evidence:
`analysis/vc3d-crash/reopen-blank-evidence/PHerc0826_reopened_blank_scale0.05.png`
and the `PHerc0813` equivalent, at `millerandmuller/sense-check`.

**What I expected or needed:** Either bug to not stop a scripted
open-many-samples-in-one-session read workflow: a fixed `resolveLasagnaForVolume`
in the release channel actually being distributed, and re-opening a
sample to either work or fail loudly rather than silently render nothing.

**Evidence / reproduction:** Full crash reports (`.ips`, redacted: device
identifiers zeroed, local process/coalition name replaced) and the
reopen-blank screenshots: `analysis/vc3d-crash/` at
`millerandmuller/sense-check`, including `README.md` there with the full
investigation timeline.

- [x] I personally encountered or reproduced this using the version and
  data stated above.

## Details

Neither bug blocked this project in the end (switching to `latest` fixed
the crash; the zoomed reading crops used for the actual sense-reading task
read the S3 zarr directly via matplotlib rather than through VC3D, so the
reopen-blank bug only cost redoing screenshots at a tighter zoom, which
was skipped rather than worked around). Filed for the maintainers' record
in case either throw site or the attach/evict logic recurs elsewhere.
