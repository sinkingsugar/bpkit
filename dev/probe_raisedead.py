import unreal
def line(*a): unreal.log(" ".join(str(x) for x in a))
ar = unreal.AssetRegistryHelpers.get_asset_registry()

def tags(path, name, keys):
    ad = ar.get_asset_by_object_path("%s.%s" % (path, name))
    line("\n=== %s ===" % path)
    for t in keys:
        v = ad.get_tag_value(t) if ad else None
        if v:
            line("  %-22s %s" % (t, v))

K = ["ParentClass", "NativeParentClass", "BlueprintType", "NumReplicatedProperties"]
tags("/Game/Sorcery/Rituals/BP_RItual_RaiseDead", "BP_RItual_RaiseDead", K)

# the spawned undead - find BP_NecromancyZombie_Main
zomb = [a for a in ar.get_assets_by_path("/Game", recursive=True)
        if "NecromancyZombie" in str(a.asset_name) or "Necromancy" in str(a.asset_name)]
line("\n=== Necromancy assets (%d) ===" % len(zomb))
for a in zomb[:25]:
    line("  ", a.asset_name, "  ", a.package_name)

tags("/Game/Systems/Necromancy/BP_NecromancyZombie_Main",
     "BP_NecromancyZombie_Main", K)  # path guessed; real one printed above
