"""Re-stow the dancer, then diagnose WHY the pose is wrong: skeleton match,
animation mode, relative transform, world rotation vs socket."""
import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def find(cn):
    for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        if cn in a.get_class().get_name():
            return a
    return None
def tag(t):
    a = unreal.GameplayStatics.get_all_actors_with_tag(world, t); return a[0] if a else None
mgr, rider, horse = find("BP_MF_Recipe"), tag("TEST_RIDER"), tag("TEST_HORSE")
if not (mgr and rider and horse):
    print("missing:", mgr, rider, horse); raise SystemExit

mgr.call_method("Stow")
print(">>> re-stowed")

rmesh = rider.get_editor_property("mesh")
hmesh = horse.get_editor_property("mesh")

# skeleton match?
def skel_of(comp):
    sk = comp.get_editor_property("skeletal_mesh")
    return sk.get_editor_property("skeleton") if sk else None
rsk = skel_of(rmesh)
anim = mgr.get_editor_property("MountIdleAnim")
ask = anim.get_editor_property("skeleton") if anim else None
print("rider skeleton:", rsk.get_name() if rsk else None)
print("anim  skeleton:", ask.get_name() if ask else None)
print("skeleton MATCH:", rsk == ask)

# anim mode + what single-node anim is actually set to play
print("animation_mode:", rmesh.get_editor_property("animation_mode"))
try:
    adata = rmesh.get_editor_property("animation_data")  # FSingleAnimationPlayData
    print("anim_to_play:", adata.get_editor_property("anim_to_play"))
    print("looping     :", adata.get_editor_property("looping"))
    print("playing     :", adata.get_editor_property("playing"))
except Exception as e:
    print("animation_data err:", str(e).splitlines()[-1][:70])

# transforms via Transform (Budgeted lacks the scalar getters)
rt = rmesh.get_relative_transform()
wt = rmesh.get_world_transform()
st = hmesh.get_socket_transform("attachrider")
print("mesh REL loc:", rt.translation, "| REL rot:", rt.rotation.rotator())
print("mesh WORLD rot:", wt.rotation.rotator())
print("socket WORLD rot:", st.rotation.rotator())
