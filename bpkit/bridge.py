"""bpkit.bridge - read & write Unreal Engine 5.6 Blueprint node graphs from Python.

RUN THIS INSIDE THE EDITOR (ship it over remote_execution with ue_run.py). It is
NOT a standalone module: it resolves the editor's exported C++ functions by
address and calls them via ctypes, so it must execute in the editor process where
those DLLs are mapped and the UObject pointers are real.

Why ctypes: the content-only Conan Exiles Enhanced Dev Kit doesn't reflect
graph editing to the `unreal` Python API (you can't spawn/wire K2 nodes, or even
read a graph's nodes). But the C++ copy/paste entrypoints ARE exported from the
loaded editor DLLs, so we call them directly:

    WRITE: void FEdGraphUtilities::ImportNodesFromText(UEdGraph*, const FString&, TSet<UEdGraphNode*>&)
    READ:  void FEdGraphUtilities::ExportNodesToText(TSet<UObject*> /*byval*/, FString&)

ImportNodesFromText is literally what Ctrl+V runs. The engine's own
compile_blueprint is the validator.

Public API:
    read_blueprint(path)                       -> [{index, graph_ptr, node_count, text}, ...]
    inject(bp_path, text, graph_name=...)      -> {ok, pasted, compiled?, saved?}
    can_import(graph_ptr, text) -> bool        # non-mutating schema pre-check
    import_nodes(graph_ptr, text) -> int       # mutating paste, returns node count
    export_nodes(node_ptrs) -> str             # serialize nodes to copy/paste text
    find_object / find_graph / get_all_graphs / objects_with_outer
    scratch_blueprint(...)                     # throwaway Actor BP for testing

CRITICAL GOTCHA: ExportNodesToText takes its TSet BY VALUE and runs ~TSet on
return, which FMemory::Free's the set's buffers. So a hand-built set's element
buffer MUST be allocated with the engine's FMemory::Malloc, never ctypes -- else
UE frees a pointer it never malloc'd and corrupts the heap (delayed crash). We
read graphs one node at a time (a set-of-1, FMemory-backed); connections survive
because LinkedTo refs are embedded per-node by name+pin-GUID, so concatenating
single-node exports reproduces the multi-node text losslessly.
"""
import ctypes

