"""C1 live parity test: prove the COMPILED BP_MF_Recipe.Stow (Blueprint logic, not
Python) reproduces the proven §8 cosmetic mount.

Needs: PIE running (player pawn) + admin (for Summon). Self-guiding — prints what to
do if prerequisites are missing. Idempotent-ish (reuses tagged actors).

Usage:
  python ue_run.py dev/c1_pie_test.py          # run the stow test
  (edit ACTION below to 'restore' to test the reverse)
Run: python ue_run.py dev/c1_pie_test.py
"""
import unreal

ACTION = "stow"   # 'stow' or 'restore'
RECIPE = "/Game/_Scratch/BP_MF_Recipe.BP_MF_Recipe_C"
FIGHTER = "/Game/Characters/NPCs/Necromancy_followers/Blueprints/BP_FiniteLifespanUndeadThrall.BP_FiniteLifespanUndeadThrall_C"

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn() if pc else None
if not pawn:
    print("!! NOT IN PIE (no player pawn). Press Play, become admin, then re-run.")
    raise SystemExit

def all_chars():
    return list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter))

def by_tag(t):
    a = unreal.GameplayStatics.get_all_actors_with_tag(world, t)
    return a[0] if a else None

def summon(path, tag):
    before = set(a.get_name() for a in all_chars())
    unreal.SystemLibrary.execute_console_command(world, "Summon " + path, pc)
    for a in all_chars():
        if a.get_name() not in before:
            a.tags = list(a.tags) + [tag]
            return a
    return None

# --- horse: an actor whose mesh has the 'attachrider' socket ---
horse = by_tag("TEST_HORSE")
if not horse:
    for c in all_chars():
        m = c.get_editor_property("mesh")
        if m and m.does_socket_exist("attachrider") and c != pawn:
            horse = c; horse.tags = list(horse.tags) + ["TEST_HORSE"]; break
if not horse:
    print("!! No horse with 'attachrider' socket found. Spawn/admin-summon a mount")
    print("   (e.g. BP_NPC_Mounts_Horse_Knight4) near you, then re-run.")
    raise SystemExit
print("horse:", horse.get_name())

# --- fighter rider: a human NPC the user spawned via admin panel
# (any non-player ConanCharacter WITHOUT the attachrider socket = not a mount) ---
rider = by_tag("TEST_RIDER")
if not rider:
    cands = []
    for c in all_chars():
        if c == pawn or c == horse:
            continue
        m = c.get_editor_property("mesh")
        if m and m.does_socket_exist("attachrider"):
            continue   # that's a mount, skip
        d = (c.get_actor_location() - pawn.get_actor_location()).length()
        cands.append((d, c))
    cands.sort(key=lambda x: x[0])
    if cands:
        rider = cands[0][1]
        rider.tags = list(rider.tags) + ["TEST_RIDER"]
if not rider:
    print("!! No human NPC found. Spawn a thrall/fighter from the ADMIN PANEL near you, re-run.")
    raise SystemExit
print("rider:", rider.get_name(), rider.get_class().get_name())

# --- recipe manager instance (Summon may be deferred; persists across runs) ---
def find_mgr():
    for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        if "BP_MF_Recipe" in a.get_class().get_name():
            return a
    return None
mgr = find_mgr()
if not mgr:
    unreal.load_object(None, RECIPE)   # load class first so Summon can resolve it
    unreal.SystemLibrary.execute_console_command(world, "Summon " + RECIPE, pc)
    mgr = find_mgr()
if not mgr:
    print(">> Summoned BP_MF_Recipe (spawn is deferred a frame). Rider/horse are tagged;")
    print(">> just say 'go' again to run the actual test now that the manager exists.")
    raise SystemExit
print("recipe mgr:", mgr.get_name())

# --- set vars + invoke the COMPILED event ---
mgr.set_editor_property("Rider", rider)
mgr.set_editor_property("Mount", horse)
print("set Rider/Mount; MountIdleAnim default:",
      mgr.get_editor_property("MountIdleAnim"))

mgr.call_method(ACTION.capitalize())   # Stow / Restore -> runs compiled graph
print(">>> called %s on compiled BP" % ACTION.capitalize())

# --- objective check: rider mesh root should sit on the horse 'attachrider' socket ---
rmesh = rider.get_editor_property("mesh")
hmesh = horse.get_editor_property("mesh")
rloc = rmesh.get_world_location()
sloc = hmesh.get_socket_location("attachrider")
d = (rloc - sloc).length()
print("rider mesh loc:", rloc)
print("socket    loc:", sloc)
print("distance:", round(d, 2), "=> ", "ON SOCKET (pass)" if d < 25 else "OFF (check)")
print("rider attach parent:", rider.get_attach_parent_actor())
