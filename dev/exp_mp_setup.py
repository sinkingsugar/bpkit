import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def call(o, n, *a):
    try: return getattr(o, n)(*a)
    except Exception as e: return "ERR(%s)" % str(e)[:50]

# host = player 0's pawn
pc = unreal.GameplayStatics.get_player_controller(world, 0)
host = pc.get_controlled_pawn()
tsc = host.get_thrall_system_component()
print("host:", host.get_name())

# signatures for the follow API
for n in ("set_following", "server_set_following"):
    m = getattr(unreal.ThrallSystemComponent, n, None)
    print(" ", n, "::", (m.__doc__ or "NONE").splitlines()[0] if m else "MISSING")

# candidate neutral NPCs to enlist (horses + 1 humanoid)
allc = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter)
horses = [c for c in allc if c.is_mountable()][:3]
hums = [c for c in allc if (not c.is_mountable()) and "BasePlayerChar" not in c.get_class().get_name()][:1]
print("candidate horses:", [h.get_name() for h in horses], "humanoid:", [h.get_name() for h in hums])

print("\nbefore:", call(tsc, "get_follower_group_counts"))
for npc in horses + hums:
    print("  set_following(%s):" % npc.get_class().get_name(), call(tsc, "set_following", npc, True))
print("after:", call(tsc, "get_follower_group_counts"),
      "| following:", [f.get_class().get_name() for f in tsc.get_following_thrall_characters()])
