import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if world is None:
    print("NO PIE"); raise SystemExit
def call(o, n, *a):
    try: return getattr(o, n)(*a)
    except Exception as e: return "ERR(%s)" % str(e)[:25]

print("accessible game world:", world.get_name())
print("net mode:", call(unreal.SystemLibrary, "get_net_mode", world) if hasattr(unreal.SystemLibrary, "get_net_mode") else "?")

# players in THIS world
pcs = []
for pc in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PlayerController):
    pawn = pc.get_controlled_pawn()
    pcs.append((pc.get_name(), pawn.get_name() if pawn else None, call(pc, "has_authority")))
print("\nPlayerControllers in this world:", len(pcs))
for n, p, auth in pcs:
    print("   %s -> pawn %s | has_authority=%s" % (n, p, auth))

# managers in THIS world
mgrs = [m for m in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
        if "MountedFollowerManager" in m.get_class().get_name()]
print("\nMountedFollowerManager instances in this world:", len(mgrs))
for m in mgrs:
    print("   %s | local_role=%s has_authority=%s Initialized=%s MgrVersion=%s" % (
        m.get_name(), call(m, "get_local_role"), call(m, "has_authority"),
        m.get_editor_property("Initialized"), m.get_editor_property("MgrVersion")))

# how many BasePlayerChar exist (both players' pawns visible here = server world)
players = [c for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter)
           if "BasePlayerChar" in c.get_class().get_name()]
print("\nBasePlayerChar count in this world:", len(players), "(2 = server world sees both)")
