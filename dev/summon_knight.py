import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)

KNIGHTS = [
    "/Game/Characters/NPCs/Hooved_Wild/Blueprints/BP_NPC_Mounts_Horse_Knight.BP_NPC_Mounts_Horse_Knight_C",
    "/Game/Characters/NPCs/Hooved_Wild/Blueprints/BP_NPC_Mounts_Horse_Demon.BP_NPC_Mounts_Horse_Demon_C",
]

before = set(a.get_name() for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter))
for path in KNIGHTS:
    c = unreal.load_object(None, path)
    print("preload", path.rsplit("/",1)[1], "->", c is not None)
    if c:
        unreal.SystemLibrary.execute_console_command(world, "Summon " + path, pc)
        print("  summoned")

after = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter)
print("\nConanCharacters now:", len(after))
for a in after:
    if a.get_name() not in before:
        cn = a.get_class().get_name()
        try: rider = a.get_rider()
        except Exception: rider = "?"
        try: sad = a.get_embedded_saddle_id()
        except Exception: sad = "?"
        try: attached = a.get_attached_actors()
        except Exception as e: attached = "err:%s" % e
        print("NEW:", a.get_name(), "| class", cn)
        print("   get_rider=", rider, " saddle=", sad)
        print("   attached_actors=", [x.get_name() for x in attached] if isinstance(attached, list) else attached)
