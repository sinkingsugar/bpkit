import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
for _m in ("bp_bridge",):
    sys.modules.pop(_m, None)
import unreal
import bp_bridge as bp

FULL = "/Game/_Scratch/BP_MountedFollowerManager.BP_MountedFollowerManager"
bp_obj = unreal.load_asset("/Game/_Scratch/BP_MountedFollowerManager")
unreal.BlueprintEditorLibrary.compile_blueprint(bp_obj)
bp_ptr, graph_ptr = bp.find_graph(FULL, "EventGraph")
txt = bp.export_nodes(bp.graph_nodes(graph_ptr))
import re
flagged = []
for b in re.split(r'(?=Begin Object Class=)', txt):
    if "bHasCompilerMessage=True" in b or "ErrorMsg" in b:
        nm = re.search(r'Name="([^"]+)"', b)
        em = re.search(r'ErrorMsg="([^"]*)"', b)
        flagged.append((nm.group(1) if nm else "?", em.group(1) if em else "(flagged)"))
print("compile errors:", flagged if flagged else "(none - clean)")
