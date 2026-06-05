import unreal

ar = unreal.AssetRegistryHelpers.get_asset_registry()

PKGS = [
    "/Game/Characters/MountFunctionLibrary",
    "/Game/Characters/NPCs/Hooved_Wild/Blueprints/BP_NPC_Mounts_Horse",
    "/Game/Characters/NPCs/Hooved_Wild/Blueprints/BP_NPC_Mounts_Camel",
    "/Game/Characters/NPCs/Bear/Blueprints/BP_NPC_Wildlife_Bear_Brown_pet",
    "/Game/Characters/NPCs/Necromancy_followers/Blueprints/BP_FiniteLifespanUndeadThrall",
]

for pkg in PKGS:
    print("\n=== %s ===" % pkg)
    datas = ar.get_assets_by_package_name(pkg)
    if not datas:
        print("  (none)")
        continue
    for d in datas:
        cn = str(d.asset_class_path.asset_name) if hasattr(d, "asset_class_path") else "?"
        print("  asset:", d.asset_name, " class:", cn)
        for tag in ["ParentClass", "NativeParentClass", "GeneratedClass", "NumReplicatedProperties", "BlueprintType"]:
            try:
                v = d.get_tag_value(tag)
                if v:
                    print("       %-20s = %s" % (tag, v))
            except Exception as e:
                pass
