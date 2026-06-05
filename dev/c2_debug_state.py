import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn()

mount = pawn.get_mount()
print("=== ACTUAL player mount state ===")
print("pawn.get_mount():", mount.get_name() if mount else None)
print("pawn.is_mountable():", pawn.is_mountable() if hasattr(pawn,'is_mountable') else '?')
# which char (if any) reports the player as its rider?
for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter):
    try:
        r = c.get_rider()
    except Exception:
        r = None
    if r == pawn:
        print("  ", c.get_class().get_name(), "has player as RIDER")

print("\n=== manager state ===")
for m in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
    if "MountedFollowerManager" in m.get_class().get_name():
        print(m.get_name(), "| Initialized:", m.get_editor_property("Initialized"),
              "| WasMounted:", m.get_editor_property("WasMounted"))

print("\n=== what IsValid(GetMount) would evaluate to ===")
print("GetMount valid?:", mount is not None)
print("(if you are mounted right now but get_mount() is None -> that's the detection bug)")
