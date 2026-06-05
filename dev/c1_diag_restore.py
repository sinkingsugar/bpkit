import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def find(cn):
    for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        if cn in a.get_class().get_name(): return a
def tag(t):
    a = unreal.GameplayStatics.get_all_actors_with_tag(world, t); return a[0] if a else None
mgr, rider = find("BP_MF_Recipe"), tag("TEST_RIDER")
rmesh = rider.get_editor_property("mesh")
cap = rider.get_editor_property("capsule_component")

saved = mgr.get_editor_property("SavedMeshXform")
print("SavedMeshXform:", saved.translation, "| rot", saved.rotation.rotator())
relt = rmesh.get_relative_transform()
print("mesh REL now  :", relt.translation, "| rot", relt.rotation.rotator())
print("match saved?  :", saved.translation.equals(relt.translation, 1.0))

# what's the DEFAULT (class CDO) mesh relative transform for this NPC?
cdo = unreal.get_default_object(rider.get_class())
cmesh = cdo.get_editor_property("mesh") if cdo else None
if cmesh:
    try:
        ct = cmesh.get_relative_transform()
        print("CDO mesh REL  :", ct.translation, "| rot", ct.rotation.rotator())
    except Exception as e:
        print("cdo rel err:", str(e).splitlines()[-1][:50])

print("mesh attach parent comp:", rmesh.get_attach_parent())
print("cap world loc :", cap.get_world_location())
print("mesh world loc:", rmesh.get_world_location())
