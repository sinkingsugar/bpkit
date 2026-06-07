"""Surface a Blueprint's real compile errors. compile_blueprint doesn't raise, so
read the error annotations the compiler writes onto the nodes (bHasCompilerMessage/
ErrorMsg) and report which node + message. Edit FULL to point at your asset.
Run: python ue_run.py bpkit/ops/compile_errors.py
"""
from bpkit import bridge as bp
import unreal

FULL = "/Game/_Scratch/BP_MF_Recipe.BP_MF_Recipe"
bp_obj = unreal.load_asset("/Game/_Scratch/BP_MF_Recipe")
unreal.BlueprintEditorLibrary.compile_blueprint(bp_obj)

bp_ptr, graph_ptr = bp.find_graph(FULL, "EventGraph")
txt = bp.export_nodes(bp.graph_nodes(graph_ptr))

# split into node blocks, flag any with a compiler message
import re
blocks = re.split(r'(?=Begin Object Class=)', txt)
flagged = 0
for b in blocks:
    if "bHasCompilerMessage=True" in b or "ErrorMsg" in b or 'ErrorType' in b:
        flagged += 1
        nm = re.search(r'Name="([^"]+)"', b)
        fn = re.search(r'MemberName="([^"]+)"', b)
        em = re.search(r'ErrorMsg="([^"]*)"', b)
        print("NODE:", nm.group(1) if nm else "?",
              "| fn:", fn.group(1) if fn else "-",
              "| ErrorMsg:", em.group(1) if em else "(flagged, see block)")
if not flagged:
    print("no per-node error annotations found in exported text.")
    print("dumping each node's function ref + any orphan/disconnected required pins:")
    for b in blocks:
        if "K2Node_CallFunction" not in b:
            continue
        fn = re.search(r'MemberName="([^"]+)"', b)
        parent = re.search(r"MemberParent=\"[^']*'([^']+)'", b)
        # required (non-default) input data pins with no link and no default
        print("  fn:", fn.group(1) if fn else "?", "| parent:", parent.group(1) if parent else "?")
