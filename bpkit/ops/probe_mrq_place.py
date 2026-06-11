"""Place (or remove) the scratch BP_MrqEchoController in the editor level so PIE
duplicates it and its BeginPlay/Tick run in a real game world.
Usage: ue_run this file (places); pass-through cleanup is probe_mrq_place_off.py."""
import unreal

PATH = "/Game/_Scratch/BP_MrqEchoController"
bp_obj = unreal.load_asset(PATH)
assert bp_obj, "scratch controller missing -- run mods/mrq-echo/01_mrq.py first"
gen = unreal.BlueprintEditorLibrary.generated_class(bp_obj)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    if a.get_class().get_name().startswith("BP_MrqEchoController"):
        print("already placed:", a.get_name()); break
else:
    inst = eas.spawn_actor_from_class(gen, unreal.Vector(0.0, 0.0, -100000.0))
    print("placed:", inst.get_name())
