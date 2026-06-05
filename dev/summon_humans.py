"""Load human NPC classes into memory FIRST (so Summon can resolve them), summon
each, and report. Spawns deferred — recount in a follow-up run."""
import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)

CANDS = [
    "/Game/Characters/NPCs/Humanoid/HumanoidNPCCharacter_Nordheimer.HumanoidNPCCharacter_Nordheimer_C",
    "/Game/Characters/NPCs/Humanoid/HumanoidNPCCharacter_NordheimerHulda.HumanoidNPCCharacter_NordheimerHulda_C",
    "/Game/Characters/NPCs/Humanoid/HumanoidNPCCharacter_RelicHunters.HumanoidNPCCharacter_RelicHunters_C",
]
print("ConanChars now:", len(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter)))
for path in CANDS:
    cls = unreal.load_object(None, path)
    print("load", path.rsplit("/", 1)[-1], "->", "OK" if cls else "FAIL")
    if cls:
        unreal.SystemLibrary.execute_console_command(world, "Summon " + path, pc)
print("issued summons (deferred); recount next run")
