import unreal
EAL = unreal.EditorAssetLibrary
print("=== /Game/_Scratch contents ===")
for a in EAL.list_assets("/Game/_Scratch", recursive=True, include_folder=False):
    print("  ", a)
# recompile the manager to confirm clean
print("\n=== recompile manager ===")
mgr = unreal.load_object(None, "/Game/_Scratch/BP_MountedFollowerManager.BP_MountedFollowerManager")
unreal.BlueprintEditorLibrary.compile_blueprint(mgr)
print("manager recompiled (no exception = compiled)")
