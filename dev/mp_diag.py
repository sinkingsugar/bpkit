import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if world is None:
    print("NO PIE"); raise SystemExit
def call(o, n, *a):
    try: return getattr(o, n)(*a)
    except Exception as e: return "ERR(%s)" % str(e)[:25]
def rd(o, n):
    try: return o.get_editor_property(n)
    except Exception as e: return "ERR"

# all players in this (server) world
pcs = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PlayerController)
print("=== PLAYERS (server world) ===", len(pcs))
for i, pc in enumerate(pcs):
    pawn = pc.get_controlled_pawn()
    if not pawn: continue
    tsc = call(pawn, "get_thrall_system_component")
    grp = call(tsc, "get_follower_group_counts") if tsc and "ERR" not in str(tsc) else "?"
    nfol = len(tsc.get_following_thrall_characters()) if tsc and "ERR" not in str(tsc) else "?"
    # mounted?
    ridden = None
    for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter):
        if call(c, "get_rider") == pawn: ridden = c
    print("  P%d %s | followers=%s groups=%s | mounted_on=%s" % (
        i, pawn.get_name(), nfol, grp, ridden.get_name() if ridden else "NO"))

# the manager
mgr = None
for m in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
    if "MountedFollowerManager" in m.get_class().get_name(): mgr = m
print("\n=== MANAGER ===")
if mgr:
    for p in ("MgrVersion", "Initialized", "WasMounted", "HumanoidCounter", "PlayerMount"):
        v = rd(mgr, p)
        print("  %s = %s" % (p, v.get_name() if hasattr(v, "get_name") else v))
    sh = rd(mgr, "SpareHorses")
    print("  SpareHorses =", [x.get_name() if x else None for x in sh] if isinstance(sh, (list, unreal.Array)) else sh)

# stow state of every humanoid follower of player 0
print("\n=== HUMANOID STOW STATE (server truth) ===")
p0 = pcs[0].get_controlled_pawn() if pcs else None
tsc0 = call(p0, "get_thrall_system_component") if p0 else None
if tsc0 and "ERR" not in str(tsc0):
    for f in tsc0.get_following_thrall_characters():
        if not call(f, "is_mountable"):
            mesh = f.get_editor_property("Mesh")
            par = mesh.get_attach_parent()
            owner = par.get_owner().get_class().get_name() if par and par.get_owner() else "self"
            print("  %s collision=%s mesh->%s loc=%s" % (
                f.get_class().get_name(), call(f, "get_actor_enable_collision"), owner, f.get_actor_location()))
