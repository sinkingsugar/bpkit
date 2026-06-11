"""Remove the placed BP_MrqEchoController probe actor from the editor level and
re-save the map so it isn't left dirty."""
import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
n = 0
for a in eas.get_all_level_actors():
    if a.get_class().get_name().startswith("BP_MrqEchoController"):
        print("destroying:", a.get_name())
        a.destroy_actor(); n += 1
print("removed %d actor(s)" % n)
print("map saved:", unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, False))
