import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def by_tag(t):
    a = unreal.GameplayStatics.get_all_actors_with_tag(world, t); return a[0] if a else None
horse = by_tag("TEST_HORSE"); rider = by_tag("TEST_RIDER")

# Try the authoritative server seat sequence directly (bypass the client process gate)
seq = []
try:
    pre = rider.bp_pre_mount_server_client(horse); seq.append(("bp_pre_mount_server_client", pre))
except Exception as e: seq.append(("bp_pre_mount_server_client ERR", str(e)[:50]))
try:
    rider.bp_mount_server(horse); seq.append(("bp_mount_server", "called"))
except Exception as e: seq.append(("bp_mount_server ERR", str(e)[:50]))
try:
    rider.replicate_mount(horse); seq.append(("replicate_mount", "called"))
except Exception as e: seq.append(("replicate_mount ERR", str(e)[:50]))
try:
    post = rider.bp_post_mount_server_client(horse, True); seq.append(("bp_post_mount_server_client", post))
except Exception as e: seq.append(("bp_post ERR", str(e)[:50]))
for k, v in seq:
    print(" ", k, "->", v)
print("AFTER: rider.get_mount():", rider.get_mount(), " horse.get_rider():", horse.get_rider())
print("rider attach parent:", rider.get_attach_parent_actor())
