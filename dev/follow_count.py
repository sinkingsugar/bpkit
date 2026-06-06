import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if world is None:
    print("NO PIE"); raise SystemExit
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn()
tsc = pawn.get_thrall_system_component()
def call(o, n, *a):
    try: return getattr(o, n)(*a)
    except Exception as e: return "ERR(%s)" % str(e)[:30]
fols = tsc.get_following_thrall_characters()
print("FOLLOW COUNT:", len(fols), "| groups:", call(tsc, "get_follower_group_counts"))
for f in fols:
    print("   -", f.get_class().get_name(), "| mountable:", call(f, "is_mountable"))
# also: is the player mounted right now?
ridden = None
for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter):
    if call(c, "get_rider") == pawn:
        ridden = c
print("player mounted on:", ridden.get_name() if ridden else "NONE")
