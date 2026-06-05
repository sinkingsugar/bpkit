import unreal
PATH = "/Game/_Scratch/BP_MountedFollowerManager"
bp = unreal.load_object(None, PATH + "." + PATH.rsplit("/", 1)[-1])
print("loaded:", bp)
# compile and report
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
status = bp.get_editor_property("status")  # EBlueprintStatus
print("BP status enum:", status)
# status: BS_UpToDate=2 good; BS_Error=4 bad; BS_Dirty=1; BS_Unknown=0; BS_UpToDateWithWarnings=3
# Also scan ALL loaded blueprints in _Scratch for error status
print("\n=== _Scratch BP statuses ===")
ar = unreal.AssetRegistryHelpers.get_asset_registry()
for a in ar.get_assets_by_path("/Game/_Scratch", recursive=True):
    cn = str(a.asset_class_path.asset_name) if hasattr(a, "asset_class_path") else "?"
    if "Blueprint" in cn:
        obj = a.get_asset()
        try:
            st = obj.get_editor_property("status")
        except Exception:
            st = "n/a"
        print("  ", a.asset_name, "->", st)
