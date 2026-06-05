"""Adaptive mount test on admin-panel-spawned actors in the LIVE PIE world.

Finds the player, the horse (is_mountable / 'Mount' in class name), and a rider
candidate (nearest other ConanCharacter). Seats the rider via mount(), commands
the horse AI to a destination, and stashes refs (tags) for the re-measure step.

    python ue_run.py dev/mount_test_live.py
"""
import unreal

ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world = ues.get_game_world()
if not world:
    print("!! no game world (Play not running?)"); raise SystemExit
print("world:", world.get_path_name())

player = unreal.GameplayStatics.get_player_pawn(world, 0)
ploc = player.get_actor_location()
print("player:", player.get_name(), "loc:", ploc)

# All ConanCharacters in the world
chars = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter)
others = [c for c in chars if c != player]
print("ConanCharacters (excl. player):", len(others))
for c in others:
    try:
        mountable = c.is_mountable()
    except Exception:
        mountable = "?"
    print("   -", c.get_name(), "class=", c.get_class().get_name(),
          "is_mountable=", mountable, "dist=", int((c.get_actor_location() - ploc).length()))

# Pick the horse = mountable or 'Mount'/'Horse' in class; rider = nearest other non-mount
horse = None
for c in others:
    cn = c.get_class().get_name().lower()
    try:
        if c.is_mountable() or "mount" in cn or "horse" in cn:
            horse = c; break
    except Exception:
        if "mount" in cn or "horse" in cn:
            horse = c; break
riders = [c for c in others if c != horse]
riders.sort(key=lambda c: (c.get_actor_location() - ploc).length())
rider = riders[0] if riders else None
print("\nCHOSEN horse:", horse.get_name() if horse else None,
      "| rider:", rider.get_name() if rider else None)

if not (horse and rider):
    print("!! need both a horse and one other NPC spawned near you. Spawn them and re-run.")
    raise SystemExit

horse.tags = list(horse.tags) + ["TEST_HORSE"]
rider.tags = list(rider.tags) + ["TEST_RIDER"]

# Ensure both have controllers
for a, nm in ((horse, "horse"), (rider, "rider")):
    if not a.get_controller():
        try:
            a.spawn_default_controller()
        except Exception as e:
            print(nm, "ctrl err:", e)
    print(nm, "controller:", a.get_controller())

# Seat the rider
try:
    print("can_mount ->", rider.can_mount(horse), "(None == OK)")
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
except Exception as e:
    print("  link err:", e)

# Command the horse AI to ride to a point ~1500 past the player
nav = unreal.NavigationSystemV1.get_navigation_system(world)
dest = unreal.Vector(ploc.x - 1500, ploc.y, ploc.z)
if nav:
    try:
        p = nav.project_point_to_navigation(dest, unreal.Vector(1200, 1200, 1200))
        if p: dest = p
    except Exception:
        pass
ctrl = horse.get_controller()
print("horse ctrl is AIController:", isinstance(ctrl, unreal.AIController))
if isinstance(ctrl, unreal.AIController):
    try:
        ctrl.move_to_location(dest, -1.0, True, True, False, True, None, True)
        print("issued horse move_to_location ->", dest)
    except Exception as e:
        print("move err:", e)

print("HORSE_POS_T0", horse.get_actor_location())
print("DEST", dest)
