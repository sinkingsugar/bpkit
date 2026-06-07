"""In-editor regression tests for the forthvm Blueprint primitives -- the mechanics
the generated VM is built from, proven by spawn+call+assert (not eyeballing). Needs
ST_FCell (run 00_create_fcell.py first) and Play STOPPED.

    & $py ue_run.py mods/forthvm/test_vm.py

Covered (live-verified): the typed cell Make/Break round-trip, and the typed stack
(TArray<ST_FCell>) push + read-back + length. These are the atomic ops the Switch
dispatch + tick-stepper compose. Fresh timestamped package each run -> no
undo-buffer asset accumulation. Grows as the VM gains opcodes.
"""
import sys, re, time
for _m in list(sys.modules):
    if _m == "bpkit" or _m.startswith("bpkit."):
        sys.modules.pop(_m, None)
import unreal
from bpkit import bridge as bp, ir

BEL = unreal.BlueprintEditorLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
EAL = unreal.EditorAssetLibrary
PKG = "/Game/_Scratch/_vmtest/run_%d" % int(time.time())
SOBJ = "/Game/ForthVM/ST_FCell.ST_FCell"
STYPE = '"/Script/CoreUObject.UserDefinedStruct\'%s\'"' % SOBJ
KARR = "/Script/Engine.KismetArrayLibrary"

_results = []
def expect(name, ok, detail=""):
    _results.append((name, bool(ok), detail))


def fresh_bp(name):
    obj, _ = bp.scratch_blueprint(pkg=PKG, name=name)
    return obj, PKG + "/" + name + "." + name


def st(node, pin, d, array=False):
    """type a pin as struct/ST_FCell (array=True for TArray<ST_FCell>)."""
    p = node.pin(pin); p.dir = d
    p.set("PinType.PinCategory", '"struct"')
    p.set("PinType.PinSubCategoryObject", STYPE)
    if array:
        p.set("PinType.ContainerType", "Array")
    return p


def caf(g, fn, pos=(0, 0)):
    return g.node("K2Node_CallArrayFunction",
        ['FunctionReference=(MemberParent="/Script/CoreUObject.Class\'%s\'",MemberName="%s")' % (KARR, fn)],
        base="CAF", pos=pos)


def real_errors(txt):
    return [b for b in re.split(r"(?=Begin Object Class=)", txt)
            if "ErrorMsg" in b and 'ErrorMsg=""' not in b
            and "Override pins have been removed" not in b]   # benign MakeStruct resave note


def validate(full):
    bp_ptr, gp = bp.find_graph(full, "EventGraph")
    txt = bp.export_nodes(bp.graph_nodes(gp))
    orph = re.findall(r'PinName="([^"]+)"[^)]*?bOrphanedPin=True', txt)
    return orph, real_errors(txt)


def run(full, method):
    gc = unreal.load_object(None, full + "_C")
    inst = EAS.spawn_actor_from_class(gc, unreal.Vector(0, 0, 0))
    inst.call_method(method)
    return inst


# resolve the cell's float member pin + check the struct exists ----------------
def resolve_fpin():
    _, probe = fresh_bp("BP_VMTProbe")
    pbp, pgp = bp.find_graph(probe, "EventGraph"); bp.clear_graph(pbp, pgp)
    bp.inject(probe, ('Begin Object Class=/Script/BlueprintGraph.K2Node_MakeStruct Name="MK"\n'
                      '   StructType=%s\nEnd Object\n') % STYPE, graph_name="EventGraph")
    txt = bp.export_nodes(bp.graph_nodes(pgp))
    for line in txt.splitlines():
        if 'PinName="MemberVar' in line and 'PinType.PinCategory="real"' in line:
            return re.search(r'PinName="([^"]+)"', line).group(1)
    return None


# --- tests ------------------------------------------------------------------
def test_cell_roundtrip(FP):
    """Make ST_FCell with F=5.0 -> Break -> Out; assert Out==5.0."""
    obj, full = fresh_bp("BP_T_Cell")
    BEL.add_member_variable(obj, "Out", BEL.get_basic_type_by_name("real"))
    g = ir.Graph("EventGraph")
    ev = g.custom_event("Run")
    mk = g.node("K2Node_MakeStruct", ["StructType=%s" % STYPE], base="MakeStruct", pos=(300, 0))
    g.typed_input(mk, FP, "5.0", "real")
    bk = g.node("K2Node_BreakStruct", ["StructType=%s" % STYPE], base="BreakStruct", pos=(600, 0))
    st(bk, "ST_FCell", "EGPD_Input")
    setn = g.var_set("Out", "real", pos=(900, 0))
    g.wire(ev, "then", setn, "execute", exec=True)
    g.wire(mk, "ST_FCell", bk, "ST_FCell", exec=False)
    g.wire(bk, FP, setn, "Out", exec=False)
    bp_ptr, gp = bp.find_graph(full, "EventGraph"); bp.clear_graph(bp_ptr, gp)
    bp.inject(full, g.render(), graph_name="EventGraph")
    orph, errs = validate(full)
    expect("cell: no orphans", not orph, str(orph[:4]))
    expect("cell: compiles clean", not errs, str([re.search(r'ErrorMsg="([^"]*)"', e).group(1)[:60] for e in errs]))
    inst = run(full, "Run")
    expect("cell: Make(F=5.0)->Break->5.0", abs(inst.get_editor_property("Out") - 5.0) < 1e-6,
           "Out=%s" % inst.get_editor_property("Out"))
    EAS.destroy_actor(inst)


