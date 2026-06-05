import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def by_tag(t):
    a = unreal.GameplayStatics.get_all_actors_with_tag(world, t); return a[0] if a else None
rider = by_tag("TEST_RIDER")
print("rider:", rider.get_name() if rider else None)
mesh = rider.get_editor_property("mesh")

# Diagnose modular mesh: how many skeletal mesh comps, which follow a leader
sk_comps = rider.get_components_by_class(unreal.SkeletalMeshComponent)
print("skeletal mesh comps:", len(sk_comps))
leader = mesh
print("leader mesh:", leader.get_name())

# Find a HORSE human mounted idle anim on SK_human_Skeleton
ar = unreal.AssetRegistryHelpers.get_asset_registry()
anims = ar.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine","AnimSequence"), search_sub_classes=True)
horse_idle = None
fallback = None
for a in anims:
    nm = str(a.asset_name).lower()
    if "mounted" in nm and "idle" in nm and "horse" in nm:
        horse_idle = str(a.package_name)+"."+str(a.asset_name); break
    if horse_idle is None and "mounted" in nm and "idle" in nm and "camel" not in nm and fallback is None:
        fallback = str(a.package_name)+"."+str(a.asset_name)
pick = horse_idle or fallback
print("anim pick:", pick)
anim = unreal.load_object(None, pick) if pick else None

# Force single-node on leader + all parts, stop montages, play looping
for comp in sk_comps:
    try:
        ai = comp.get_anim_instance()
        if ai:
            ai.stop_all_montages(0.0)
    except Exception:
        pass
if anim:
    leader.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    leader.play_animation(anim, True)
    print("playing on leader:", anim.get_name())
    # Parts following leader pose should inherit; if a part has its own AnimBP, force single-node too
    for comp in sk_comps:
        if comp == leader:
            continue
        try:
            if comp.get_anim_instance():
                comp.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
                comp.play_animation(anim, True)
        except Exception:
            pass

# --- Pacify: set team id + faction-ish ---
ctrl = rider.get_controller()
print("\npacify: rider/ctrl faction/team methods:")
for obj, nm in ((rider, "rider"), (ctrl, "ctrl")):
    if not obj: continue
    for m in dir(obj):
        if any(k in m.lower() for k in ("faction","team","pacif","aggro","threat","hostil","ally","relationship")):
            print("  ", nm, ".", m)
# Try generic team id = same as player (0)
try:
    if ctrl and hasattr(ctrl, "set_generic_team_id"):
        ctrl.set_generic_team_id(unreal.GenericTeamId(0))
        print("set_generic_team_id(0)")
except Exception as e:
    print("team err:", e)
# Try thrall component pacifist
try:
    tc = rider.get_thrall_component()
    if tc and hasattr(tc, "set_editor_property"):
        tc.set_editor_property("is_pacifist", True)
        print("set thrall is_pacifist=True")
except Exception as e:
    print("pacifist err:", e)
