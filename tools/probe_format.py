"""In-editor payload: use CanImportNodesFromText as a non-destructive oracle to
find an accepted node-text format. Mutates nothing."""
import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan\tools")
import importlib, ue_bp_inject as bpi
importlib.reload(bpi)

bp, full = bpi.scratch_blueprint()
graph_ptr = bpi.find_object("EventGraph", outer=bpi.find_object(full))
print("graph_ptr ->", hex(graph_ptr or 0))

GUID = "0123456789ABCDEF0123456789ABCDEF"

candidates = {
    "comment_full": (
        'Begin Object Class=/Script/UnrealEd.EdGraphNode_Comment Name="EdGraphNode_Comment_0"\n'
        '   NodeWidth=400\n'
        '   NodeHeight=200\n'
        '   NodeComment="injected via ctypes"\n'
        '   NodePosX=128\n'
        '   NodePosY=128\n'
        '   NodeGuid=' + GUID + '\n'
        'End Object\n'
    ),
    "comment_min": (
        'Begin Object Class=/Script/UnrealEd.EdGraphNode_Comment Name="EdGraphNode_Comment_0"\n'
        '   NodeComment="hi"\n'
        '   NodeGuid=' + GUID + '\n'
        'End Object\n'
    ),
    "comment_no_guid": (
        'Begin Object Class=/Script/UnrealEd.EdGraphNode_Comment Name="EdGraphNode_Comment_0"\n'
        '   NodeComment="hi"\n'
        'End Object\n'
    ),
}

for name, text in candidates.items():
    try:
        ok = bpi.can_import(graph_ptr, text)
    except Exception as e:
        ok = "ERR:%s" % e
    print("  %-16s -> %s" % (name, ok))
