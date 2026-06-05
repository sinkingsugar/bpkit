import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def find(cn):
    for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        if cn in a.get_class().get_name(): return a
def tag(t):
    a = unreal.GameplayStatics.get_all_actors_with_tag(world, t); return a[0] if a else None
mgr, rider = find("BP_MF_Recipe"), tag("TEST_RIDER")
rmesh = rider.get_editor_property("mesh")
anim = mgr.get_editor_property("MountIdleAnim")

print("mesh class:", rmesh.get_class().get_name())
print("anim/budget/tick/visibility members:")
for m in sorted(dir(rmesh)):
    if any(k in m.lower() for k in ("budget", "visibility_based", "anim_tick", "set_animation",
                                    "play_anim", "update_rate", "tick_pose", "force")):
        if not m.startswith("__"):
            print("   ", m)

# try: force always-tick + re-play, see if anim_to_play populates
try:
    rmesh.set_editor_property("visibility_based_anim_tick_option",
        unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
    print("set visibility_based_anim_tick_option = ALWAYS")
except Exception as e:
    print("vis tick err:", str(e).splitlines()[-1][:70])
rmesh.set_component_tick_enabled(True)
rmesh.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
rmesh.play_animation(anim, True)
ad = rmesh.get_editor_property("animation_data")
print("after force+play -> anim_to_play:", ad.get_editor_property("anim_to_play"))
