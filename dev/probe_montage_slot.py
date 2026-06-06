import unreal
def call(o, n, *a):
    try: return getattr(o, n)(*a)
    except Exception as e: return "ERR(%s)" % str(e)[:50]
m = unreal.load_object(None, "/Game/_Scratch/AM_MF_idle_HORSE.AM_MF_idle_HORSE")
print("montage:", m)
# slot-related properties/methods
print("slot-ish attrs:", [a for a in dir(m) if any(k in a.lower() for k in ("slot","track","group"))][:15])
for p in ("slot_anim_tracks", "slots", "slot_name", "group_name", "anim_montage_slot"):
    print("  get_editor_property(%s):" % p, call(m, "get_editor_property", p))
# montage-editing libraries?
print("\nlibs:", [n for n in dir(unreal) if "montage" in n.lower() or n in ("AnimationLibrary",)][:10])
fac = unreal.AnimMontageFactory()
print("factory slot-ish props:", [a for a in dir(fac) if any(k in a.lower() for k in ("slot","source","preview"))][:10])
# existing game full-body montage to clone? find one on Fullbody3rd via an emote/dance montage
ar = unreal.AssetRegistryHelpers.get_asset_registry()
far = unreal.ARFilter(class_names=["AnimMontage"], recursive_classes=True,
                      package_paths=["/Game/Characters/humans/animations"], recursive_paths=True)
ms = ar.get_assets(far)
print("\nhuman montages sample:", [str(a.asset_name) for a in ms[:8]], "... total", len(ms))
