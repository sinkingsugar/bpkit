import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if world is None:
    print("NO PIE"); raise SystemExit
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn()
def call(o, n, *a):
    try: return getattr(o, n)(*a)
    except Exception as e: return "ERR(%s)" % str(e)[:40]
chars = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter)
players = [c for c in chars if "BasePlayerChar" in c.get_class().get_name()]
print("ConanCharacter count:", len(chars))
print("BasePlayerChar count:", len(players), "<-- >1 means a duplicate player spawned")
for p in players:
    print("   ", p.get_name(), "controlled=" + str(p == pawn))
print("player.is_formation_leader:", call(pawn, "is_formation_leader"))
lc = call(pawn, "get_my_formation_leader_component")
print("player.leader_comp:", lc.get_name() if lc and "ERR" not in str(lc) else lc)
for f in pawn.get_thrall_system_component().get_following_thrall_characters():
    if f.is_mountable():
        print("  horse", f.get_name(), "in_formation=", call(f, "is_in_formation"))
