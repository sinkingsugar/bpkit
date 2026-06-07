"""Generate the forthvm interpreter Blueprint (BP_ForthVM) and run it.

Architecture: a `Step` event executes ONE bytecode instruction; the loop is "call
Step until Running=false" (a Tick in-game, Python in tests). Dispatch is a Branch
chain (SwitchInteger case pins can't be authored via paste). Pure-node ordering
matters: the opcode and inline operands are CAPTURED into member vars BEFORE IP is
advanced, so the branch tests and operand reads see the right cells.

THIS BUILD = the minimal slice (LIT_FLOAT / PRINT / HALT) running `5.0 .` -> Out 5.0,
proving the whole pipeline. DUP/MUL/ADD/MK_VEC are added as more handlers (burst 4).
Run with Play stopped, after 00_create_fcell.py.

    & $py ue_run.py mods/forthvm/build_vm.py
"""
import sys, os, re, time
for _m in list(sys.modules):
    if _m == "bpkit" or _m.startswith("bpkit."):
        sys.modules.pop(_m, None)
import unreal
from bpkit import bridge as bp, ir, config as _cfg
sys.path.insert(0, os.path.join(_cfg.REPO_ROOT, "mods", "forthvm"))
sys.modules.pop("config", None); import config as MOD
sys.modules.pop("isa", None); import isa

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if les.is_in_play_in_editor():
    print("ABORT: in PIE"); raise SystemExit
BEL = unreal.BlueprintEditorLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
EAL = unreal.EditorAssetLibrary
SOBJ = MOD.OUTPUT_PKG + "/" + MOD.STRUCT + "." + MOD.STRUCT
STYPE = '"/Script/CoreUObject.UserDefinedStruct\'%s\'"' % SOBJ
KARR = "/Script/Engine.KismetArrayLibrary"
KMATH = "/Script/Engine.KismetMathLibrary"
if not EAL.does_asset_exist(SOBJ.split(".")[0]):
    print("ABORT: %s missing -- run 00_create_fcell.py" % SOBJ); raise SystemExit


def fpin():  # resolve the cell's float member pin name live
    _, pr = bp.scratch_blueprint(pkg="/Game/_Scratch/_vmgen", name="BP_FP")
    pf = "/Game/_Scratch/_vmgen/BP_FP.BP_FP"
    a, gp = bp.find_graph(pf, "EventGraph"); bp.clear_graph(a, gp)
    bp.inject(pf, 'Begin Object Class=/Script/BlueprintGraph.K2Node_MakeStruct Name="MK"\n   StructType=%s\nEnd Object\n' % STYPE, "EventGraph")
    t = bp.export_nodes(bp.graph_nodes(gp))
    EAL.delete_asset(pf.split(".")[0])
    for line in t.splitlines():
        if 'PinName="MemberVar' in line and 'PinType.PinCategory="real"' in line:
            return re.search(r'PinName="([^"]+)"', line).group(1)


F_PIN = fpin()
print("F_PIN =", F_PIN)

# --- build BP_ForthVM --------------------------------------------------------
path = MOD.OUTPUT_PKG + "/" + MOD.VM
objpath = path + "." + MOD.VM
# reuse-or-create (NEVER delete+recreate -- that leaves the old BP pinned in the undo
# buffer and the recompiled class comes back stale; clear_graph + re-inject is clean
# and re-runnable in-session). add_member_variable no-ops on existing vars.
obj, _ = bp.scratch_blueprint(pkg=MOD.OUTPUT_PKG, name=MOD.VM)
fcell = unreal.load_asset(SOBJ)
intT = BEL.get_basic_type_by_name("int"); realT = BEL.get_basic_type_by_name("real")
boolT = BEL.get_basic_type_by_name("bool"); cellAT = BEL.get_array_type(BEL.get_struct_type(fcell))
for nm, ty in (("Code", BEL.get_array_type(intT)), ("Floats", BEL.get_array_type(realT)),
               ("Data", cellAT), ("IP", intT), ("Running", boolT), ("Out", realT),
               ("Opcode", intT), ("Operand", intT), ("TmpAF", realT), ("TmpBF", realT)):
    BEL.add_member_variable(obj, nm, ty)
    BEL.set_blueprint_variable_instance_editable(obj, nm, True)


def st(node, pin, d, array=False):
    p = node.pin(pin); p.dir = d
    p.set("PinType.PinCategory", '"struct"'); p.set("PinType.PinSubCategoryObject", STYPE)
    if array: p.set("PinType.ContainerType", "Array")
    return p


