import unreal
def call(o, n, *a):
    try: return getattr(o, n)(*a)
    except Exception as e: return "ERR(%s)" % str(e)[:60]

# 1) inspect the existing horse montage's slot(s)
mv = unreal.load_object(None, "/Game/Characters/humans/animations/mounted/Horse/AM_human_mounted_movement_HORSE.AM_human_mounted_movement_HORSE")
print("movement montage:", mv.get_name() if mv else None)
try:
    tracks = mv.get_editor_property("slot_anim_tracks")
    print("  slots:", [str(t.get_editor_property("slot_name")) for t in tracks])
except Exception as e:
    print("  slot read ERR:", e)

# 2) create a montage from the seated IDLE sequence
idle = unreal.load_object(None, "/Game/Characters/humans/animations/mounted/Horse/A_human_mounted_idle_HORSE.A_human_mounted_idle_HORSE")
print("\nidle seq:", idle.get_name() if idle else None)
at = unreal.AssetToolsHelpers.get_asset_tools()
made = None
try:
    factory = unreal.AnimMontageFactory()
    print("factory:", factory)
    if hasattr(factory, "set_editor_property"):
        try: factory.set_editor_property("source_animation", idle)
        except Exception as e: print("  set source_animation:", e)
    pkg = "/Game/_Scratch"
    if unreal.EditorAssetLibrary.does_asset_exist(pkg + "/AM_MF_idle_HORSE"):
        unreal.EditorAssetLibrary.delete_asset(pkg + "/AM_MF_idle_HORSE")
    made = at.create_asset("AM_MF_idle_HORSE", pkg, unreal.AnimMontage, factory)
    print("created montage:", made)
    if made:
        tr = made.get_editor_property("slot_anim_tracks")
        print("  new montage slots:", [str(t.get_editor_property("slot_name")) for t in tr])
        unreal.EditorAssetLibrary.save_asset(pkg + "/AM_MF_idle_HORSE")
except Exception as e:
    print("create ERR:", e)
