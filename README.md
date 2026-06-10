# bpkit

**Read, author, edit, and compile Unreal Engine 5 Blueprint node graphs from
*outside* the editor** — no C++ compilation, no editor UI, no clipboard, no window
focus. Built for **content-only kits** (a packaged editor with no C++ toolchain),
where Blueprint graph editing isn't otherwise reachable by automation.

Blueprints are a visual language meant for a human clicking in the editor; bpkit
treats the graph as **data** so an agent (it's built for **Claude Code**) — or a
plain script — can manipulate it at scale. It
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

## Not just authoring — interrogate the game

Reading is half the tool. Point Claude Code at any shipped Blueprint and just **ask
how the game works** — "what gates mounting?", "where do follower caps live?",
"what does this recipe actually spawn?" Claude dumps the graphs, follows the wires,
and answers, turning the dev kit into a queryable knowledge base of the game's own
logic. [`docs/CONAN-NOTES.md`](docs/CONAN-NOTES.md) is exactly that: live-verified
facts about Conan's internals produced by interrogating its Blueprints — useful even
if you never author a node.

## Engine-agnostic

The `bpkit` core is generic. Install-specific paths live only in
[`bpkit/config.py`](bpkit/config.py) and are overridable via `BPKIT_*` environment
variables (engine root, bundled Python, plugin path, remote-exec endpoints). Point
them at any UE project to reuse the toolchain. The Conan Exiles "mounted followers"
work is one **application** of the framework, in [`mods/`](mods/).

## Quick start — with Claude Code (the intended way)

bpkit is built to be driven by **[Claude Code](https://claude.com/claude-code)**.
The repo ships its own slash-commands in [`.claude/skills/`](.claude/skills/), plus a
`bpkit` skill that **auto-loads** — so you can just *describe* a Blueprint task in
plain language and have Claude drive the editor for you, no Python required.

> **Editor prerequisite (any path):** launch the editor and make sure the **Python
> Editor Script Plugin** is enabled (*Edit → Plugins → search "Python"*; restart the
> editor if you just enabled it — the Conan dev kit ships with it already on), then
> *Project Settings → Plugins → Python → **Enable Remote Execution***.

1. **Open this repo in Claude Code.**
2. **`/setup`** — adaptive health check: verifies the remote-exec channel *and* that
   the native ctypes bridge resolves on *your* editor build. It self-heals symbol
   drift instead of hard-failing.
3. Then **just ask** — *"read BP_BatDemonGlider"*, *"author a ModController that
   raises the Mount cap"*, *"why does this graph fail to compile?"* — the `bpkit`
   skill carries the standing rules and Claude does the work. Or use the explicit
   commands:

   | command | does |
   |---|---|
   | `/bp-read <asset>` | dump a blueprint's graphs as a dense, navigable outline |
   | `/deploy <mod>` | build & deploy a whole mod from its `manifest.py` (Play stopped) |
   | `/bp-test` | run the offline + in-editor test suites |
   | `/bp-channel` | quick "is the editor channel live?" check |

4. **`/install`** (once) — copies these commands into `~/.claude/skills/` so they
   work from any project directory, not just this repo.

<details>
<summary><b>Or drive it yourself, no Claude Code</b> — the manual / scripting path</summary>

Every skill is a thin wrapper over a plain Python entrypoint you can run directly
with the editor's **bundled** interpreter (bare `python` hits the disabled Windows
Store alias):

```powershell
$py = 'C:\Program Files\Epic Games\CEUE5Devkit\Engine\Binaries\ThirdParty\Python3\Win64\python.exe'

& $py ue_run.py bpkit\ops\ping.py                 # is the remote-exec channel up?
& $py ue_run.py bpkit\ops\selftest.py             # does the native ctypes bridge resolve?
& $py ue_run.py examples\inject_and_compile.py    # author a node -> compile -> save
& $py ue_run.py examples\author_logic.py          # author wired logic from intent
& $py ue_run.py examples\edit_graph.py            # in-place edit (read->IR->rewire->replace)
& $py ue_run.py tests\test_bp_authoring.py        # deterministic regression suite
& $py ue_run.py bpkit\ops\deploy.py mounted-followers   # build+deploy a whole mod (Play stopped)
```

`ue_run.py` ships a local payload's source into the running editor and injects the
repo root onto its `sys.path`, so payloads just `import bpkit`. The offline library
tests need no editor: `& $py tests\test_offline.py`.
</details>

## Layout

| path | what |
|---|---|
| `.claude/skills/` | the **Claude Code entry point**: `/setup`, `/install`, `/bp-read`, `/deploy`, `/bp-test`, `/bp-channel`, + the auto-loading `bpkit` skill |
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

## License

[MIT](LICENSE). The bpkit framework and mod build scripts are original work; they
contain no Funcom or Epic code or assets.
