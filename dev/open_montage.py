import unreal
m = unreal.load_object(None, "/Game/_Scratch/AM_MF_idle_HORSE.AM_MF_idle_HORSE")
ss = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
ss.open_editor_for_assets([m])
print("opened montage editor for AM_MF_idle_HORSE (slot is currently DefaultSlot)")
