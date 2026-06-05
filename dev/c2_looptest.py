"""Does bp_ir.foreach actually ITERATE at runtime? Deterministic isolation test:
a scratch BP with a custom event that ForEach's GetAllActorsOfClass(Actor) and
increments Count. Spawn in the editor world, call the event, read Count. No PIE,
no mount, no framework. Run with Play STOPPED. Run: python ue_run.py dev/c2_looptest.py
"""
import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
for _m in ("bp_ir", "bp_bridge", "bp_author", "bp_compact"):
    sys.modules.pop(_m, None)
import unreal
import bp_bridge as bp
import bp_ir as ir

PKG, NAME = "/Game/_Scratch", "BP_LoopTest"
PATH = PKG + "/" + NAME
FULL = PATH + "." + NAME
GS = "/Script/Engine.GameplayStatics"
KML = "/Script/Engine.KismetMathLibrary"

bp_obj, _ = bp.scratch_blueprint(pkg=PKG, name=NAME)
unreal.BlueprintEditorLibrary.add_member_variable(bp_obj, "Count",
    unreal.BlueprintEditorLibrary.get_basic_type_by_name("int"))
unreal.BlueprintEditorLibrary.add_member_variable(bp_obj, "Done",
    unreal.BlueprintEditorLibrary.get_basic_type_by_name("bool"))

g = ir.Graph("EventGraph")
ev = g.custom_event("TestLoop")
getAll = g.call("GetAllActorsOfClass", GS, pos=(300, 0))
# ActorClass input = Actor (class pin)
ac = getAll.pin("ActorClass"); ac.dir = "EGPD_Input"
ac.set("PinType.PinCategory", '"class"')
ac.set("PinType.PinSubCategoryObject", ir.obj_path("/Script/Engine.Actor"))
ac.set("DefaultObject", "/Script/Engine.Actor")
loop = g.foreach("/Script/Engine.Actor", pos=(600, 0))
g.wire(getAll, "OutActors", loop, "Array", exec=False)
# GetAllActorsOfClass is IMPURE (has exec) -> must be in the exec chain or it's pruned
g.wire(ev, "then", getAll, "execute", exec=True)
g.wire(getAll, "then", loop, "Exec", exec=True)
# LoopBody -> Count = Count + 1
getC = g.var_get("Count", "int", pos=(850, 250))
add = g.call("Add_IntInt", KML, pos=(1050, 200))
g.wire(getC, "Count", add, "A", exec=False)
g.typed_input(add, "B", "1", "int")
setC = g.var_set("Count", "int", pos=(1250, 0))
g.wire(add, "ReturnValue", setC, "Count", exec=False)
g.wire(loop, "LoopBody", setC, "execute", exec=True)
# Completed -> Done=true, so we can tell "macro ran but array empty" from "macro never ran"
setDone = g.var_set("Done", "bool", pos=(900, -150))
setDone.pin("Done").literal("true")
g.wire(loop, "Completed", setDone, "execute", exec=True)

text = g.render()
bp_ptr, gp = bp.find_graph(FULL, "EventGraph")
bp.clear_graph(bp_ptr, gp)
print("inject:", bp.inject(FULL, text, graph_name="EventGraph"))

# run it: spawn in editor world, call TestLoop, read Count
gc = unreal.load_object(None, FULL + "_C")
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
inst = eas.spawn_actor_from_class(gc, unreal.Vector(0, 0, 0))
print("instance:", inst.get_name() if inst else None)
world = inst.get_world()
n_actors = len(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor))
print("actors in world:", n_actors)
inst.call_method("TestLoop")
print("Count after TestLoop:", inst.get_editor_property("Count"))
print("Done (Completed fired)?:", inst.get_editor_property("Done"))
print(">> Done=True + Count=0 -> loop RAN but array empty (test artifact).")
print(">> Done=False -> macro never executed (ForEach authoring broken).")
print(">> Count>0 -> ForEach works.")
eas.destroy_actor(inst)
