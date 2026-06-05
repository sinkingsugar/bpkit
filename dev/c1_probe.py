"""Pin down the few authoring primitives C1 needs."""
import unreal

print("=== add_member_variable signature ===")
print(unreal.BlueprintEditorLibrary.add_member_variable.__doc__)

print("\n=== ConanCharacter class chain (is it a Character -> GetMesh valid?) ===")
cc = unreal.ConanCharacter
print("ConanCharacter is Character subclass:", issubclass(cc, unreal.Character))
print("ConanCharacter is Pawn subclass:", issubclass(cc, unreal.Pawn))

print("\n=== mounted-idle anim full path ===")
ar = unreal.AssetRegistryHelpers.get_asset_registry()
anims = ar.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "AnimSequence"),
                               search_sub_classes=True)
for a in anims:
    nm = str(a.asset_name)
    if nm == "A_human_mounted_idle_HORSE":
        print("FOUND:", str(a.package_name) + "." + nm)
        break
else:
    # fallback: any mounted idle horse
    for a in anims:
        nm = str(a.asset_name).lower()
        if "mounted" in nm and "idle" in nm and "horse" in nm:
            print("fallback:", str(a.package_name) + "." + str(a.asset_name))
            break

print("\n=== how to express EAnimationMode + EAttachmentRule enum defaults ===")
print("AnimationMode SINGLE_NODE int:", int(unreal.AnimationMode.ANIMATION_SINGLE_NODE))
print("AttachmentRule SNAP_TO_TARGET int:", int(unreal.AttachmentRule.SNAP_TO_TARGET))
# byte/enum pins in node text usually take the UENUM display name as DefaultValue:
print("enum display names: 'AnimationSingleNode', 'SnapToTarget' (typical K2 byte-pin default)")
