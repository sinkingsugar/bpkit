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
    # void UEdGraphSchema_K2::CreateFunctionGraphTerminators(UEdGraph&, UClass*) const
    # -- the editor's own override-graph builder: creates entry+result with the PARENT
    #    signature for a graph named exactly like the parent function (see
    #    create_function_override; a pasted FunctionEntry can NEVER become an override).
    "CreateFunctionGraphTerminators": ("UnrealEditor-BlueprintGraph.dll",
                                       b"?CreateFunctionGraphTerminators@UEdGraphSchema_K2@@UEBAXAEAVUEdGraph@@PEAVUClass@@@Z"),
    # bool UEdGraphSchema_K2::TryCreateConnection(UEdGraphPin*, UEdGraphPin*) const
    # -- wire two LIVE pins (works across paste sets; ImportNodesFromText can't)
    "TryCreateConnection": ("UnrealEditor-BlueprintGraph.dll",
                            b"?TryCreateConnection@UEdGraphSchema_K2@@UEBA_NPEAVUEdGraphPin@@0@Z"),
    # UEdGraphPin* UEdGraphNode::FindPin(const TCHAR*, EEdGraphPinDirection) const
    "FindPin": ("UnrealEditor-Engine.dll",
                b"?FindPin@UEdGraphNode@@QEBAPEAVUEdGraphPin@@PEB_WW4EEdGraphPinDirection@@@Z"),
    # === UMG: the designer's own copy/paste, the widget analogue of Im/ExportNodesToText ===
    # void FWidgetBlueprintEditorUtils::ExportWidgetsToText(TArray<UWidget*> /*byval*/, FString& out)
    #   -- TArray is BY VALUE -> ~TArray frees its buffer on return, so the element buffer MUST be
    #      FMemory::Malloc'd (same gotcha as ExportNodesToText's by-value TSet).
    "ExportWidgetsToText": ("UnrealEditor-UMGEditor.dll",
                            b"?ExportWidgetsToText@FWidgetBlueprintEditorUtils@@SAXV?$TArray@PEAVUWidget@@V?$TSizedDefaultAllocator@$0CA@@@@@AEAVFString@@@Z"),
    # void FWidgetBlueprintEditorUtils::ImportWidgetsFromText(UWidgetBlueprint*, const FString&,
    #        TSet<UWidget*>& outImported, TMap<FName, UWidgetSlotPair*>& outSlots)
    "ImportWidgetsFromText": ("UnrealEditor-UMGEditor.dll",
                              b"?ImportWidgetsFromText@FWidgetBlueprintEditorUtils@@SAXPEAVUWidgetBlueprint@@AEBVFString@@AEAV?$TSet@PEAVUWidget@@U?$DefaultKeyFuncs@PEAVUWidget@@$0A@@@VFDefaultSetAllocator@@@@AEAV?$TMap@VFName@@PEAVUWidgetSlotPair@@VFDefaultSetAllocator@@U?$TDefaultMapHashableKeyFuncs@VFName@@PEAVUWidgetSlotPair@@$0A@@@@@@Z"),
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


# ----------------------------------------------------------------------------
# UMG: read/write widget trees (FWidgetBlueprintEditorUtils Im/ExportWidgetsFromText)
# ----------------------------------------------------------------------------
def widget_tree(wbp_ptr):
    """The UWidgetTree subobject of a UWidgetBlueprint (the WBP's `widget_tree` is
    NOT reflected to Python in this build, but the subobject is findable by name)."""
    return find_object("WidgetTree", outer=wbp_ptr)


def tree_widgets(wbp_ptr):
    """Every UWidget owned by the WBP's widget tree (root + descendants)."""
    wt = widget_tree(wbp_ptr)
    return objects_with_outer(wt) if wt else []


