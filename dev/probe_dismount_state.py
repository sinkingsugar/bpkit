import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def call(o,n,*a):
    try: return getattr(o,n)(*a)
    except Exception as e: return "ERR(%s)"%str(e)[:40]
pc = unreal.GameplayStatics.get_player_controller(world,0)
host = pc.get_controlled_pawn()
tsc = host.get_thrall_system_component()
hum = next((f for f in tsc.get_following_thrall_characters() if not f.is_mountable()), None)
print("player mounted? get_rider on follow horses:")
for h in tsc.get_following_thrall_characters():
    if h.is_mountable():
        r = h.get_rider()
        print("  horse", h.get_name(), "rider:", r.get_name() if r else None)
if hum:
    par = hum.get_attach_parent_actor()
    print("FOLLOWER:", hum.get_name())
    print("  attach_parent:", par.get_name() if par else "** DETACHED **")
    mesh = hum.get_editor_property("Mesh")
    print("  anim_mode:", call(mesh,"get_animation_mode"))
    cm = hum.get_component_by_class(unreal.CharacterMovementComponent)
    print("  movement_mode:", cm.get_editor_property("movement_mode") if cm else "?")
    print("  collision_enabled:", call(hum,"get_actor_enable_collision"))
