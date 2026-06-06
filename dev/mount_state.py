import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if world is None:
    print("NO PIE"); raise SystemExit
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn()
tsc = pawn.get_thrall_system_component()
def call(o, n, *a):
    try: return getattr(o, n)(*a)
    except Exception as e: return "ERR(%s)" % str(e)[:25]

# mount state (truth)
ridden = None
for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter):
    if call(c, "get_rider") == pawn: ridden = c
mi = call(pawn, "get_mount_input")
print("MOUNTED:", ridden.get_name() if ridden else "NO", "| GetMountInput valid:",
      "yes" if (mi and "ERR" not in str(mi)) else "no/none")

# manager state
mgr = None
for m in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
    if "MountedFollowerManager" in m.get_class().get_name(): mgr = m
if mgr:
    print("MGR: WasMounted=%s Initialized=%s HumanoidCounter=%s MgrVersion=%s" % (
        mgr.get_editor_property("WasMounted"), mgr.get_editor_property("Initialized"),
        mgr.get_editor_property("HumanoidCounter"), mgr.get_editor_property("MgrVersion")))

# followers: count + per-humanoid stow state (collision + mesh attach)
fols = tsc.get_following_thrall_characters()
print("FOLLOW COUNT:", len(fols))
for f in fols:
    if not call(f, "is_mountable"):  # humanoid
        mesh = f.get_editor_property("Mesh")
        par = mesh.get_attach_parent()
        owner = par.get_owner().get_class().get_name() if par and par.get_owner() else "self"
        print("  HUMANOID %s collision=%s mesh.attachedTo=%s (stowed=%s)" % (
            f.get_name(), call(f, "get_actor_enable_collision"), owner,
            "YES" if not call(f, "get_actor_enable_collision") else "no"))
