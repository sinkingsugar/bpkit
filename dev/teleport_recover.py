import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if world is None:
    print("NO PIE"); raise SystemExit
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn()
print("player was at:", pawn.get_actor_location())

# pick a safe target: a PlayerStart if present, else origin lifted high so they drop to ground
target = None
starts = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PlayerStart)
if starts:
    target = starts[0].get_actor_location()
    print("using PlayerStart at:", target)
else:
    target = unreal.Vector(0.0, 0.0, 2000.0)
    print("no PlayerStart -> using origin high:", target)

# teleport the player
pawn.set_actor_location(target, False, True)

# teleport every ConanCharacter (horses + followers) in a ring around the target
import math
others = [c for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter) if c != pawn]
for i, c in enumerate(others):
    ang = (i / max(1, len(others))) * 2.0 * math.pi
    off = unreal.Vector(target.x + 300.0 * math.cos(ang), target.y + 300.0 * math.sin(ang), target.z + 100.0)
    c.set_actor_location(off, False, True)
print("teleported player + %d others to safety" % len(others))
print("player now at:", pawn.get_actor_location())
