"""Call the compiled Restore on the existing manager (reverse of Stow)."""
import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def find(cls_name):
    for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        if cls_name in a.get_class().get_name():
            return a
    return None
mgr = find("BP_MF_Recipe")
rider = unreal.GameplayStatics.get_all_actors_with_tag(world, "TEST_RIDER")
rider = rider[0] if rider else None
horse = unreal.GameplayStatics.get_all_actors_with_tag(world, "TEST_HORSE")
horse = horse[0] if horse else None
print("mgr:", mgr.get_name() if mgr else None, "rider:", rider.get_name() if rider else None)
if not (mgr and rider and horse):
    print("!! missing actors"); raise SystemExit

rmesh = rider.get_editor_property("mesh")
before = rmesh.get_world_location()
mgr.call_method("Restore")
print(">>> called Restore on compiled BP")
after = rmesh.get_world_location()
sloc = horse.get_editor_property("mesh").get_socket_location("attachrider")
print("rider mesh before:", before)
print("rider mesh after :", after)
print("dist from socket now:", round((after - sloc).length(), 1),
      "=> ", "DETACHED (pass)" if (after - sloc).length() > 25 else "still on socket")
mc = rider.get_editor_property("character_movement")
print("movement mode after restore:", mc.get_editor_property("movement_mode") if mc else "?")
