import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)

def by_tag(t):
    a = unreal.GameplayStatics.get_all_actors_with_tag(world, t); return a[0] if a else None

horse = by_tag("TEST_HORSE")
if horse:
    try:
        print("current horse embedded_saddle_id:", horse.get_embedded_saddle_id())
    except Exception as e:
        print("saddle id err:", e)
    try:
        print("current horse is_mountable():", horse.is_mountable())
    except Exception as e:
        print("is_mountable err:", e)

# Summon a Knight mount variant — does it come with a rider?
KNIGHT = "/Game/Characters/NPCs/Hooved_Wild/Blueprints/BP_NPC_Mounts_Horse_Knight.BP_NPC_Mounts_Horse_Knight_C"
before = set(a.get_name() for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter))
unreal.SystemLibrary.execute_console_command(world, "Summon " + KNIGHT, pc)
after = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter)
print("\nConanCharacters after Knight summon:", len(after))
for a in after:
    if a.get_name() not in before:
        knight = a
        print("NEW:", a.get_name(), a.get_class().get_name())
        try:
            print("  is_mountable:", a.is_mountable(), " get_rider:", a.get_rider(),
                  " embedded_saddle:", a.get_embedded_saddle_id())
        except Exception as e:
            print("  state err:", e)
        # any attached actors (a pre-mounted rider would be attached)?
        try:
            attached = a.get_attached_actors() if hasattr(a, "get_attached_actors") else None
            print("  attached actors:", attached)
        except Exception as e:
            print("  attached err:", e)
        a.tags = list(a.tags) + ["TEST_KNIGHT"]
