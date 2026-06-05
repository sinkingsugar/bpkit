import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def by_tag(t):
    a = unreal.GameplayStatics.get_all_actors_with_tag(world, t); return a[0] if a else None
horse = by_tag("TEST_HORSE"); rider = by_tag("TEST_RIDER")
print("rider.get_mount():", rider.get_mount())
print("horse.get_rider():", horse.get_rider())
print("rider attach parent:", rider.get_attach_parent_actor())
print("rider loc:", rider.get_actor_location(), " horse loc:", horse.get_actor_location())
