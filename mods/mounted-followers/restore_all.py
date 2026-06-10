import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if world is None:
    print("NO PIE"); raise SystemExit
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn()
def call(o, n, *a):
    try: return getattr(o, n)(*a)
    except Exception as e: return "ERR(%s)" % str(e)[:30]

# 1) player leaves/loses formation leadership
call(pawn, "leave_formation")
print("player left formation; is_leader now:", call(pawn, "is_formation_leader"))

tsc = pawn.get_thrall_system_component()
fols = tsc.get_following_thrall_characters()
print("followers:", len(fols))
for f in fols:
    # 2) leave formation + stop auto-rejoin
    call(f, "leave_formation")
    try: f.set_editor_property("can_autojoin_formation", False)
    except Exception: pass
    # 3) v30+ stows ACTOR-attach the follower to the horse (the rider's own mesh stays
    # parented to its capsule, so the mesh check below never fires for them): detach the
    # actor, re-enable movement/collision, restore the AnimBP.
    try:
        par_actor = f.get_attach_parent_actor()
        if par_actor and par_actor != f:
            f.detach_from_actor(unreal.DetachmentRule.KEEP_WORLD,
                                unreal.DetachmentRule.KEEP_WORLD,
                                unreal.DetachmentRule.KEEP_WORLD)
            f.set_actor_enable_collision(True)
            try:
                f.get_editor_property("CharacterMovement").set_movement_mode(
                    unreal.MovementMode.MOVE_WALKING, 0)
            except Exception:
                pass
            f.get_editor_property("Mesh").set_animation_mode(
                unreal.AnimationMode.ANIMATION_BLUEPRINT)
            print("  actor-detached", f.get_class().get_name())
    except Exception as e:
        print("  actor-detach err on", f.get_class().get_name(), str(e)[:40])
    # 3b) legacy (pre-v30) mesh-attach un-stow: detach mesh to own capsule + re-enable
    try:
        mesh = f.get_editor_property("Mesh")
        cap = f.get_editor_property("CapsuleComponent")
        par = mesh.get_attach_parent()
        if par and par.get_owner() and par.get_owner() != f:
            mesh.attach_to_component(cap, "", unreal.AttachmentRule.SNAP_TO_TARGET,
                                     unreal.AttachmentRule.SNAP_TO_TARGET,
                                     unreal.AttachmentRule.SNAP_TO_TARGET, False)
            mesh.set_relative_location_and_rotation(unreal.Vector(0, 0, -96),
                                                    unreal.Rotator(0, -90, 0), False, False)
            mesh.set_animation_mode(unreal.AnimationMode.ANIMATION_BLUEPRINT)
            f.set_actor_enable_collision(True)
            cm = f.get_character_movement() if hasattr(f, "get_character_movement") else None
            print("  un-stowed", f.get_class().get_name())
    except Exception as e:
        print("  un-stow err on", f.get_class().get_name(), str(e)[:40])

print("DONE. Followers should be back to regular follow.")
print("If any still won't follow, Stop+Play once for a clean reset, then test mount/dismount.")
