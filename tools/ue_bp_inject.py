"""In-editor ctypes bridge to UE's native Blueprint-graph paste path.

RUN THIS INSIDE THE EDITOR (via tools/ue_run.py), never with the standalone
interpreter -- it depends on the engine DLLs already being mapped into the
process and on real UObject pointers from that same address space.

Why this exists: the content-only Conan kit doesn't reflect graph-editing to
Python (can't spawn/wire K2 nodes, can't even read a graph). But the C++ paste
entrypoint IS exported from the loaded editor DLLs, so we call it by address:

    void FEdGraphUtilities::ImportNodesFromText(UEdGraph*, const FString&,
                                                TSet<UEdGraphNode*>&)

That is exactly what Ctrl+V runs. Feed it node text -> real nodes appear in the
graph, with zero window focus / clipboard / UI automation.

This file currently implements Stage 0 (layout primitives) + Stage 1 (read-only
proof via the non-mutating CanImportNodesFromText). The mutating import is added
only after Stage 1 validates the whole ctypes stack.
"""
import ctypes

# --- exact decorated (MSVC-mangled) names, verified via tools/pe_exports.py ---
SYM = {
    # UObject* StaticFindObject(UClass*, UObject* Outer, const TCHAR* Name, bool ExactClass)
    "StaticFindObject": ("UnrealEditor-CoreUObject.dll",
                         b"?StaticFindObject@@YAPEAVUObject@@PEAVUClass@@PEAV1@PEB_W_N@Z"),
    # bool FEdGraphUtilities::CanImportNodesFromText(const UEdGraph*, const FString&)
    "CanImportNodesFromText": ("UnrealEditor-UnrealEd.dll",
                               b"?CanImportNodesFromText@FEdGraphUtilities@@SA_NPEBVUEdGraph@@AEBVFString@@@Z"),
    # void FEdGraphUtilities::ImportNodesFromText(UEdGraph*, const FString&, TSet<UEdGraphNode*>&)
    "ImportNodesFromText": ("UnrealEditor-UnrealEd.dll",
                            b"?ImportNodesFromText@FEdGraphUtilities@@SAXPEAVUEdGraph@@AEBVFString@@AEAV?$TSet@PEAVUEdGraphNode@@U?$DefaultKeyFuncs@PEAVUEdGraphNode@@$0A@@@VFDefaultSetAllocator@@@@@Z"),
    # void FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(UBlueprint*)
    "MarkBlueprintAsStructurallyModified": ("UnrealEditor-UnrealEd.dll",
                                            b"?MarkBlueprintAsStructurallyModified@FBlueprintEditorUtils@@SAXPEAVUBlueprint@@@Z"),
    # void FEdGraphUtilities::ExportNodesToText(TSet<UObject*> /*by value*/, FString& /*out*/)
    "ExportNodesToText": ("UnrealEditor-UnrealEd.dll",
                          b"?ExportNodesToText@FEdGraphUtilities@@SAXV?$TSet@PEAVUObject@@U?$DefaultKeyFuncs@PEAVUObject@@$0A@@@VFDefaultSetAllocator@@@@AEAVFString@@@Z"),
    # void UBlueprint::GetAllGraphs(TArray<UEdGraph*>&) const
    "GetAllGraphs": ("UnrealEditor-Engine.dll",
                     b"?GetAllGraphs@UBlueprint@@QEBAXAEAV?$TArray@PEAVUEdGraph@@V?$TSizedDefaultAllocator@$0CA@@@@@@Z"),
    # void GetObjectsWithOuter(const UObjectBase*, TArray<UObject*>&, bool nested, EObjectFlags, EInternalObjectFlags)
    "GetObjectsWithOuter": ("UnrealEditor-CoreUObject.dll",
                            b"?GetObjectsWithOuter@@YAXPEBVUObjectBase@@AEAV?$TArray@PEAVUObject@@V?$TSizedDefaultAllocator@$0CA@@@@@_NW4EObjectFlags@@W4EInternalObjectFlags@@@Z"),
    # void* FMemory::Malloc(SIZE_T, uint32 alignment)  /  void FMemory::Free(void*)
    "Malloc": ("UnrealEditor-Core.dll", b"?Malloc@FMemory@@SAPEAX_KI@Z"),
    "Free":   ("UnrealEditor-Core.dll", b"?Free@FMemory@@SAXPEAX@Z"),
}

