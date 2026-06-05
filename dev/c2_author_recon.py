"""Nail the class paths + function owners C2's BeginPlay graph needs to author."""
import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn()
tsc = pawn.get_thrall_system_component()

print("ConanCharacter path:", unreal.ConanCharacter.static_class().get_path_name())
print("ModController path  :", unreal.ModController.static_class().get_path_name())
print("live tsc class      :", tsc.get_class().get_path_name())
print("native ThrallSystemComponent path:",
      unreal.ThrallSystemComponent.static_class().get_path_name() if hasattr(unreal, "ThrallSystemComponent") else "MISSING")

# which native class declares the functions we'll call? (check presence on native types)
def has(cls, m): return hasattr(cls, m)
print("\nConanCharacter.get_thrall_system_component:", has(unreal.ConanCharacter, "get_thrall_system_component"))
print("ConanCharacter.get_mount/get_rider:", has(unreal.ConanCharacter, "get_mount"), has(unreal.ConanCharacter, "get_rider"))
tscls = unreal.ThrallSystemComponent if hasattr(unreal, "ThrallSystemComponent") else None
if tscls:
    for m in ("add_thrall_group_limit_adjustment", "get_following_thrall_characters"):
        print("ThrallSystemComponent.%s:" % m, has(tscls, m))

# GameplayStatics getter return + pin: GetPlayerCharacter
print("\nGetPlayerCharacter doc:", (unreal.GameplayStatics.get_player_character.__doc__ or "?").split("\n\n")[0])
