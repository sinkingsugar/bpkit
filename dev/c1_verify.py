import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
import unreal
import bp_bridge as bp

FULL = "/Game/_Scratch/BP_MF_Recipe.BP_MF_Recipe"
bp_ptr, graph_ptr = bp.find_graph(FULL, "EventGraph")
nodes = bp.graph_nodes(graph_ptr)
print("EventGraph live node count:", len(nodes))
txt = bp.export_nodes(nodes)
for line in txt.splitlines():
    s = line.strip()
    if s.startswith("Begin Object") or "MemberName" in s or "CustomFunctionName" in s:
        print("  ", s[:140])

# compile + report status
bp_obj = unreal.load_asset("/Game/_Scratch/BP_MF_Recipe")
unreal.BlueprintEditorLibrary.compile_blueprint(bp_obj)
try:
    status = bp_obj.get_editor_property("status")
    print("\nblueprint status:", status)
except Exception as e:
    print("status err:", e)
print("is BP up to date:", unreal.BlueprintEditorLibrary.is_blueprint_dirty(bp_obj) if hasattr(unreal.BlueprintEditorLibrary,'is_blueprint_dirty') else "?")
