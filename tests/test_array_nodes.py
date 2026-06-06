"""Isolation test: do K2Node_CallArrayFunction (Array_Clear/Array_Add) + K2Node_GetArrayItem
paste + compile + RUN correctly? Validates the node mechanics before wiring C3 into the manager.
Builds an int array [10,20,30] in BP, reads [1] and [0] back, asserts 20 and 10."""
import sys
for _m in list(sys.modules):
    if _m == "bpkit" or _m.startswith("bpkit."):
        sys.modules.pop(_m, None)
import unreal, re
from bpkit import bridge as bp, ir
BEL = unreal.BlueprintEditorLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
import time
PKG = "/Game/_Scratch/_probe_%d" % int(time.time())
NAME = "BP_ArrProbe"
path = PKG + "/" + NAME
full = path + "." + NAME
KARRC = "/Script/Engine.KismetArrayLibrary"
KML = "/Script/Engine.KismetMathLibrary"

obj, _ = bp.scratch_blueprint(pkg=PKG, name=NAME)
intt = BEL.get_basic_type_by_name("int")
BEL.add_member_variable(obj, "IntArr", BEL.get_array_type(intt))
for vn in ("ResA", "ResB", "Len"):
    BEL.add_member_variable(obj, vn, intt)

g = ir.Graph("EventGraph")
def cref(c): return "/Script/CoreUObject.Class'%s'" % c
def settype(pin, cat, container=None, ref=False, const=False):
    pin.set("PinType.PinCategory", '"%s"' % cat)
    if container: pin.set("PinType.ContainerType", container)
    if ref: pin.set("PinType.bIsReference", "True")
    if const: pin.set("PinType.bIsConst", "True")
def arr_fn(member, cat, pos):
    n = g.node("K2Node_CallArrayFunction",
        ['FunctionReference=(MemberParent="%s",MemberName="%s")' % (cref(KARRC), member)],
        base="ArrFn", pos=pos)
    sp = n.pin("self"); sp.dir = "EGPD_Input"; settype(sp, "object")
    sp.set("PinType.PinSubCategoryObject", cref(KARRC))
    sp.set("DefaultObject", "/Script/Engine.Default__KismetArrayLibrary"); sp.set("bHidden", "True")
    tp = n.pin("TargetArray"); tp.dir = "EGPD_Input"; settype(tp, cat, "Array", ref=True, const=True)
    tp.set("bDefaultValueIsIgnored", "True")
    return n
def get_item(arr_node, arr_pin, idx_lit, cat, pos):
    n = g.node("K2Node_GetArrayItem", ["bReturnByRefDesired=False"], base="GetItem", pos=pos)
    ap = n.pin("Array"); ap.dir = "EGPD_Input"; settype(ap, cat, "Array")
    ip = n.pin("Dimension 1"); ip.dir = "EGPD_Input"; settype(ip, "int"); ip.set("DefaultValue", '"%s"' % idx_lit)
    op = n.pin("Output"); op.dir = "EGPD_Output"; settype(op, cat)
    g.wire(arr_node, arr_pin, n, "Array", exec=False)
    return n

ev = g.custom_event("Run")
chain_prev = (ev, "then")
def chain(n):
    global chain_prev
    g.wire(chain_prev[0], chain_prev[1], n, "execute", exec=True); chain_prev = (n, "then")

clr = arr_fn("Array_Clear", "int", (300, 0))
arrGet0 = g.var_get("IntArr", "int", pos=(0, 250)); arrGet0.pin("IntArr").set("PinType.ContainerType", "Array")
g.wire(arrGet0, "IntArr", clr, "TargetArray", exec=False)
chain(clr)
for i, val in enumerate((10, 20, 30)):
    add = arr_fn("Array_Add", "int", (600 + i * 250, 0))
    ag = g.var_get("IntArr", "int", pos=(600 + i * 250, 250)); ag.pin("IntArr").set("PinType.ContainerType", "Array")
    g.wire(ag, "IntArr", add, "TargetArray", exec=False)
    ni = add.pin("NewItem"); ni.dir = "EGPD_Input"; settype(ni, "int"); ni.set("DefaultValue", '"%d"' % val)
    chain(add)
# ResA = IntArr[1], ResB = IntArr[0]
agA = g.var_get("IntArr", "int", pos=(1400, 250)); agA.pin("IntArr").set("PinType.ContainerType", "Array")
giA = get_item(agA, "IntArr", 1, "int", (1600, 250))
setA = g.var_set("ResA", "int", pos=(1850, 0)); g.wire(giA, "Output", setA, "ResA", exec=False); chain(setA)
agB = g.var_get("IntArr", "int", pos=(1400, 500)); agB.pin("IntArr").set("PinType.ContainerType", "Array")
giB = get_item(agB, "IntArr", 0, "int", (1600, 500))
setB = g.var_set("ResB", "int", pos=(2100, 0)); g.wire(giB, "Output", setB, "ResB", exec=False); chain(setB)

bp_ptr, gp = bp.find_graph(full, "EventGraph")
bp.clear_graph(bp_ptr, gp)
print("inject:", bp.inject(full, g.render(), graph_name="EventGraph"))
BEL.compile_blueprint(unreal.load_asset(path))
txt = bp.export_nodes(bp.graph_nodes(gp))
orph = re.findall(r'PinName="[^"]+"[^)]*?bOrphanedPin=True', txt)
wild = [b for b in re.split(r'(?=Begin Object)', txt) if 'PinCategory="wildcard"' in b and "MacroInstance" not in b]
print("ORPHANS:", len(orph), "| WILDCARD nodes:", len(wild))
# spawn + run + assert
gc = unreal.load_object(None, full + "_C")
inst = EAS.spawn_actor_from_class(gc, unreal.Vector(0, 0, 0))
inst.call_method("Run")
ra, rb = inst.get_editor_property("ResA"), inst.get_editor_property("ResB")
print("ResA(expect 20):", ra, "| ResB(expect 10):", rb)
print("ARRAY NODES WORK" if (ra == 20 and rb == 10 and not orph and not wild) else "FAIL")
EAS.destroy_actor(inst)
unreal.EditorAssetLibrary.delete_directory(PKG)
