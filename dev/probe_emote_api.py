import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def call(o,n,*a):
    try: return getattr(o,n)(*a)
    except Exception as e: return "ERR(%s)"%str(e)[:50]
pc=unreal.GameplayStatics.get_player_controller(world,0); host=pc.get_controlled_pawn()
tsc=host.get_thrall_system_component()
hum=next((f for f in tsc.get_following_thrall_characters() if not f.is_mountable()),None)
# emote methods on the rider
print("RIDER emote methods:", [m for m in dir(hum) if "emote" in m.lower() and not m.startswith("_")])
# emote component?
print("\ncomponents w/ emote/anim/perform:")
for c in hum.get_components_by_class(unreal.ActorComponent):
    cn=c.get_class().get_name()
    if any(k in cn.lower() for k in ("emote","perform","entertain","anim","montage")):
        print("  ", cn, "->", [m for m in dir(c) if any(k in m.lower() for k in ("emote","play","start","perform","montage")) and not m.startswith("_")][:15])
# play montage with replication? ConanCharacter-level replicated montage helpers
print("\nRIDER replicated-anim methods:", [m for m in dir(hum) if any(k in m.lower() for k in ("multicast","replicat","net_","_server","_client")) and any(k in m.lower() for k in ("montage","anim","emote","play")) and not m.startswith("_")][:20])
