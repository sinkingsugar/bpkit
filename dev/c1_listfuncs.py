import unreal
FULL = "/Game/_Scratch/BP_MF_Recipe.BP_MF_Recipe"
bp = unreal.load_asset("/Game/_Scratch/BP_MF_Recipe")
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
gc = unreal.load_object(None, FULL + "_C")
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
inst = eas.spawn_actor_from_class(gc, unreal.Vector(0, 0, 0))
print("inst:", inst.get_name() if inst else None)
base = set(dir(unreal.Actor))
extra = sorted(m for m in dir(inst) if m not in base and not m.startswith("_"))
print("BP-added python members:", extra)
# also try calling via snake_case if present
for nm in ("stow", "restore"):
    if hasattr(inst, nm):
        try:
            getattr(inst, nm)()
            print(nm, "() ran")
        except Exception as e:
            print(nm, "err:", str(e).splitlines()[-1][:80])
    else:
        print(nm, "NOT a python method")
if inst:
    eas.destroy_actor(inst)
