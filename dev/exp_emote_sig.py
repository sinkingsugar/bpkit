import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def call(o,n,*a):
    try: return "OK:%s" % getattr(o,n)(*a)
    except Exception as e: return "ERR: %s" % str(e)[:160]
pc=unreal.GameplayStatics.get_player_controller(world,0); host=pc.get_controlled_pawn()
tsc=host.get_thrall_system_component()
hum=next((f for f in tsc.get_following_thrall_characters() if not f.is_mountable()),None)
ec=next((c for c in hum.get_components_by_class(unreal.ActorComponent) if "Emote" in c.get_class().get_name()), None)
for fn in ("start_emote","start_emote_animation","start_emote_in_section","start_emote_with_props","start_emote_local","stop_emote_animation"):
    print("%s() -> %s" % (fn, call(ec, fn)))