def export_widgets(widget_ptrs):
    """Serialize UWidget*s to designer copy/paste text (the widget analogue of
    export_nodes). ExportWidgetsToText takes its TArray<UWidget*> BY VALUE and runs
    ~TArray on return, so the element buffer is FMemory::Malloc'd -- UE frees what it
    legitimately owns (same crash-safety contract as the by-value TSet export)."""
    ptrs = [int(p) for p in widget_ptrs if p]
    if not ptrs:
        return ""
    n = len(ptrs)
    elem = proc("Malloc", ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32)(8 * n, 8)
    for i, p in enumerate(ptrs):
        ctypes.c_uint64.from_address(elem + 8 * i).value = p
    ta = (ctypes.c_byte * 16)()                       # TArray<UWidget*> { data; num; max }
    ctypes.c_uint64.from_buffer(ta, 0).value = elem
    ctypes.c_int32.from_buffer(ta, 8).value = n
    ctypes.c_int32.from_buffer(ta, 12).value = n
    out = FString()
    # x64 MSVC: a >8-byte by-value struct is passed by hidden pointer -> byref(ta).
    proc("ExportWidgetsToText", None, ctypes.c_void_p, ctypes.c_void_p)(
        ctypes.byref(ta), ctypes.byref(out))
    return out.str()


def import_widgets(wbp_ptr, text):
    """MUTATING: paste widget copy/paste `text` into a WidgetBlueprint, creating real
    UWidgets parented to its widget tree. Returns the imported-widget count (from the
    out-TSet). NOTE: like the designer, this CREATES the widgets but does not itself
    place a root / re-parent -- the caller sets the tree root (set_root_widget) or
    re-parents via the returned slot map. The TMap<FName,UWidgetSlotPair*> out-param is
    accepted into a zeroed buffer (valid empty TMap state) and ignored here."""
    fs = FString.make(text)
    tset = _empty_tset()
    tmap = _empty_tset(256)                           # zeroed TMap out-param
    proc("ImportWidgetsFromText", None, ctypes.c_void_p, ctypes.c_void_p,
         ctypes.c_void_p, ctypes.c_void_p)(
        wbp_ptr, ctypes.byref(fs), ctypes.byref(tset), ctypes.byref(tmap))
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


def _parse_links(text):
    """Parse exported/rendered node text into a set of links. Each link is a
    frozenset of two (nodeName, pinName) endpoints -- so direction and the
    src/dst double-listing collapse to one entry. Links are matched by NAME
    (node + pin), NOT PinId: PinIds are regenerated on paste (notably wildcard
    pins), but node+pin names are stable."""
    import re
    pin_name = {}      # (node, pinId) -> pinName
    pin_links = []     # (node, pinId, [(dstNode, dstPinId), ...])
    for blk in re.split(r'(?=Begin Object Class=)', text):
        m = re.search(r'Begin Object Class=\S+ Name="([^"]+)"', blk)
        if not m:
            continue
        node = m.group(1)
        for pin in re.findall(r'CustomProperties Pin \((.*)\)', blk):
            pid = (re.search(r'PinId=([0-9A-Fa-f]+)', pin) or [None, None])[1]
            pn = (re.search(r'PinName="([^"]+)"', pin) or [None, None])[1]
            if not pid or not pn:
                continue
            pin_name[(node, pid)] = pn
            lm = re.search(r'LinkedTo=\(([^)]*)\)', pin)
            if lm and lm.group(1).strip():
                entries = [tuple(e.split()) for e in lm.group(1).split(',')
                           if len(e.split()) == 2]
                if entries:
                    pin_links.append((node, pid, entries))
    links = set()
    for node, pid, entries in pin_links:
        # match pin names CASE-INSENSITIVELY: the engine canonicalizes pin names to the
        # UFunction's real param casing on reconstruction (authored "Title"/"Message" ->
        # "title"/"message"), and paste's own FindPin is case-insensitive too.
        src = (node, pin_name.get((node, pid), "?").lower())
        for (dnode, dpid) in entries:
            links.add(frozenset((src, (dnode, pin_name.get((dnode, dpid), "?").lower()))))
    return links


