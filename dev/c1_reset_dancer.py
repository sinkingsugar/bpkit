"""Reset the corrupted dancer's mesh to its class-default relative transform, so we
can re-test a CLEAN single Stow->Restore cycle."""
import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def tag(t):
    a = unreal.GameplayStatics.get_all_actors_with_tag(world, t); return a[0] if a else None
rider = tag("TEST_RIDER")
rmesh = rider.get_editor_property("mesh")
cap = rider.get_editor_property("capsule_component")

cdo = unreal.get_default_object(rider.get_class())
cmesh = cdo.get_editor_property("mesh")
ct = cmesh.get_relative_transform()
print("CDO default mesh REL:", ct.translation, "| rot", ct.rotation.rotator())

# make sure mesh is parented to the capsule, then apply default offset
rmesh.attach_to_component(cap, "", unreal.AttachmentRule.KEEP_WORLD,
    unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
rmesh.set_relative_transform(ct, False, False)
print("reset dancer mesh to default offset -> she should stand normally now")
print("mesh REL after reset:", rmesh.get_relative_transform().translation)
