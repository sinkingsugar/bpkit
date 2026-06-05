"""Phase 1: summon a persistent human NPC + the recipe manager. Spawns are deferred
a frame, so phase 2 (dev/c1_pie_test.py) detects + tests them on the next run."""
import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)

def n_chars():
    return len(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter))

HUMANS = [
    "/Game/Characters/NPCs/Humanoid/HumanoidNPCCharacter_Nordheimer.HumanoidNPCCharacter_Nordheimer_C",
]
RECIPE = "/Game/_Scratch/BP_MF_Recipe.BP_MF_Recipe_C"

print("ConanChars before:", n_chars())
for h in HUMANS:
    unreal.SystemLibrary.execute_console_command(world, "Summon " + h, pc)
    print("issued Summon:", h.rsplit("/", 1)[-1])
unreal.SystemLibrary.execute_console_command(world, "Summon " + RECIPE, pc)
print("issued Summon: BP_MF_Recipe (manager)")
print("(spawns are deferred — run dev/c1_pie_test.py next to detect + test)")
