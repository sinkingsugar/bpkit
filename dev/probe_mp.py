import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if world is None:
    print("NO PIE"); raise SystemExit
def rd(o, n):
    try: return o.get_editor_property(n)
    except Exception as e: return "ERR(%s)" % str(e)[:25]
def call(o, n, *a):
    try: return getattr(o, n)(*a)
    except Exception as e: return "ERR(%s)" % str(e)[:25]

# manager replication setup
mgr = None
for m in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
    if "MountedFollowerManager" in m.get_class().get_name(): mgr = m
print("=== MANAGER (ModController) ===")
if mgr:
    for p in ("replicates", "only_relevant_to_owner", "net_load_on_client"):
        print("  %s = %s" % (p, rd(mgr, p)))
    print("  local_role:", call(mgr, "get_local_role"), "| has_authority:", call(mgr, "has_authority"))

# ModController base class defaults (CDO)
base = unreal.load_object(None, "/Script/DreamworldMods.ModController")
print("\n=== ModController base ===", base)

# is the player's mount state + follower list replicated (readable on clients)?
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn()
print("\n=== replicated-data check ===")
print("  player replicates:", rd(pawn, "replicates"))
tsc = pawn.get_thrall_system_component()
print("  TSC replicates:", rd(tsc, "replicates") if tsc else "no tsc")
horse = next((f for f in tsc.get_following_thrall_characters() if f.is_mountable()), None)
if horse:
    print("  horse replicates:", rd(horse, "replicates"),
          "| get_rider replicated? (rider set):", call(horse, "get_rider") is not None)
