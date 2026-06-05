import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)
print("world:", world.get_name() if world else None)
print("pc:", pc.get_name() if pc else None, "| is_admin:",
      pc.is_admin() if (pc and hasattr(pc, "is_admin")) else "?")

def counts():
    cc = len(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter))
    pw = len(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Pawn))
    ac = len(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor))
    return cc, pw, ac

print("before (ConanChar, Pawn, Actor):", counts())
UNDEAD = "/Game/Characters/NPCs/Necromancy_followers/Blueprints/BP_FiniteLifespanUndeadThrall.BP_FiniteLifespanUndeadThrall_C"
unreal.SystemLibrary.execute_console_command(world, "Summon " + UNDEAD, pc)
print("issued Summon")
print("after  (ConanChar, Pawn, Actor):", counts())

# Try alternate: spawn via class load + SpawnActor (won't work in PIE per prior finding, but confirm)
print("\n-- also try a known-different cheat: 'SpawnItem'/'GiveItem' irrelevant; check console works --")
unreal.SystemLibrary.execute_console_command(world, "stat fps", pc)
print("issued 'stat fps' (toggle) — if you SEE fps stat appear in PIE, console commands ARE reaching the game")
