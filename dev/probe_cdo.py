"""Inspect CDO defaults + components of the mount pawn, a pet, and a thrall to
understand AI control, mountability, saddle/seat sockets, and follow wiring.

    python ue_run.py dev/probe_cdo.py
"""
import unreal


def gc(path):
    """Load the BlueprintGeneratedClass for an asset path (.._C)."""
    bp = unreal.load_asset(path)
    if not bp:
        return None
    # generated class object path is path + "_C"
    cls = unreal.load_object(None, path + "_C")
    return cls


def show(path, props):
    print("\n" + "=" * 72)
    print("CDO:", path)
    cls = gc(path)
    if not cls:
        print("  !! no class")
        return
    cdo = unreal.get_default_object(cls)
    for p in props:
        try:
            v = cdo.get_editor_property(p)
            print("  %-32s = %s" % (p, v))
        except Exception as e:
            print("  %-32s ERR %s" % (p, str(e)[:50]))
    # components via SimpleConstructionScript not easily reachable; list subobjects
    try:
        comps = cdo.get_components_by_class(unreal.ActorComponent)
        print("  -- components (%d):" % len(comps))
        for c in comps:
            print("      ", c.get_class().get_name(), c.get_name())
    except Exception as e:
        print("  (components err:", e, ")")


COMMON = ["ai_controller_class", "auto_possess_ai", "is_mountable", "is_mount",
          "is_pet", "is_thrall", "is_companion", "net_load_on_client"]

show("/Game/Characters/NPCs/Hooved_Wild/Blueprints/BP_NPC_Mounts_Horse",
     COMMON + ["mount_input", "should_unequip_offhand_when_mounting"])
show("/Game/Characters/NPCs/Bear/Blueprints/BP_NPC_Wildlife_Bear_Brown_pet", COMMON)
show("/Game/Characters/NPCs/Necromancy_followers/Blueprints/BP_FiniteLifespanUndeadThrall", COMMON)

# Find the AI controller classes used for followers + their behavior trees
print("\n\n###### AI controller / behavior-tree assets ######")
ar = unreal.AssetRegistryHelpers.get_asset_registry()
bps = ar.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "Blueprint"), search_sub_classes=True)
for a in bps:
    n = str(a.asset_name).lower()
    if ("aicontroller" in n or "ai_controller" in n or n.startswith("aic_")
            or "controller" in n and ("thrall" in n or "follow" in n or "pet" in n or "npc" in n or "mount" in n)):
        print("  AIC", a.package_name, a.asset_name)
