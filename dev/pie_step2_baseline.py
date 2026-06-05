"""Step 2 (baseline): in the sim world, spawn a horse, give it an AI controller,
issue a navmesh MoveTo, and stash refs in a module global for step 3 to re-check.

    python ue_run.py dev/pie_step2_baseline.py
"""
import unreal

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
print("in PIE:", les.is_in_play_in_editor())
worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
print("pie worlds:", [w.get_path_name() for w in worlds])
if not worlds:
    print("!! no sim world yet — wait and retry")
    raise SystemExit

world = worlds[0]

HORSE = "/Game/Characters/NPCs/Hooved_Wild/Blueprints/BP_NPC_Mounts_Horse.BP_NPC_Mounts_Horse_C"
horse_cls = unreal.load_object(None, HORSE)
print("horse class:", horse_cls)

# Find a spawn point: the PlayerStart location, projected to navmesh.
nav = unreal.NavigationSystemV1.get_navigation_system(world)
print("nav system:", nav)

# Spawn near origin; AlmostEmpty PlayerStart is near 0,0. Use a known point.
loc = unreal.Vector(0, 0, 200)
rot = unreal.Rotator(0, 0, 0)

# Project to navmesh to get a valid start
start = loc
if nav:
    try:
        projected = nav.project_point_to_navigation(loc, unreal.Vector(500, 500, 500))
        if projected:
            start = projected
            print("projected start:", start)
    except Exception as e:
        print("project err:", e)

horse = unreal.GameplayStatics.begin_deferred_actor_spawn_from_class(
    world, horse_cls, unreal.Transform(unreal.Vector(start.x, start.y, start.z), rot, unreal.Vector(1, 1, 1)),
    unreal.SpawnActorCollisionHandlingMethod.ADJUST_IF_POSSIBLE_BUT_ALWAYS_SPAWN)
horse = unreal.GameplayStatics.finish_spawning_actor(horse, unreal.Transform(unreal.Vector(start.x, start.y, start.z), rot, unreal.Vector(1, 1, 1)))
print("spawned horse:", horse)

# Possess with its default AI controller
if horse:
    try:
        horse.spawn_default_controller()
        print("spawned default controller; controller=", horse.get_controller())
    except Exception as e:
        print("spawn_default_controller err:", e)

    # Issue an AI move ~1200 units along +X
    dest = unreal.Vector(start.x + 1200, start.y, start.z)
    if nav:
        try:
            proj = nav.project_point_to_navigation(dest, unreal.Vector(800, 800, 800))
            if proj:
                dest = proj
        except Exception:
            pass
    ctrl = horse.get_controller()
    print("controller:", ctrl)
    if isinstance(ctrl, unreal.AIController):
        res = unreal.AIBlueprintHelperLibrary.simple_move_to_location(ctrl, dest) if hasattr(unreal.AIBlueprintHelperLibrary, "simple_move_to_location") else None
        try:
            ctrl.move_to_location(dest, -1.0, True, True, False, True, None, True)
            print("issued move_to_location ->", dest)
        except Exception as e:
            print("move_to_location err:", e)

    # Stash for step 3
    import sys as _s
    g = _s.modules.get("__main__")
    unreal.log("BASELINE_HORSE_START %s" % str(start))
    # Tag the horse so step 3 can find it
    horse.tags = ["TEST_HORSE"]
    print("START_POS", start.x, start.y, start.z)
    print("HORSE_POS_NOW", horse.get_actor_location())
