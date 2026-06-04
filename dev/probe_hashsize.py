"""In-editor payload: SAFE read of HashSize + hash head from real UE sets across
sizes. Pure reads, no Export -> cannot crash."""
import sys, ctypes
sys.path.insert(0, r"C:\Users\sugar\devel\conan\tools")
import importlib, ue_bp_inject as bpi
importlib.reload(bpi)


def comment_blob(n):
    return "".join(
        'Begin Object Class=/Script/UnrealEd.EdGraphNode_Comment Name="H_%d"\n'
        '   NodeComment="h%d"\nEnd Object\n' % (i, i) for i in range(n))


bp, full = bpi.scratch_blueprint(name="BP_HashCal")
graph_ptr = bpi.find_object("EventGraph", outer=bpi.find_object(full))

for N in (1, 2, 3, 4, 5, 8, 16, 33, 64, 100):
    cnt, gt = bpi.import_nodes_capture(graph_ptr, comment_blob(N))
    raw = ctypes.string_at(ctypes.addressof(gt), 128)
    hashsize = int.from_bytes(raw[72:76], "little")
    hash_inline = raw[56:72].hex(" ")
    hash_secptr = int.from_bytes(raw[64:72], "little")
    print("N=%-3d HashSize=%-4d hash[56:72]=%s secptr=0x%X"
          % (N, hashsize, hash_inline, hash_secptr))
