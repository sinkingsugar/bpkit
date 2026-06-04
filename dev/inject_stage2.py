"""In-editor payload: STAGE 2 -- the real mutating injection.

Paste a comment node into the scratch BP's EventGraph via native
ImportNodesFromText, mark the blueprint modified, recompile, and report.
A comment node is schema-trivial (no pins to wire) so it isolates the
paste mechanism from node-wiring concerns."""
import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan\tools")
import importlib, ue_bp_inject as bpi
importlib.reload(bpi)
import unreal

bp, full = bpi.scratch_blueprint()
bp_ptr = bpi.find_object(full)
graph_ptr = bpi.find_object("EventGraph", outer=bp_ptr)
print("bp_ptr   ->", hex(bp_ptr or 0))
print("graph_ptr->", hex(graph_ptr or 0))

TEXT = (
    'Begin Object Class=/Script/UnrealEd.EdGraphNode_Comment Name="EdGraphNode_Comment_0"\n'
    '   NodeWidth=420\n'
    '   NodeHeight=160\n'
    '   NodeComment="injected by Claude via ctypes ImportNodesFromText"\n'
    '   NodePosX=96\n'
    '   NodePosY=96\n'
    'End Object\n'
)

print("CanImport ->", bpi.can_import(graph_ptr, TEXT))

pasted = bpi.import_nodes(graph_ptr, TEXT)
print("ImportNodesFromText pasted node count ->", pasted)

bpi.mark_structurally_modified(bp_ptr)
print("marked structurally modified")

res = unreal.BlueprintEditorLibrary.compile_blueprint(bp)
print("compile_blueprint returned ->", res)

# persist so the result is inspectable on disk / on reopen
saved = unreal.EditorAssetLibrary.save_asset(full.split(".")[0])
print("save_asset ->", saved)
print("=== Stage 2 done ===")