def intarr(node, pin, d):
    p = node.pin(pin); p.dir = d
    p.set("PinType.PinCategory", '"int"'); p.set("PinType.ContainerType", "Array")
    return p


def caf(g, fn, pos):
    return g.node("K2Node_CallArrayFunction",
        ['FunctionReference=(MemberParent="/Script/CoreUObject.Class\'%s\'",MemberName="%s")' % (KARR, fn)],
        base="CAF", pos=pos)


g = ir.Graph("EventGraph")
ev = g.custom_event("Step", pos=(0, 0))

# capture Opcode = Code[IP]   (BEFORE advancing IP)
codeG = g.var_get("Code", "int", pos=(200, -100)); intarr(codeG, "Code", "EGPD_Output")
ipG = g.var_get("IP", "int", pos=(200, 50))
getOp = g.node("K2Node_GetArrayItem", [], base="GAI", pos=(420, -50))
intarr(getOp, "Array", "EGPD_Input")
getOp.pin("Output").typed("int", direction="EGPD_Output")
g.wire(codeG, "Code", getOp, "Array", exec=False)
g.wire(ipG, "IP", getOp, "Dimension 1", exec=False)
setOp = g.var_set("Opcode", "int", pos=(640, 0)); g.wire(getOp, "Output", setOp, "Opcode", exec=False)
g.wire(ev, "then", setOp, "execute", exec=True)
# IP = IP + 1
ipG2 = g.var_get("IP", "int", pos=(640, 120))
inc = g.call("Add_IntInt", KMATH, pos=(820, 120)); g.wire(ipG2, "IP", inc, "A", exec=False)
g.typed_input(inc, "B", "1", "int")
setIP = g.var_set("IP", "int", pos=(1000, 60)); g.wire(inc, "ReturnValue", setIP, "IP", exec=False)
g.wire(setOp, "then", setIP, "execute", exec=True)

opG = g.var_get("Opcode", "int", pos=(1180, 200))   # one read, fanned to all Equals


def equal(k, pos):
    e = g.call("EqualEqual_IntInt", KMATH, pos=pos)
    g.wire(opG, "Opcode", e, "A", exec=False)
    g.typed_input(e, "B", str(k), "int")
    return e


def branch(cond, pos):
    b = g.branch(pos=pos)
    g.wire(cond, "ReturnValue", b, "Condition", exec=False)
    return b


# dispatch chain: LIT_FLOAT(2) -> DUP(5) -> MUL(10) -> PRINT(13) -> HALT(0)
bF = branch(equal(isa.LIT_FLOAT, (1200, 300)), (1400, 300))
bD = branch(equal(isa.DUP, (1200, 1200)), (1400, 1200))
bM = branch(equal(isa.MUL, (1200, 1500)), (1400, 1500))
bP = branch(equal(isa.PRINT, (1200, 600)), (1400, 600))
bH = branch(equal(isa.HALT, (1200, 900)), (1400, 900))
g.wire(setIP, "then", bF, "execute", exec=True)
g.wire(bF, "Else", bD, "execute", exec=True)
g.wire(bD, "Else", bM, "execute", exec=True)
g.wire(bM, "Else", bP, "execute", exec=True)
g.wire(bP, "Else", bH, "execute", exec=True)

