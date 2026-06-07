---
name: bpkit
description: Drive Unreal Engine 5 Blueprint graphs from outside the editor with bpkit — read, author, edit, inject and compile K2 node graphs over the remote-exec channel. Use for ANY UE Blueprint node-graph task: authoring nodes, fixing pins, mod authoring, reading a graph. (Windows + an editor build with Remote Execution on.)
paths: bpkit/**, mods/**, examples/**, tests/**
---

bpkit drives Blueprints by shipping Python into the running editor over remote-exec; the editor's own compiler is the validator. Standing rules for any BP task:

**Run** payloads with the bundled Python via `ue_run.py` (path = `bpkit.config.BUNDLED_PYTHON`, or `$env:BPKIT_PYTHON`; bare `python` may hit the Windows Store alias):
`& $py ue_run.py <payload.py>`. Liveness: `& $py ue_run.py bpkit/ops/ping.py`. Native-bridge health: `& $py ue_run.py bpkit/ops/selftest.py` (or `/setup`) — if a symbol FAILs to resolve on a build, re-derive its name with `bpkit.pe` and patch `SYM`; don't assume the bridge is broken.

**Safety (non-negotiable):**
- Author/compile only with Play STOPPED — check `unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor()` first; never compile during PIE (breaks live instances).
- Don't start PIE yourself; the user controls Play.
- Never call a native UFunction with guessed/empty args to "reveal" its signature — it can crash the editor. Read the reflected `__doc__` or the BP `FunctionEntry` pins instead.

**Authoring:**
- Reload first: pop `bpkit`/`bpkit.*` from `sys.modules` at the top of the payload (the editor caches modules across calls).
- Build graphs with `from bpkit import ir, author`; paste + compile + save with `bridge.inject`.
- TYPE every non-string default and every VariableGet/Set pin, or it orphans and the autogen default silently wins. Verify after inject: zero `bOrphanedPin=True` pins.
- Array nodes = `K2Node_CallArrayFunction` (fully-typed TargetArray); indexed read = `K2Node_GetArrayItem`. ForEach needs a `ResolvedWildcardType` header + an exec-wired array source, or it compiles but does nothing.
- "compiled" ≠ "no errors": scan the exported graph for `wildcard` pins / `ErrorMsg` (pattern in `bpkit/ops/compile_errors.py`).

**Read deep references only when needed:**
- `docs/INTERNALS.md` — the ctypes bridge (symbol resolution, FString/TArray/TSet, the by-value `~TSet` crash + fix, read/write/edit flows).
- `docs/CONAN-NOTES.md` — Conan facts (mount gating, follower caps, ModController hook, MP/replication).
- `docs/ARCHITECTURE.md` — design rationale.
