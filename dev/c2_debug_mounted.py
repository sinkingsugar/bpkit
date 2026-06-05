"""Capture the follower list WHILE the player is mounted -- distinguishes
'followers vanish while mounted' (array empty -> loop has nothing) from
'loop doesn't iterate' (array has the dancer but no STOW)."""
import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn()
mount = pawn.get_mount()
print("MOUNTED?:", mount is not None, "| mount:", mount.get_name() if mount else None)
tsc = pawn.get_thrall_system_component()
chars = tsc.get_following_thrall_characters()
print("following count WHILE MOUNTED:", len(chars))
for c in chars:
    print("  ", c.get_class().get_name(), "| is_mount:", c.get_editor_property("is_mount"))
print("group counts:", tsc.get_follower_group_counts())
if mount is None:
    print(">> NOT mounted -- get on a horse and stay seated, then re-run")
elif not chars:
    print(">> CONFIRMED: followers vanish while mounted (array empty at loop time)")
else:
    nonmount = [c for c in chars if not c.get_editor_property("is_mount")]
    print(">> followers present while mounted, non-mounts:", len(nonmount),
          "-> if no STOW logged, the LOOP itself isn't iterating")
