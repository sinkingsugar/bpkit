# Conan Exiles Enhanced — bpkit Blueprint tooling

Working dir for Giovanni's experiments driving the **Conan Exiles Enhanced Dev Kit** (UE 5.6.1)
from outside the editor. The engine install is *not* here; this repo holds only tooling/scripts/notes
(git-able; never put kit source here). The framework is **bpkit** (engine-agnostic) — see `README.md`
and `docs/` for depth; this file is the operational quick-reference.

## Who / environment
- **User:** Giovanni Petrantoni — GitHub `sinkingsugar` (id 7008900), email `g@hasten.gg`.
  git on this box: `user.name=Giovanni Petrantoni`, `user.email=7008900+sinkingsugar@users.noreply.github.com`.
- **Machine:** Windows 11 IoT Enterprise LTSC 2024. Keep the **Microsoft Store OFF**; prefer Win32 `.exe`/`.msi`
  (sideloading MSIX from official GitHub releases via `Add-AppxPackage` is fine).
- **Tooling** (full paths; a shell opened before install needs them): git `C:\Program Files\Git\cmd\git.exe`;
  winget (sideloaded MSIX); gh `C:\Program Files\GitHub CLI\gh.exe`.

## The Dev Kit + remote-control channel
- **Install:** `C:\Program Files\Epic Games\CEUE5Devkit` (177 GB — don't write here). Launch `RunDevKit.bat`.
  **Project:** `...\UE4\ConanSandbox.uproject`. Engine: `5.6.1-364449+++exiles+release`.
- Content-only kit: **no C++ compilation, no binary plugins.** That's why graph editing goes through the
  `bpkit` ctypes bridge (`docs/ARCHITECTURE.md`, `docs/INTERNALS.md`).
- **Remote execution** is ON (Project Settings → Plugins → Python). bpkit drives the editor directly over it —
  **MCP is not needed** here.

### Running things (fresh shells bite on this)
- **WHICH PYTHON:** bare `python` hits the (disabled) Windows Store alias and dies. ALWAYS use the bundled
  interpreter (`bpkit.config.BUNDLED_PYTHON`):
  `& 'C:\Program Files\Epic Games\CEUE5Devkit\Engine\Binaries\ThirdParty\Python3\Win64\python.exe' ...`
- **Two usage patterns — don't cross them:**
  - `python examples/smoketest.py` — a **standalone client** (opens its own connection).
  - `python ue_run.py <payload>` — `<payload>` is **editor-side** code (`import unreal; ...`); ue_run ships its
    source into the editor and runs it there. Running a standalone client *through* ue_run double-wraps and
    prints a false `NO NODE FOUND`. Liveness check: `python ue_run.py bpkit/ops/ping.py`.
- **Module cache:** the editor caches imports across `ue_run` calls. After editing a `bpkit` lib, pop
  `bpkit`/`bpkit.*` from `sys.modules` at the top of the payload before importing (snippet in `docs/INTERNALS.md` §1).
- ue_run injects the repo root onto the editor's `sys.path`, so payloads just `import bpkit` (no hardcoded path).

### Hard rules (each cost real time or trust)
- **Do NOT start Play (PIE) yourself** — the user controls Play. Only read/experiment in the user's own session.
- **Never author/compile a Blueprint during PIE** (breaks live instances). Check
  `LevelEditorSubsystem.is_in_play_in_editor()` first; author with Play stopped.
- **Never fire a native UFunction with guessed/empty args** to "reveal" its signature — it can crash the editor.
  Read the reflected `__doc__` or the BP `FunctionEntry` pins instead (`docs/CONAN-NOTES.md`).
- A Slate modal freezes the channel → rescue from a host process: `& $py bpkit/ops/dismiss_modal.py enter`.

## Where things live
- **Framework:** `bpkit/` (`bridge`/`ir`/`author`/`compact`/`pe`/`config`) + `bpkit/ops/` (ping, selftest, pie,
  modal, cleanup, log tail, compile-errors, **deploy**). All code uses `from bpkit import ...` (no root shims).
- **Examples:** `examples/`. **Regression suite:** `tests/` (run with Play stopped). **Mods:** `mods/<name>/`
  each with a `manifest.py` (deploy plan) + ordered build steps; deploy with `bpkit/ops/deploy.py <name>` (`/deploy`).
- **Knowledge base — read these instead of re-deriving:**
  - `docs/ARCHITECTURE.md` — design; what the stock API can't do; why ctypes; no MCP/plugin/transpiler.
  - `docs/INTERNALS.md` — bridge internals: symbol resolution, FString/TArray/TSet, the by-value `~TSet`
    crash + fix, read/write/edit flows, the typed-pin orphan trap, array/ForEach authoring, compile-flag caveats.
  - `docs/CONAN-NOTES.md` — live-verified Conan facts: mount seating is player-gated, `get_mount` broken
    (use `get_rider`), follower group caps, the ModController hook, MP/replication rules.
  - `docs/JOURNEY.md` — provenance (how the bridge + mod were reverse-engineered).
  - `mods/mounted-followers/FEASIBILITY.md` — the mounted-followers design audit + roadmap.

## Architecture (one line)
Hybrid, small, no transpiler/MCP/plugin: data/asset/compile via the reflected `unreal` API; node-graph logic
via authored node-**text** pasted through the ctypes bridge; engine `compile_blueprint` is the validator.
