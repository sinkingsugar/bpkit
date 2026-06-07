---
name: setup
description: Setup / health check for bpkit — verify the editor channel, Python, Remote Execution, AND that the native ctypes bridge resolves on THIS editor build. Adaptive: diagnose and self-heal, don't hard-fail. Run after pulling the repo.
disable-model-invocation: true
---

Run bpkit's readiness check **as a smart diagnosis, not a pass/fail script** — your job is to get it working, adapting where needed and only reporting a real blocker if you genuinely can't. `$py` = `bpkit.config.BUNDLED_PYTHON` (or `$env:BPKIT_PYTHON`; bare `python` may hit the disabled Windows Store alias — use the engine's bundled interpreter).

## 1. Channel
`& $py ue_run.py bpkit/ops/ping.py`
- `ENGINE_VERSION` printed → live.
- `no editor node found` → editor not running or Remote Execution off. Tell the user: launch the Dev Kit editor, then **Project Settings → Plugins → Python → enable "Remote Execution"**, then re-run `/setup`.
- Python path error → set `$env:BPKIT_PYTHON` to `<engine>\Engine\Binaries\ThirdParty\Python3\Win64\python.exe` (or edit `BPKIT_ENGINE_ROOT` in `bpkit/config.py`).

## 2. Native bridge (the important diagnosis)
`& $py ue_run.py bpkit/ops/selftest.py` — resolves every exported symbol the ctypes bridge calls **on THIS editor build**, plus one read-only native call.
- `BRIDGE OK` → the native layer works here; nothing to do.
- One or more `FAIL` → **do NOT hard-fail. Adapt.** The decorated names are MSVC-mangled and stable across UE5, but a different build can differ. For each failed symbol:
  1. Note its DLL (the 2nd element of that key's `bpkit.bridge.SYM` entry) under `<engine>\Engine\Binaries\Win64\`.
  2. Find the current decorated name: `& $py -m bpkit.pe "<that DLL>" <a substring of the C++ function, e.g. ImportNodesFromText>`.
  3. Patch that entry in `bpkit/bridge.py` `SYM` with the name `pe` reports, then re-run `selftest`. Repeat until `BRIDGE OK`.
  - If a symbol simply isn't exported at all, this probably isn't an editor build (shipping/monolithic) — the bridge needs an editor build; say so.
- `functional ... : False` (but symbols resolved) → calls resolve but the probe didn't round-trip; re-run after confirming you're not mid-compile, and sanity-check `find_object`.

## 3. Report
Short status: channel up? · bridge OK (or exactly what you adapted)? · then the ready commands: `/bp-channel`, `/bp-read <asset>`, `/bp-test`, and `/install` (use these from any project). Run `/bp-test` if you want full functional coverage beyond the symbol check.
