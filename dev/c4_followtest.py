"""Try to make a 2nd horse follow by replicating the existing horse's follow state
directly (set followed PC + register with the thrall system), bypassing the
ThrallItem claim flow. Probe for the needed setters/registrars first."""
import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn()
tsc = pawn.get_thrall_system_component()

# what setters exist for follow state on a ConanCharacter + add-follower on tsc?
def members(obj, kws):
    return sorted(m for m in dir(obj) if not m.startswith("_")
                  and any(k in m.lower() for k in kws))
print("horse follow setters:", members(unreal.ConanCharacter,
      ("set_followed", "start_follow", "set_follow", "assign", "set_owner", "register")))
print("tsc add/register:", members(tsc,
      ("add", "register", "start_follow", "set_follow", "assign", "begin_follow")))
print("pc command_follower:", (pc.command_follower.__doc__ or "?").split("\n\n")[0]
      if hasattr(pc, "command_follower") else "MISSING")
