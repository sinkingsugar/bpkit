# bpkit

**Read, author, edit, and compile Unreal Engine 5 Blueprint node graphs from
*outside* the editor** — no C++ compilation, no editor UI, no clipboard, no window
focus. Built for **content-only kits** (a packaged editor with no C++ toolchain),
where Blueprint graph editing isn't otherwise reachable by automation.

Blueprints are a visual language meant for a human clicking in the editor; bpkit
treats the graph as **data** so scripts (or an LLM) can manipulate it at scale. It
ships authored node-text into the editor over the Python remote-execution channel
and pastes it via the editor's own exported C++ functions (`ctypes`, in-process);
the engine's compiler is the validator.

```
WRITE: authored node text -> CanImportNodesFromText -> ImportNodesFromText
       -> MarkBlueprintAsStructurallyModified -> compile_blueprint -> save_asset
READ:  GetAllGraphs -> UEdGraph::Nodes -> ExportNodesToText (per node) -> node text
```

Verified live on UE 5.6.1 (Conan Exiles Enhanced Dev Kit): reads a full production
blueprint (19 graphs, ~950 nodes, 2.8 MB) and authors/compiles new logic, editor stable.

## Engine-agnostic

The `bpkit` core is generic. Install-specific paths live only in
[`bpkit/config.py`](bpkit/config.py) and are overridable via `BPKIT_*` environment
variables (engine root, bundled Python, plugin path, remote-exec endpoints). Point
them at any UE project to reuse the toolchain. The Conan Exiles "mounted followers"
work is one **application** of the framework, in [`mods/`](mods/).

## Quick start

```powershell
# the editor's BUNDLED python (bare `python` hits the disabled Windows Store alias)
$py = 'C:\Program Files\Epic Games\CEUE5Devkit\Engine\Binaries\ThirdParty\Python3\Win64\python.exe'

& $py examples\smoketest.py                       # is the remote-exec channel up?
& $py ue_run.py examples\inject_and_compile.py    # author a node -> compile -> save
& $py ue_run.py examples\author_logic.py          # author wired logic from intent
& $py ue_run.py examples\edit_graph.py            # in-place edit (read->IR->rewire->replace)
& $py ue_run.py tests\test_bp_authoring.py        # deterministic regression suite
& $py ue_run.py bpkit\ops\deploy.py mounted-followers   # build+deploy a whole mod (Play stopped)
```

Editor prerequisite: *Project Settings → Plugins → Python → Enable Remote
Execution* (on). `ue_run.py` ships a local payload's source into the running editor
and injects the repo root onto its `sys.path`, so payloads just `import bpkit`.

## Layout

| path | what |
|---|---|
| `bpkit/` | the framework: `bridge` (ctypes engine), `ir` (Graph IR), `author` (DSL), `compact` (navigation), `pe` (symbol dumper), `config` |
| `bpkit/ops/` | reusable operational tools: editor ping, native-bridge self-test, PIE control, modal rescue, scratch cleanup, log tail, compile-error scan, **mod deploy** |
| `ue_run.py` | host-side driver: ship a `.py` into the running editor, echo its output |
| `examples/` | minimal framework examples (read / inject / author / edit) |
| `tests/` | deterministic in-editor regression suite for the authoring toolchain |
| `mods/mounted-followers/` | the Conan mod as a reproducible recipe: `manifest.py` (deploy plan) + ordered build steps + its feasibility doc |
| `docs/` | the knowledge base (below) |

## Docs

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — the design: what the stock API
  can't do, why the ctypes bridge, why no MCP/plugin/transpiler, the layers.
- [docs/INTERNALS.md](docs/INTERNALS.md) — the bridge in depth: symbol resolution,
  FString/TArray/TSet marshalling, the by-value `~TSet` crash + fix, read/write/edit
  flows, the typed-pin orphan trap and other authoring gotchas.
- [docs/CONAN-NOTES.md](docs/CONAN-NOTES.md) — live-verified Conan facts (mount
  gating, follower caps, the ModController hook, MP/replication).
- [docs/JOURNEY.md](docs/JOURNEY.md) — how the bridge and the mod were
  reverse-engineered (provenance).

## Status

- ✅ Read any graph → canonical node text (safe, verified)
- ✅ Write: author/edit → paste → compile → save (safe, verified)
- ✅ Navigable compaction of node text (~23×) for token-cheap reasoning
- ✅ Declarative + IR authoring with typed pins, arrays, ForEach
- ✅ Reference mod (mounted followers) reproducible end-to-end, SP + MP

## Notes

This drives a managed Epic install; the engine/kit is **not** part of this repo.
Nothing derived from the kit's `/Game` assets is committed (see `.gitignore`) —
that content is Funcom's.
