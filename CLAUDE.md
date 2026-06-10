# Conan Exiles Enhanced — bpkit Blueprint tooling

Working dir for experiments driving the **Conan Exiles Enhanced Dev Kit** (UE 5.6.1)
from outside the editor. The engine install is *not* here; this repo holds only tooling/scripts/notes
(git-able; never put kit source here). The framework is **bpkit** (engine-agnostic) — see `README.md`
and `docs/` for depth; this file is the operational quick-reference.

## Environment
- Windows 11. The **Microsoft Store is OFF** on this box; prefer Win32 `.exe`/`.msi`
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

### Shipping a mod (editor build ≠ packaged mod)
`/deploy` only authors Blueprints into the **editor** (`/Game/<Mod>`); it does NOT package. The real
game runs a **cook → pak** produced by the Dev Kit mod tool (e.g. `...\UE4\Saved\Mods\<Mod>\Output\<Mod>.pak`).
Things that cost real time here:
- **Mod assets MUST be authored under `/Game/Mods/<ModName>/`** (set `mf_config.OUTPUT_PKG` there;
  it's writable when that mod is the **active** mod). Only then does the cook tag them **(Mod Asset)**;
  anything in a scratch root like `/Game/<Mod>` cooks as a **(Base Asset)** and Conan **culls its
  ModController as `[1]Invalid class`** (loads but never registers — runs in PIE, dead in the packaged
  game). This was the actual mounted-followers bug (2026-06-08). Confirm in the cook dialog that the BPs
  read **(Mod Asset)**. (full write-up: `docs/CONAN-NOTES.md` §Packaging.)
- **"Requires Load On Startup" (`modinfo.json` `bRequiresLoadOnStartup`) is NOT needed** for a
  ModController mod — empirically the controller registers fine without it (cooked game, 2026-06-10).
  It was chased first during the packaging bringup and was a red herring both times; the real gate is
  the (Mod Asset) placement above. Leave it at the default unless the mod truly needs boot-time loading.
- **Verify a cooked pak — don't trust the cook silently.** Outer is a "fat" pak; UnrealPak is
  `C:\Program Files\Epic Games\CEUE5Devkit\Engine\Binaries\Win64\UnrealPak.exe`:
  `UnrealPak.exe <Mod>.pak -List` (shows `modinfo.json` + per-platform paks), extract, then
  `UnrealPak.exe <Mod>-Windows.utoc -List` for the IoStore **asset** list. `.ucas` is Oodle-compressed
  → text-grep finds nothing; always use `-List`.
- **Shipping strips `PrintString` AND `GetAll`** (screen + log + console). For visible in-game diagnostics
  use Conan HUD funcs: `ConanCharacter.HUDShowFIFO(text)` (local event feed) or
  `ClientHUDShowNotification(text, positive)` (server→client banner). Build the FText via `Conv_StringToText`.

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
    (use `get_rider`), follower group caps, the ModController hook, MP/replication rules, **packaging/
    shipping (the (Mod Asset) rule, pak inspection, Shipping-safe diagnostics)**.
  - `docs/JOURNEY.md` — provenance (how the bridge + mod were reverse-engineered).
  - `mods/mounted-followers/FEASIBILITY.md` — the mounted-followers design audit + roadmap.

## Architecture (one line)
Hybrid, small, no transpiler/MCP/plugin: data/asset/compile via the reflected `unreal` API; node-graph logic
via authored node-**text** pasted through the ctypes bridge; engine `compile_blueprint` is the validator.
