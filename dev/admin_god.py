import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)
try:
    print("is_admin:", pc.is_admin())
except Exception as e:
    print("is_admin err:", e)
cm = pc.conan_cheat_manager
# Re-fire god now that admin panel is open
try:
    cm.god()
    print("called cm.god()")
except Exception as e:
    print("god err:", e)
for cmd in ["God", "cheat God"]:
    unreal.SystemLibrary.execute_console_command(world, cmd, pc)
    print("exec:", cmd)
