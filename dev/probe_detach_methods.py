import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def call(o,n,*a):
    try: return "OK:%s" % getattr(o,n)(*a)
    except Exception as e: return "ERR:%s" % str(e)[:60]
pc = unreal.GameplayStatics.get_player_controller(world,0)
host = pc.get_controlled_pawn()
tsc = host.get_thrall_system_component()
hum = next((f for f in tsc.get_following_thrall_characters() if not f.is_mountable()), None)
if hum:
    print("hum detach methods:", [m for m in dir(hum) if 'detach' in m.lower()])
    root = call(hum, "k2_get_root_component")
    if "ERR" in str(root): root = hum.get_editor_property("root_component")
    print("root:", root.get_class().get_name() if root and "ERR" not in str(root) else root)
    if root and "ERR" not in str(root):
        print("root detach methods:", [m for m in dir(root) if 'detach' in m.lower()])
        # try detaching via the root component
        R = unreal.DetachmentRule.KEEP_WORLD
        print("root.detach_from_component:", call(root, "detach_from_component", R, R, R))
        print("after -> attach_parent:", hum.get_attach_parent_actor().get_name() if hum.get_attach_parent_actor() else "** DETACHED **")
