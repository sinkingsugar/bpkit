"""In-editor payload: dump the raw bytes of a genuine UE-built TSet<UEdGraphNode*>
(the out-set from an import) so we can mirror its exact layout when hand-building
a TSet for ExportNodesToText. Pure reads -- cannot crash the editor."""
import sys, ctypes
sys.path.insert(0, r"C:\Users\sugar\devel\conan\tools")
import importlib, ue_bp_inject as bpi
importlib.reload(bpi)

bp, full = bpi.scratch_blueprint(name="BP_Introspect")
graph_ptr = bpi.find_object("EventGraph", outer=bpi.find_object(full))

TEXT = ('Begin Object Class=/Script/UnrealEd.EdGraphNode_Comment Name="C0"\n'
        '   NodeComment="introspect"\n'
        'End Object\n')
count, tset = bpi.import_nodes_capture(graph_ptr, TEXT)
print("count ->", count)


def u32(buf, off): return int.from_bytes(bytes(buf[off:off+4]), "little")
def u64(buf, off): return int.from_bytes(bytes(buf[off:off+8]), "little")
def i32(buf, off):
    v = u32(buf, off)
    return v - (1 << 32) if v >= (1 << 31) else v


raw = bytes(tset)
print("TSet first 96 bytes (hex):")
for r in range(0, 96, 16):
    print("  %03d: %s" % (r, raw[r:r+16].hex(" ")))

data_ptr = u64(raw, 0)
print("Elements.Data.ptr  = 0x%016X" % data_ptr)
print("Elements.Data.Num  = %d" % i32(raw, 8))
print("Elements.Data.Max  = %d" % i32(raw, 12))
print("BitArray.Inline[0..16] =", raw[16:32].hex(" "))
print("BitArray.SecondaryPtr  = 0x%016X" % u64(raw, 32))
print("BitArray.NumBits = %d  MaxBits = %d" % (i32(raw, 40), i32(raw, 44)))
print("Sparse.FirstFreeIndex = %d  NumFreeIndices = %d" % (i32(raw, 48), i32(raw, 52)))
print("Hash region [56..80] =", raw[56:80].hex(" "))

# deref the element buffer: first element's first 8 bytes should be the node ptr
if data_ptr:
    elem = (ctypes.c_char * 32).from_address(data_ptr)
    eraw = bytes(elem)
    print("Element[0] 32 bytes:", eraw.hex(" "))
    print("Element[0].Value(node ptr) = 0x%016X" % int.from_bytes(eraw[0:8], "little"))
