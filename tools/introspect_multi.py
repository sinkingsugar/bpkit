"""In-editor payload: SAFE layout calibration. For several N, import N comment
nodes (the import out-TSet is a genuine UE-built TSet), parse its exact binary
layout, then build my make_tset() for the SAME node pointers and diff the
iterator-relevant fields. NO ExportNodesToText call anywhere -> cannot crash."""
import sys, ctypes
sys.path.insert(0, r"C:\Users\sugar\devel\conan\tools")
import importlib, ue_bp_inject as bpi
importlib.reload(bpi)


def u32(b, o): return int.from_bytes(b[o:o+4], "little")
def u64(b, o): return int.from_bytes(b[o:o+8], "little")
def i32(b, o):
    v = u32(b, o)
    return v - (1 << 32) if v >= (1 << 31) else v


def read_mem(addr, size):
    return bytes((ctypes.c_char * size).from_address(addr))


def parse_tset(buf):
    """buf: 128-byte tset (ctypes array). Returns a dict of fields + the list of
    node pointers in allocated-slot order."""
    raw = ctypes.string_at(ctypes.addressof(buf), 128)
    data_ptr = u64(raw, 0); num = i32(raw, 8); mx = i32(raw, 12)
    secptr = u64(raw, 32); numbits = i32(raw, 40); maxbits = i32(raw, 44)
    firstfree = i32(raw, 48); numfree = i32(raw, 52)
    # allocation bit words: from secondary if set, else inline [16:32]
    nwords = max(1, (maxbits + 31) // 32)
    if secptr:
        bitsrc = read_mem(secptr, nwords * 4)
    else:
        bitsrc = raw[16:16 + nwords * 4]
    setbits = [i for i in range(numbits) if (u32(bitsrc, (i // 32) * 4) >> (i % 32)) & 1]
    # elements (stride 16) for allocated slots
    ptrs = []
    elem_meta = []
    if data_ptr and mx > 0:
        ebuf = read_mem(data_ptr, mx * 16)
        for i in setbits:
            ptrs.append(u64(ebuf, i * 16))
            elem_meta.append((i32(ebuf, i * 16 + 8), i32(ebuf, i * 16 + 12)))
    return dict(num=num, mx=mx, secptr=bool(secptr), numbits=numbits, maxbits=maxbits,
                firstfree=firstfree, numfree=numfree, nset=len(setbits),
                ptrs=ptrs, elem_meta=elem_meta, inline=raw[16:32].hex())


def comment_blob(n):
    return "".join(
        'Begin Object Class=/Script/UnrealEd.EdGraphNode_Comment Name="C_%d"\n'
        '   NodeComment="c%d"\n   NodePosX=%d\n   NodePosY=%d\nEnd Object\n'
        % (i, i, (i % 20) * 24, (i // 20) * 24) for i in range(n))


bp, full = bpi.scratch_blueprint(name="BP_TSetCal")
graph_ptr = bpi.find_object("EventGraph", outer=bpi.find_object(full))
print("graph_ptr ->", hex(graph_ptr or 0))

for N in (1, 5, 33, 64, 100, 200, 400):
    cnt, gt = bpi.import_nodes_capture(graph_ptr, comment_blob(N))
    G = parse_tset(gt)
    # build mine for the SAME pointers (in UE's allocated-slot order)
    mine_buf = bpi.make_tset(G["ptrs"])
    M = parse_tset(mine_buf)
    print("\n--- N=%d  (import pasted=%d, UE set nset=%d) ---" % (N, cnt, G["nset"]))
    def line(tag, d):
        print("  %-3s Num=%-4d Max=%-4d sec=%-5s NumBits=%-4d MaxBits=%-5d "
              "First=%-3d NumFree=%-2d nset=%-4d"
              % (tag, d["num"], d["mx"], d["secptr"], d["numbits"], d["maxbits"],
                 d["firstfree"], d["numfree"], d["nset"]))
    line("UE", G); line("ME", M)
    # do my pointers match UE's (same set, same order)?
    same_ptrs = G["ptrs"] == M["ptrs"]
    print("  ptrs identical:", same_ptrs, "| UE elem_meta[0:3]:", G["elem_meta"][:3])