_k32 = ctypes.windll.kernel32
_k32.GetModuleHandleW.restype = ctypes.c_void_p
_k32.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
_k32.GetProcAddress.restype = ctypes.c_void_p
_k32.GetProcAddress.argtypes = [ctypes.c_void_p, ctypes.c_char_p]


def _resolve(key):
    dll, name = SYM[key]
    h = _k32.GetModuleHandleW(dll)
    if not h:
        raise OSError("module not mapped: %s" % dll)
    addr = _k32.GetProcAddress(h, name)
    if not addr:
        raise OSError("export not found in %s: %s" % (dll, name.decode()))
    return addr


# --- Stage 0: argument layout primitives -------------------------------------

class FString(ctypes.Structure):
    """UE FString == TArray<TCHAR>: { TCHAR* data; int32 num; int32 max }.
    num/max COUNT THE NULL TERMINATOR. We keep the backing buffer alive by
    stashing it on the instance (._buf) so it isn't GC'd while UE reads it."""
    _fields_ = [("data", ctypes.c_void_p), ("num", ctypes.c_int32), ("max", ctypes.c_int32)]

    @classmethod
    def make(cls, s):
        buf = ctypes.create_unicode_buffer(s)        # s + trailing NUL, UTF-16
        n = len(s) + 1
        fs = cls(ctypes.cast(buf, ctypes.c_void_p), n, n)
        fs._buf = buf
        return fs


def empty_tset(nbytes=256):
    """A zero-initialized buffer used as an empty TSet<UEdGraphNode*>& out-param.
    A value-zeroed UE TSet is the valid empty state (empty TArray + empty inline
    TBitArray, lazily-built hash). The callee only writes into it; we never run
    its destructor, so whatever it heap-allocates simply leaks for the session."""
    return (ctypes.c_byte * nbytes)()


# --- typed callables ----------------------------------------------------------

def _static_find_object():
    fn = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                          ctypes.c_wchar_p, ctypes.c_bool)(_resolve("StaticFindObject"))
    return fn


def _can_import():
    return ctypes.CFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(
        _resolve("CanImportNodesFromText"))


def _import_nodes():
    # void(UEdGraph*, const FString&, TSet<UEdGraphNode*>&)
    return ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(
        _resolve("ImportNodesFromText"))


def _mark_modified():
    # void(UBlueprint*)
    return ctypes.CFUNCTYPE(None, ctypes.c_void_p)(
        _resolve("MarkBlueprintAsStructurallyModified"))


def find_object(name, outer=None, klass=None, exact=False):
    """StaticFindObject(klass, outer, name, exact). klass/outer None => match any
    class / parse `name` as a full object path (e.g. '/Game/X.X' or, with an
    outer, a subobject name like 'EventGraph')."""
    return _static_find_object()(klass, outer, name, exact)


# --- high-level operations ----------------------------------------------------

def can_import(graph_ptr, text):
    """Non-destructive oracle: would the schema accept `text` into this graph?"""
    fs = FString.make(text)
    return bool(_can_import()(graph_ptr, ctypes.byref(fs)))


def import_nodes_capture(graph_ptr, text):
    """MUTATING: paste `text` as real nodes. Returns (count, tset_buffer). The
    count is the out-TSet's inner sparse-array Num (byte offset 8 of the TSet);
    the buffer is the *live, UE-built* TSet<UEdGraphNode*> holding the pasted
    nodes -- layout-identical to TSet<UObject*>, so it can be handed straight to
    ExportNodesToText for a readback round-trip."""
    fs = FString.make(text)
    tset = empty_tset()
    _import_nodes()(graph_ptr, ctypes.byref(fs), ctypes.byref(tset))
    num = ctypes.c_int32.from_buffer(tset, 8).value
    return num, tset


def import_nodes(graph_ptr, text):
    """MUTATING paste; returns count of nodes pasted."""
    return import_nodes_capture(graph_ptr, text)[0]


