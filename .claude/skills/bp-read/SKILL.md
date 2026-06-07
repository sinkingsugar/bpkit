---
name: bp-read
description: Read an Unreal blueprint's node graphs and show a dense, navigable outline. Use when inspecting or understanding a Blueprint's logic. Argument is the asset path, e.g. /Game/Foo/BP_Bar.
argument-hint: <asset-path>
---

Read the blueprint at `$ARGUMENTS` and summarize its graphs (do not paste the raw dump — use the compact view).

1. Dump every graph: `& $py ue_run.py examples/read_blueprint.py "$ARGUMENTS"` — writes `dump_<Name>.txt` at the repo root and prints per-graph node/char counts.
2. Navigate it: `& $py bpkit/compact.py dump_<Name>.txt --summary` (graph map + entry points), then `--graph <GraphName>` to drill into one graph.
3. Report the graph map and any graph the user asks about. For the exact text of a single node (e.g. to author a variant), re-export just that node losslessly rather than reading the whole dump.

($py = `bpkit.config.BUNDLED_PYTHON` or `$env:BPKIT_PYTHON`. With no argument, `read_blueprint` falls back to its default asset constant.)
