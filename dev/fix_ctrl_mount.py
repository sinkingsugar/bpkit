"""Give the summoned pawns real AI controllers (summon + possess), then retry
mount() and command the horse to move.

    python ue_run.py dev/fix_ctrl_mount.py
"""
import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if not world:
    print("!! no game world"); raise SystemExit
pc = unreal.GameplayStatics.get_player_controller(world, 0)
ploc = unreal.GameplayStatics.get_player_pawn(world, 0).get_actor_location()

def by_tag(tag):
    a = unreal.GameplayStatics.get_all_actors_with_tag(world, tag)
    return a[0] if a else None

horse = by_tag("TEST_HORSE")
rider = by_tag("TEST_RIDER")
print("horse:", horse, "rider:", rider)
if not (horse and rider):
    print("!! tagged actors missing — re-run mount_test_live first"); raise SystemExit

HOOVED = "/Game/Characters/NPCs/Hooved_Wild/CreatureAIControllerHooved.CreatureAIControllerHooved_C"
HUMAN = "/Game/Systems/AI/NewAI/HumanAIController.HumanAIController_C"

def existing_ai():
    return set(c.get_name() for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.AIController))

def summon_ctrl(path):
    before = existing_ai()
    unreal.SystemLibrary.execute_console_command(world, "Summon " + path, pc)
    for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.AIController):
        if c.get_name() not in before:
            return c
    return None

# Possess horse with Hooved AI, rider with Human AI
for pawn, path, nm in ((horse, HOOVED, "horse"), (rider, HUMAN, "rider")):
    if pawn.get_controller():
        print(nm, "already controlled by", pawn.get_controller().get_name()); continue
    ctrl = summon_ctrl(path)
    print(nm, "summoned ctrl:", ctrl)
    if ctrl:
        try:
            ctrl.possess(pawn)
            print("  ", nm, "now controlled by:", pawn.get_controller())
        except Exception as e:
            print("  possess err:", e)

# Retry mount
print("\n-- retry mount --")
try:
    print("can_mount ->", rider.can_mount(horse))
except Exception as e:
    print("can_mount err:", e)
try:
    rider.mount(horse)
    print("called rider.mount(horse)")
except Exception as e:
    print("mount err:", e)
print("  rider.get_mount():", rider.get_mount())
print("  horse.get_rider():", horse.get_rider())

# Move the horse
nav = unreal.NavigationSystemV1.get_navigation_system(world)
dest = unreal.Vector(ploc.x - 1500, ploc.y, ploc.z)
if nav:
    p = nav.project_point_to_navigation(dest, unreal.Vector(1200, 1200, 1200))
    if p: dest = p
ctrl = horse.get_controller()
print("horse ctrl:", ctrl, "isAI:", isinstance(ctrl, unreal.AIController))
if isinstance(ctrl, unreal.AIController):
    try:
        ctrl.move_to_location(dest, -1.0, True, True, False, True, None, True)
        print("issued horse move ->", dest)
    except Exception as e:
        print("move err:", e)
print("HORSE_POS_T0", horse.get_actor_location())
