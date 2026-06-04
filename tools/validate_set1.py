"""In-editor payload: prove my set-of-1 is byte-identical to a real UE set-of-1
(pure reads), THEN do a single safe Export to confirm. No multi-element sets."""
import sys, ctypes
sys.path.insert(0, r"C:\Users\sugar\devel\conan\tools")
import importlib, ue_bp_inject as bpi
importlib.reload(bpi)


def hx(b): return b.hex(" ")


bp, full = bpi.scratch_blueprint(name="BP_Set1Val")
graph_ptr = bpi.find_object("EventGraph", outer=bpi.find_object(full))

# real UE set-of-1
TXT = ('Begin Object Class=/Script/UnrealEd.EdGraphNode_Comment Name="ONE"\n'
       '   NodeComment="SET1-MARKER-9Q"\nEnd Object\n')
cnt, gt = bpi.import_nodes_capture(graph_ptr, TXT)
node_ptr = int.from_bytes(ctypes.string_at(int.from_bytes(
    ctypes.string_at(ctypes.addressof(gt), 8), "little"), 8), "little")
print("imported node_ptr ->", hex(node_ptr))

mine = bpi.make_tset([node_ptr])
gt_b = ctypes.string_at(ctypes.addressof(gt), 128)
me_b = ctypes.string_at(ctypes.addressof(mine), 128)

# compare [8:76] (everything except Data.ptr@0:8, which legitimately differs)
print("UE  [8:76]:", hx(gt_b[8:76]))
print("ME  [8:76]:", hx(me_b[8:76]))
diffs = [o for o in range(8, 76) if gt_b[o] != me_b[o]]
print("byte diffs in [8:76] (excl Data.ptr):", diffs)

# now a SINGLE safe export of my set-of-1
out = bpi.FString()
bpi._export_nodes()(ctypes.byref(mine), ctypes.byref(out))
text = bpi.read_fstring(out)
print("=== Export(mine) -> %d chars, marker present: %s ==="
      % (len(text), "SET1-MARKER-9Q" in text))
print(text)
