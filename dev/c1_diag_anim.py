import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def find(cn):
    for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        if cn in a.get_class().get_name(): return a
def tag(t):
    a = unreal.GameplayStatics.get_all_actors_with_tag(world, t); return a[0] if a else None
mgr, rider = find("BP_MF_Recipe"), tag("TEST_RIDER")
rmesh = rider.get_editor_property("mesh")

mgr.call_method("Stow")
ad = rmesh.get_editor_property("animation_data")
print("after BP Stow  -> anim_to_play:", ad.get_editor_property("anim_to_play"))

anim = mgr.get_editor_property("MountIdleAnim")
print("MountIdleAnim on mgr instance:", anim.get_name() if anim else None)

# manual play, same as the proven §8 python path
rmesh.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
rmesh.play_animation(anim, True)
ad2 = rmesh.get_editor_property("animation_data")
print("after manual play -> anim_to_play:", ad2.get_editor_property("anim_to_play"))