def _export_nodes():
    # void(TSet<UObject*> by-value -> hidden ptr, FString& out)
    return ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p)(
        _resolve("ExportNodesToText"))


def read_fstring(fs):
    """Decode a populated FString struct to a Python str."""
    if not fs.data or fs.num <= 1:
        return ""
    return ctypes.wstring_at(fs.data, fs.num - 1)  # drop the trailing NUL


def export_text_from_tset(tset_buffer):
    """Run ExportNodesToText on a (UE-built) TSet of nodes and return the text.
    The out FString MUST start zeroed (data=null) so the exporter doesn't try to
    free a non-UE buffer; it allocates and fills it, then we decode."""
    out = FString()                  # zero-initialized: data=0, num=0, max=0
    _export_nodes()(ctypes.byref(tset_buffer), ctypes.byref(out))
    return read_fstring(out)


# --- arbitrary-graph reading: hand-built TSet + TArray plumbing ---------------

def make_tset(pointers):
    """Build a TSet<UObject*> from a list of raw pointers, laid out like a real UE
    set (verified against a live one) so ExportNodesToText can iterate it. Only the
    fields the set-iterator reads are populated; the hash is left zero (iteration
    walks the sparse array via allocation bits, never the hash).

    Layout calibrated byte-for-byte against real UE sets (introspect_multi):
    MaxBits = ceil(N/32)*32, bits inline for <=4 words (N<=128) else heap. The
    hash is left zero -- iteration walks the sparse array via allocation bits,
    never the hash. Backing buffers pinned on ._keep so they outlive the call.

    NOTE: a MULTI-element set built this way still faults UE's exporter for
    reasons beyond the documented layout, so for reading use export_pointers_
    individually() (set-of-1, proven safe). make_tset stays correct/minimal for
    the N=1 case and as a reference. Returns the 128-byte tset buffer."""
    n = len(pointers)
    elem = (ctypes.c_byte * (max(n, 1) * 16))()
    for i, p in enumerate(pointers):
        ctypes.c_uint64.from_buffer(elem, i * 16 + 0).value = p or 0
        ctypes.c_int32.from_buffer(elem, i * 16 + 8).value = -1   # HashNextId
        ctypes.c_int32.from_buffer(elem, i * 16 + 12).value = i   # HashIndex
    words = max(1, (n + 31) // 32)
    bits = (ctypes.c_uint32 * words)()
    for i in range(n):
        bits[i // 32] |= (1 << (i % 32))

    t = (ctypes.c_byte * 128)()
    ctypes.c_uint64.from_buffer(t, 0).value = ctypes.addressof(elem)   # Data.ptr
    ctypes.c_int32.from_buffer(t, 8).value = n                         # Data.Num
    ctypes.c_int32.from_buffer(t, 12).value = n                        # Data.Max
    if words <= 4:                                                     # inline bits
        for w in range(words):
            ctypes.c_uint32.from_buffer(t, 16 + w * 4).value = bits[w]
    else:                                                             # heap bits
        ctypes.c_uint64.from_buffer(t, 32).value = ctypes.addressof(bits)
    ctypes.c_int32.from_buffer(t, 40).value = n                        # NumBits
    ctypes.c_int32.from_buffer(t, 44).value = words * 32               # MaxBits
    ctypes.c_int32.from_buffer(t, 48).value = -1                       # FirstFreeIndex
    ctypes.c_int32.from_buffer(t, 52).value = 0                        # NumFreeIndices
    # Hash: a VALID hash is required -- the exporter masks the bucket index with
    # (HashSize-1); HashSize=0 -> 0xFFFFFFFF mask -> wild OOB read -> crash.
    # For n==1 it's trivial and byte-matches a real UE set-of-1: HashSize=1
    # (mask 0 -> bucket 0), inline head(+56)=0 -> element 0 (HashIndex=0,
    # HashNextId=-1 already set above). n>1 would need UE's pointer-hash + a heap
    # bucket table; export_pointers_individually only ever builds n==1 sets.
    if n == 1:
        ctypes.c_int32.from_buffer(t, 56).value = 0                    # bucket head -> elem 0
        ctypes.c_int32.from_buffer(t, 72).value = 1                    # HashSize
    t._keep = (elem, bits)
    return t


def export_pointers(pointers):
    """ExportNodesToText over an arbitrary list of node pointers via a single
    multi-element TSet. WARNING: faults UE's exporter for many graphs -- use
    export_pointers_individually() for safe reading. Kept for experiments."""
    if not pointers:
        return ""
    return export_text_from_tset(make_tset(pointers))


def _fmemory_malloc():
    return ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32)(_resolve("Malloc"))


def _make_set1_uemem(node_ptr, malloc):
    """Build a TSet<UObject*> of exactly one node whose element buffer is
    allocated by UE's FMemory. ExportNodesToText takes the set BY VALUE and runs
    ~TSet on return, which FMemory::Free's the element buffer -- so it MUST be
    UE-allocated or the allocator corrupts (this was the real crash cause). The
    inline bit-array + inline hash (HashSize=1) have no heap, so ~TSet only frees
    the element buffer. Returns the 128-byte tset (the element buffer is owned by
    UE and freed by the export call; do not free it here)."""
    elem = malloc(16, 16)                                  # UE-owned; freed by ~TSet
    ctypes.memmove(elem, int(node_ptr).to_bytes(8, "little"), 8)  # element[0].Value
    ctypes.c_int32.from_address(elem + 8).value = -1      # HashNextId
    ctypes.c_int32.from_address(elem + 12).value = 0      # HashIndex
    t = (ctypes.c_byte * 128)()
    ctypes.c_uint64.from_buffer(t, 0).value = elem        # Data.ptr
    ctypes.c_int32.from_buffer(t, 8).value = 1            # Data.Num
    ctypes.c_int32.from_buffer(t, 12).value = 1           # Data.Max
    ctypes.c_uint32.from_buffer(t, 16).value = 1          # AllocationFlags inline: bit 0
    ctypes.c_int32.from_buffer(t, 40).value = 1           # NumBits
    ctypes.c_int32.from_buffer(t, 44).value = 32          # MaxBits
    ctypes.c_int32.from_buffer(t, 48).value = -1          # FirstFreeIndex
    ctypes.c_int32.from_buffer(t, 52).value = 0           # NumFreeIndices
    ctypes.c_int32.from_buffer(t, 56).value = 0           # hash bucket head -> elem 0
    ctypes.c_int32.from_buffer(t, 72).value = 1           # HashSize (mask 0 -> bucket 0)
    return t


def export_pointers_individually(pointers):
    """Crash-safe, lossless graph read: export each node as its own set-of-1 and
    concatenate. Connections survive because LinkedTo refs are embedded per-node
    by name+pin-GUID, so concatenation reproduces the multi-node export text.
    Each set's element buffer is UE-allocated (FMemory) so the by-value ~TSet on
    return frees it cleanly instead of corrupting the heap."""
    fn = _export_nodes()
    malloc = _fmemory_malloc()
    parts = []
    for p in pointers:
        if not p:
            continue
        t = _make_set1_uemem(p, malloc)
        out = FString()
        fn(ctypes.byref(t), ctypes.byref(out))
        parts.append(read_fstring(out))
    return "".join(parts)


def _read_tarray_ptrs(buf16):
    """Decode a TArray<T*> {ptr, int32 num, int32 max} into a Python list of ptrs."""
    data = ctypes.c_uint64.from_buffer(buf16, 0).value
    num = ctypes.c_int32.from_buffer(buf16, 8).value
    if not data or num <= 0:
        return []
    arr = (ctypes.c_uint64 * num).from_address(data)
    return [arr[i] for i in range(num)]


def _get_all_graphs():
    return ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p)(_resolve("GetAllGraphs"))


