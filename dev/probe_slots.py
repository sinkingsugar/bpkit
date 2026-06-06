import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def call(o, n, *a):
    try: return getattr(o, n)(*a)
    except Exception as e: return "ERR(%s)" % str(e)[:50]
pc = unreal.GameplayStatics.get_player_controller(world, 0)
host = pc.get_controlled_pawn()
tsc = host.get_thrall_system_component()
hum = next((f for f in tsc.get_following_thrall_characters() if not f.is_mountable()), None)
if hum:
    mesh = hum.get_editor_property("Mesh")
    sk = call(mesh, "get_skinned_asset") if hasattr(mesh, "get_skinned_asset") else None
    if not sk or "ERR" in str(sk):
        sk = mesh.get_editor_property("skeletal_mesh") if hasattr(mesh, "get_editor_property") else None
    print("skeletal mesh:", sk.get_name() if sk and "ERR" not in str(sk) else sk)
    skel = call(sk, "get_skeleton") if sk and "ERR" not in str(sk) else None
    if not skel or "ERR" in str(skel):
        skel = sk.get_editor_property("skeleton") if sk and "ERR" not in str(sk) else None
    print("skeleton:", skel.get_name() if skel and "ERR" not in str(skel) else skel)
    if skel and "ERR" not in str(skel):
        print("slot group names:", call(skel, "get_slot_group_names"))
    # the anim instance class
    anim = mesh.get_anim_instance()
    print("anim instance:", anim.get_class().get_name() if anim else None)
    print("anim methods w/ slot:", [m for m in dir(anim) if "slot" in m.lower()][:10] if anim else None)
