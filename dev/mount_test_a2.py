"""Spawn a horse via EditorActorSubsystem and report WHICH world it lands in
(PIE vs editor) + whether it gets an AI controller. Decides our spawn path."""
import unreal

ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
gw = ues.get_game_world()
print("game world:", gw.get_path_name() if gw else None)
player = unreal.GameplayStatics.get_player_pawn(gw, 0) if gw else None
ploc = player.get_actor_location() if player else unreal.Vector(0, 0, 200)
print("player loc:", ploc)

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
horse_cls = unreal.load_object(None, "/Game/Characters/NPCs/Hooved_Wild/Blueprints/BP_NPC_Mounts_Horse.BP_NPC_Mounts_Horse_C")
loc = unreal.Vector(ploc.x + 500, ploc.y, ploc.z + 100)
horse = eas.spawn_actor_from_class(horse_cls, loc, unreal.Rotator(0, 0, 0))
print("spawned:", horse)
if horse:
    print("  horse.get_world():", horse.get_world().get_path_name())
    print("  is in PIE world:", "UEDPIE" in horse.get_world().get_path_name())
    horse.tags = ["TEST_HORSE"]
    try:
        horse.spawn_default_controller()
        print("  controller:", horse.get_controller())
    except Exception as e:
        print("  ctrl err:", e)
