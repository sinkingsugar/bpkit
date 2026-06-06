import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if world is None:
    print("NO PIE -- press Play (MP) with a follower out"); raise SystemExit
def call(o,n,*a):
    try: return "OK:%s" % getattr(o,n)(*a)
    except Exception as e: return "ERR:%s" % str(e)[:80]
pc=unreal.GameplayStatics.get_player_controller(world,0); host=pc.get_controlled_pawn()
tsc=host.get_thrall_system_component()
hum=next((f for f in tsc.get_following_thrall_characters() if not f.is_mountable()),None)
if not hum:
    print("no humanoid follower"); raise SystemExit
ec=next((c for c in hum.get_components_by_class(unreal.ActorComponent) if "Emote" in c.get_class().get_name()),None)
print("follower:", hum.get_name(), "| emote controller:", ec.get_class().get_name() if ec else None)
EM = unreal.CharacterEmotes.SIT_ON_GROUND   # clear, visible pose to test replication
print("learn_emote:", call(ec, "learn_emote", EM, False))
print("can_perform_emote:", call(ec, "can_perform_emote", EM, True))
print("start_emote:", call(ec, "start_emote", EM))   # this is the multicasting one
print(">> does the follower SIT_ON_GROUND on BOTH screens (host AND client)?")
