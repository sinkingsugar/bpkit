"""Example: in-place EDIT of an existing graph via the replace flow.

    python ue_run.py examples/edit_graph.py

Plain ImportNodesFromText can't wire a new node to a pre-existing one (paste only
cross-links within the pasted set). So to rewire existing nodes we: read the graph
-> bp_ir -> mutate (the new wire is now intra-set) -> clear_graph -> re-import the
whole rendered graph -> compile. Here we drop in two UNWIRED nodes, then edit the
graph to connect them."""
import sys, importlib
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
import bp_compact, bp_ir, bp_bridge
# the editor process is long-lived and caches modules; reload so edits to the
# library are picked up without restarting the editor (in dependency order).
for _m in (bp_compact, bp_ir, bp_bridge):
    importlib.reload(_m)
bp = bp_bridge
import unreal

asset_obj, full = bp.scratch_blueprint(name="BP_ReplaceDemo")
asset = full.split(".")[0]
bp_ptr, graph_ptr = bp.find_graph(full, "EventGraph")
bp.clear_graph(bp_ptr, graph_ptr)       # clean slate (deterministic across reruns)

# --- set up an "existing" graph: a CustomEvent and a PrintString, UNWIRED ---
g0 = bp_ir.Graph("EventGraph")
g0.custom_event("Trigger")
g0.call("PrintString", "/Script/Engine.KismetSystemLibrary",
        inputs={"InString": "edited in by replace-flow"}, pos=(360, 0))
bp.inject(full, g0.render())            # import + compile + save (no wire yet)

print("=== BEFORE edit ===")
text = bp.export_nodes(bp.objects_with_outer(graph_ptr))
print(bp_ir.Graph.parse_one(text, "EventGraph").compact())

# --- EDIT: read -> IR -> wire the two existing nodes -> replace ---
g = bp_ir.Graph.parse_one(text, "EventGraph")
ev = g.by_type("CustomEvent")[0]
call = g.by_type("CallFunction")[0]
g.wire(ev, "then", call, "execute")     # new edge, now intra-set

removed = bp.clear_graph(bp_ptr, graph_ptr)
pasted = bp.import_nodes(graph_ptr, g.render())
bp.mark_structurally_modified(bp_ptr)
unreal.BlueprintEditorLibrary.compile_blueprint(unreal.load_asset(asset))
unreal.EditorAssetLibrary.save_asset(asset)
print("\nreplace: removed %d, re-imported %d nodes, compiled" % (removed, pasted))

print("\n=== AFTER edit ===")
text2 = bp.export_nodes(bp.objects_with_outer(graph_ptr))
g2 = bp_ir.Graph.parse_one(text2, "EventGraph")
print(g2.compact())
ev2 = g2.by_type("CustomEvent")[0]
print("Trigger.then is now wired:", bool(ev2.pin("then").links))
# NOTE: the live session may also surface undo-buffer orphans (nodes RemoveNode
# detached but the transaction system still references, so GC can't collect them).
# They are NOT in the graph's authoritative node-array and are not serialized --
# the saved asset is clean. A Nodes-array reader (vs objects_with_outer) is the fix.
