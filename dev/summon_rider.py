import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)
RIDER = "/Game/Characters/NPCs/Necromancy_followers/Blueprints/BP_FiniteLifespanUndeadThrall.BP_FiniteLifespanUndeadThrall_C"
before = set(a.get_name() for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter))
unreal.SystemLibrary.execute_console_command(world, "Summon " + RIDER, pc)
print("summoned rider")
for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter):
    if a.get_name() not in before:
        print("  NEW:", a.get_name(), a.get_class().get_name())
