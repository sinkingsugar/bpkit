"""Deterministic unit tests for the BP-authoring toolchain (bp_ir + bp_bridge).

Each test authors a throwaway Blueprint, injects + compiles it, spawns an instance in
the editor world, drives it via call_method, and ASSERTS on read-back state -- no PIE,
no mounting, no eyeballing. Catches the "compiles clean but does nothing" class of bug
(orphaned typed pins, inert wildcard macros) that cost us dearly.

Run with Play STOPPED:  python ue_run.py tests/test_bp_authoring.py

Designed to grow into a real regression suite -- add test_* functions; the runner at
the bottom discovers and reports them.
"""
import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
for _m in ("bp_ir", "bp_bridge", "bp_author", "bp_compact"):
    sys.modules.pop(_m, None)
import unreal
import re
import bp_bridge as bp
import bp_ir as ir

BEL = unreal.BlueprintEditorLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
PKG = "/Game/_Scratch/_tests"
KML = "/Script/Engine.KismetMathLibrary"

_results = []
def expect(name, ok, detail=""):
    _results.append((name, bool(ok), detail))

# --- helpers ----------------------------------------------------------------
def fresh_bp(name):
    path = PKG + "/" + name
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        unreal.EditorAssetLibrary.delete_asset(path)
    obj, _ = bp.scratch_blueprint(pkg=PKG, name=name)
    return obj, path + "." + name

def inject(full, graph):
    bp_ptr, gp = bp.find_graph(full, "EventGraph")
    bp.clear_graph(bp_ptr, gp)
    return bp.inject(full, graph.render(), graph_name="EventGraph")

def orphans(full):
    bp_ptr, gp = bp.find_graph(full, "EventGraph")
    txt = bp.export_nodes(bp.graph_nodes(gp))
    return re.findall(r'PinName="[^"]+"[^)]*?bOrphanedPin=True', txt)

def compile_errors(full):
    obj = unreal.load_asset(full.split(".")[0])
    BEL.compile_blueprint(obj)
    bp_ptr, gp = bp.find_graph(full, "EventGraph")
    txt = bp.export_nodes(bp.graph_nodes(gp))
    return [b for b in re.split(r'(?=Begin Object Class=)', txt) if "ErrorMsg" in b]

def spawn_call(full, method, props=None):
    gc = unreal.load_object(None, full + "_C")
    inst = EAS.spawn_actor_from_class(gc, unreal.Vector(0, 0, 0))
    for k, v in (props or {}).items():
        inst.set_editor_property(k, v)
    inst.call_method(method)
    return inst

# --- tests ------------------------------------------------------------------
def test_foreach_iterates():
    """ForEach LoopBody must fire once per element of a non-empty array."""
    obj, full = fresh_bp("BP_T_ForEach")
    BEL.add_member_variable(obj, "Items",
        BEL.get_array_type(BEL.get_object_reference_type(unreal.Actor.static_class())))
    BEL.add_member_variable(obj, "Count", BEL.get_basic_type_by_name("int"))
    BEL.set_blueprint_variable_instance_editable(obj, "Items", True)
    g = ir.Graph("EventGraph")
    ev = g.custom_event("Run")
    items = g.var_get("Items", "object", ir.obj_path("/Script/Engine.Actor"))
    items.pin("Items").set("PinType.ContainerType", "Array")
    loop = g.foreach("/Script/Engine.Actor")
    g.wire(items, "Items", loop, "Array", exec=False)
    g.wire(ev, "then", loop, "Exec", exec=True)
    getC = g.var_get("Count", "int")
    add = g.call("Add_IntInt", KML); g.wire(getC, "Count", add, "A", exec=False)
    g.typed_input(add, "B", "1", "int")
    setC = g.var_set("Count", "int"); g.wire(add, "ReturnValue", setC, "Count", exec=False)
    g.wire(loop, "LoopBody", setC, "execute", exec=True)
    inject(full, g)
    expect("foreach: no orphans", not orphans(full))
    expect("foreach: compiles clean", not compile_errors(full))
    world = EAS.get_all_level_actors()  # any non-empty source
    some = list(unreal.GameplayStatics.get_all_actors_of_class(
        EAS.get_all_level_actors()[0].get_world(), unreal.Actor))[:4] if EAS.get_all_level_actors() else []
    inst = spawn_call(full, "Run", {"Items": some})
    expect("foreach: LoopBody fires per element", inst.get_editor_property("Count") == len(some),
           "Count=%d expected=%d" % (inst.get_editor_property("Count"), len(some)))
    EAS.destroy_actor(inst)

