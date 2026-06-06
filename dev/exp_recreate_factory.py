import unreal
def call(o, n, *a):
    try: return getattr(o, n)(*a)
    except Exception as e: return "ERR(%s)" % str(e)[:50]
idle = unreal.load_object(None, "/Game/Characters/humans/animations/mounted/Horse/A_human_mounted_idle_HORSE.A_human_mounted_idle_HORSE")
at = unreal.AssetToolsHelpers.get_asset_tools()
dest = "/Game/_Scratch"
factory = unreal.AnimMontageFactory()
factory.set_editor_property("source_animation", idle)
if unreal.EditorAssetLibrary.does_asset_exist(dest + "/AM_MF_idle_HORSE"):
    unreal.EditorAssetLibrary.delete_asset(dest + "/AM_MF_idle_HORSE")
m = at.create_asset("AM_MF_idle_HORSE", dest, unreal.AnimMontage, factory)
print("created:", m)
print("  play_length:", call(m, "get_play_length"))
print("  slot names:", call(unreal.AnimationLibrary, "get_montage_slot_names", m))
unreal.EditorAssetLibrary.save_asset(dest + "/AM_MF_idle_HORSE")
print("saved -> /Game/_Scratch/AM_MF_idle_HORSE (has the idle content; slot needs -> Fullbody3rd)")
