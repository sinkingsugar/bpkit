import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if world is None:
    print("NO GAME WORLD -> not in PIE. Press Play first.")
    raise SystemExit

pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn() if pc else None
print("player pawn:", pawn.get_name() if pawn else None)

# 1) manager: which class + state
print("\n=== MANAGER ===")
mgr = None
for m in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
    if "MountedFollowerManager" in m.get_class().get_name():
        mgr = m
        try: ver = m.get_editor_property("MgrVersion")
        except Exception as e: ver = "NO_PROP"
        print("  %s | MgrVersion=%s (2=FIXED class live, 0=stale) | Init=%s | WasMounted=%s" % (
            m.get_name(), ver, m.get_editor_property("Initialized"), m.get_editor_property("WasMounted")))
if mgr is None:
    print("  NO MANAGER INSTANCE")

# 2) real mount state (get_mount is broken; use get_rider scan)
print("\n=== MOUNT STATE (truth) ===")
ridden = None
for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter):
    try:
        if c.get_rider() == pawn and pawn is not None:
            ridden = c
    except Exception:
        pass
print("  horse with player as rider:", ridden.get_name() if ridden else "NONE (not mounted)")

# 3) followers + which are mounts
print("\n=== FOLLOWERS ===")
if pawn is not None:
    try:
        tsc = pawn.get_thrall_system_component()
        fols = tsc.get_following_thrall_characters()
        print("  count:", len(fols))
        for f in fols:
            ism = False
            try: ism = f.is_mount()
            except Exception: pass
            print("   -", f.get_class().get_name(), "| IsMount:", ism)
    except Exception as e:
        print("  follower read failed:", e)
