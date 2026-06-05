"""Mount test v2 — for an admin-spawned SADDLED horse + a thrall.

Picks the horse that actually has an embedded saddle (real rideable mount),
picks a thrall rider, ensures both have AI controllers, seats the rider via
mount(), then commands the horse to ride off. Tags actors for the re-measure.

    python ue_run.py dev/mount_test_v2.py
"""
import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if not world:
    print("!! no game world"); raise SystemExit
pc = unreal.GameplayStatics.get_player_controller(world, 0)
player = unreal.GameplayStatics.get_player_pawn(world, 0)
ploc = player.get_actor_location()

chars = [c for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter) if c != player]
print("=== %d non-player ConanCharacters ===" % len(chars))
def info(c):
    try: sad = c.get_embedded_saddle_id()
    except Exception: sad = "?"
    try: mtb = c.is_mountable()
    except Exception: mtb = "?"
    try: thr = c.get_editor_property("is_thrall")
    except Exception: thr = "?"
    try: pet = c.get_editor_property("is_pet")
    except Exception: pet = "?"
    ctrl = c.get_controller()
    return sad, mtb, thr, pet, ctrl
for c in chars:
    sad, mtb, thr, pet, ctrl = info(c)
    print("  -", c.get_name(), "| saddle=", sad, "mountable=", mtb, "thrall=", thr, "pet=", pet,
          "ctrl=", ctrl.get_class().get_name() if ctrl else None,
          "dist=", int((c.get_actor_location()-ploc).length()))

# Horse = has embedded saddle; else mountable + 'horse/mount' in name
horse = None
for c in chars:
    if info(c)[0] not in (None, "?", 0):
        horse = c; break
if not horse:
    for c in chars:
        cn = c.get_class().get_name().lower()
        if info(c)[1] is True and ("horse" in cn or "mount" in cn):
            horse = c; break
# Rider = a thrall, else nearest non-horse humanoid
cands = [c for c in chars if c is not horse]
thralls = [c for c in cands if str(info(c)[2]) == "True" or "thrall" in c.get_class().get_name().lower()]
pool = thralls or cands
pool.sort(key=lambda c: (c.get_actor_location()-ploc).length())
rider = pool[0] if pool else None

print("\nCHOSEN horse:", horse.get_name() if horse else None,
      "(saddle=%s)" % (info(horse)[0] if horse else "-"),
      "| rider:", rider.get_name() if rider else None)
if not (horse and rider):
    print("!! need a saddled horse + a thrall. Adjust spawns and re-run."); raise SystemExit

horse.tags = list(horse.tags) + ["TEST_HORSE"]
rider.tags = list(rider.tags) + ["TEST_RIDER"]

# Ensure controllers (admin-spawned should already have them)
HUMAN = "/Game/Systems/AI/NewAI/HumanAIController.HumanAIController_C"
HOOVED = "/Game/Characters/NPCs/Hooved_Wild/CreatureAIControllerHooved.CreatureAIControllerHooved_C"
def ensure(pawn, path, nm):
    if pawn.get_controller():
        print(nm, "ctrl ok:", pawn.get_controller().get_class().get_name()); return
    unreal.load_object(None, path)
    before = {c.get_name() for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.AIController)}
    unreal.SystemLibrary.execute_console_command(world, "Summon " + path, pc)
    for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.AIController):
        if c.get_name() not in before:
            c.possess(pawn); break
    print(nm, "ctrl now:", pawn.get_controller())
ensure(horse, HOOVED, "horse")
ensure(rider, HUMAN, "rider")

print("\ncan_mount ->", rider.can_mount(horse), "(None == OK)")
rider.mount(horse)
print("called mount; rider.get_mount():", rider.get_mount(), " horse.get_rider():", horse.get_rider())

# Command the horse to ride to a point ~1200 away
dest = unreal.Vector(ploc.x - 1200, ploc.y, ploc.z)
hc = horse.get_controller()
if isinstance(hc, unreal.AIController):
    hc.move_to_location(dest, -1.0, True, True, False, True, None, True)
    print("issued horse move ->", dest)
print("HORSE_POS_T0", horse.get_actor_location())
