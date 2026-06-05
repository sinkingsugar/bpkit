import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def by_tag(t):
    a = unreal.GameplayStatics.get_all_actors_with_tag(world, t); return a[0] if a else None
rider = by_tag("TEST_RIDER"); horse = by_tag("TEST_HORSE")
mesh = rider.get_editor_property("mesh")
hmesh = horse.get_editor_property("mesh")

# Detach the ACTOR (capsule) from the horse, then attach the MESH root to attachrider
rider.detach_from_actor(unreal.DetachmentRule.KEEP_WORLD, unreal.DetachmentRule.KEEP_WORLD, unreal.DetachmentRule.KEEP_WORLD)
mesh.attach_to_component(hmesh, "attachrider",
    unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET,
    unreal.AttachmentRule.KEEP_WORLD, False)
print("mesh attached to attachrider. mesh world loc:", mesh.get_world_location())
print("horse mesh socket loc:", hmesh.get_socket_location("attachrider"))
# Anim still single-node looping from before; reassert just in case
print("anim mode:", mesh.get_animation_mode())
print("done - rider MESH root snapped to attachrider socket")
