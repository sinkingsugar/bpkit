"""Definitive: does ForEach LoopBody fire per element? Uses a member-var array set
from Python (no world/empty-array ambiguity). Run with Play STOPPED."""
import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
for _m in ("bp_ir", "bp_bridge", "bp_author", "bp_compact"):
    sys.modules.pop(_m, None)
import unreal
import bp_bridge as bp
import bp_ir as ir

PKG, NAME = "/Game/_Scratch", "BP_IterTest"
PATH = PKG + "/" + NAME
FULL = PATH + "." + NAME
KML = "/Script/Engine.KismetMathLibrary"

bp_obj, _ = bp.scratch_blueprint(pkg=PKG, name=NAME)
BEL = unreal.BlueprintEditorLibrary
itemsT = BEL.get_array_type(BEL.get_object_reference_type(unreal.Actor.static_class()))
BEL.add_member_variable(bp_obj, "Items", itemsT)
BEL.add_member_variable(bp_obj, "Count", BEL.get_basic_type_by_name("int"))
BEL.set_blueprint_variable_instance_editable(bp_obj, "Items", True)

g = ir.Graph("EventGraph")
ev = g.custom_event("Run")
getItems = g.var_get("Items", "object", ir.obj_path("/Script/Engine.Actor"), pos=(250, 200))
getItems.pin("Items").set("PinType.ContainerType", "Array")  # it's an array var
loop = g.foreach("/Script/Engine.Actor", pos=(500, 0))
g.wire(getItems, "Items", loop, "Array", exec=False)
g.wire(ev, "then", loop, "Exec", exec=True)
getC = g.var_get("Count", "int", pos=(750, 250))
add = g.call("Add_IntInt", KML, pos=(950, 200))
g.wire(getC, "Count", add, "A", exec=False)
g.typed_input(add, "B", "1", "int")
setC = g.var_set("Count", "int", pos=(1150, 0))
g.wire(add, "ReturnValue", setC, "Count", exec=False)
g.wire(loop, "LoopBody", setC, "execute", exec=True)

text = g.render()
bp_ptr, gp = bp.find_graph(FULL, "EventGraph")
bp.clear_graph(bp_ptr, gp)
print("inject:", bp.inject(FULL, text, graph_name="EventGraph"))

gc = unreal.load_object(None, FULL + "_C")
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
inst = eas.spawn_actor_from_class(gc, unreal.Vector(0, 0, 0))
world = inst.get_world()
some = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor))[:5]
inst.set_editor_property("Items", some)
print("set Items to", len(some), "actors")
inst.call_method("Run")
print("Count after Run:", inst.get_editor_property("Count"))
print(">> Count == %d -> ForEach ITERATES. 0 -> LoopBody never fires (broken)." % len(some))
eas.destroy_actor(inst)
