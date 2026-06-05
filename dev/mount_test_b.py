"""Mount test, part B: re-measure the horse a few seconds after part A issued the
move. Did it actually travel while carrying the rider? That answers Approach A.

    python ue_run.py dev/mount_test_b.py
"""
import unreal

ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world = ues.get_game_world()
if not world:
    print("!! no game world")
    raise SystemExit

horse = None
rider = None
for a in unreal.GameplayStatics.get_all_actors_with_tag(world, "TEST_HORSE"):
    horse = a
for a in unreal.GameplayStatics.get_all_actors_with_tag(world, "TEST_RIDER"):
    rider = a
print("horse:", horse)
print("rider:", rider)
if horse:
    loc = horse.get_actor_location()
    vel = horse.get_velocity()
    print("HORSE_POS_NOW", loc)
    print("HORSE_VELOCITY", vel, "speed=", vel.length())
    ctrl = horse.get_controller()
    print("horse controller:", ctrl)
    try:
        mc = horse.get_movement_component() if hasattr(horse, "get_movement_component") else None
        print("movement comp:", mc)
    except Exception:
        pass
    try:
        print("horse.get_rider():", horse.get_rider())
        print("horse.is_mount (prop):", horse.get_editor_property("is_mount"))
    except Exception as e:
        print("rider link err:", e)
if rider:
    print("rider loc:", rider.get_actor_location())
    try:
        print("rider.get_mount():", rider.get_mount())
    except Exception as e:
        print("mount link err:", e)
