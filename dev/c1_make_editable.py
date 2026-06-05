"""Make BP_MF_Recipe's Rider/Mount/MountIdleAnim instance-editable (so Python/the
poller can set them on a spawned instance), recompile + save. The graph is already
built & correct — this only flips the edit flags. Run with PIE STOPPED."""
import unreal
bp = unreal.load_asset("/Game/_Scratch/BP_MF_Recipe")
print("loaded:", bp.get_name() if bp else None)
for vn in ("Rider", "Mount", "MountIdleAnim"):
    ok = unreal.BlueprintEditorLibrary.set_blueprint_variable_instance_editable(bp, vn, True)
    print("instance_editable", vn, "->", ok)
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
unreal.EditorAssetLibrary.save_asset("/Game/_Scratch/BP_MF_Recipe")
print("compiled + saved")
