import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def call(o,n,*a):
    try: return getattr(o,n)(*a)
    except Exception as e: return "ERR(%s)"%str(e)[:45]
pc=unreal.GameplayStatics.get_player_controller(world,0); host=pc.get_controlled_pawn()
tsc=host.get_thrall_system_component()
hum=next((f for f in tsc.get_following_thrall_characters() if not f.is_mountable()),None)
horse=next((f for f in tsc.get_following_thrall_characters() if f.is_mountable()),None)
print("follower:", hum.get_name() if hum else None, "| horse:", horse.get_name() if horse else None)
# mount/seat/ride methods on the rider (ConanCharacter)
print("\nRIDER mount-ish methods:", [m for m in dir(hum) if any(k in m.lower() for k in ("mount","ride","seat","saddle"))][:25])
# on the horse
print("\nHORSE mount-ish methods:", [m for m in dir(horse) if any(k in m.lower() for k in ("mount","ride","seat","rider","saddle","passenger"))][:25])
# components on the horse (a mount/seat component?)
print("\nHORSE components:")
for c in horse.get_components_by_class(unreal.ActorComponent):
    cn = c.get_class().get_name()
    if any(k in cn.lower() for k in ("mount","seat","rider","saddle")):
        print("   ", cn, "-> methods:", [m for m in dir(c) if any(k in m.lower() for k in ("mount","seat","rider","add","set")) ][:12])
# how does the PLAYER get mounted? check player's mount-ish methods + current mount
print("\nPLAYER get_mount:", call(host,"get_mount"), "| methods:", [m for m in dir(host) if "mount" in m.lower()][:15])
