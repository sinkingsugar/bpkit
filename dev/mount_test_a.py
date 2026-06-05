"""Mount test, part A (run after the user clicks Play and is in-world).

Against the LIVE game world: find player, spawn a horse + a rider NPC near them on
navmesh, possess both with AI, seat the rider via mount(), then command the horse's
AI to path to a destination. Tags actors so part B can re-measure movement.

    python ue_run.py dev/mount_test_a.py
"""
import unreal

ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world = ues.get_game_world()
print("game world:", world.get_path_name() if world else None)
if not world:
    print("!! no game world — is Play running?")
    raise SystemExit

player = unreal.GameplayStatics.get_player_pawn(world, 0)
print("player pawn:", player)
if not player:
    print("!! no player pawn")
    raise SystemExit
ploc = player.get_actor_location()
print("player loc:", ploc)

nav = unreal.NavigationSystemV1.get_navigation_system(world)
print("nav system:", nav)


def on_nav(p, extent=600.0):
    if not nav:
        return p
    try:
        r = nav.project_point_to_navigation(p, unreal.Vector(extent, extent, extent))
        return r if r else p
    except Exception:
        return p


def spawn(path, loc, tag):
    cls = unreal.load_object(None, path)
    if not cls:
        print("  !! class load failed:", path)
        return None
    t = unreal.Transform(loc, unreal.Rotator(0, 0, 0), unreal.Vector(1, 1, 1))
    a = unreal.GameplayStatics.begin_deferred_actor_spawn_from_class(
        world, cls, t, unreal.SpawnActorCollisionHandlingMethod.ADJUST_IF_POSSIBLE_BUT_ALWAYS_SPAWN)
    a = unreal.GameplayStatics.finish_spawning_actor(a, t)
    if a:
        a.tags = [tag]
        try:
            a.spawn_default_controller()
        except Exception as e:
            print("  spawn_default_controller err:", e)
    return a


horse_loc = on_nav(unreal.Vector(ploc.x + 500, ploc.y, ploc.z + 100))
rider_loc = on_nav(unreal.Vector(ploc.x + 500, ploc.y + 250, ploc.z + 100))

horse = spawn("/Game/Characters/NPCs/Hooved_Wild/Blueprints/BP_NPC_Mounts_Horse.BP_NPC_Mounts_Horse_C",
              horse_loc, "TEST_HORSE")
print("horse:", horse, "ctrl:", horse.get_controller() if horse else None)

rider = spawn("/Game/Characters/NPCs/Necromancy_followers/Blueprints/BP_FiniteLifespanUndeadThrall.BP_FiniteLifespanUndeadThrall_C",
              rider_loc, "TEST_RIDER")
print("rider:", rider, "ctrl:", rider.get_controller() if rider else None)

# Seat the rider
if horse and rider:
    try:
        msg = rider.can_mount(horse)
        print("can_mount ->", msg, "(None == OK)")
    except Exception as e:
        print("can_mount err:", e)
    try:
        rider.mount(horse)
        print("called rider.mount(horse)")
    except Exception as e:
        print("mount err:", e)
    try:
        print("  rider.get_mount():", rider.get_mount())
        print("  horse.get_rider():", horse.get_rider())
        print("  horse.is_mountable():", horse.is_mountable())
    except Exception as e:
        print("  link check err:", e)

    # Command the horse AI to path away (toward a point past the player)
    dest = on_nav(unreal.Vector(ploc.x - 1500, ploc.y, ploc.z + 100), 1000)
    ctrl = horse.get_controller()
    print("horse controller:", ctrl, "is AIController:", isinstance(ctrl, unreal.AIController))
    if isinstance(ctrl, unreal.AIController):
        try:
            ctrl.move_to_location(dest, -1.0, True, True, False, True, None, True)
            print("issued horse move_to_location ->", dest)
        except Exception as e:
            print("move_to_location err:", e)

    print("HORSE_POS_T0", horse.get_actor_location())
    print("DEST", dest)