def test_foreach_empty_completes():
    """ForEach over an empty array iterates 0 times but Completed still fires."""
    obj, full = fresh_bp("BP_T_ForEachEmpty")
    BEL.add_member_variable(obj, "Items",
        BEL.get_array_type(BEL.get_object_reference_type(unreal.Actor.static_class())))
    BEL.add_member_variable(obj, "Count", BEL.get_basic_type_by_name("int"))
    BEL.add_member_variable(obj, "Done", BEL.get_basic_type_by_name("bool"))
    g = ir.Graph("EventGraph")
    ev = g.custom_event("Run")
    items = g.var_get("Items", "object", ir.obj_path("/Script/Engine.Actor"))
    items.pin("Items").set("PinType.ContainerType", "Array")
    loop = g.foreach("/Script/Engine.Actor")
    g.wire(items, "Items", loop, "Array", exec=False)
    g.wire(ev, "then", loop, "Exec", exec=True)
    getC = g.var_get("Count", "int")
    add = g.call("Add_IntInt", KML); g.wire(getC, "Count", add, "A", exec=False)
    g.typed_input(add, "B", "1", "int")
    setC = g.var_set("Count", "int"); g.wire(add, "ReturnValue", setC, "Count", exec=False)
    g.wire(loop, "LoopBody", setC, "execute", exec=True)
    setD = g.var_set("Done", "bool"); setD.pin("Done").literal("true")
    g.wire(loop, "Completed", setD, "execute", exec=True)
    inject(full, g)
    inst = spawn_call(full, "Run", {})  # Items defaults to empty
    expect("foreach-empty: 0 iterations", inst.get_editor_property("Count") == 0)
    expect("foreach-empty: Completed fires", inst.get_editor_property("Done") is True)
    EAS.destroy_actor(inst)

def test_typed_enum_default_merges():
    """A typed enum default must merge onto the canonical pin (no orphan, value set)."""
    obj, full = fresh_bp("BP_T_TypedDefault")
    g = ir.Graph("EventGraph")
    ev = g.event("ReceiveBeginPlay")
    # SetAnimationMode takes an EAnimationMode byte pin
    n = g.call("SetAnimationMode", "/Script/Engine.SkeletalMeshComponent")
    g.typed_input(n, "InAnimationMode", "AnimationSingleNode", "byte",
                  ir.enum_path("/Script/Engine.EAnimationMode"))
    g.wire(ev, "then", n, "execute", exec=True)
    inject(full, g)
    bp_ptr, gp = bp.find_graph(full, "EventGraph")
    txt = bp.export_nodes(bp.graph_nodes(gp))
    expect("typed-default: no orphans", not orphans(full))
    expect("typed-default: value present on canonical pin",
           'DefaultValue="AnimationSingleNode"' in txt and "bOrphanedPin=True" not in
           [l for l in txt.splitlines() if "InAnimationMode" in l and 'DefaultValue="AnimationSingleNode"' in l][0])

# --- runner -----------------------------------------------------------------
TESTS = [test_foreach_iterates, test_foreach_empty_completes, test_typed_enum_default_merges]
print("=== BP authoring unit tests ===")
for t in TESTS:
    try:
        t()
    except Exception as e:
        import traceback
        expect(t.__name__ + " (raised)", False, traceback.format_exc().splitlines()[-1][:120])
passed = sum(1 for _, ok, _ in _results if ok)
for name, ok, detail in _results:
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, "  -- " + detail if detail and not ok else ""))
print("=== %d/%d passed ===" % (passed, len(_results)))