def _get_objects_with_outer():
    return ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_bool,
                            ctypes.c_uint32, ctypes.c_int32)(_resolve("GetObjectsWithOuter"))


def get_all_graphs(bp_ptr):
    ta = (ctypes.c_byte * 16)()
    _get_all_graphs()(bp_ptr, ctypes.byref(ta))
    return _read_tarray_ptrs(ta)


def objects_with_outer(outer_ptr, include_nested=False):
    ta = (ctypes.c_byte * 16)()
    _get_objects_with_outer()(outer_ptr, ctypes.byref(ta), include_nested, 0, 0)
    return _read_tarray_ptrs(ta)


def read_blueprint_graphs(path):
    """Top-level: '/Game/X.X' -> list of {graph_ptr, node_count, text} for every
    graph in the blueprint (event graphs + function graphs), via the engine's own
    GetAllGraphs / GetObjectsWithOuter / ExportNodesToText."""
    bp = find_object(path)
    if not bp:
        raise ValueError("blueprint not found: %s" % path)
    out = []
    for g in get_all_graphs(bp):
        nodes = objects_with_outer(g, include_nested=False)
        out.append({"graph_ptr": g, "node_count": len(nodes),
                    "text": export_pointers_individually(nodes)})
    return out


def mark_structurally_modified(bp_ptr):
    """Tell the blueprint system the graph changed so the next compile picks it
    up (and the editor UI refreshes)."""
    _mark_modified()(bp_ptr)


