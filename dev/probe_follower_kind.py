import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if world is None:
    print("NO PIE"); raise SystemExit
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn()
tsc = pawn.get_thrall_system_component()
fols = tsc.get_following_thrall_characters()
print("followers:", len(fols))

def trymeth(o, name, *args):
    try:
        f = getattr(o, name)
        return f(*args)
    except Exception as e:
        return "ERR:%s" % str(e)[:40]

for f in fols:
    cn = f.get_class().get_name()
    row = {
        "is_mount": trymeth(f, "is_mount"),
        "is_mountable": trymeth(f, "is_mountable"),
        "get_rider": trymeth(f, "get_rider"),
        "get_mount": trymeth(f, "get_mount"),
        "get_mount_input": trymeth(f, "get_mount_input"),
    }
    print("  %-34s %s" % (cn, row))

# also list ALL UFunctions on the horse vs entertainer that contain 'mount'
print("\n=== ConanCharacter methods containing 'mount' ===")
cc = fols[0].get_class()
seen = set()
for f in fols:
    for m in dir(f):
        if "mount" in m.lower() and m not in seen:
            seen.add(m)
print(sorted(seen))
