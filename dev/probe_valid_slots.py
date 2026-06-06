import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def call(o, n, *a):
    try: return getattr(o, n)(*a)
    except Exception as e: return "ERR(%s)" % str(e)[:40]
pc = unreal.GameplayStatics.get_player_controller(world, 0)
host = pc.get_controlled_pawn()
tsc = host.get_thrall_system_component()
hum = next((f for f in tsc.get_following_thrall_characters() if not f.is_mountable()), None)
if hum:
    mesh = hum.get_editor_property("Mesh")
    anim = mesh.get_anim_instance()
    idle = unreal.load_object(None, "/Game/Characters/humans/animations/mounted/Horse/A_human_mounted_idle_HORSE.A_human_mounted_idle_HORSE")
    cands = ["FullBody", "Fullbody", "FullBodySlot", "Full Body", "UpperBody", "UpperBodySlot",
             "DefaultSlot", "DefaultGroup", "Mounted", "MountedSlot", "Body", "Locomotion",
             "AdditiveSlot", "FaceSlot", "Action"]
    for s in cands:
        r = call(anim, "play_slot_animation_as_dynamic_montage", idle, s, 0.05, 0.05, 1.0, 1)
        valid = (r is not None) and ("ERR" not in str(r))
        active = call(anim, "is_slot_active", s)
        if valid or (active is True):
            print("SLOT '%s' -> valid=%s active=%s" % (s, valid, active))
        call(anim, "stop_slot_animation", 0.0, s)
    print("done -- valid slots listed above")