# --- Stage 1: read-only proof of the whole stack -----------------------------

def selftest_readonly():
    import unreal

    print("=== Stage 1: read-only ctypes proof ===")

    # addresses first -- pure, can't crash anything
    for k in ("StaticFindObject", "CanImportNodesFromText",
              "ImportNodesFromText", "MarkBlueprintAsStructurallyModified"):
        print("  resolve %-36s 0x%016X" % (k, _resolve(k)))

    # a controlled scratch blueprint we own (create-or-reuse)
    PKG, NAME = "/Game/_InjectScratch", "BP_InjectScratch"
    path = PKG + "/" + NAME
    eal = unreal.EditorAssetLibrary
    if not eal.does_asset_exist(path):
        factory = unreal.BlueprintFactory()
        factory.set_editor_property("parent_class", unreal.Actor)
        at = unreal.AssetToolsHelpers.get_asset_tools()
        bp = at.create_asset(NAME, PKG, unreal.Blueprint, factory)
        eal.save_asset(path)
        print("  created scratch BP:", path)
    else:
        bp = eal.load_asset(path)
        print("  reused scratch BP: ", path)

    full = bp.get_path_name()                       # '/Game/_InjectScratch/BP_InjectScratch.BP_InjectScratch'
    print("  bp path_name:", full)

    bp_ptr = find_object(full)
    print("  StaticFindObject(bp)    -> 0x%016X" % (bp_ptr or 0))
    if not bp_ptr:
        print("  [!] could not find the UBlueprint pointer; aborting")
        return

    # the default ubergraph of a fresh BP is named 'EventGraph'; outer = the BP
    graph_ptr = find_object("EventGraph", outer=bp_ptr)
    print("  StaticFindObject(graph) -> 0x%016X" % (graph_ptr or 0))
    if not graph_ptr:
        print("  [!] 'EventGraph' not found under BP outer; name may differ")
        return

    can = _can_import()
    # empty + garbage text: both must return a clean bool WITHOUT crashing.
    # That alone proves proc-resolution + FString layout + the Win64 ABI.
    for label, text in (("empty", ""), ("garbage", "not a node blob")):
        fs = FString.make(text)
        r = can(graph_ptr, ctypes.byref(fs))
        print("  CanImportNodesFromText(%-7s) -> %s" % (label, bool(r)))

    print("=== Stage 1 OK: ctypes stack is live and non-crashing ===")


def scratch_blueprint(pkg="/Game/_InjectScratch", name="BP_InjectScratch"):
    """Create-or-reuse a throwaway Actor blueprint; return (bp_pyobj, full_path)."""
    import unreal
    path = pkg + "/" + name
    eal = unreal.EditorAssetLibrary
    if not eal.does_asset_exist(path):
        factory = unreal.BlueprintFactory()
        factory.set_editor_property("parent_class", unreal.Actor)
        at = unreal.AssetToolsHelpers.get_asset_tools()
        bp = at.create_asset(name, pkg, unreal.Blueprint, factory)
        eal.save_asset(path)
    else:
        bp = eal.load_asset(path)
    return bp, bp.get_path_name()
