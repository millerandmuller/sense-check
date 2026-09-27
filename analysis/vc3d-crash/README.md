# VC3D crash, 2026-09-26 14:33:48 -0500 (pid 8754)

`VC3D-2026-09-26-143348.ips` is macOS's own crash report, copied verbatim
from `~/Library/Logs/DiagnosticReports/`.

## What it says

- `SIGABRT` (`Abort trap: 6`), triggered by `abort()` from an uncaught C++
  exception (`libc++abi.dylib: __cxa_throw` -> `std::terminate`).
- The throw site, from the faulting thread's (thread 0, main thread)
  backtrace:
  `vc3d::opendata::resolveLasagnaForVolume(VolumePkg const&, std::string const&)`.
- `parentProc: Python` (pid 8680) -- this is the `vc3d-mcp` bridge process
  that launches VC3D with `--agent-bridge`, running inside this build
  session's own process group.
- `procRole: Background` at the time of the crash.

## What this session can and cannot confirm about the trigger

This session's own record of bridge calls before the crash: one call,
`vc3d_describe_catalog_sample("PHerc0826")`, which completed successfully
and returned PHerc0826's representations, including a `lasagna`-kind entry
(`modelId 20260419180421`, `ref "0:3"`). No bridge call was in flight at the
exact crash timestamp -- the next bridge call this session made (some time
later, `vc3d_open_catalog_sample`) failed immediately with connection
refused, meaning VC3D was already down by then.

**Hypothesis, not a finding:** the throw site (`resolveLasagnaForVolume`) is
consistent with VC3D resolving PHerc0826's lasagna representation lazily,
in the background, sometime after the `describe_catalog_sample` RPC had
already returned -- which would explain a main-thread crash with no bridge
call in flight. This session has no server-side VC3D or bridge log to
confirm that, or to rule out an unrelated cause (a stale volume package
from an earlier interaction, a manual GUI action, or something else). Treat
the causal link to `describe_catalog_sample(PHerc0826)` as unverified.

## Second crash, 2026-09-26 14:51:04 -0500 (pid 23895) -- reproduced and pinned down

After a relaunch, this session called `vc3d_open_catalog_sample("PHerc0826", wait=true)`
as the first step of resuming the VC3D screenshot half of F2. VC3D crashed
within the same second, `VC3D-2026-09-26-145104.ips`, **identical stack**:
`SIGABRT` from an uncaught throw in `vc3d::opendata::resolveLasagnaForVolume`.

This time there is no ambiguity: the trigger is `vc3d_open_catalog_sample`
attaching PHerc0826's `lasagna`-kind representation (`modelId 20260419180421`,
seen in the earlier `vc3d_describe_catalog_sample` output) and VC3D's own
lasagna-resolution code throwing while trying to resolve it -- reproduced
2/2. This also retroactively explains the first crash: the describe call
alone had already probably triggered the same lazy resolution once.

**Fix attempted, did not work:** `vc3d_open_catalog_sample("PHerc0826",
resources={"kinds": []}, wait=true)` -- explicitly asking to attach only
the raw volume -- crashed VC3D again, identical stack,
`VC3D-2026-09-26-145720.ips` (14:57:20). So `resolveLasagnaForVolume` runs
regardless of the client's requested `kinds` filter; VC3D appears to always
probe for a lasagna representation when opening a catalog sample, and that
probe itself throws for PHerc0826, independent of what gets attached.
The bug is in opening PHerc0826 specifically, not in what a client asks
for.

**Working hypothesis (Lutfiya, being tested):** PHerc0826, PHerc0211, and
PHerc0125 each have a catalog umbilicus entry that PHerc0800 lacks, despite
0800 and 0826 having structurally identical lasagna descriptors otherwise.
If a default-kinds open of PHerc0800 survives while PHerc0211 crashes the
same way, the umbilicus entry is implicated as the actual trigger inside
`resolveLasagnaForVolume`, not the lasagna descriptor shape itself.

## Resolution

Root cause confirmed independently: villa PR #1225 (merged 2026-08-17) fixes
an exception-handling bug where `resolveLasagnaForVolume` throws as
designed, but `lld`-linked macOS executables lose the unwind info needed for
the surrounding `catch` to run, so the throw always escalates to
`std::terminate`/`SIGABRT`. The installed "stable" build (`fc25b4d`,
2026-07-31) predates the fix; the "latest" release (`6e3816c`,
2026-09-25) carries it. The earlier "umbilicus entry" hypothesis (PHerc0826/
0211/0125 have one, PHerc0800 doesn't) was retired once the catalog
descriptors were compared and found structurally identical between 0800 and
0826 -- the difference was the build, not the data.

After switching `.mcp.json` to the `latest` build and client (protocol 2),
all 23 volumes opened and screenshotted cleanly across the full F2 batch,
zero bridge errors.

## Separate finding: re-opening an already-opened catalog sample renders blank

Not a crash -- the bridge stays up (pings fine throughout) -- but re-opening
a catalog sample already opened earlier in the same VC3D session produces a
viewport that reports success (`"opened": true`, correct scale label, correct
crosshair position at high zoom) yet shows no volume content, at any zoom
level including the exact default (scale 0.05) that rendered it correctly
the first time. Reproduced on two different samples (PHerc0826, PHerc0813).

The `open_catalog_sample` response is the tell: a first-time open reports
`"attached": {"volumes": 1, ...}` (or more for a default-kinds open); a
repeat open of the same sample reports `"attached": {"volumes": 0, ...}`
with a message `"Skipped <volume> (ome-zarr): already attached"` -- the
bridge believes the resource is still attached from the earlier session and
skips re-attaching it, but whatever GPU-side resource backed that texture
appears to have been evicted when a later sample was opened (only one
volume is resident at a time), leaving a dangling reference.

Explicit re-selection (`vc3d_select_volume` on the same, already-current
volume) does not fix it. This session did not find a workaround short of a
full VC3D relaunch, and did not want to ask for a fourth relaunch just to
verify one. Practical consequence: F2's 69 VC3D screenshots (committed
earlier, default zoom) cannot be cheaply redone at a tighter, umbilicus-
centered zoom in the same running session -- the zoomed reading crops
(`render_umbilicus_crops.py`, matplotlib, reads the S3 zarr directly rather
than through VC3D) serve that purpose instead.

## What this is not

This is not a claim that villa's or VC3D's code is wrong, and no VC3D code
change is in scope for this project (the project plan,
Dealbreakers). It is a factual record of a crash encountered while using
the Agent Bridge on real data, kept in case it is useful later (e.g. if the
same throw site recurs, or if a bug report becomes worth filing separately
from this month's submission).