def missing_links(authored_text, final_text):
    """Links present in `authored_text` (what we rendered/pasted) but ABSENT from
    `final_text` (what survived paste+compile). Catches wires the engine silently
    drops on import -- notably K2Node_GetArrayItem's wildcard Output -> a typed
    consumer (no orphan, no compile error; the consumer just keeps its default,
    which caused the v39 `dc MFHorses N` always-set-to-0 bug). Returns a sorted
    list of 'A.pin <-> B.pin' strings. Re-make any drop with connect_pins, then
    re-check (expect empty). See the getarrayitem-output-paste-drop note."""
    out = []
    for link in _parse_links(authored_text) - _parse_links(final_text):
        ends = sorted(link)
        a, b = ends[0], ends[-1]
        out.append("%s.%s <-> %s.%s" % (a[0], a[1], b[0], b[1]))
    return sorted(out)


def _relink_dropped(graph_ptr, authored_text):
    """For every authored in-text wire that did NOT survive paste, reconnect it live
    via connect_pins (the K2Node_GetArrayItem.Output wildcard class -- no orphan, no
    compile error, the consumer just keeps its default). Node+pin names are preserved
    across paste, so we map name -> live node_ptr and re-link by name. Returns
    (relinked, still_missing) as lists of 'A.pin <-> B.pin' strings. Cross-set links
    (to nodes NOT in `authored_text`, e.g. a function-entry) are out of scope -- they
    were never in the paste, so missing_links won't report them; the caller handles
    those with its own connect_pins."""
    import re
    miss = missing_links(authored_text, export_nodes(graph_nodes(graph_ptr)))
    if not miss:
        return [], []
    name2ptr = {}
    for p in graph_nodes(graph_ptr):
        m = re.search(r'Name="([^"]+)"', export_nodes([p]).splitlines()[0])
        if m:
            name2ptr[m.group(1)] = p
    relinked, still = [], []
    for link in miss:
        a, b = link.split(" <-> ")
        an, ap = a.rsplit(".", 1)
        bn, bpn = b.rsplit(".", 1)
        pa = find_pin(name2ptr[an], ap, 2) if an in name2ptr else 0
        pb = find_pin(name2ptr[bn], bpn, 2) if bn in name2ptr else 0
        (relinked if (pa and pb and connect_pins(pa, pb)) else still).append(link)
    return relinked, still


def inject(bp_path, text, graph_name="EventGraph", precheck=True, compile=True,
           save=True, relink=True):
    """High-level write: paste `text` into <bp_path>'s <graph_name>, then (by
    default) compile and save. `bp_path` is a full object path '/Game/X.X'.
    With relink=True (default) inject SELF-HEALS: any authored wire the engine
    silently drops on paste (the GetArrayItem.Output wildcard class) is reconnected
    live via connect_pins. Returns a result dict incl. `relinked` (wires re-made)
    and `dropped_links` (wires STILL missing after relink -- should be empty; a
    non-empty list is a real bug). Compile/save use the reflected `unreal` API."""
    import unreal
    bp_ptr, graph_ptr = find_graph(bp_path, graph_name)
    if not bp_ptr:
        raise ValueError("blueprint not found: %s" % bp_path)
    if not graph_ptr:
        raise ValueError("graph %r not found in %s" % (graph_name, bp_path))
    if precheck and not can_import(graph_ptr, text):
        return {"ok": False, "reason": "schema rejected the text", "pasted": 0}
    pasted = import_nodes(graph_ptr, text)
    result = {"ok": True, "pasted": pasted}
    try:
        if relink:
            result["relinked"], result["dropped_links"] = _relink_dropped(graph_ptr, text)
        else:
            result["dropped_links"] = missing_links(text, export_nodes(graph_nodes(graph_ptr)))
    except Exception as e:
        result["dropped_links"] = ["<link-check failed: %r>" % e]
    mark_structurally_modified(bp_ptr)
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
    # load_asset is the source of truth (returns the asset if present, None if absent). does_asset_exist
    # proved UNRELIABLE -- it can return False for an asset that loads fine (asset-registry staleness
    # after heavy asset churn, even post force-rescan). Gating create on it wrongly tried to create OVER
    # an existing asset, which then failed. So: load first, create only if truly absent.
    bp = eal.load_asset(path)
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
# function OVERRIDE authoring + live pin wiring (proven on RconCommand, 2026-06-11)
# ----------------------------------------------------------------------------
def k2_schema():
    """The UEdGraphSchema_K2 CDO (the `this` for schema member calls)."""
    s = find_object("/Script/BlueprintGraph.Default__EdGraphSchema_K2")
    if not s:
        raise RuntimeError("EdGraphSchema_K2 CDO not found (editor running?)")
    return s


