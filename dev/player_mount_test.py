import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
player = unreal.GameplayStatics.get_player_pawn(world, 0)
def by_tag(t):
    a = unreal.GameplayStatics.get_all_actors_with_tag(world, t); return a[0] if a else None
horse = by_tag("TEST_HORSE")
print("horse:", horse.get_name() if horse else None, "class:", horse.get_class().get_name() if horse else None)
print("horse.is_mountable():", horse.is_mountable())
print("horse embedded_saddle_id:", horse.get_embedded_saddle_id())
print("player.can_mount(horse):", player.can_mount(horse), "(None==OK)")
player.mount(horse)
print("called player.mount(horse)")
print("  player.get_mount():", player.get_mount())
print("  horse.get_rider():", horse.get_rider())
print("  player attach parent:", player.get_attach_parent_actor())
