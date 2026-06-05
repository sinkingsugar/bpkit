import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def by_tag(t):
    a = unreal.GameplayStatics.get_all_actors_with_tag(world, t); return a[0] if a else None
horse = by_tag("TEST_HORSE"); rider = by_tag("TEST_RIDER")

print("rider attach parent:", rider.get_attach_parent_actor())
print("horse attach parent:", horse.get_attach_parent_actor())
print("rider get_mount:", rider.get_mount(), " horse get_rider:", horse.get_rider())
print("rider is_dismounting:", rider.is_dismounting() if hasattr(rider,'is_dismounting') else '?')
try:
    print("rider get_mount_input:", rider.get_mount_input())
except Exception as e:
    print("get_mount_input err:", e)

# Try the lower-level server mount hooks directly
print("\n-- trying bp_mount_server / bp_pre/post --")
for fn, arg in [("bp_pre_mount_server_client", horse), ("bp_mount_server", horse),
                ("bp_post_mount_server_client", horse)]:
    try:
        f = getattr(rider, fn)
        if fn == "bp_post_mount_server_client":
            r = f(horse, True)
        else:
            r = f(arg)
        print(fn, "->", r)
    except Exception as e:
        print(fn, "ERR", str(e)[:80])

print("after: rider.get_mount:", rider.get_mount(), " horse.get_rider:", horse.get_rider())
print("rider attach parent now:", rider.get_attach_parent_actor())

# Also: does the horse respond to a SHORT nav move with a plain controller?
# Check navmesh presence near the horse.
loc = horse.get_actor_location()
pt = unreal.NavigationSystemV1.get_random_reachable_point_in_radius(world, loc, 600.0)
print("\nnav reachable point near horse (radius 600):", pt)