def find_pin(node_ptr, pin_name, direction=2):
    """UEdGraphNode::FindPin (TCHAR* overload). direction: 0=input, 1=output,
    2=EGPD_MAX (any). FName compare, so case-insensitive. Returns UEdGraphPin*
    (0 if absent)."""
    fn = proc("FindPin", ctypes.c_void_p, ctypes.c_void_p, ctypes.c_wchar_p,
              ctypes.c_int32)
    return fn(node_ptr, pin_name, direction)


def connect_pins(src_pin_ptr, dst_pin_ptr):
    """UEdGraphSchema_K2::TryCreateConnection -- schema-validated wire between two
    LIVE pins. THE way to wire across paste sets / to pre-existing nodes
    (ImportNodesFromText only cross-links within one pasted set)."""
    fn = proc("TryCreateConnection", ctypes.c_bool, ctypes.c_void_p,
              ctypes.c_void_p, ctypes.c_void_p)
    return bool(fn(k2_schema(), src_pin_ptr, dst_pin_ptr))


def create_function_override(bp_obj, func_name, parent_class_path):
    """Create (or rebuild) a FUNCTION OVERRIDE graph -- entry+result carrying the
    parent function's exact signature, exec-prewired -- via the editor's own path
    (UEdGraphSchema_K2::CreateFunctionGraphTerminators). Returns (bp_ptr, graph_ptr);
    compile afterwards.

    Needed because pasting a K2Node_FunctionEntry can NEVER produce an override:
    PostPasteNode unconditionally rewrites its FunctionReference to a self-function
    named after the containing graph (MemberParent wiped), and matching
    UserDefinedPins still compile as 'declared in a parent with a different
    signature'. BlueprintEditorLibrary's add_function_graph/rename_graph
    auto-uniquify a parent-colliding name, so the graph is created with a
    throwaway name, emptied, UObject-renamed (no K2 validation), then the native
    terminator builder reads the signature off the parent class. (Worked out on
    RconCommandObject.RconCommand, 2026-06-11.)"""
    import unreal
    full = bp_obj.get_path_name()
    bp_ptr, g_ptr = find_graph(full, func_name)
    if not g_ptr:
        g_ed = unreal.BlueprintEditorLibrary.add_function_graph(bp_obj, "TMP_" + func_name)
        bp_ptr, g_ptr = find_graph(full, g_ed.get_name())
        if not g_ptr:
            raise RuntimeError("could not create function graph on %s" % full)
        clear_graph(bp_ptr, g_ptr)
        if not g_ed.rename(func_name):
            raise RuntimeError("could not rename graph to %s" % func_name)
    else:
        clear_graph(bp_ptr, g_ptr)          # rebuild flow: re-terminate in place
    cls_ptr = find_object(parent_class_path)
    if not cls_ptr:
        raise ValueError("parent class not found: %s" % parent_class_path)
    fn = proc("CreateFunctionGraphTerminators", None, ctypes.c_void_p,
              ctypes.c_void_p, ctypes.c_void_p)
    fn(k2_schema(), g_ptr, cls_ptr)
    return bp_ptr, g_ptr


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
