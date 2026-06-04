"""In-editor payload: AUTHORING PROOF 2 -- author a WIRED graph (BeginPlay ->
PrintString) from minimal text, compile, and read it back through bp_compact to
confirm the exec wire survived import + pin reconstruction + compile."""
import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
import bp_bridge as bp
import bp_compact as bc
import unreal

bp_obj, full = bp.scratch_blueprint(name="BP_Author2")
bp_ptr, graph_ptr = bp.find_graph(full, "EventGraph")

# two minimal nodes cross-linked by pin id: event.then <-> call.execute.
# proper non-degenerate 32-hex GUIDs (avoid zero/low-value special-casing & collisions)
EV_NODE = "8F2A4C7E91B6D3450A1C2E4F6B8D0A11"
FN_NODE = "3D9E1F0B7C5A2648D1E3F507A9B2C4D6"
EV_THEN = "C4A7E2B8169D3F50721A8C4E0B6D9F32"
FN_EXEC = "5B1D3F7092E4A6C8B0D2F4861A3C5E79"
FN_STR = "A9F3C1E5709B2D4680C2E4A6183B5D7F"
TEXT = (
    'Begin Object Class=/Script/BlueprintGraph.K2Node_Event Name="K2Node_Event_BeginPlay"\n'
    '   EventReference=(MemberParent="/Script/CoreUObject.Class\'/Script/Engine.Actor\'",MemberName="ReceiveBeginPlay")\n'
    '   bOverrideFunction=True\n   NodePosX=0\n   NodePosY=0\n'
    '   NodeGuid=' + EV_NODE + '\n'
    '   CustomProperties Pin (PinId=' + EV_THEN + ',PinName="then",Direction="EGPD_Output",'
    'PinType.PinCategory="exec",LinkedTo=(K2Node_CallFunction_Print ' + FN_EXEC + ',))\n'
    'End Object\n'
    'Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction Name="K2Node_CallFunction_Print"\n'
    '   FunctionReference=(MemberParent="/Script/CoreUObject.Class\'/Script/Engine.KismetSystemLibrary\'",MemberName="PrintString")\n'
    '   NodePosX=320\n   NodePosY=0\n'
    '   NodeGuid=' + FN_NODE + '\n'
    '   CustomProperties Pin (PinId=' + FN_EXEC + ',PinName="execute",Direction="EGPD_Input",'
    'PinType.PinCategory="exec",LinkedTo=(K2Node_Event_BeginPlay ' + EV_THEN + ',))\n'
    '   CustomProperties Pin (PinId=' + FN_STR + ',PinName="InString",'
    'Direction="EGPD_Input",PinType.PinCategory="string",DefaultValue="BeginPlay! authored by bp_bridge")\n'
    'End Object\n')

print("can_import:", bp.can_import(graph_ptr, TEXT))
print("pasted:", bp.import_nodes(graph_ptr, TEXT))
bp.mark_structurally_modified(bp_ptr)
unreal.BlueprintEditorLibrary.compile_blueprint(unreal.load_asset(full.split(".")[0]))
print("compiled OK (no exception)")
unreal.EditorAssetLibrary.save_asset(full.split(".")[0])

# read back the whole graph, compacted
text = bp.export_nodes(bp.objects_with_outer(graph_ptr))
nodes = bc.parse_nodes(text)
print("\n=== authored graph (compacted) ===")
print(bc.compact_graph(nodes, "EventGraph"))

# correctness checks
n_beginplay = text.count('MemberName="ReceiveBeginPlay"')
print("ReceiveBeginPlay events in graph:", n_beginplay, "(want 1)")
