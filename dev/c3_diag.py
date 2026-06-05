import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if world is None:
    print("NO PIE"); raise SystemExit
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn()

# is the player mounted? (scan horses' rider)
ridden = None
for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter):
    try:
        if c.get_rider() == pawn:
            ridden = c
    except Exception:
        pass
print("player mounted on:", ridden.get_name() if ridden else "NONE (not mounted)")

# manager array state
mgr = None
for m in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
    if "MountedFollowerManager" in m.get_class().get_name():
        mgr = m
if mgr is None:
    print("NO MANAGER"); raise SystemExit
for p in ("MgrVersion", "HumanoidCounter", "DbgCount"):
    try: print("mgr.%s =" % p, mgr.get_editor_property(p))
    except Exception as e: print("mgr.%s ERR %s" % (p, e))
try:
    sh = mgr.get_editor_property("SpareHorses")
    print("mgr.SpareHorses len =", len(sh), "->", [x.get_name() if x else None for x in sh])
except Exception as e:
    print("SpareHorses read ERR:", e)

# per horse: who rides it (helps see ridden vs spare)
print("\nhorses get_rider:")
for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter):
    try:
        if c.is_mountable():
            r = c.get_rider()
            print("  %-30s rider=%s" % (c.get_class().get_name(), r.get_name() if r else None))
    except Exception:
        pass

# per entertainer: is its mesh attached to a horse? (parent of mesh)
print("\nentertainer mesh attach parent:")
for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter):
    try:
        if not c.is_mountable():
            mesh = c.get_editor_property("Mesh") if hasattr(c, "get_editor_property") else None
            par = mesh.get_attach_parent() if mesh else None
            print("  %-30s mesh.parent=%s" % (c.get_class().get_name(),
                  par.get_owner().get_name() if par and par.get_owner() else par))
    except Exception as e:
        print("  attach read err:", e)
