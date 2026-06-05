# Conan Exiles Enhanced — AI-assisted Blueprint tooling

Working dir for Giovanni's experiments driving the **Conan Exiles Enhanced Dev Kit** (UE 5.6.1)
from outside the editor, to assist with Blueprint/mod work. Engine install is *not* here; this dir
holds only our tooling/scripts/notes (keep it git-able, never put source in the Program Files kit).

---

## Who / environment

- **User:** Giovanni Petrantoni — GitHub `sinkingsugar` (id 7008900), email `g@hasten.gg`.
  - git identity on this box: `user.name=Giovanni Petrantoni`,
    `user.email=7008900+sinkingsugar@users.noreply.github.com` (gh token lacks `user` scope).
- **Machine:** Windows 11 IoT Enterprise **LTSC 2024**. Keep the **Microsoft Store OFF**
  (no `Microsoft.WindowsStore`); prefer Win32 `.exe`/`.msi`. Sideloading MSIX from official
  GitHub releases via `Add-AppxPackage` is fine (local MSIX subsystem, no Store/MS-account).
- **Tooling paths** (on system PATH, but a shell opened before install needs full paths):
  - git 2.54.0 — `C:\Program Files\Git\cmd\git.exe`
  - winget 1.28.240 — `C:\Users\sugar\AppData\Local\Microsoft\WindowsApps\winget.exe` (sideloaded MSIX)
  - Windows Terminal 1.24.x — sideloaded MSIX, launch via `wt`
  - gh 2.93.0 — `C:\Program Files\GitHub CLI\gh.exe` (git credential helper for github.com/gist over HTTPS)

---

## The Dev Kit + remote-control channel

- **Install:** `C:\Program Files\Epic Games\CEUE5Devkit`  (managed Epic install, 177 GB — don't write here).
  Launch: `RunDevKit.bat` → `Engine\Binaries\Win64\UnrealEditor.exe UE4\ConanSandbox.uproject -ModDevKit`.
- **Project:** `C:\Program Files\Epic Games\CEUE5Devkit\UE4\ConanSandbox.uproject` (the `UE4` folder is the project dir).
- **Engine reports:** `5.6.1-364449+++exiles+release`.
- Content-only kit: **no C++ compilation, can't add binary plugins.** (Legacy non-Enhanced kit was
  UE 4.15.3 and predates UE Python entirely — not in use.)

### Python Remote Execution — VERIFIED WORKING (2026-06-04)
`PythonScriptPlugin` ships **compiled** in the kit (`Engine\Plugins\Experimental\PythonScriptPlugin\
Binaries\Win64\UnrealEditor-PythonScriptPlugin*.dll` + `Content\Python\remote_execution.py`), so live
external control works with **zero compilation**.

To use:
1. Editor: "Python Editor Script Plugin" enabled (it is). **Project Settings → Plugins → Python →
   "Enable Remote Execution"** ON (it is; toggle is *project*-level, not Editor Prefs).
2. Run a client with the **bundled** interpreter so versions match:
   `& 'C:\Program Files\Epic Games\CEUE5Devkit\Engine\Binaries\ThirdParty\Python3\Win64\python.exe' <script>`
   pointing `sys.path` at the plugin's `Content\Python` and importing `remote_execution`.
   Defaults are same-machine-ready: multicast `239.0.0.1:6766`, command `127.0.0.1:6776`.
- Smoke test: `examples/smoketest.py` (prints engine ver + logs into the editor).
- API probe:  `dev/ue_probe_bp.py` (provenance; targets the pre-refactor API).

> **WHICH PYTHON (fresh shells bite on this).** Bare `python` on this box hits the Windows
> **Store app-execution alias** and dies with `Python was not found; ... Microsoft Store` — there
> is NO system Python and the Store is deliberately OFF. ALWAYS invoke the **bundled** interpreter
> by full path for BOTH `ue_run.py` and standalone clients:
> `& 'C:\Program Files\Epic Games\CEUE5Devkit\Engine\Binaries\ThirdParty\Python3\Win64\python.exe' ue_run.py <payload>`
> (`ue_run.py` self-inserts the plugin's `Content\Python` onto `sys.path`, so `remote_execution`
> imports without extra setup.) In Bash, set `PY="C:/Program Files/.../python.exe"` once and use `"$PY"`.

> **INVOCATION GOTCHA (cost an hour of false "channel down" debugging 2026-06-05).**
> Two DIFFERENT usage patterns — do not cross them:
> - `python examples/smoketest.py` — run a **standalone client DIRECTLY**. It opens its
>   own `remote_execution` connection. (Use the bundled python; same machine.)
> - `python ue_run.py <payload>` — `<payload>` must be **editor-side code** (`import unreal;
>   ...`); ue_run ships its *source* into the editor and runs it there.
> Running `ue_run.py examples/smoketest.py` DOUBLE-WRAPS: the editor runs the client, which
> then tries to multicast-discover a node *from inside the editor*, finds none, and prints
> `NO NODE FOUND` — which looks exactly like a dead channel but isn't. If `ue_run.py` echoes
> `[Info]` `LogPython` lines back at all, the channel is FINE; read what the payload actually
> did. Quick liveness check: `python ue_run.py dev/ping.py`.