# --- exported symbols: exact MSVC-decorated names (find them with `python -m bpkit.pe`) ---
SYM = {
    # UObject* StaticFindObject(UClass*, UObject* Outer, const TCHAR* Name, bool ExactClass)
    "StaticFindObject": ("UnrealEditor-CoreUObject.dll",
                         b"?StaticFindObject@@YAPEAVUObject@@PEAVUClass@@PEAV1@PEB_W_N@Z"),
    # void GetObjectsWithOuter(const UObjectBase*, TArray<UObject*>&, bool nested, EObjectFlags, EInternalObjectFlags)
    "GetObjectsWithOuter": ("UnrealEditor-CoreUObject.dll",
                            b"?GetObjectsWithOuter@@YAXPEBVUObjectBase@@AEAV?$TArray@PEAVUObject@@V?$TSizedDefaultAllocator@$0CA@@@@@_NW4EObjectFlags@@W4EInternalObjectFlags@@@Z"),
    # void UBlueprint::GetAllGraphs(TArray<UEdGraph*>&) const
    "GetAllGraphs": ("UnrealEditor-Engine.dll",
                     b"?GetAllGraphs@UBlueprint@@QEBAXAEAV?$TArray@PEAVUEdGraph@@V?$TSizedDefaultAllocator@$0CA@@@@@@Z"),
    # bool FEdGraphUtilities::CanImportNodesFromText(const UEdGraph*, const FString&)
    "CanImportNodesFromText": ("UnrealEditor-UnrealEd.dll",
                               b"?CanImportNodesFromText@FEdGraphUtilities@@SA_NPEBVUEdGraph@@AEBVFString@@@Z"),
    # void FEdGraphUtilities::ImportNodesFromText(UEdGraph*, const FString&, TSet<UEdGraphNode*>&)
    "ImportNodesFromText": ("UnrealEditor-UnrealEd.dll",
                            b"?ImportNodesFromText@FEdGraphUtilities@@SAXPEAVUEdGraph@@AEBVFString@@AEAV?$TSet@PEAVUEdGraphNode@@U?$DefaultKeyFuncs@PEAVUEdGraphNode@@$0A@@@VFDefaultSetAllocator@@@@@Z"),
    # void FEdGraphUtilities::ExportNodesToText(TSet<UObject*> byval, FString& out)
    "ExportNodesToText": ("UnrealEditor-UnrealEd.dll",
                          b"?ExportNodesToText@FEdGraphUtilities@@SAXV?$TSet@PEAVUObject@@U?$DefaultKeyFuncs@PEAVUObject@@$0A@@@VFDefaultSetAllocator@@@@AEAVFString@@@Z"),
    # void FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(UBlueprint*)
    "MarkBlueprintAsStructurallyModified": ("UnrealEditor-UnrealEd.dll",
                                            b"?MarkBlueprintAsStructurallyModified@FBlueprintEditorUtils@@SAXPEAVUBlueprint@@@Z"),
    # void* FMemory::Malloc(SIZE_T, uint32 alignment)
    "Malloc": ("UnrealEditor-Core.dll", b"?Malloc@FMemory@@SAPEAX_KI@Z"),
    # void FBlueprintEditorUtils::RemoveNode(UBlueprint*, UEdGraphNode*, bool bDontRecompile)
    "RemoveNode": ("UnrealEditor-UnrealEd.dll",
                   b"?RemoveNode@FBlueprintEditorUtils@@SAXPEAVUBlueprint@@PEAVUEdGraphNode@@_N@Z"),
    # bool FStructureEditorUtils::AddVariable(UUserDefinedStruct*, const FEdGraphPinType&)
    "AddStructVariable": ("UnrealEditor-UnrealEd.dll",
                          b"?AddVariable@FStructureEditorUtils@@SA_NPEAVUUserDefinedStruct@@AEBUFEdGraphPinType@@@Z"),
}

# ----------------------------------------------------------------------------
# low level: resolve an export to a callable, cached per (symbol, signature)
# ----------------------------------------------------------------------------
_k32 = ctypes.windll.kernel32
_k32.GetModuleHandleW.restype = ctypes.c_void_p
_k32.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
_k32.GetProcAddress.restype = ctypes.c_void_p
_k32.GetProcAddress.argtypes = [ctypes.c_void_p, ctypes.c_char_p]

_addr_cache = {}
_proc_cache = {}


def resolve(key):
    """Return the raw address of an exported symbol from its already-loaded DLL."""
    if key in _addr_cache:
        return _addr_cache[key]
    dll, name = SYM[key]
    h = _k32.GetModuleHandleW(dll)
    if not h:
        raise OSError("module not mapped: %s (is the editor running?)" % dll)
    addr = _k32.GetProcAddress(h, name)
    if not addr:
        raise OSError("export not found in %s: %s" % (dll, name.decode()))
    _addr_cache[key] = addr
    return addr


def proc(key, restype, *argtypes):
    """Return a cached ctypes callable for an exported symbol."""
    if key not in _proc_cache:
        _proc_cache[key] = ctypes.CFUNCTYPE(restype, *argtypes)(resolve(key))
    return _proc_cache[key]


# ----------------------------------------------------------------------------
# argument marshalling: FString / TArray / TSet
# ----------------------------------------------------------------------------
class FString(ctypes.Structure):
    """UE FString == TArray<TCHAR>: { TCHAR* data; int32 num; int32 max }, where
    num/max INCLUDE the null terminator. Build with .make(); an empty FString()
    is the valid zeroed state UE will allocate into."""
    _fields_ = [("data", ctypes.c_void_p), ("num", ctypes.c_int32), ("max", ctypes.c_int32)]

    @classmethod
    def make(cls, s):
        buf = ctypes.create_unicode_buffer(s)            # s + trailing NUL (UTF-16)
        fs = cls(ctypes.cast(buf, ctypes.c_void_p), len(s) + 1, len(s) + 1)
        fs._buf = buf                                    # pin so it outlives the call
        return fs

    def str(self):
        if not self.data or self.num <= 1:
            return ""
        return ctypes.wstring_at(self.data, self.num - 1)


