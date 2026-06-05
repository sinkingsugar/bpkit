"""Raise the 'Mount' group cap and inspect how the existing horse follows, so we
can wire a 2nd one. Step 1 of the live multi-horse proof."""
import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn()
tsc = pawn.get_thrall_system_component()

print("before:", tsc.get_follower_group_counts())
tsc.add_thrall_group_limit_adjustment("Mount", 5)
print("added +5 to Mount cap")
print("after :", tsc.get_follower_group_counts())
print("num in Mount group:", tsc.get_number_following_thralls_in_group("Mount", False, False))

# inspect the existing following horse: what wires it to the player?
horse = None
for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter):
    if "Mounts_Horse" in c.get_class().get_name():
        horse = c; break
print("\nexisting horse:", horse.get_name() if horse else None)
if horse:
    print("  followed PC == player PC:", horse.get_followed_player_controller() == pc)
    ffc = horse.get_my_formation_follower_component() if hasattr(horse, "get_my_formation_follower_component") else None
    print("  formation follower comp:", ffc.get_class().get_name() if ffc else None)
    print("  is_formation_follower:", horse.is_formation_follower() if hasattr(horse, "is_formation_follower") else "?")

# how does a thrall get registered as following? signatures
for m in ("initialize_spawned_thrall", "post_initialize_spawned_thrall", "spawn_thrall",
          "can_thrall_start_following"):
    f = getattr(tsc, m, None)
    print("\n%s:" % m, (f.__doc__ or "?").split("\n\n")[0] if f else "MISSING")
