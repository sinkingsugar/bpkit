import unreal
EAL = unreal.EditorAssetLibrary
targets = [
    "/Game/_Scratch/_tests/BP_T_ForEach",
    "/Game/_Scratch/_tests/BP_T_ForEachEmpty",
    "/Game/_Scratch/_tests/BP_T_TypedDefault",
]
for t in targets:
    if EAL.does_asset_exist(t):
        try:
            ok = EAL.delete_asset(t)
        except Exception as e:
            ok = "EXC:%s" % e
        print("delete_asset %s -> %s" % (t, ok))
    else:
        print("absent:", t)
# try the dir again (now empty)
d = "/Game/_Scratch/_tests"
if EAL.does_directory_exist(d):
    print("delete_directory %s -> %s" % (d, EAL.delete_directory(d)))
print("remaining in _tests:",
      EAL.list_assets(d, recursive=True, include_folder=False) if EAL.does_directory_exist(d) else "(gone)")
