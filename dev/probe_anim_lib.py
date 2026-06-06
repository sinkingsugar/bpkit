import unreal
# montage/slot/track functions across likely editor libraries
for libname in ("AnimationLibrary", "MontageEditorLibrary", "AnimMontage"):
    lib = getattr(unreal, libname, None)
    if lib:
        fns = [m for m in dir(lib) if any(k in m.lower() for k in ("slot","montage","track","segment","group")) and not m.startswith("__")]
        print("%s:" % libname, fns[:20])
# does AnimMontage expose a constructor / new_object path where we can set slot?
print("\nAnimMontage editor props sample:", [p for p in dir(unreal.AnimMontage) if not p.startswith("_")][:25])
# what slot does the game's real mounted montage use? play it live + scan slots
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if world:
    def call(o,n,*a):
        try: return getattr(o,n)(*a)
        except Exception as e: return "ERR"
    pc=unreal.GameplayStatics.get_player_controller(world,0); host=pc.get_controlled_pawn()
    tsc=host.get_thrall_system_component()
    hum=next((f for f in tsc.get_following_thrall_characters() if not f.is_mountable()),None)
    if hum:
        mesh=hum.get_editor_property("Mesh"); mesh.set_animation_mode(unreal.AnimationMode.ANIMATION_BLUEPRINT)
        mv=unreal.load_object(None,"/Game/Characters/humans/animations/mounted/Horse/AM_human_mounted_movement_HORSE.AM_human_mounted_movement_HORSE")
        call(hum,"play_anim_montage",mv,0.2,"")
        anim=mesh.get_anim_instance()
        for s in ("Fullbody3rd","Emote","Right3rd","Left3rd","AttackMontage3rd","AttackMontageTorso3rd","Additive3rd","MODFullBody"):
            if call(anim,"is_slot_active",s) is True:
                print("  movement montage ACTIVE on slot:", s)
