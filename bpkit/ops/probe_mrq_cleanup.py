"""Tear down the MRQ recv probe: destroy the spawned actor, disconnect the
executor socket, drop the builtins stash, delete the scratch BP."""
import unreal, builtins

state = getattr(builtins, "_mrq_probe", None)
if state:
    inst = state.get("inst")
    if inst:
        try:
            inst.destroy_actor(); print("actor destroyed")
        except Exception as e:
            print("actor destroy:", e)
    try:
        state["ex"].disconnect_socket(); print("socket disconnected")
    except Exception as e:
        print("disconnect:", e)
    del builtins._mrq_probe
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    if a.get_class().get_name().startswith("BP_MrqRecvProbe"):
        print("destroying stray:", a.get_name()); a.destroy_actor()
if unreal.EditorAssetLibrary.does_asset_exist("/Game/_Scratch/BP_MrqRecvProbe"):
    ok = unreal.EditorAssetLibrary.delete_asset("/Game/_Scratch/BP_MrqRecvProbe")
    print("scratch BP deleted:", ok)
print("CLEANUP DONE")