> **MODULE CACHE:** the editor's Python caches imported modules across `ue_run` calls, so after
> editing a lib (`bp_ir`/`bp_bridge`/…) a payload that imports it gets the STALE version. Force a
> reload at the top: `import sys; [sys.modules.pop(m, None) for m in ("bp_ir","bp_bridge","bp_author","bp_compact")]`
> then import. PIE control: `dev/pie_play.py`/`pie_end.py`/`pie_state.py` (drive Play via
> LevelEditorSubsystem); `python dev/dismiss_modal.py enter` (host-side) clears a modal that froze
> the channel. NEVER author/compile a BP while in PIE (breaks live instances). ModController
> subclasses AUTO-SPAWN on play (DreamworldMods) but BEFORE the player exists — do player-dependent
> init on tick (guard with a bool), not BeginPlay.

**MCP is NOT needed here.** Claude Code has shell+Python, so it drives the editor directly over
`remote_execution` — strictly more capable than a fixed MCP tool surface. MCP only earns its place for
external/sandboxed clients or a guardrailed tool menu.

---

## What the stock `unreal` Python API can / can't do (probed live 2026-06-04)

CAN (fully automatable):
- load / find / **create** assets (`AssetTools` + factories), duplicate into variants
- add/remove **function graphs**, find event graph (`add_function_graph`, `find_event_graph`)
- add/edit **variables** + flags (`add_member_variable`, `set_blueprint_variable_*`)
- edit **properties / CDO defaults / DataTable rows / components** (`get/set_editor_property`,
  `SubobjectDataSubsystem`)
- **compile** blueprints (`BlueprintEditorLibrary.compile_blueprint`) → feedback loop closes

CANNOT *via the stock `unreal` Python API* (not reflected; would be C++ unavailable in content-only kit):
- spawn a K2 node (CallFunction/Branch/etc.), wire/connect pins
- even *read* a graph's nodes (`function_graphs`/`uber_graph_pages` not exposed)
- no `KismetEditorUtilities`, no `ImportNodesFromText` → Python can't paste nodes either

> **SUPERSEDED 2026-06-04 — the ctypes bridge defeats the whole list.** The C++ paste/copy
> entrypoints ARE exported from the loaded editor DLLs, so in-process Python calls them by address
> via `ctypes` (zero compilation, zero UI/clipboard/focus). Both directions work and are SAFE:
> **WRITE** = `ImportNodesFromText` + compile + save; **READ** = enumerate (`GetAllGraphs` /
> `GetObjectsWithOuter`) + `ExportNodesToText` per node. Read the entire `BP_BatDemonGlider` (19
> graphs, 959 nodes, 2.84 MB) with zero crashes. Key gotcha: `ExportNodesToText` takes the `TSet`
> BY VALUE and `~TSet`-frees its buffers, so the set's element buffer MUST be `FMemory::Malloc`'d,
> not ctypes — else heap corruption + delayed crash (cost 2 editor crashes to learn; see memory
> `ctypes-bp-paste`). Tooling at repo root: `bp_bridge.py` (the library — was `ue_bp_inject.py`
> before the refactor), `ue_run.py`, `pe_exports.py`.

## Architecture decision

Hybrid, intentionally small — **no transpiler, no MCP, no plugin**:
- **Data/asset/compile 80% → thin Python helper** over `remote_execution` (fully automated).
- **Node-graph logic 20% → BP node *text*** authored by Claude → pasted (human or UI-automation Ctrl+V),
  since neither Python nor a C++ helper can build graphs in this kit. Engine compile = the validator.
- (Shards→BP angle was explored and dropped; not the point. JS/TS→BP also dropped.)

Next:
1. Nail the hand-built `TSet` layout SAFELY: validate `make_tset()` byte-for-byte against a real
   UE-built set (from an import out-`TSet`) via `memcmp` BEFORE ever calling `ExportNodesToText` —
   pure byte compare can't crash. Then arbitrary-graph reading is done. (See memory `ctypes-bp-paste`.)
2. Discover canonical text for real *logic* nodes (CallFunction/Event/Branch + wired pins) from the
   exported examples, parameterize, inject, let `compile_blueprint` validate.
3. **BP-text compaction / navigation tool.** Exported node text is hugely verbose (~20 default flags
   per pin line; 17 graphs of BP_BatDemonGlider = 1.38 MB). Build a lossless-ish compactor + an index
   so Claude can navigate a blueprint's logic (nodes, connections, sub-graphs) WITHOUT pulling the
   full text into context every time — drop redundant pin defaults, summarize per-graph/per-node,
   allow drill-down by node/graph id. Token efficiency is the goal.
