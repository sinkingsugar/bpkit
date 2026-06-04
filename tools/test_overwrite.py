"""In-editor payload: verify the 'reuse a real UE set-of-1 as a template, swap the
element pointer' approach. Export two DIFFERENT nodes through one UE-built set."""
import sys, ctypes
sys.path.insert(0, r"C:\Users\sugar\devel\conan\tools")
import importlib, ue_bp_inject as bpi
importlib.reload(bpi)


def export_via_template(template, data_ptr, node_ptr):
    ctypes.c_uint64.from_buffer(template, 0)  # touch (no-op safety)
    # overwrite element[0].Value (first 8 bytes of UE's element buffer)
    ctypes.memmove(data_ptr, node_ptr.to_bytes(8, "little"), 8)
    out = bpi.FString()
    bpi._export_nodes()(ctypes.byref(template), ctypes.byref(out))
    return bpi.read_fstring(out)


bp, full = bpi.scratch_blueprint(name="BP_Overwrite")
graph_ptr = bpi.find_object("EventGraph", outer=bpi.find_object(full))

# build a valid UE set-of-1 template (import one dummy node)
_, template = bpi.import_nodes_capture(
    graph_ptr,
    'Begin Object Class=/Script/UnrealEd.EdGraphNode_Comment Name="TPL"\n'
    '   NodeComment="template"\nEnd Object\n')
tmpl_data_ptr = int.from_bytes(ctypes.string_at(ctypes.addressof(template), 8), "little")
print("template Data.ptr ->", hex(tmpl_data_ptr))

# two more distinct nodes to export through the template
_, sA = bpi.import_nodes_capture(
    graph_ptr,
    'Begin Object Class=/Script/UnrealEd.EdGraphNode_Comment Name="AAA"\n'
    '   NodeComment="NODE-ALPHA"\nEnd Object\n')
_, sB = bpi.import_nodes_capture(
    graph_ptr,
    'Begin Object Class=/Script/UnrealEd.EdGraphNode_Comment Name="BBB"\n'
    '   NodeComment="NODE-BRAVO"\nEnd Object\n')
ptrA = int.from_bytes(ctypes.string_at(int.from_bytes(ctypes.string_at(ctypes.addressof(sA), 8), "little"), 8), "little")
ptrB = int.from_bytes(ctypes.string_at(int.from_bytes(ctypes.string_at(ctypes.addressof(sB), 8), "little"), 8), "little")
print("ptrA=%s ptrB=%s" % (hex(ptrA), hex(ptrB)))

tA = export_via_template(template, tmpl_data_ptr, ptrA)
print("export A -> %d chars | ALPHA present: %s" % (len(tA), "NODE-ALPHA" in tA))
tB = export_via_template(template, tmpl_data_ptr, ptrB)
print("export B -> %d chars | BRAVO present: %s | ALPHA absent: %s"
      % (len(tB), "NODE-BRAVO" in tB, "NODE-ALPHA" not in tB))
