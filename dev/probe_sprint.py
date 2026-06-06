import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if world is None:
    print("NO PIE"); raise SystemExit
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn()
tsc = pawn.get_thrall_system_component()
horse = next((f for f in tsc.get_following_thrall_characters() if f.is_mountable()), None)
if not horse:
    print("no horse following"); raise SystemExit

def rd(o, name):
    try: return o.get_editor_property(name)
    except Exception as e: return "ERR(%s)" % str(e)[:30]

print("horse:", horse.get_class().get_name())
print("  additional_following_distance =", rd(horse, "additional_following_distance"))
ai = horse.get_controller()
print("AI:", ai.get_class().get_name() if ai else None)
for p in ("statr_sprint_distance", "stop_sprint_distance", "end_leashing_distance_from_home_sqr"):
    print("  AI.%s =" % p, rd(ai, p))
# acceptance range / movement distance knobs
print("  horse.waypoint_acceptance_range =", rd(horse, "waypoint_acceptance_range"))
print("  TSC.max_thrall_movement_distance =", rd(tsc, "max_thrall_movement_distance"))
