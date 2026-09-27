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
