"""C2 prerequisite: how is the follower/pet/mount cap counted, and is it one
shared limit or separate buckets? Probe the live player + game settings."""
import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn() if pc else None
print("player:", pawn.get_name() if pawn else None, "| pc:", pc.get_class().get_name() if pc else None)

def members(obj, kws):
    return sorted(m for m in dir(obj) if not m.startswith("_")
                  and any(k in m.lower() for k in kws))

KW = ("follower", "thrall", "pet", "mount", "limit", "max", "count", "num_", "active")
print("\n== pawn members ==", members(pawn, KW) if pawn else [])
print("\n== pc members ==", members(pc, KW) if pc else [])

# ThrallComponent on the player?
for getter in ("get_thrall_component",):
    if pawn and hasattr(pawn, getter):
        tc = getattr(pawn, getter)()
        print("\n== thrall component:", tc.get_class().get_name() if tc else None)
        if tc:
            print("  members:", members(tc, KW))

# current followers in world + their pet/thrall flags
print("\n== current ConanCharacters following this player ==")
for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter):
    if c == pawn:
        continue
    try:
        fpc = c.get_followed_player_controller() if hasattr(c, "get_followed_player_controller") else None
    except Exception:
        fpc = None
    if fpc == pc:
        ip = c.get_editor_property("is_pet") if "is_pet" in dir(c) else "?"
        it = c.get_editor_property("is_thrall") if "is_thrall" in dir(c) else "?"
        print("  follower:", c.get_class().get_name(), "| is_pet:", ip, "| is_thrall:", it)

# game settings with follower limits?
print("\n== ConanGameMode / settings follower-limit members ==")
for cls_name in ("ConanGameMode", "ConanGameInstance"):
    if hasattr(unreal, cls_name):
        cdo = unreal.get_default_object(getattr(unreal, cls_name))
        print(cls_name, ":", members(cdo, ("follower", "pet", "limit", "max")) [:20])