# --- handler: LIT_FLOAT --- operand = Code[IP]; IP++; push Make(Type=1,F=Floats[operand])
cG = g.var_get("Code", "int", pos=(1700, 250)); intarr(cG, "Code", "EGPD_Output")
ipH = g.var_get("IP", "int", pos=(1700, 350))
getOperand = g.node("K2Node_GetArrayItem", [], base="GAI", pos=(1900, 300))
intarr(getOperand, "Array", "EGPD_Input"); getOperand.pin("Output").typed("int", direction="EGPD_Output")
g.wire(cG, "Code", getOperand, "Array", exec=False)
g.wire(ipH, "IP", getOperand, "Dimension 1", exec=False)
setOperand = g.var_set("Operand", "int", pos=(2120, 250)); g.wire(getOperand, "Output", setOperand, "Operand", exec=False)
g.wire(bF, "Then", setOperand, "execute", exec=True)
ipH2 = g.var_get("IP", "int", pos=(2120, 400)); inc2 = g.call("Add_IntInt", KMATH, pos=(2300, 400))
g.wire(ipH2, "IP", inc2, "A", exec=False); g.typed_input(inc2, "B", "1", "int")
setIP2 = g.var_set("IP", "int", pos=(2480, 350)); g.wire(inc2, "ReturnValue", setIP2, "IP", exec=False)
g.wire(setOperand, "then", setIP2, "execute", exec=True)
# f = Floats[Operand]
flG = g.var_get("Floats", "real", pos=(2700, 250))
flG.pin("Floats").typed("real", direction="EGPD_Output").set("PinType.ContainerType", "Array")
opndG = g.var_get("Operand", "int", pos=(2700, 400))
getF = g.node("K2Node_GetArrayItem", [], base="GAI", pos=(2900, 300))
fa = getF.pin("Array"); fa.dir = "EGPD_Input"; fa.set("PinType.PinCategory", '"real"'); fa.set("PinType.ContainerType", "Array")
getF.pin("Output").typed("real", direction="EGPD_Output")
g.wire(flG, "Floats", getF, "Array", exec=False)
g.wire(opndG, "Operand", getF, "Dimension 1", exec=False)
mk = g.node("K2Node_MakeStruct", ["StructType=%s" % STYPE], base="MakeStruct", pos=(3100, 300))
# wire f -> Make.F (minimal test reads F via Break; Type tag set later in burst 4)
mk.pin(F_PIN).typed("real", direction="EGPD_Input")
g.wire(getF, "Output", mk, F_PIN, exec=False)
dataPush = g.var_get("Data", "struct", STYPE, pos=(3100, 500)); st(dataPush, "Data", "EGPD_Output", array=True)
add = caf(g, "Array_Add", (3300, 400)); st(add, "TargetArray", "EGPD_Input", array=True); st(add, "NewItem", "EGPD_Input")
g.wire(dataPush, "Data", add, "TargetArray", exec=False)
g.wire(mk, "ST_FCell", add, "NewItem", exec=False)
g.wire(setIP2, "then", add, "execute", exec=True)

# --- handler: PRINT --- Out = Data[len-1].F ; Array_Remove(Data, len-1)
dLp = g.var_get("Data", "struct", STYPE, pos=(1700, 650)); st(dLp, "Data", "EGPD_Output", array=True)
lenP = caf(g, "Array_Length", (1900, 650)); st(lenP, "TargetArray", "EGPD_Input", array=True)
g.wire(dLp, "Data", lenP, "TargetArray", exec=False)
idxP = g.call("Subtract_IntInt", KMATH, pos=(2100, 650)); g.wire(lenP, "ReturnValue", idxP, "A", exec=False)
g.typed_input(idxP, "B", "1", "int")
dGp = g.var_get("Data", "struct", STYPE, pos=(2100, 780)); st(dGp, "Data", "EGPD_Output", array=True)
getC = g.node("K2Node_GetArrayItem", [], base="GAI", pos=(2300, 720)); st(getC, "Array", "EGPD_Input", array=True); st(getC, "Output", "EGPD_Output")
g.wire(dGp, "Data", getC, "Array", exec=False); g.wire(idxP, "ReturnValue", getC, "Dimension 1", exec=False)
bkP = g.node("K2Node_BreakStruct", ["StructType=%s" % STYPE], base="BreakStruct", pos=(2500, 720)); st(bkP, "ST_FCell", "EGPD_Input")
g.wire(getC, "Output", bkP, "ST_FCell", exec=False)
setOut = g.var_set("Out", "real", pos=(2700, 650)); g.wire(bkP, F_PIN, setOut, "Out", exec=False)
g.wire(bP, "Then", setOut, "execute", exec=True)
dRp = g.var_get("Data", "struct", STYPE, pos=(2700, 820)); st(dRp, "Data", "EGPD_Output", array=True)
rem = caf(g, "Array_Remove", (2900, 720)); st(rem, "TargetArray", "EGPD_Input", array=True)
g.wire(dRp, "Data", rem, "TargetArray", exec=False)
idxP2 = g.call("Subtract_IntInt", KMATH, pos=(2700, 950))
dLp2 = g.var_get("Data", "struct", STYPE, pos=(2500, 950)); st(dLp2, "Data", "EGPD_Output", array=True)
lenP2 = caf(g, "Array_Length", (2600, 1050)); st(lenP2, "TargetArray", "EGPD_Input", array=True)
g.wire(dLp2, "Data", lenP2, "TargetArray", exec=False); g.wire(lenP2, "ReturnValue", idxP2, "A", exec=False)
g.typed_input(idxP2, "B", "1", "int")
g.wire(idxP2, "ReturnValue", rem, "IndexToRemove", exec=False)
g.wire(setOut, "then", rem, "execute", exec=True)

