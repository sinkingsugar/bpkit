import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def call(o,n,*a):
    try: return getattr(o,n)(*a)
    except Exception as e: return "ERR(%s)"%str(e)[:45]
pc = unreal.GameplayStatics.get_player_controller(world,0)
host = pc.get_controlled_pawn()
print("HOST pawn class:", host.get_class().get_name())
print("  get_player_state:", call(host,"get_player_state"))
print("  get_controller:", call(host,"get_controller").get_class().get_name() if call(host,"get_controller") and "ERR" not in str(call(host,"get_controller")) else call(host,"get_controller"))
print("  is_player_controlled:", call(host,"is_player_controlled"))
print("  is_mountable:", call(host,"is_mountable"))
print("  attach_parent:", call(host,"get_attach_parent_actor").get_name() if call(host,"get_attach_parent_actor") and "ERR" not in str(call(host,"get_attach_parent_actor")) else call(host,"get_attach_parent_actor"))
# and a following thrall, for comparison
tsc = host.get_thrall_system_component()
hum = next((f for f in tsc.get_following_thrall_characters() if not f.is_mountable()), None)
if hum:
    print("FOLLOWER class:", hum.get_class().get_name(), "| get_player_state:", call(hum,"get_player_state"), "| is_player_controlled:", call(hum,"is_player_controlled"))
