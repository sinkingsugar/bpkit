# conan-bp-tools

External Python tooling to drive **Conan Exiles Enhanced Dev Kit** (Unreal Engine 5.6,
content-only) Blueprints from *outside* the editor — **reading and writing Blueprint node
graphs with no editor UI, no clipboard, no window focus, and zero C++ compilation.**

The content-only Dev Kit doesn't reflect graph editing to the `unreal` Python API (you can't
spawn/wire K2 nodes, or even read a graph). But the C++ copy/paste entrypoints *are* exported
from the editor's already-loaded DLLs — so in-process Python resolves them by address and calls
them via `ctypes`. The engine's own compiler is the validator.

```
WRITE:  authored node text → CanImportNodesFromText (safe pre-check) → ImportNodesFromText
        → MarkBlueprintAsStructurallyModified → compile_blueprint → save_asset
READ:   GetAllGraphs → UEdGraph::Nodes (direct read) → ExportNodesToText (per node) → node text
```

Verified by reading an entire production blueprint (19 graphs, 942 nodes, ~2.8 MB of node text)
and by injecting + compiling nodes, with the editor staying stable.

`GetObjectsWithOuter` was the original node-enumeration path but is now only a fallback: it also
surfaces orphaned nodes left in the transaction (undo) buffer, so the direct `UEdGraph::Nodes`
read is authoritative.

## How it connects

The editor ships Epic's `PythonScriptPlugin` **compiled**, with Remote Execution available
(Project Settings → Plugins → Python → *Enable Remote Execution*). A client run with the editor's
**bundled** interpreter talks to it over `remote_execution` (multicast `239.0.0.1:6766`, command
`127.0.0.1:6776`). Code shipped this way runs **inside** the editor process — same address space
as the engine DLLs, which is what makes the `ctypes` bridge possible.

## Layout

| path | role |
|---|---|
| `bp_bridge.py` | **the library** — proc resolution, FString/TSet/TArray marshalling, read/write/compile. Public API: `read_blueprint`, `inject`, `can_import`, `import_nodes`, `export_nodes`, `find_object/find_graph`, `scratch_blueprint`. Runs inside the editor. |
| `bp_ir.py` | unified Graph IR — parse exported node text → edit (`wire`/`unwire`/`remove`) → render back to import text. Pure stdlib, runs in-editor or offline. |
| `bp_author.py` | declarative authoring DSL: build a graph from intent (`event`/`call`/`branch`/`wire`) → import text. Pure stdlib. |
| `bp_compact.py` | compress exported node text into a dense, navigable outline (~23x smaller). Pure stdlib, runs offline on a dump. `--summary` / `--graph NAME` / `--node NAME` / `--split`. |
| `ue_run.py` | driver: ships a local `.py` into the running editor over `remote_execution` and echoes its output |
| `pe_exports.py` | dependency-free PE export-table dumper (find the decorated symbol names to resolve) |
| `examples/read_blueprint.py` | read every graph of a blueprint to node text |
| `examples/inject_and_compile.py` | inject a node, compile, save |
| `examples/author_logic.py` | author wired logic from intent (`bp_author`) → inject → compile |
| `examples/edit_graph.py` | parse a real graph into the IR (`bp_ir`), edit, render back, inject |
| `examples/smoketest.py` | remote-execution connectivity check |
| `dev/` | the reverse-engineering / journey scripts (provenance; target the old API — see `dev/README.md`) |

## Usage

```powershell
# run any in-editor payload via the editor's bundled interpreter
$py = 'C:\Program Files\Epic Games\CEUE5Devkit\Engine\Binaries\ThirdParty\Python3\Win64\python.exe'
& $py ue_run.py examples\read_blueprint.py
& $py ue_run.py examples\inject_and_compile.py
```

Payloads that use the library insert the repo root on `sys.path` and `import bp_bridge`
(see the examples) — `MODE_EXEC_FILE` ships the file source verbatim, so the import path
must be set inside the payload.

## Key gotcha (why this took care to get right)

`ExportNodesToText` takes its `TSet` **by value** and runs `~TSet` on return, which
`FMemory::Free`s the set's internal buffers. A hand-built set whose memory is ctypes-allocated
makes UE free pointers it never `malloc`'d → heap corruption + a *delayed* crash. The set's
element buffer must be allocated with the engine's exported `FMemory::Malloc`. See the comments
in `bp_bridge.py` (the header note and `_make_set1_fmemory`).

## Navigating a blueprint

```powershell
# 1. dump the blueprint's node text from the editor (gitignored output)
& $py ue_run.py examples\read_blueprint.py
# 2. navigate offline at ~23x compression
& $py bp_compact.py dump_BP_BatDemonGlider.txt --summary           # graph map + entry points
& $py bp_compact.py dump_BP_BatDemonGlider.txt --graph LerpCamRotation
```

The compact view is lossy-for-navigation; for the exact text of one node (e.g. to author
a variant) re-export just that node losslessly with `bp_bridge.export_nodes([node_ptr])`.

## Status / roadmap

- ✅ Write (inject + compile + save) — safe, verified
- ✅ Read (any graph → canonical node text) — safe, verified
- ✅ Blueprint-text compactor + navigator (`bp_compact.py`, ~23x)
- ✅ Author / edit wired-logic nodes (`bp_author.py` intent DSL, `bp_ir.py` parse→edit→render),
  inject, let `compile_blueprint` validate (see `examples/author_logic.py`, `examples/edit_graph.py`)
- ⬜ Discover canonical text for the full set of real logic-node patterns and parameterize them

## Notes

This drives a managed Epic install; the engine/kit is **not** part of this repo. Nothing derived
from the kit's `/Game` assets is committed (see `.gitignore`) — that content is Funcom's.
