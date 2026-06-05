import unreal
def line(*a): unreal.log(" ".join(str(x) for x in a))

ar = unreal.AssetRegistryHelpers.get_asset_registry()

def tags(pkg, name):
    ad = ar.get_asset_by_object_path("%s.%s" % (pkg, name))
    line("\n=== %s ===" % pkg)
    for t in ["ParentClass", "NativeParentClass", "BlueprintType",
              "NumReplicatedProperties", "ClassFlags"]:
        v = ad.get_tag_value(t) if ad else None
        if v:
            line("  %-22s %s" % (t, v))

tags("/Game/Characters/Corpse", "Corpse")
tags("/Game/Sorcery/Rituals/BP_Ritual_RecallCorpse", "BP_Ritual_RecallCorpse")

# CorpseType enum
ct = unreal.load_asset("/Game/Characters/CorpseType")
line("\nCorpseType:", type(ct).__name__)
try:
    for i in range(ct.num_enums() - 1):  # last is _MAX
        line("  ", ct.get_name_by_index(i))
except Exception as e:
    line("  err:", e)