def _read_tarray_ptrs(buf16):
    """Decode a TArray<T*> { ptr; int32 num; int32 max } into a list of pointers."""
    data = ctypes.c_uint64.from_buffer(buf16, 0).value
    num = ctypes.c_int32.from_buffer(buf16, 8).value
    if not data or num <= 0:
        return []
    arr = (ctypes.c_uint64 * num).from_address(data)
    return [arr[i] for i in range(num)]


def _empty_tset(nbytes=256):
    """Zeroed buffer usable as an empty TSet<...>& out-param (a value-zeroed UE
    TSet is the valid empty state)."""
    return (ctypes.c_byte * nbytes)()


def _make_set1_fmemory(node_ptr):
    """Build a TSet<UObject*> of exactly one node, with its element buffer
    allocated by UE's FMemory so the by-value ~TSet in ExportNodesToText can
    legitimately free it. Inline bit-array + inline hash (HashSize=1, mask 0 ->
    bucket 0) mean the element buffer is the only heap allocation. Returns the
    128-byte tset (UE owns/frees the element buffer via the export call)."""
    elem = proc("Malloc", ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32)(16, 16)
    ctypes.memmove(elem, int(node_ptr).to_bytes(8, "little"), 8)   # element[0].Value
    ctypes.c_int32.from_address(elem + 8).value = -1               # HashNextId
    ctypes.c_int32.from_address(elem + 12).value = 0               # HashIndex
    t = (ctypes.c_byte * 128)()
    ctypes.c_uint64.from_buffer(t, 0).value = elem                 # Data.ptr
    ctypes.c_int32.from_buffer(t, 8).value = 1                     # Data.Num
    ctypes.c_int32.from_buffer(t, 12).value = 1                    # Data.Max
    ctypes.c_uint32.from_buffer(t, 16).value = 1                   # AllocationFlags inline: bit 0
    ctypes.c_int32.from_buffer(t, 40).value = 1                    # NumBits
    ctypes.c_int32.from_buffer(t, 44).value = 32                   # MaxBits
    ctypes.c_int32.from_buffer(t, 48).value = -1                   # FirstFreeIndex
    ctypes.c_int32.from_buffer(t, 52).value = 0                    # NumFreeIndices
    ctypes.c_int32.from_buffer(t, 56).value = 0                    # hash bucket head -> elem 0
    ctypes.c_int32.from_buffer(t, 72).value = 1                    # HashSize
    return t


# ----------------------------------------------------------------------------
# object lookup
# ----------------------------------------------------------------------------
def find_object(name, outer=None, klass=None, exact=False):
    """StaticFindObject(klass, outer, name, exact). With klass=None it matches any
    class; with outer=None it parses `name` as a full path ('/Game/X.X'); with an
    outer it finds a subobject by name (e.g. 'EventGraph')."""
    fn = proc("StaticFindObject", ctypes.c_void_p, ctypes.c_void_p,
              ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_bool)
    return fn(klass, outer, name, exact)


def obj_addr(unreal_obj):
    """Native address of a live `unreal` wrapper (UObject or struct value), parsed
    from its repr -- UE Python reprs include the pointer: <... (0xADDR) ...>. Used to
    pass an engine-built struct (e.g. an FEdGraphPinType) by-ref into a bridge call."""
    import re
    m = re.search(r"0x([0-9A-Fa-f]+)", repr(unreal_obj))
    return int(m.group(1), 16) if m else None


