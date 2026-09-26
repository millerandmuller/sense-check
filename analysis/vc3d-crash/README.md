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
  that launches VC3D with `--agent-bridge`; `coalitionName:
  com.example.build-session` -- the build session's process group.
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

**Fix applied for the rest of F2's screenshot pass:** every subsequent
`vc3d_open_catalog_sample` call for all 23 volumes passes
`resources: {"kinds": []}` to attach only each sample's raw volume and
explicitly exclude `normal_grids`/`lasagna`/`prediction` representations,
none of which F2's screenshots need. This is a workaround in how this
session drives the bridge, not a VC3D or villa code change.

## What this is not

This is not a claim that villa's or VC3D's code is wrong, and no VC3D code
change is in scope for this project (the project plan,
Dealbreakers). It is a factual record of a crash encountered while using
the Agent Bridge on real data, kept in case it is useful later (e.g. if the
same throw site recurs, or if a bug report becomes worth filing separately
from this month's submission).
