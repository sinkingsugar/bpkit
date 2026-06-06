import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if world is None:
    print("NO PIE -- press Play (MP) + mount first"); raise SystemExit
cls = unreal.load_object(None, "/Game/_Scratch/BP_MountedFollowerManager.BP_MountedFollowerManager_C")
mgrs = unreal.GameplayStatics.get_all_actors_of_class(world, cls)
print("managers (server):", [m.get_name() for m in mgrs])
if mgrs:
    mgr = mgrs[0]
    for nm in ("MCSeat", "mc_seat", "m_c_seat"):
        try:
            mgr.call_method(nm); print("called %s OK" % nm); break
        except Exception as e:
            print("  %s -> %s" % (nm, str(e)[:50]))
    print(">> MCSeat multicast fired from the SERVER. Did the follower seat on BOTH screens now (esp. the CLIENT)?")
