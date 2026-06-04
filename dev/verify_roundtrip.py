"""In-editor payload: prove we can SEE the graph contents as text.
Paste a marked comment node, then run the engine's own ExportNodesToText on the
UE-built out-TSet and print the serialized text back."""
import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan\tools")
import importlib, ue_bp_inject as bpi
importlib.reload(bpi)

bp, full = bpi.scratch_blueprint(name="BP_RoundTrip")
graph_ptr = bpi.find_object("EventGraph", outer=bpi.find_object(full))
print("graph_ptr ->", hex(graph_ptr or 0))

MARKER = "ROUNDTRIP-MARKER-7F3A"
TEXT = (
    'Begin Object Class=/Script/UnrealEd.EdGraphNode_Comment Name="EdGraphNode_Comment_0"\n'
    '   NodeWidth=400\n'
    '   NodeHeight=150\n'
    '   NodeComment="' + MARKER + '"\n'
    '   NodePosX=64\n'
    '   NodePosY=64\n'
    'End Object\n'
)

count, tset = bpi.import_nodes_capture(graph_ptr, TEXT)
print("pasted count ->", count)

text_back = bpi.export_text_from_tset(tset)
print("=== ExportNodesToText returned %d chars ===" % len(text_back))
print(text_back)
print("=== marker round-tripped? ->", MARKER in text_back, "===")
