"""C0 recon for the mounted-followers mod. Read-only. Answers the four facts the
build plan hinges on:

  1. Player pawn Blueprint we target (in PIE: the live pawn's class; else: candidates).
  2. Every §8 recipe function is reflected + BlueprintCallable (-> usable as a K2 node).
  3. Conan's persistent-mod-logic hook (how a mod auto-spawns an always-present actor).
  4. get_mount()/get_rider() are readable for the polling manager (C2).

Run: python ue_run.py mods/mounted-followers/00_recon.py
"""
import unreal

def hdr(t): print("\n=== %s ===" % t)

ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world = None
try:
    world = ues.get_game_world()
except Exception as e:
    print("no game world:", e)

# ---------------------------------------------------------------- 1. player pawn
hdr("1. PLAYER PAWN")
pawn_cls = None
if world:
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    print("player controller:", pc.get_name() if pc else None)
    if pc:
        pawn = pc.get_controlled_pawn()
        if pawn:
            pawn_cls = pawn.get_class()
            print("LIVE player pawn:", pawn.get_name(), "| class:", pawn_cls.get_name())
            print("  class path:", pawn_cls.get_path_name())
if not pawn_cls:
    print("(no live pawn -- not in PIE). Candidate player BPs in the registry:")
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    bps = ar.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "Blueprint"),
                                 search_sub_classes=True)
    n = 0
    for a in bps:
        nm = str(a.asset_name)
        if any(k in nm.lower() for k in ("playerchar", "bp_player", "pccharacter", "playerpawn")):
            print("  ", a.package_name, a.asset_name)
            n += 1
            if n > 20: break
    if not n:
        print("  (none matched 'player*' by name -- will need a live PIE probe)")

# ----------------------------------------------- 2. recipe functions reflected?
hdr("2. RECIPE FUNCTIONS (reflected + BlueprintCallable?)")
# (python_attr, owning unreal class, what the BP node is)
CHECKS = [
    ("attach_to_component",        unreal.SceneComponent,            "attach mesh-root to socket"),
    ("set_collision_enabled",      unreal.PrimitiveComponent,        "kill collision"),
    ("set_simulate_physics",       unreal.PrimitiveComponent,        "kill physics"),
    ("set_component_tick_enabled", unreal.ActorComponent,            "tick on/off"),
    ("set_animation_mode",         unreal.SkeletalMeshComponent,     "force single-node"),
    ("play_animation",             unreal.SkeletalMeshComponent,     "pose anim"),
    ("disable_movement",           unreal.CharacterMovementComponent,"freeze movement"),
    ("stop_movement_immediately",  unreal.MovementComponent,         "stop movement"),
    ("detach_from_actor",          unreal.Actor,                     "restore: detach"),
]
for attr, cls, why in CHECKS:
    has = hasattr(cls, attr)
    print("  [%s] %s.%s  (%s)" % ("OK" if has else "!!", cls.__name__, attr, why))

# component getters on the character
hdr("2b. CHARACTER COMPONENT GETTERS")
for attr in ("get_editor_property",):  # mesh/capsule/character_movement are editor props
    pass
cc = unreal.ConanCharacter
for getter in ("mesh", "capsule_component", "character_movement"):
    print("  ConanCharacter editor-prop '%s' present:" % getter,
          getter in [str(p) for p in unreal.get_default_object(cc).__dir__()] if False else "(check live)")

# ----------------------------------------------- 3. persistent-mod hook
hdr("3. PERSISTENT-MOD HOOK CANDIDATES")
# Conan mod framework: look for ModController / GameInstance / GameMode hooks.
ar = unreal.AssetRegistryHelpers.get_asset_registry()
allbp = ar.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "Blueprint"),
                               search_sub_classes=True)
KW = ("modcontroller", "mod_controller", "modplugin", "gameinstance", "moddingframework",
      "funcom", "serverapi", "modhook")
hits = 0
for a in allbp:
    s = (str(a.package_name) + " " + str(a.asset_name)).lower()
    if any(k in s for k in KW):
        print("  ", a.package_name, a.asset_name)
        hits += 1
        if hits > 30: break
if not hits:
    print("  (no name-matched mod hook -- inspect ConanGameMode/GameInstance native classes)")
# native gamemode / gameinstance present?
for nm in ("ConanGameMode", "ConanGameInstance", "FuncomLiveServices", "ModController"):
    print("  native unreal.%s:" % nm, hasattr(unreal, nm))

# ----------------------------------------------- 4. mount-state readable?
hdr("4. MOUNT-STATE API (for polling manager)")
for m in ("get_mount", "get_rider", "is_mountable"):
    print("  ConanCharacter.%s:" % m, hasattr(unreal.ConanCharacter, m))

print("\n=== C0 RECON DONE ===")
