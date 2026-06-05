"""Raise the player's 'Mount' follower-group cap (+5) so multiple horses can follow.
Runtime adjustment -> must be re-applied each fresh PIE session (the real mod does
this in the ModController's BeginPlay). Additive/mod-safe."""
import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn()
tsc = pawn.get_thrall_system_component()
tsc.add_thrall_group_limit_adjustment("Mount", 5)
print("Mount cap +5 applied. current group counts:", tsc.get_follower_group_counts())