def add_struct_variable(struct_ptr, pintype_ptr):
    """FStructureEditorUtils::AddVariable(UUserDefinedStruct*, const FEdGraphPinType&)
    -> bool. struct_ptr: the UUserDefinedStruct* (find_object on its OBJECT path
    '/Game/X/ST.ST', NOT the package path). pintype_ptr: address of an engine-built
    FEdGraphPinType (BlueprintEditorLibrary.get_basic_type_by_name / get_struct_type,
    then obj_addr()). Appends a member of that type (auto-named). Returns True on add.

    GOTCHA: keep the pin wrapper ALIVE across this call. The FEdGraphPinType is owned
    by the Python wrapper; if it's GC'd before this reads the address, the address is
    freed memory and AddVariable silently falls back to an int member. So hold a
    reference (e.g. `pin = get_basic_type_by_name(...); add_struct_variable(s, obj_addr(pin))`),
    don't inline it. Pin category names: int / int64 / bool, and "real" for float."""
    fn = proc("AddStructVariable", ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    return bool(fn(ctypes.c_void_p(struct_ptr), ctypes.c_void_p(pintype_ptr)))


def get_all_graphs(bp_ptr):
    """All UEdGraph* of a blueprint (event graphs + function graphs)."""
    ta = (ctypes.c_byte * 16)()
    proc("GetAllGraphs", None, ctypes.c_void_p, ctypes.c_void_p)(bp_ptr, ctypes.byref(ta))
    return _read_tarray_ptrs(ta)


def objects_with_outer(outer_ptr, include_nested=False):
    """Direct UObject children of `outer` (for a UEdGraph: its UEdGraphNodes).
    WARNING: finds children by ownership, so after RemoveNode it still surfaces
    undo-buffer orphans. Use graph_nodes() for the authoritative live node list."""
    ta = (ctypes.c_byte * 16)()
    proc("GetObjectsWithOuter", None, ctypes.c_void_p, ctypes.c_void_p,
         ctypes.c_bool, ctypes.c_uint32, ctypes.c_int32)(
        outer_ptr, ctypes.byref(ta), include_nested, 0, 0)
    return _read_tarray_ptrs(ta)


# --- authoritative graph nodes: read UEdGraph::Nodes (TArray) directly ---------
# The 'Nodes' TArray offset within UEdGraph is discovered once by scanning the
# object for the first TArray whose elements are all plausible UObjects (no FName
# / reflection needed). Unlike objects_with_outer this reflects the graph's real
# node list -- RemoveNode drops nodes from it immediately, so no orphan pollution.
_NODES_OFFSET = None
_OBJ_CLASS_OFF = 0x10            # UObjectBase::ClassPrivate offset (stable)


def _try_u64(addr):
    try:
        return ctypes.c_uint64.from_address(addr).value
    except (OSError, ValueError):
        return None


def _try_i32(addr):
    try:
        return ctypes.c_int32.from_address(addr).value
    except (OSError, ValueError):
        return None


def _looks_like_uobject(ptr):
    if not ptr or ptr < 0x10000:
        return False
    vtable = _try_u64(ptr)                       # must have a vtable
    klass = _try_u64(ptr + _OBJ_CLASS_OFF)       # ...and a ClassPrivate
    return bool(vtable and vtable > 0x10000 and klass and klass > 0x10000)


def _find_nodes_offset(graph_ptr):
    """Locate UEdGraph::Nodes: the first TArray<ptr> in the object whose first few
    elements are all valid UObjects. Cached process-wide (same class layout)."""
    global _NODES_OFFSET
    if _NODES_OFFSET is not None:
        return _NODES_OFFSET
    for off in range(0x20, 0x90, 8):
        data = _try_u64(graph_ptr + off)
        num = _try_i32(graph_ptr + off + 8)
        mx = _try_i32(graph_ptr + off + 12)
        if data is None or num is None or mx is None:
            continue
        if not (0 < num <= 50000 and num <= mx <= 200000 and data > 0x10000):
            continue
        elems = (ctypes.c_uint64 * min(num, 4)).from_address(data)
        try:
            if all(_looks_like_uobject(elems[i]) for i in range(min(num, 4))):
                _NODES_OFFSET = off
                return off
        except (OSError, ValueError):
            continue
    return None


def graph_nodes(graph_ptr):
    """Authoritative live node list of a graph (reads UEdGraph::Nodes). Falls back
    to objects_with_outer if the offset can't be discovered (e.g. empty graph seen
    before any populated one)."""
    off = _find_nodes_offset(graph_ptr)
    if off is None:
        return objects_with_outer(graph_ptr)
    data = _try_u64(graph_ptr + off)
    num = _try_i32(graph_ptr + off + 8)
    if not data or not num or num <= 0:
        return []
    arr = (ctypes.c_uint64 * num).from_address(data)
    return [arr[i] for i in range(num)]


def find_graph(bp_path, graph_name="EventGraph", load=True):
    """Resolve (bp_ptr, graph_ptr) for a blueprint path + graph name, loading the
    asset into memory first if needed. Returns (None, None) if not found."""
    bp = find_object(bp_path)
    if not bp and load:
        import unreal
        unreal.EditorAssetLibrary.load_asset(bp_path.split(".")[0])
        bp = find_object(bp_path)
    if not bp:
        return None, None
    return bp, find_object(graph_name, outer=bp)


# ----------------------------------------------------------------------------
# READ
# ----------------------------------------------------------------------------
def export_nodes(node_ptrs):
    """Serialize nodes to copy/paste text. Exports each node as its own
    FMemory-backed set-of-1 and concatenates -- crash-safe, and lossless because
    LinkedTo refs are embedded per node."""
    fn = proc("ExportNodesToText", None, ctypes.c_void_p, ctypes.c_void_p)
    parts = []
    for p in node_ptrs:
        if not p:
            continue
        t = _make_set1_fmemory(p)
        out = FString()
        fn(ctypes.byref(t), ctypes.byref(out))
        parts.append(out.str())
    return "".join(parts)


def read_blueprint(path, load=True):
    """'/Game/X.X' -> [{index, graph_ptr, node_count, text}] for every graph."""
    bp = find_object(path)
    if not bp and load:
        import unreal
        unreal.EditorAssetLibrary.load_asset(path.split(".")[0])
        bp = find_object(path)
    if not bp:
        raise ValueError("blueprint not found: %s" % path)
    out = []
    for i, g in enumerate(get_all_graphs(bp)):
        nodes = graph_nodes(g)
        out.append({"index": i, "graph_ptr": g, "node_count": len(nodes),
                    "text": export_nodes(nodes)})
    return out


# ----------------------------------------------------------------------------
# WRITE
# ----------------------------------------------------------------------------
def can_import(graph_ptr, text):
    """Non-mutating oracle: would the schema accept `text` into this graph?"""
    fs = FString.make(text)
    return bool(proc("CanImportNodesFromText", ctypes.c_bool,
                     ctypes.c_void_p, ctypes.c_void_p)(graph_ptr, ctypes.byref(fs)))


def import_nodes(graph_ptr, text):
    """MUTATING: paste `text` as real nodes into the graph. Returns the number of
    nodes pasted (read from the out-TSet's element count)."""
    fs = FString.make(text)
    tset = _empty_tset()
    proc("ImportNodesFromText", None, ctypes.c_void_p, ctypes.c_void_p,
         ctypes.c_void_p)(graph_ptr, ctypes.byref(fs), ctypes.byref(tset))
    return ctypes.c_int32.from_buffer(tset, 8).value


def mark_structurally_modified(bp_ptr):
    """Tell the blueprint system the graph changed (so compile/UI pick it up)."""
    proc("MarkBlueprintAsStructurallyModified", None, ctypes.c_void_p)(bp_ptr)


def remove_node(bp_ptr, node_ptr, dont_recompile=True):
    """FBlueprintEditorUtils::RemoveNode -- delete one node from its blueprint."""
    proc("RemoveNode", None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_bool)(
        bp_ptr, node_ptr, dont_recompile)


def clear_graph(bp_ptr, graph_ptr, gc=True):
    """Remove every node from a graph (snapshot first, then delete). Returns the
    count removed. Used by the read->modify->write 'replace' edit flow, since
    ImportNodesFromText only cross-links WITHIN the pasted set -- so to rewire
    existing nodes you re-import the whole (mutated) graph as one set.

    RemoveNode detaches a node from the graph's node-array but leaves it parented
    to the graph until GC, so objects_with_outer would still surface the orphans.
    gc=True runs a GC pass to actually destroy them, keeping reads authoritative."""
    nodes = graph_nodes(graph_ptr)
    for n in nodes:
        remove_node(bp_ptr, n, True)
    if gc:
        import unreal
        unreal.SystemLibrary.collect_garbage()
    return len(nodes)


def inject(bp_path, text, graph_name="EventGraph", precheck=True, compile=True, save=True):
    """High-level write: paste `text` into <bp_path>'s <graph_name>, then (by
    default) compile and save. `bp_path` is a full object path '/Game/X.X'.
    Returns a result dict. Compile/save use the reflected `unreal` API."""
    import unreal
    bp_ptr, graph_ptr = find_graph(bp_path, graph_name)
    if not bp_ptr:
        raise ValueError("blueprint not found: %s" % bp_path)
    if not graph_ptr:
        raise ValueError("graph %r not found in %s" % (graph_name, bp_path))
    if precheck and not can_import(graph_ptr, text):
        return {"ok": False, "reason": "schema rejected the text", "pasted": 0}
    pasted = import_nodes(graph_ptr, text)
    mark_structurally_modified(bp_ptr)
    result = {"ok": True, "pasted": pasted}
    asset_path = bp_path.split(".")[0]
    bp_obj = unreal.load_asset(asset_path)
    if compile:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp_obj)
        result["compiled"] = True
    if save:
        result["saved"] = bool(unreal.EditorAssetLibrary.save_asset(asset_path))
    return result


