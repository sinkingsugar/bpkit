import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn()
def call(o, n, *a):
    try: return getattr(o, n)(*a)
    except Exception as e: return "ERR(%s)" % str(e)[:25]

# ground truth: does any mount have the player as rider?
ridden = None
for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter):
    if call(c, "get_rider") == pawn: ridden = c
print("GROUND TRUTH (a mount has player as rider):", ridden.get_name() if ridden else "NOT MOUNTED")

# candidate detectors
mi = call(pawn, "get_mount_input")
print("\n--- candidate mount detectors ---")
print("1. IsValid(GetMountInput):", unreal.SystemLibrary.is_valid(mi) if mi != None and "ERR" not in str(mi) else False, "(obj=%s)" % (mi if "ERR" in str(mi) else (mi.get_name() if mi else None)))
print("2. get_mount():", call(pawn, "get_mount"))
print("3. player attach_parent:", end=" ")
ap = pawn.get_attach_parent_actor() if hasattr(pawn, "get_attach_parent_actor") else "?"
print(ap.get_name() if ap and ap != "?" else ap)
# any boolean-ish mount-state methods/props
print("\n--- mount-state methods on player ---")
for n in ("is_mounted","is_riding","is_dismounting","get_mount_state","is_in_mounted_state","get_is_mounted"):
    if hasattr(pawn, n):
        print("   %s -> %s" % (n, call(pawn, n)))
print("   (props w/ mount/ride/seat:)", [x for x in dir(pawn) if any(k in x.lower() for k in ("ismount","mounted","riding","seated")) and not x.startswith("set")][:12])
