import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
player = unreal.GameplayStatics.get_player_pawn(world, 0)
def by_tag(t):
    a = unreal.GameplayStatics.get_all_actors_with_tag(world, t); return a[0] if a else None
horse = by_tag("TEST_HORSE")
print("=== player-mounted control snapshot ===")
print("player:", player.get_name())
print("player.get_mount():", player.get_mount())
print("player attach parent:", player.get_attach_parent_actor())
if horse:
    print("tagged horse.get_rider():", horse.get_rider())
# Also scan ALL mounts for a rider (the player may be on a different horse)
for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter):
    try:
        r = c.get_rider()
        if r:
            print("MOUNT", c.get_name(), "has RIDER", r.get_name(),
                  "| is_mountable", c.is_mountable(), "saddle", c.get_embedded_saddle_id())
    except Exception:
        pass
