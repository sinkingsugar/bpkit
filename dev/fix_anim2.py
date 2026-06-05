import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def by_tag(t):
    a = unreal.GameplayStatics.get_all_actors_with_tag(world, t); return a[0] if a else None
rider = by_tag("TEST_RIDER")
mesh = rider.get_editor_property("mesh")
print("rider:", rider.get_name())

# RE-ENABLE the mesh tick (was disabled in the freeze -> anim couldn't evaluate)
mesh.set_component_tick_enabled(True)
rider.set_actor_tick_enabled(True)   # actor tick can drive anim too; movement comp stays disabled below

# Pick a passive horse mounted idle (fallback to combat idle)
ar = unreal.AssetRegistryHelpers.get_asset_registry()
anims = ar.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine","AnimSequence"), search_sub_classes=True)
passive=None; combat=None
for a in anims:
    nm=str(a.asset_name).lower()
    if "mounted" in nm and "idle" in nm and "horse" in nm:
        full=str(a.package_name)+"."+str(a.asset_name)
        if "combat" in nm: combat=combat or full
        else: passive=passive or full
pick = passive or combat
print("anim:", pick)
anim = unreal.load_object(None, pick)
mesh.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
mesh.play_animation(anim, True)
print("animation_mode now:", mesh.get_animation_mode())
print("mesh tick enabled:", mesh.is_component_tick_enabled())

# Make sure movement stays dead (don't reintroduce pulling)
mc = rider.get_editor_property("character_movement")
mc.disable_movement(); mc.set_component_tick_enabled(False); mc.set_active(False, False)
# capsule collision stays off
caps = rider.get_editor_property("capsule_component")
caps.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
print("done: mesh animates, movement/capsule stay disabled")