# --- handler: HALT --- Running=false
setR = g.var_set("Running", "bool", pos=(1700, 900)); setR.pin("Running").typed("bool", direction="EGPD_Input").literal("false")
g.wire(bH, "Then", setR, "execute", exec=True)

# --- handler: DUP --- push a copy of the top cell
dDup = g.var_get("Data", "struct", STYPE, pos=(1700, 1200)); st(dDup, "Data", "EGPD_Output", array=True)
lenD = caf(g, "Array_Length", (1880, 1300)); st(lenD, "TargetArray", "EGPD_Input", array=True)
g.wire(dDup, "Data", lenD, "TargetArray", exec=False)
idxD = g.call("Subtract_IntInt", KMATH, pos=(2060, 1300)); g.wire(lenD, "ReturnValue", idxD, "A", exec=False)
g.typed_input(idxD, "B", "1", "int")
dDupG = g.var_get("Data", "struct", STYPE, pos=(2060, 1180)); st(dDupG, "Data", "EGPD_Output", array=True)
getTop = g.node("K2Node_GetArrayItem", [], base="GAI", pos=(2260, 1200))
st(getTop, "Array", "EGPD_Input", array=True); st(getTop, "Output", "EGPD_Output")
g.wire(dDupG, "Data", getTop, "Array", exec=False); g.wire(idxD, "ReturnValue", getTop, "Dimension 1", exec=False)
dDupP = g.var_get("Data", "struct", STYPE, pos=(2460, 1300)); st(dDupP, "Data", "EGPD_Output", array=True)
addD = caf(g, "Array_Add", (2660, 1200)); st(addD, "TargetArray", "EGPD_Input", array=True); st(addD, "NewItem", "EGPD_Input")
g.wire(dDupP, "Data", addD, "TargetArray", exec=False); g.wire(getTop, "Output", addD, "NewItem", exec=False)
g.wire(bD, "Then", addD, "execute", exec=True)


# --- handler: MUL (float) --- pop b->TmpBF, pop a->TmpAF, push Make(F=TmpAF*TmpBF)
def pop_float_into(tmp, y):
    """exec: SetTmp <- Break(Data[len-1]).F ; then Array_Remove(Data,len-1). Returns
    (entry_exec_node, exit_exec_node) for chaining."""
    dl = g.var_get("Data", "struct", STYPE, pos=(1700, y)); st(dl, "Data", "EGPD_Output", array=True)
    ln = caf(g, "Array_Length", (1840, y + 90)); st(ln, "TargetArray", "EGPD_Input", array=True)
    g.wire(dl, "Data", ln, "TargetArray", exec=False)
    ix = g.call("Subtract_IntInt", KMATH, pos=(2000, y + 90)); g.wire(ln, "ReturnValue", ix, "A", exec=False)
    g.typed_input(ix, "B", "1", "int")
    dg = g.var_get("Data", "struct", STYPE, pos=(2000, y - 70)); st(dg, "Data", "EGPD_Output", array=True)
    gi = g.node("K2Node_GetArrayItem", [], base="GAI", pos=(2200, y))
    st(gi, "Array", "EGPD_Input", array=True); st(gi, "Output", "EGPD_Output")
    g.wire(dg, "Data", gi, "Array", exec=False); g.wire(ix, "ReturnValue", gi, "Dimension 1", exec=False)
    bk = g.node("K2Node_BreakStruct", ["StructType=%s" % STYPE], base="BreakStruct", pos=(2400, y)); st(bk, "ST_FCell", "EGPD_Input")
    g.wire(gi, "Output", bk, "ST_FCell", exec=False)
    setT = g.var_set(tmp, "real", pos=(2600, y)); g.wire(bk, F_PIN, setT, tmp, exec=False)
    # remove last (recompute len-1 fresh)
    dr = g.var_get("Data", "struct", STYPE, pos=(2600, y + 130)); st(dr, "Data", "EGPD_Output", array=True)
    rm = caf(g, "Array_Remove", (2820, y)); st(rm, "TargetArray", "EGPD_Input", array=True)
    g.wire(dr, "Data", rm, "TargetArray", exec=False)
    dl2 = g.var_get("Data", "struct", STYPE, pos=(2600, y + 210)); st(dl2, "Data", "EGPD_Output", array=True)
    ln2 = caf(g, "Array_Length", (2700, y + 250)); st(ln2, "TargetArray", "EGPD_Input", array=True)
    g.wire(dl2, "Data", ln2, "TargetArray", exec=False)
    ix2 = g.call("Subtract_IntInt", KMATH, pos=(2820, y + 210)); g.wire(ln2, "ReturnValue", ix2, "A", exec=False)
    g.typed_input(ix2, "B", "1", "int")
    g.wire(ix2, "ReturnValue", rm, "IndexToRemove", exec=False)
    g.wire(setT, "then", rm, "execute", exec=True)
    return setT, rm


