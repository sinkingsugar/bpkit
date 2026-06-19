"""Shigawire recon -- READ-ONLY. No PIE, no UFunction calls (only dir()/__doc__/
hasattr/asset-registry reads). Answers the make-or-break feasibility questions from
FEASIBILITY.md before any build step is written:

  1. PULL  -- can we move the PLAYER toward a point? (LaunchCharacter / AddImpulse /
              AddForce on ConanCharacter + its movement component; reflected + signature)
  2. THROW -- how do Conan throwables (bola/axe) fire a projectile? a copyable template.
  3. CC    -- is there a callable stagger/knockdown/stun/status on the character or AI?
  4. CABLE -- is CableComponent (cosmetic rope) authorable? + ProjectileMovementComponent.

Run: python ue_run.py mods/shigawire/00_recon.py
"""
import unreal

def hdr(t): print("\n=== %s ===" % t)

def getcls(name):
    """unreal.<name> if the binding exists, else None (never raises)."""
    return getattr(unreal, name, None)

def grep_methods(cls, keywords, indent="    "):
    """Print script-exposed methods of cls whose name contains any keyword, with the
    first line of their __doc__ (the Python signature). Pure reflection -- no calls."""
    if cls is None:
        print(indent + "(class not bound in this build)")
        return []
    try:
        names = [n for n in dir(cls) if not n.startswith("_")]
    except Exception as e:
        print(indent + "(dir() failed: %s)" % e)
        return []
    matched = sorted({n for n in names
                      if any(k in n.lower() for k in keywords)})
    if not matched:
        print(indent + "(no method name matched %s)" % list(keywords))
        return []
    for n in matched:
        try:
            doc = (getattr(cls, n).__doc__ or "").strip()
            first = doc.splitlines()[0] if doc else "(no doc)"
        except Exception as e:
            first = "(doc read failed: %s)" % e
        print(indent + "%-34s %s" % (n, first))
    return matched

def show_mro(cls, label):
    if cls is None:
        print("  %s: (not bound)" % label); return
    try:
        chain = " -> ".join(c.__name__ for c in cls.__mro__ if c.__name__ != "object")
    except Exception:
        chain = "(mro unavailable)"
    print("  %s MRO: %s" % (label, chain))

# What classes are even bound? (so a missing probe = 'not bound' not 'no method')
hdr("0. CLASS BINDINGS PRESENT")
WANT = ["ConanCharacter", "ConanPlayerCharacter", "ConanNPC", "ConanAttacker",
        "Character", "CharacterMovementComponent", "ConanCharacterMovementComponent",
        "ConanAIController", "ConanAttackerAIController", "ConanPlayerController",
        "ProjectileMovementComponent", "CableComponent", "ConanProjectile",
        "ConanStatusEffect", "StatusEffect", "GameplayStatics", "ConanGameMode"]
for nm in WANT:
    c = getcls(nm)
    print("  unreal.%-34s %s" % (nm, "OK" if c is not None else "-- absent"))

cc   = getcls("ConanCharacter")
chr_ = getcls("Character")
cmc  = getcls("CharacterMovementComponent")
show_mro(cc, "ConanCharacter")
show_mro(getcls("ConanPlayerCharacter"), "ConanPlayerCharacter")

# Try to discover the *Conan* movement-component subclass via the CDO (property read,
# not a UFunction call -- CharacterMovement is a BlueprintReadOnly subobject).
conan_cmc_cls = None
if cc is not None:
    try:
        cdo = unreal.get_default_object(cc)
        movecomp = cdo.get_editor_property("character_movement")
        if movecomp:
            conan_cmc_cls = movecomp.get_class()
            print("  ConanCharacter.CharacterMovement class:", conan_cmc_cls.get_name())
    except Exception as e:
        print("  (could not read CharacterMovement subobject:", e, ")")

# ---------------------------------------------------------------- 1. PULL
hdr("1. PULL -- move the player toward a point")
PULL_KW = ("launch", "impulse", "force", "velocity", "teleport", "jump",
           "dash", "push", "knockback", "movement_mode", "set_movement",
           "add_movement", "ground_dash", "grappl", "pull", "reel")
