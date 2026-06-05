import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
for _m in ("bp_ir", "bp_bridge"): sys.modules.pop(_m, None)
import unreal, re
import bp_bridge as bp
import bp_ir as ir
BEL = unreal.BlueprintEditorLibrary

PKG = "/Game/_Scratch/_probe"
name = "BP_Probe_Typed"
path = PKG + "/" + name
if unreal.EditorAssetLibrary.does_asset_exist(path):
    unreal.EditorAssetLibrary.delete_asset(path)
obj, _ = bp.scratch_blueprint(pkg=PKG, name=name, parent=unreal.Character)
full = path + "." + name

g = ir.Graph("EventGraph")
ev = g.event("ReceiveBeginPlay")
mesh = g.var_get("Mesh", "object", ir.obj_path("/Script/Engine.SkeletalMeshComponent"))
n = g.call("SetAnimationMode", "/Script/Engine.SkeletalMeshComponent")
g.wire(mesh, "Mesh", n, "self", exec=False)
g.typed_input(n, "InAnimationMode", "AnimationSingleNode", "byte",
              ir.enum_path("/Script/Engine.EAnimationMode"))
g.wire(ev, "then", n, "execute", exec=True)
bp_ptr, gp = bp.find_graph(full, "EventGraph")
bp.clear_graph(bp_ptr, gp)
print("inject:", bp.inject(full, g.render(), graph_name="EventGraph"))
BEL.compile_blueprint(unreal.load_asset(path))
txt = bp.export_nodes(bp.graph_nodes(gp))
errs = [b.splitlines()[0] for b in re.split(r'(?=Begin Object Class=)', txt) if "ErrorMsg" in b]
print("ORPHANS:", re.findall(r'PinName="[^"]+"[^)]*?bOrphanedPin=True', txt))
print("COMPILE ERRORS:", errs if errs else "(none)")
# show the SetAnimationMode self pin + Mesh node linkage
for blk in re.split(r'(?=Begin Object Class=)', txt):
    if "SetAnimationMode" in blk or 'MemberName="Mesh"' in blk:
        for l in blk.splitlines():
            if "self" in l.lower() or "Mesh" in l or "LinkedTo" in l:
                print("  |", l.strip()[:140])
unreal.EditorAssetLibrary.delete_directory(PKG)
print("cleaned probe")
