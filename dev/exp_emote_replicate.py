import unreal
ar = unreal.AssetRegistryHelpers.get_asset_registry()
far = unreal.ARFilter(class_names=["AnimMontage"], recursive_classes=True)
emotes = [a for a in ar.get_assets(far) if "emote" in str(a.asset_name).lower()
          and any(k in str(a.asset_name).lower() for k in ("dance","sit","cheer","taunt","laugh"))]
print("emote montages:", [str(a.asset_name) for a in emotes[:10]])
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def call(o,n,*a):
    try: return getattr(o,n)(*a)
    except Exception as e: return "ERR(%s)"%str(e)[:45]
pc=unreal.GameplayStatics.get_player_controller(world,0); host=pc.get_controlled_pawn()
tsc=host.get_thrall_system_component()
hum=next((f for f in tsc.get_following_thrall_characters() if not f.is_mountable()),None)
if hum and emotes:
    em = emotes[0]
    mtg = unreal.load_object(None, "%s.%s" % (str(em.package_name), str(em.asset_name)))
    mesh = hum.get_editor_property("Mesh"); mesh.set_animation_mode(unreal.AnimationMode.ANIMATION_BLUEPRINT)
    ai = call(hum,"get_controller"); call(ai,"stop_emote")
    brain = ai.get_editor_property("brain_component") if ai and "ERR" not in str(ai) else None
    if brain: call(brain,"stop_logic","t")
    print("playing emote montage:", em.asset_name, "->", call(hum,"play_anim_montage", mtg, 0.3, ""))
    print(">> does the follower do this emote on BOTH screens, or only player 0?")