def test_stack_push_read(FP):
    """Push a cell onto TArray<ST_FCell>, read it back + length; assert 5.0 / 1."""
    obj, full = fresh_bp("BP_T_Stack")
    BEL.add_member_variable(obj, "Data", BEL.get_array_type(BEL.get_struct_type(unreal.load_asset(SOBJ))))
    BEL.add_member_variable(obj, "Out", BEL.get_basic_type_by_name("real"))
    BEL.add_member_variable(obj, "Len", BEL.get_basic_type_by_name("int"))
    g = ir.Graph("EventGraph")
    ev = g.custom_event("Run")
    mk = g.node("K2Node_MakeStruct", ["StructType=%s" % STYPE], base="MakeStruct", pos=(300, -200))
    g.typed_input(mk, FP, "5.0", "real")
    dA = g.var_get("Data", "struct", STYPE); st(dA, "Data", "EGPD_Output", array=True)
    add = caf(g, "Array_Add", (300, 0)); st(add, "TargetArray", "EGPD_Input", array=True); st(add, "NewItem", "EGPD_Input")
    g.wire(dA, "Data", add, "TargetArray", exec=False)
    g.wire(mk, "ST_FCell", add, "NewItem", exec=False)
    dG = g.var_get("Data", "struct", STYPE); st(dG, "Data", "EGPD_Output", array=True)
    get = g.node("K2Node_GetArrayItem", [], base="GAI", pos=(780, 120))
    st(get, "Array", "EGPD_Input", array=True); st(get, "Output", "EGPD_Output")
    g.typed_input(get, "Dimension 1", "0", "int")
    g.wire(dG, "Data", get, "Array", exec=False)
    bk = g.node("K2Node_BreakStruct", ["StructType=%s" % STYPE], base="BreakStruct", pos=(1000, 120))
    st(bk, "ST_FCell", "EGPD_Input")
    g.wire(get, "Output", bk, "ST_FCell", exec=False)
    setOut = g.var_set("Out", "real", pos=(1250, 120)); g.wire(bk, FP, setOut, "Out", exec=False)
    dL = g.var_get("Data", "struct", STYPE); st(dL, "Data", "EGPD_Output", array=True)
    ln = caf(g, "Array_Length", (780, 320)); st(ln, "TargetArray", "EGPD_Input", array=True)
    g.wire(dL, "Data", ln, "TargetArray", exec=False)
    setLen = g.var_set("Len", "int", pos=(1250, 320)); g.wire(ln, "ReturnValue", setLen, "Len", exec=False)
    g.wire(ev, "then", add, "execute", exec=True)
    g.wire(add, "then", setOut, "execute", exec=True)
    g.wire(setOut, "then", setLen, "execute", exec=True)
    bp_ptr, gp = bp.find_graph(full, "EventGraph"); bp.clear_graph(bp_ptr, gp)
    bp.inject(full, g.render(), graph_name="EventGraph")
    orph, errs = validate(full)
    expect("stack: no orphans", not orph, str(orph[:4]))
    expect("stack: compiles clean", not errs, str([re.search(r'ErrorMsg="([^"]*)"', e).group(1)[:60] for e in errs]))
    inst = run(full, "Run")
    o, l = inst.get_editor_property("Out"), inst.get_editor_property("Len")
    expect("stack: push->read 5.0", abs(o - 5.0) < 1e-6, "Out=%s" % o)
    expect("stack: length==1 after push", l == 1, "Len=%s" % l)
    EAS.destroy_actor(inst)


# --- runner -----------------------------------------------------------------
print("=== forthvm in-editor tests ===")
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if les.is_in_play_in_editor():
    print("ABORT: in PIE -- run with Play stopped"); raise SystemExit
if not EAL.does_asset_exist(SOBJ.split(".")[0]):
    print("ABORT: %s missing -- run mods/forthvm/00_create_fcell.py first" % SOBJ); raise SystemExit

try:
    FP = resolve_fpin()
    if not FP:
        raise RuntimeError("could not resolve the float member pin of ST_FCell")
    for t in (test_cell_roundtrip, test_stack_push_read):
        try:
            t(FP)
        except Exception:
            import traceback
            expect(t.__name__ + " (raised)", False, traceback.format_exc().splitlines()[-1][:120])
finally:
    if EAL.does_directory_exist(PKG):
        for a in list(EAL.list_assets(PKG, recursive=True, include_folder=False)):
            try: EAL.delete_asset(a.split(".")[0])
            except Exception: pass
        EAL.delete_directory(PKG)
    print("cleanup:", PKG)

passed = sum(1 for _, ok, _ in _results if ok)
for name, ok, detail in _results:
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, "  -- " + detail if detail and not ok else ""))
print("=== %d/%d passed ===" % (passed, len(_results)))
