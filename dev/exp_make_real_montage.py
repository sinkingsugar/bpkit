import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def call(o, n, *a):
    try: return getattr(o, n)(*a)
    except Exception as e: return "ERR(%s)" % str(e)[:50]
pc = unreal.GameplayStatics.get_player_controller(world, 0)
host = pc.get_controlled_pawn()
tsc = host.get_thrall_system_component()
hum = next((f for f in tsc.get_following_thrall_characters() if not f.is_mountable()), None)
if hum:
    mesh = hum.get_editor_property("Mesh")
    mesh.set_animation_mode(unreal.AnimationMode.ANIMATION_BLUEPRINT)
    anim = mesh.get_anim_instance()
    idle = unreal.load_object(None, "/Game/Characters/humans/animations/mounted/Horse/A_human_mounted_idle_HORSE.A_human_mounted_idle_HORSE")
    # transient montage that already has the Fullbody3rd slot baked in
    dyn = call(anim, "play_slot_animation_as_dynamic_montage", idle, "Fullbody3rd", 0.25, 0.25, 1.0, 1)
    print("dynamic montage:", dyn, "| group:", call(dyn, "get_group_name"))
    # duplicate the transient montage into a REAL saved asset (slot carries over)
    at = unreal.AssetToolsHelpers.get_asset_tools()
    dest = "/Game/_Scratch"
    if unreal.EditorAssetLibrary.does_asset_exist(dest + "/AM_MF_idle_FB"):
        unreal.EditorAssetLibrary.delete_asset(dest + "/AM_MF_idle_FB")
    real = call(at, "duplicate_asset", "AM_MF_idle_FB", dest, dyn)
    print("real asset:", real)
    if real and "ERR" not in str(real):
        print("  group_name:", call(real, "get_group_name"), "| is_dynamic:", call(real, "is_dynamic_montage"))
        unreal.EditorAssetLibrary.save_asset(dest + "/AM_MF_idle_FB")
        print("  saved -> /Game/_Scratch/AM_MF_idle_FB")
