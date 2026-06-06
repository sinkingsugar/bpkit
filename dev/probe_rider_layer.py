import unreal
ar = unreal.AssetRegistryHelpers.get_asset_registry()
# everything under Mounts_v2
print("=== /Game/Systems/Mounts_v2 contents ===")
for a in ar.get_assets_by_path("/Game/Systems/Mounts_v2", recursive=True):
    print("  [%s] %s" % (str(a.asset_class_path.asset_name) if hasattr(a,'asset_class_path') else a.asset_class, str(a.asset_name)))
# human-skeleton AnimBPs named like rider/mount/sit
print("\n=== human-skeleton AnimBPs (rider/mount/sit/seat in name) ===")
far = unreal.ARFilter(class_names=["AnimBlueprint"], recursive_classes=True)
for a in ar.get_assets(far):
    nm = str(a.asset_name).lower()
    if any(k in nm for k in ("rider", "mount", "sit", "seat", "ride")):
        abp = unreal.load_object(None, "%s.%s" % (str(a.package_name), str(a.asset_name)))
        ts = abp.get_editor_property("target_skeleton") if abp else None
        tsn = ts.get_name() if ts else "?"
        if "human" in tsn.lower():
            print("  HUMAN:", str(a.package_name) + "." + str(a.asset_name), "skel=", tsn)
