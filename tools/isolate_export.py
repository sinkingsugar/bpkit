"""In-editor payload: isolate WHY export of a byte-identical hand-built set faults
while UE's own set exports fine. Export gt (UE-built) vs mine vs a hybrid in one
run, each guarded so a fault doesn't stop the others."""
import sys, ctypes
sys.path.insert(0, r"C:\Users\sugar\devel\conan\tools")
import importlib, ue_bp_inject as bpi
importlib.reload(bpi)


def try_export(label, tset_buf):
    out = bpi.FString()
    try:
        bpi._export_nodes()(ctypes.byref(tset_buf), ctypes.byref(out))
        t = bpi.read_fstring(out)
        print("  %-22s -> OK (%d chars)" % (label, len(t)))
    except OSError as e:
        print("  %-22s -> FAULT %s" % (label, e))


bp, full = bpi.scratch_blueprint(name="BP_Isolate")
graph_ptr = bpi.find_object("EventGraph", outer=bpi.find_object(full))

TXT = ('Begin Object Class=/Script/UnrealEd.EdGraphNode_Comment Name="ISO"\n'
       '   NodeComment="iso"\nEnd Object\n')
cnt, gt = bpi.import_nodes_capture(graph_ptr, TXT)
gt_data_ptr = int.from_bytes(ctypes.string_at(ctypes.addressof(gt), 8), "little")
node_ptr = int.from_bytes(ctypes.string_at(gt_data_ptr, 8), "little")
print("node_ptr=%s  gt.Data.ptr=%s" % (hex(node_ptr), hex(gt_data_ptr)))

# 1) UE's own set (known good)
try_export("UE gt set", gt)

# 2) my byte-identical set
mine = bpi.make_tset([node_ptr])
try_export("my make_tset", mine)

# 3) hybrid: my header but pointing Data.ptr at UE's element buffer
hyb = bpi.make_tset([node_ptr])
ctypes.c_uint64.from_buffer(hyb, 0).value = gt_data_ptr      # use UE's element array
try_export("my header + UE elems", hyb)

# 4) gt header but Data.ptr at my element buffer
mine2 = bpi.make_tset([node_ptr])
my_data_ptr = int.from_bytes(ctypes.string_at(ctypes.addressof(mine2), 8), "little")
gt2 = (ctypes.c_byte * 128)()
ctypes.memmove(gt2, gt, 128)
ctypes.c_uint64.from_buffer(gt2, 0).value = my_data_ptr      # UE header, my elements
gt2._keep = mine2
try_export("UE header + my elems", gt2)
