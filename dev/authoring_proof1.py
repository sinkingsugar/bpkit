"""In-editor payload: AUTHORING PROOF 1 -- does a MINIMAL CallFunction node text
get its pins reconstructed by UE on import? Inject a bare PrintString (just the
FunctionReference + one input pin) and read back what UE materialized."""
import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
import bp_bridge as bp
import unreal

bp_obj, full = bp.scratch_blueprint(name="BP_Author")
bp_ptr, graph_ptr = bp.find_graph(full, "EventGraph")
print("bp=%s graph=%s" % (hex(bp_ptr or 0), hex(graph_ptr or 0)))

# minimal: class + function reference + node guid + ONE input pin with a literal
TEXT = (
    'Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction Name="K2Node_CallFunction_PrintTest"\n'
    '   FunctionReference=(MemberParent="/Script/CoreUObject.Class\'/Script/Engine.KismetSystemLibrary\'",MemberName="PrintString")\n'
    '   NodePosX=240\n   NodePosY=80\n'
    '   NodeGuid=000000000000000000000000000A0001\n'
    '   CustomProperties Pin (PinId=000000000000000000000000000000E1,PinName="InString",'
    'Direction="EGPD_Input",PinType.PinCategory="string",DefaultValue="Hello from bp_bridge")\n'
    'End Object\n')

print("can_import:", bp.can_import(graph_ptr, TEXT))

before = set(bp.objects_with_outer(graph_ptr))
pasted = bp.import_nodes(graph_ptr, TEXT)
after = bp.objects_with_outer(graph_ptr)
new = [p for p in after if p not in before]
print("pasted=%d  new node ptrs=%d" % (pasted, len(new)))

print("=== readback of the newly created node (post-import, pre-compile) ===")
print(bp.export_nodes(new))

bp.mark_structurally_modified(bp_ptr)
unreal.BlueprintEditorLibrary.compile_blueprint(unreal.load_asset(full.split(".")[0]))
print("compiled OK (no exception)")
