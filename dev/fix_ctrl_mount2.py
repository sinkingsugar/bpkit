import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)
ploc = unreal.GameplayStatics.get_player_pawn(world, 0).get_actor_location()

def by_tag(t):
    a = unreal.GameplayStatics.get_all_actors_with_tag(world, t); return a[0] if a else None
horse = by_tag("TEST_HORSE"); rider = by_tag("TEST_RIDER")

HOOVED = "/Game/Characters/NPCs/Hooved_Wild/CreatureAIControllerHooved.CreatureAIControllerHooved_C"
HUMAN  = "/Game/Systems/AI/NewAI/HumanAIController.HumanAIController_C"

# Pre-load controller classes so Summon can resolve them
for p in (HOOVED, HUMAN):
    c = unreal.load_object(None, p)
    print("loaded class:", p, "->", c is not None)

def ai_set():
    return {c.get_name(): c for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.AIController)}

def ensure_ctrl(pawn, path, nm):
    if pawn.get_controller():
        print(nm, "ctrl:", pawn.get_controller().get_name()); return
    before = ai_set()
    unreal.SystemLibrary.execute_console_command(world, "Summon " + path, pc)
    after = ai_set()
    new = [c for n, c in after.items() if n not in before]
    print(nm, "new ctrl actors:", [c.get_name() for c in new])
    for c in new:
        try:
            c.possess(pawn)
        except Exception as e:
            print("  possess err:", e)
    print(nm, "now:", pawn.get_controller())

ensure_ctrl(horse, HOOVED, "horse")
ensure_ctrl(rider, HUMAN, "rider")

print("\ncan_mount ->", rider.can_mount(horse))
rider.mount(horse)
print("called mount; immediate rider.get_mount():", rider.get_mount(),
      " horse.get_rider():", horse.get_rider())

# Kick the horse toward a destination now (so we can also see if it moves once mounted)
dest = unreal.Vector(ploc.x - 1500, ploc.y, ploc.z)
hc = horse.get_controller()
if isinstance(hc, unreal.AIController):
    hc.move_to_location(dest, -1.0, True, True, False, True, None, True)
    print("issued horse move ->", dest)
print("HORSE_POS_T0", horse.get_actor_location())
