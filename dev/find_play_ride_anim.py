"""Find a mounted/riding AnimSequence matching the rider's skeleton and play it on
the rider mesh (overrides AnimBP -> static seated pose). Also pacify the rider."""
import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def by_tag(t):
    a = unreal.GameplayStatics.get_all_actors_with_tag(world, t); return a[0] if a else None
rider = by_tag("TEST_RIDER")
print("rider:", rider.get_name() if rider else None)
if not rider:
    print("!! no rider"); raise SystemExit
mesh = rider.get_editor_property("mesh")
skel = None
try:
    sk_asset = mesh.get_editor_property("skeletal_mesh")
    skel = sk_asset.get_editor_property("skeleton") if sk_asset else None
except Exception as e:
    print("skel err:", e)
print("rider skeleton:", skel.get_name() if skel else None)

# Search AnimSequences whose name hints at riding; prefer same skeleton + idle/loop
ar = unreal.AssetRegistryHelpers.get_asset_registry()
anims = ar.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "AnimSequence"), search_sub_classes=True)
KW = ["mounted", "ride", "rider", "riding", "horse", "saddle", "mount"]
cands = []
for a in anims:
    nm = str(a.asset_name).lower()
    if any(k in nm for k in KW):
        cands.append(a)
print("ride-name anim candidates:", len(cands))

# rank: same skeleton first, then 'idle'/'loop' in name
def score(a):
    nm = str(a.asset_name).lower()
    s = 0
    if "idle" in nm or "loop" in nm: s += 2
    if "player" in str(a.package_name).lower() or "humanoid" in str(a.package_name).lower(): s += 1
    return -s
cands.sort(key=score)

chosen = None
for a in cands[:60]:
    full = str(a.package_name) + "." + str(a.asset_name)
    seq = unreal.load_object(None, full)
    if not seq:
        continue
    aseskel = seq.get_editor_property("skeleton")
    match = (aseskel == skel)
    print("  cand:", a.asset_name, "| skel_match=", match)
    if match and chosen is None:
        chosen = seq
        print("   -> CHOSEN:", a.asset_name)
        break

if chosen:
    mesh.play_animation(chosen, True)   # loop
    print("playing animation:", chosen.get_name())
else:
    print("no skeleton-matching ride anim found; listing first 15 names for manual pick:")
    for a in cands[:15]:
        print("   ", a.package_name, a.asset_name)

# Pacify: stop brain again + mark pacifist if possible
ctrl = rider.get_controller()
if ctrl:
    bc = ctrl.get_editor_property("brain_component")
    if bc:
        try: bc.stop_logic("stowed"); print("brain stopped")
        except Exception as e: print("brain err:", e)
