import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def call(o,n,*a):
    try: return getattr(o,n)(*a)
    except Exception as e: return "ERR(%s)"%str(e)[:50]
pc=unreal.GameplayStatics.get_player_controller(world,0); host=pc.get_controlled_pawn()
tsc=host.get_thrall_system_component()
hum=next((f for f in tsc.get_following_thrall_characters() if not f.is_mountable()),None)
ec=None
for c in hum.get_components_by_class(unreal.ActorComponent):
    if "Emote" in c.get_class().get_name():
        ec=c; break
print("emote controller:", ec.get_class().get_name() if ec else None)
if ec:
    ms=[m for m in dir(ec) if not m.startswith("_") and not m.startswith("get_") and not m.startswith("set_")]
    print("ALL methods:", ms)
    print("\ncurrent_emote_anim_montage:", call(ec,"current_emote_anim_montage") if hasattr(ec,"current_emote_anim_montage") else call(ec,"get_editor_property","current_emote_anim_montage"))
    print("can_emote:", call(ec,"can_emote"))
    # emote inventory (what emotes does it know)
    inv=call(hum,"get_emote_inventory")
    print("emote inventory:", inv if not isinstance(inv,(list,tuple)) else [str(x) for x in inv][:10])
