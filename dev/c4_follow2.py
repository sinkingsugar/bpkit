import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn()

# existing horse -> exact class path + how to get its ThrallComponent
horse = None
for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter):
    if "Mounts_Horse" in c.get_class().get_name():
        horse = c; break
print("existing horse class path:", horse.get_class().get_path_name() if horse else None)
tc = horse.get_thrall_component() if hasattr(horse, "get_thrall_component") else None
print("horse.get_thrall_component():", tc.get_class().get_name() if tc else None)
comps = horse.get_components_by_class(unreal.ThrallComponent) if hasattr(unreal, "ThrallComponent") else []
print("ThrallComponents on horse:", [c.get_class().get_name() for c in comps])

# summon a 2nd horse using the EXACT path (append _C for the class)
path = horse.get_class().get_path_name()   # already the _C generated class path
n0 = len(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter))
unreal.SystemLibrary.execute_console_command(world, "Summon " + path, pc)
print("summoned via", path, "| chars before:", n0)