setTB, remB = pop_float_into("TmpBF", 1500)
setTA, remA = pop_float_into("TmpAF", 1950)
afG = g.var_get("TmpAF", "real", pos=(3050, 1700)); bfG = g.var_get("TmpBF", "real", pos=(3050, 1780))
prod = g.call("Multiply_DoubleDouble", KMATH, pos=(3250, 1740))
g.wire(afG, "TmpAF", prod, "A", exec=False); g.wire(bfG, "TmpBF", prod, "B", exec=False)
mkM = g.node("K2Node_MakeStruct", ["StructType=%s" % STYPE], base="MakeStruct", pos=(3450, 1740))
mkM.pin(F_PIN).typed("real", direction="EGPD_Input")
g.wire(prod, "ReturnValue", mkM, F_PIN, exec=False)
dPushM = g.var_get("Data", "struct", STYPE, pos=(3450, 1880)); st(dPushM, "Data", "EGPD_Output", array=True)
addM = caf(g, "Array_Add", (3650, 1740)); st(addM, "TargetArray", "EGPD_Input", array=True); st(addM, "NewItem", "EGPD_Input")
g.wire(dPushM, "Data", addM, "TargetArray", exec=False); g.wire(mkM, "ST_FCell", addM, "NewItem", exec=False)
g.wire(bM, "Then", setTB, "execute", exec=True)
g.wire(remB, "then", setTA, "execute", exec=True)
g.wire(remA, "then", addM, "execute", exec=True)

# inject + validate
bp_ptr, gp = bp.find_graph(objpath, "EventGraph"); bp.clear_graph(bp_ptr, gp)
print("inject ->", bp.inject(objpath, g.render(), graph_name="EventGraph"))
txt = bp.export_nodes(bp.graph_nodes(gp))
orph = re.findall(r'PinName="([^"]+)"[^)]*?bOrphanedPin=True', txt)
errs = [b for b in re.split(r"(?=Begin Object Class=)", txt)
        if "ErrorMsg" in b and 'ErrorMsg=""' not in b and "Override pins have been removed" not in b]
print("orphans:", len(orph), orph[:10])
print("errors:", [re.search(r'ErrorMsg="([^"]*)"', e).group(1)[:70] for e in errs])
EAL.save_asset(path)

# --- run: program `5.0 .`  ->  [LIT_FLOAT,0, PRINT, HALT], Floats=[5.0] ----
gc = unreal.load_object(None, objpath + "_C")
inst = EAS.spawn_actor_from_class(gc, unreal.Vector(0, 0, 0))
inst.set_editor_property("Code", [isa.LIT_FLOAT, 0, isa.PRINT, isa.HALT])
inst.set_editor_property("Floats", [5.0])
inst.set_editor_property("IP", 0); inst.set_editor_property("Running", True)
steps = 0
while inst.get_editor_property("Running") and steps < 50:
    inst.call_method("Step"); steps += 1
out = inst.get_editor_property("Out")
print("\nRESULT  (5.0 .)        steps=%d Out=%s -> %s" % (steps, out, "PASS 5.0" if abs(out - 5.0) < 1e-6 else "FAIL"))

# program 2: `5.0 dup * .` -> 25.0
inst.set_editor_property("Data", [])
inst.set_editor_property("Code", [isa.LIT_FLOAT, 0, isa.DUP, isa.MUL, isa.PRINT, isa.HALT])
inst.set_editor_property("Floats", [5.0])
inst.set_editor_property("IP", 0); inst.set_editor_property("Out", 0.0); inst.set_editor_property("Running", True)
s2 = 0
while inst.get_editor_property("Running") and s2 < 50:
    inst.call_method("Step"); s2 += 1
out2 = inst.get_editor_property("Out")
print("RESULT  (5.0 dup * .)  steps=%d Out=%s -> %s" % (s2, out2, "PASS 25.0" if abs(out2 - 25.0) < 1e-6 else "FAIL"))
EAS.destroy_actor(inst)
if EAL.does_directory_exist("/Game/_Scratch/_vmgen"):
    EAL.delete_directory("/Game/_Scratch/_vmgen")
print("done")
