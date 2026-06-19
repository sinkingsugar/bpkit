"""Shigawire recon, detail pass -- READ-ONLY (dir()/__doc__/parent_class property
reads; no UFunction calls, no PIE). Tightens the three things 00_recon.py left fuzzy:

  A. ConanCharacterMovementComponent -- grep the BOUND TYPE (00_recon mistakenly
     dir()'d the get_class() UClass object, which lists Class wrapper attrs, not the
     reflected methods). Confirm add_impulse/add_force/velocity on the Conan subclass.
  B. Stagger / stun / knockout / knockback -- discover the arg types & buff classes
     (is add_stagger's param a float/enum/struct? is there a stun/knockout buff BP?).
  C. Thrown-weapon framework -- the native/BP parent chain of the projectile + thrown-
     weapon BPs, so we know exactly what to subclass for the hook + launcher.

Run: python ue_run.py mods/shigawire/00b_recon_detail.py
"""
import unreal

def hdr(t): print("\n=== %s ===" % t)

def grep_type(cls, keywords, indent="    "):
    if cls is None:
        print(indent + "(type not bound)"); return
    names = sorted({n for n in dir(cls)
                    if not n.startswith("_") and any(k in n.lower() for k in keywords)})
    if not names:
        print(indent + "(no match)"); return
    for n in names:
        try:
            doc = (getattr(cls, n).__doc__ or "").strip()
            first = doc.splitlines()[0] if doc else "(no doc)"
        except Exception as e:
            first = "(doc failed: %s)" % e
        print(indent + "%-34s %s" % (n, first))

# ---------------------------------------------------------------- A. Conan CMC type
hdr("A. ConanCharacterMovementComponent (BOUND TYPE -- impulse/force/velocity)")
grep_type(getattr(unreal, "ConanCharacterMovementComponent", None),
          ("impulse", "force", "velocity", "move", "launch", "teleport"))

# ---------------------------------------------------------------- B. stagger/stun
hdr("B. STAGGER / STUN / KNOCKOUT / KNOCKBACK")
print(" -- ConanCharacter CC-ish methods (full signatures):")
for n in ("add_stagger", "add_buff", "remove_buff", "can_be_knocked_out",
          "kill_character_with_ragdoll", "play_stagger_camera_shake"):
    f = getattr(unreal.ConanCharacter, n, None)
    print("    %-30s %s" % (n, (f.__doc__ or "").strip().splitlines()[0] if f else "ABSENT"))
print(" -- unreal.* types/enums/structs naming stagger/stun/knock/daze/incapacit:")
hits = sorted(n for n in dir(unreal)
              if any(k in n.lower() for k in ("stagger", "stun", "knock", "daze",
                                              "incapacit", "knockout")))
for n in hits[:60]:
    print("    unreal.%s" % n)
if not hits: print("    (none)")
print(" -- Asset registry: BUFF / stun / knockout / daze BPs by name --")
ar = unreal.AssetRegistryHelpers.get_asset_registry()
allbp = ar.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "Blueprint"),
                               search_sub_classes=True)
BKW = ("buff_stun", "_stun", "stun_", "knockout", "daze", "sleep", "_buff_")
hits = 0
for a in allbp:
    s = (str(a.package_name) + " " + str(a.asset_name)).lower()
    if any(k in s for k in BKW):
        print("    %s  /  %s" % (a.package_name, a.asset_name))
        hits += 1
        if hits >= 30: print("    ...(capped at 30)"); break
if not hits: print("    (no stun/knockout/buff BP matched by name)")
print(" -- the headline Knockback DamageTypes (CC delivery via apply_point_damage):")
for p in ("/Game/Systems/Combat/DamageTypes/BP_Knockback_Base",
          "/Game/Systems/Combat/DamageTypes/BP_Knockback_Knockdown",
          "/Game/Systems/Combat/DamageTypes/BP_Knockback_Flinch",
          "/Game/Systems/Combat/DamageTypes/BP_Knockback_NPC_Away"):
    print("    exists:", unreal.EditorAssetLibrary.does_asset_exist(p), "  ", p)

# ---------------------------------------------------------------- C. thrown framework
hdr("C. THROWN-WEAPON FRAMEWORK -- parent chains (what to subclass)")
# UBlueprint has no script-readable 'parent_class' in this binding (00b v1 failed).
# Read the BP's ParentClass / NativeParentClass off its AssetData registry tags instead
# (no asset load needed). package_name == the asset path for these.
admap = {str(a.package_name): a for a in allbp}
def parent_of(path):
    ad = admap.get(path)
    if ad is None:
        return "(not in registry)"
    out = []
    for tag in ("ParentClass", "NativeParentClass"):
        try:
            v = ad.get_tag_value(tag)
        except Exception as e:
            v = "(get_tag_value err: %s)" % e
        out.append("%s=%s" % (tag, v))
    return "  ".join(out)

TARGETS = [
    "/Game/Items/Weapons/BP_BaseProjectile",
    "/Game/Items/Weapons/BP_ThrowableProjectile",
    "/Game/Items/BP_ProjectileWeapon",
    "/Game/Items/BP_ProjectileWeaponThrown",
    "/Game/Items/BP_ProjectileWeaponLauncher",
    "/Game/Items/Weapons/Throwing/BP_throwing_offhand_axe",
    "/Game/Items/Weapons/Throwing/BP_throwing_offhand_axe_projectile_NoLoot",
]
for p in TARGETS:
    print("    %-66s parent = %s" % (p.split("/")[-1], parent_of(p)))

print("\n=== SHIGAWIRE RECON DETAIL DONE ===")
