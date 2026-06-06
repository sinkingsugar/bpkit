import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def call(o,n,*a):
    try: return getattr(o,n)(*a)
    except Exception as e: return "ERR(%s)"%str(e)[:50]
pc = unreal.GameplayStatics.get_player_controller(world,0)
host = pc.get_controlled_pawn()
tsc = host.get_thrall_system_component()
hum = next((f for f in tsc.get_following_thrall_characters() if not f.is_mountable()), None)
if hum:
    print("before detach -> attach_parent:", hum.get_attach_parent_actor().get_name() if hum.get_attach_parent_actor() else None)
    R = unreal.DetachmentRule.KEEP_WORLD
    print("k2_detach_from_actor:", call(hum, "k2_detach_from_actor", R, R, R))
    # also un-freeze
    mesh = hum.get_editor_property("Mesh"); mesh.set_animation_mode(unreal.AnimationMode.ANIMATION_BLUEPRINT)
    cm = hum.get_component_by_class(unreal.CharacterMovementComponent)
    if cm: call(cm, "set_movement_mode", unreal.MovementMode.MOVE_WALKING, 0)
    hum.set_actor_enable_collision(True)
    print("after detach  -> attach_parent:", hum.get_attach_parent_actor().get_name() if hum.get_attach_parent_actor() else "** DETACHED **")
    print(">> did the follower drop off the horse on BOTH screens?")
