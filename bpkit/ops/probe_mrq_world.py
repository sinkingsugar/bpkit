"""Read-only: which map is open in the editor, is it saved/dirty?"""
import unreal
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
print("world:", w.get_path_name())
pkg = w.get_outer()
print("package:", pkg.get_name())
print("dirty:", unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages())