print(" -- ConanCharacter:")
grep_methods(cc, PULL_KW)
print(" -- Character (engine base):")
grep_methods(chr_, PULL_KW)
print(" -- CharacterMovementComponent (engine base):")
grep_methods(cmc, PULL_KW)
if conan_cmc_cls is not None and conan_cmc_cls is not cmc:
    print(" -- %s (Conan movement subclass):" % conan_cmc_cls.get_name())
    grep_methods(conan_cmc_cls, PULL_KW)

# ---------------------------------------------------------------- 2. THROW / PROJECTILE
hdr("2. THROW / PROJECTILE -- how a thrown tool fires")
THROW_KW = ("throw", "projectile", "fire", "shoot", "launch_proj", "spawn_proj",
            "bola", "harpoon", "lasso", "missile", "thrown")
print(" -- ConanCharacter:")
grep_methods(cc, THROW_KW)
print(" -- ProjectileMovementComponent present:", getcls("ProjectileMovementComponent") is not None)
print(" -- ConanProjectile present:", getcls("ConanProjectile") is not None)
print(" -- Asset registry: throwable / projectile / hook BPs by name --")
ar = unreal.AssetRegistryHelpers.get_asset_registry()
allbp = ar.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "Blueprint"),
                               search_sub_classes=True)
ASSET_KW = ("bola", "throw", "projectile", "harpoon", "lasso", "grappl", "hook",
            "javelin", "spear_throw", "orb")
hits = 0
for a in allbp:
    s = (str(a.package_name) + " " + str(a.asset_name)).lower()
    if any(k in s for k in ASSET_KW):
        print("    %s  /  %s" % (a.package_name, a.asset_name))
        hits += 1
        if hits >= 40: print("    ...(capped at 40)"); break
if not hits:
    print("    (no throwable/projectile BP matched by name)")

# ---------------------------------------------------------------- 3. CC (stagger/stun/status)
hdr("3. CC -- stagger / knockdown / stun / status on hit")
CC_KW = ("stagger", "knock", "stun", "status", "effect", "buff", "hit_react",
         "ragdoll", "interrupt", "daze", "paralyz", "root", "immobil", "cripple",
         "stumble", "incapacit", "sleep")
print(" -- ConanCharacter:")
grep_methods(cc, CC_KW)
print(" -- ConanAIController:")
grep_methods(getcls("ConanAIController"), CC_KW)
print(" -- ConanAttackerAIController:")
grep_methods(getcls("ConanAttackerAIController"), CC_KW)
print(" -- GameplayStatics (damage entry points that may trigger native hit-react):")
grep_methods(getcls("GameplayStatics"), ("damage",))
print(" -- Status-effect classes bound in this build (unreal.* name contains 'status'/'effect'):")
try:
    sefx = sorted(n for n in dir(unreal)
                  if ("status" in n.lower() or "statuseffect" in n.lower()) and "effect" in n.lower())
    for n in sefx[:40]:
        print("    unreal.%s" % n)
    if not sefx: print("    (none)")
except Exception as e:
    print("    (scan failed:", e, ")")
print(" -- Asset registry: status-effect / stagger DataTables & BPs by name --")
SKW = ("statuseffect", "status_effect", "stagger", "knockdown", "knockback", "stun")
hits = 0
for a in allbp:
    s = (str(a.package_name) + " " + str(a.asset_name)).lower()
    if any(k in s for k in SKW):
        print("    %s  /  %s" % (a.package_name, a.asset_name))
        hits += 1
        if hits >= 30: print("    ...(capped at 30)"); break
if not hits:
    print("    (no status/stagger BP matched by name)")

# ---------------------------------------------------------------- 4. CABLE (cosmetic rope)
hdr("4. CABLE -- cosmetic rope component")
cable = getcls("CableComponent")
print("  unreal.CableComponent:", "OK (authorable)" if cable is not None else "-- absent (plugin off?)")
if cable is not None:
    show_mro(cable, "CableComponent")

print("\n=== SHIGAWIRE RECON DONE ===")
