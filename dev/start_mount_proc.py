import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def by_tag(t):
    a = unreal.GameplayStatics.get_all_actors_with_tag(world, t); return a[0] if a else None
horse = by_tag("TEST_HORSE"); rider = by_tag("TEST_RIDER")
player = unreal.GameplayStatics.get_player_pawn(world, 0)
print("horse:", horse.get_name(), "rider:", rider.get_name() if rider else None)
# Move rider right next to the horse's mounting spot first
spot = horse.get_closest_mounting_spot(rider)
print("closest mounting spot:", spot)
rider.set_actor_location(spot, False, False)
# Kick the real mount process on the AI rider
r = rider.bp_start_mount_process_client(horse)
print("rider.bp_start_mount_process_client(horse) ->", r)
print("immediate rider.get_mount():", rider.get_mount(), " horse.get_rider():", horse.get_rider())
