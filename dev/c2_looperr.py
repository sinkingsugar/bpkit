import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
for _m in ("bp_bridge",): sys.modules.pop(_m, None)
import unreal, bp_bridge as bp, re
FULL = "/Game/_Scratch/BP_LoopTest.BP_LoopTest"
bp_obj = unreal.load_asset("/Game/_Scratch/BP_LoopTest")
unreal.BlueprintEditorLibrary.compile_blueprint(bp_obj)
bp_ptr, gp = bp.find_graph(FULL, "EventGraph")
txt = bp.export_nodes(bp.graph_nodes(gp))
for b in re.split(r'(?=Begin Object Class=)', txt):
    if "ErrorMsg" in b:
        nm = re.search(r'Name="([^"]+)"', b)
        i = b.find("ErrorMsg=")
        print("NODE:", nm.group(1) if nm else "?")
        print("  ", b[i:i+400].replace("\\n", " | ").split("\n")[0])