# ----------------------------------------------------------------------------
# test convenience
# ----------------------------------------------------------------------------
def scratch_blueprint(pkg="/Game/_Scratch", name="BP_Scratch", parent=None):
    """Create-or-reuse a throwaway Actor blueprint; return (bp_pyobj, full_path).
    Useful for tests/examples; delete the package when done."""
    import unreal
    path = pkg + "/" + name
    eal = unreal.EditorAssetLibrary
    bp = eal.load_asset(path) if eal.does_asset_exist(path) else None
    if bp is None:
        factory = unreal.BlueprintFactory()
        factory.set_editor_property("parent_class", parent or unreal.Actor)
        bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, pkg, unreal.Blueprint, factory)
        if bp is None:                       # asset-registry staleness -> retry load
            bp = eal.load_asset(path)
        if bp is None:
            raise RuntimeError("could not create or load scratch BP at %s "
                               "(stale redirector? try a fresh name)" % path)
        eal.save_asset(path)
    return bp, bp.get_path_name()


# ----------------------------------------------------------------------------
# diagnostics
# ----------------------------------------------------------------------------
def selftest():
    """Diagnose the native bridge against the CURRENTLY loaded editor build, without
    mutating anything: resolve every exported symbol bpkit needs, then make one real
    read-only call to confirm marshalling + calling convention actually work.

    Returns {ok, resolved:{key:hex}, failed:{key:err}, functional}. A `failed` entry
    means that symbol's decorated name differs on this build (or it isn't an editor
    build that exports it) -- re-derive the name with bpkit.pe and patch SYM rather
    than treating the bridge as broken. `functional` is the StaticFindObject probe
    (True = a real native call round-tripped)."""
    resolved, failed = {}, {}
    for key in SYM:
        try:
            resolved[key] = hex(resolve(key))
        except Exception as e:                       # report, never raise
            failed[key] = str(e)
    functional = None
    if "StaticFindObject" in resolved:
        try:
            functional = bool(find_object("/Script/Engine.Actor"))   # always-loaded UClass
        except Exception as e:
            functional = "error: " + str(e)
    return {"ok": (not failed) and functional is True,
            "resolved": resolved, "failed": failed, "functional": functional}
