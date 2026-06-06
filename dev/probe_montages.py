import unreal
ar = unreal.AssetRegistryHelpers.get_asset_registry()
hits = []
for a in ar.get_all_assets():
    cn = str(a.asset_class_path.asset_name) if hasattr(a, "asset_class_path") else ""
    nm = str(a.asset_name)
    if cn == "AnimMontage" and any(k in nm.lower() for k in ("mount", "horse", "ride", "rider", "sit", "saddle")):
        hits.append("%s  @ %s" % (nm, str(a.package_name)))
print("=== mounted/horse AnimMontages ===", len(hits))
for h in hits[:40]:
    print("  ", h)
# also: any montage whose path is under the mounted anim folder
print("\n=== montages under .../mounted/ ===")
for a in ar.get_all_assets():
    cn = str(a.asset_class_path.asset_name) if hasattr(a, "asset_class_path") else ""
    if cn == "AnimMontage" and "mounted" in str(a.package_name).lower():
        print("  ", a.asset_name, "@", a.package_name)
