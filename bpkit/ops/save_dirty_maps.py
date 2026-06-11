"""Save dirty MAP packages only (content packages untouched). PIE refuses to
start over an unsaved dirty map when dialogs are suppressed ("PIE failed because
map save was canceled") -- run this before driving pie_play."""
import unreal
ok = unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, False)
print("saved dirty map packages:", ok)
print("still dirty:", unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages())
