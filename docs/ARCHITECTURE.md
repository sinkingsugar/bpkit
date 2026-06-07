# Architecture

## The problem this framework solves

Unreal **Blueprints** are a visual scripting language designed for a human sitting
in the editor, clicking and dragging nodes. They are deliberately primitive and
"drone-centric": there is no clean, machine-facing API to author or even *read* a
node graph. That is fine for a person; it is a wall for any kind of automation —
scripts, code-gen, or an LLM agent that wants to reason over and edit Blueprint
logic at scale.

It gets worse in a **content-only kit** (a packaged editor with no C++ toolchain —
e.g. the Conan Exiles Enhanced Dev Kit, UE 5.6). There you can't compile a helper
plugin, so even the C++ escape hatch is closed.

**bpkit treats the Blueprint graph as data.** It reads any graph to canonical
node text, lets you author/edit that text with a small semantic model, pastes it
back as real nodes, and uses the engine's own compiler as the validator — all
from outside the editor, with **no C++ compilation, no editor UI, no clipboard,
no window focus.**

## What the stock `unreal` Python API can and can't do

Probed live against UE 5.6.1 (content-only). The stock reflected API is enough
for the "data" 80% of modding but cannot touch graph logic:

**CAN (fully automatable):**
- load / find / **create** assets (`AssetTools` + factories), duplicate variants
- add/remove **function graphs**, find the event graph
- add/edit **variables** + flags (`add_member_variable`, `set_blueprint_variable_*`)
- edit **properties / CDO defaults / DataTable rows / components**
  (`get`/`set_editor_property`, `SubobjectDataSubsystem`)
- **compile** blueprints (`BlueprintEditorLibrary.compile_blueprint`) — closes the loop

**CANNOT via the stock API** (not reflected; would need C++ unavailable in the kit):
- spawn a K2 node (CallFunction / Branch / …) or wire/connect pins
- even *read* a graph's nodes (`function_graphs` / `uber_graph_pages` aren't exposed)
- no `KismetEditorUtilities`, no `ImportNodesFromText`

## The unlock: an in-process ctypes bridge

The graph-editing entrypoints aren't *reflected*, but they **are exported** from
the editor's already-loaded DLLs. Code shipped over the remote-execution channel
runs **inside** the editor process — same address space as those DLLs — so it can
resolve the exported C++ functions by address and call them directly with
`ctypes`. Zero compilation; the functions are the same ones `Ctrl+C` / `Ctrl+V`
use in the editor.

```
WRITE: authored node text -> CanImportNodesFromText (oracle) -> ImportNodesFromText
       -> MarkBlueprintAsStructurallyModified -> compile_blueprint -> save_asset
READ:  GetAllGraphs -> UEdGraph::Nodes -> ExportNodesToText (per node) -> node text
```

The full mechanism — symbol resolution, struct marshalling, the crash that had to
be defeated to read safely — is in [INTERNALS.md](INTERNALS.md).

## The hybrid architecture decision

Intentionally small. **No transpiler, no MCP server, no editor plugin.**

- **Data / asset / compile (≈80%) → reflected `unreal` API**, driven by a thin
  Python helper over remote-execution. Fully automated.
- **Node-graph logic (≈20%) → Blueprint node *text*** authored programmatically,
  pasted via the ctypes bridge. The engine's `compile_blueprint` is the validator —
  if it compiles, the text was well-formed.

Rejected alternatives (explored and dropped): a custom-language→Blueprint
transpiler; a JS/TS→BP layer; shipping a C++ helper plugin (impossible in a
content-only kit anyway).

### Why not MCP?
An agent with shell + Python already drives the editor directly over
remote-execution — strictly more capable than a fixed MCP tool surface. MCP only
earns its place for an *external/sandboxed* client or a deliberately guardrailed
tool menu. Neither applies here.

## Engine-agnostic by construction

Nothing in the `bpkit` core is Conan-specific. The only install knowledge lives
in [`bpkit/config.py`](../bpkit/config.py), and every value is overridable via
`BPKIT_*` environment variables (engine root, bundled Python, plugin path,
remote-exec endpoints). Point those at another UE project and the whole toolchain
moves with you. The Conan Exiles "mounted followers" work is just **one
application** of the framework, kept in [`mods/`](../mods/) and documented
separately in [CONAN-NOTES.md](CONAN-NOTES.md).

## The layers

| Module | Role | Runs |
|---|---|---|
| `bpkit.bridge` | the ctypes engine: resolve exports, marshal FString/TArray/TSet, read / write / compile | **in the editor** |
| `bpkit.ir` | unified Graph IR: `parse` ↔ `edit` (wire/unwire/remove) ↔ `render` ↔ `compact`, plus typed authoring | pure stdlib (apply step needs the editor) |
| `bpkit.author` | minimal declarative authoring DSL (event/call/branch/wire → import text) | pure stdlib |
| `bpkit.compact` | compress exported node text into a dense, navigable outline (~23×) for token-cheap reasoning | pure stdlib |
| `bpkit.pe` | dependency-free PE export-table dumper (find the decorated symbol names to resolve) | host-side |
| `bpkit.config` | install paths + endpoints, `BPKIT_*`-overridable | host-side |
| `ue_run.py` | host-side driver: ship a local `.py` into the running editor, echo its output | host-side |

### How a typical task composes them
1. `bpkit.bridge.read_blueprint(path)` → node text for every graph.
2. `bpkit.compact` → navigate it cheaply; drill into one node losslessly when needed.
3. `bpkit.ir` / `bpkit.author` → build or mutate the graph as text.
4. `bpkit.bridge.inject(...)` → paste + compile + save. Compile errors = feedback.
