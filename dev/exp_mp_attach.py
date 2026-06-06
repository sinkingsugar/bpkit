import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def call(o, n, *a):
    try: return getattr(o, n)(*a)
    except Exception as e: return "ERR(%s)" % str(e)[:50]

allc = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter)
horse = next((c for c in allc if c.is_mountable()), None)
hum = next((c for c in allc if (not c.is_mountable()) and "BasePlayerChar" not in c.get_class().get_name()), None)
print("horse:", horse.get_name() if horse else None, "| humanoid:", hum.get_name() if hum else None)
print("horse loc:", horse.get_actor_location() if horse else None)

if horse and hum:
    # move humanoid next to horse so it's obviously the test subject, then mesh-attach on the SERVER
    hum.set_actor_location(horse.get_actor_location(), False, True)
    hmesh = hum.get_editor_property("Mesh")
    mmesh = horse.get_editor_property("Mesh")
    r = unreal.AttachmentRule.SNAP_TO_TARGET
    ok = call(hmesh, "attach_to_component", mmesh, "attachrider", r, r, r, False)
    print("server-side mesh-attach humanoid->horse 'attachrider':", ok)
    print("humanoid mesh now attached to:", hmesh.get_attach_parent().get_owner().get_name()
          if hmesh.get_attach_parent() and hmesh.get_attach_parent().get_owner() else "?")
    print("\n>> HOST should see %s sitting on %s. Now CHECK THE OTHER CLIENT WINDOW:" % (
        hum.get_class().get_name(), horse.get_class().get_name()))
    print(">> does the joined client also see the NPC sitting on that horse?")
