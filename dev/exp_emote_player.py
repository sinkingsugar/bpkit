import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def call(o,n,*a):
    try: return "OK:%s" % getattr(o,n)(*a)
    except Exception as e: return "ERR:%s" % str(e)[:80]
pc=unreal.GameplayStatics.get_player_controller(world,0); host=pc.get_controlled_pawn()
ec=next((c for c in host.get_components_by_class(unreal.ActorComponent) if "Emote" in c.get_class().get_name()),None)
print("HOST player:", host.get_name(), "| emote controller:", ec.get_class().get_name() if ec else None)
print("net role:", host.get_local_role(), "| remote role:", host.get_remote_role(), "| has_authority:", host.has_authority())
EM = unreal.CharacterEmotes.SIT_ON_GROUND
print("learn:", call(ec,"learn_emote",EM,False))
print("start_emote:", call(ec,"start_emote",EM))
print(">> does the CLIENT (player 1) screen see the HOST (player 0) character SIT? (isolates multicast vs follower)")
