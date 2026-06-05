import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
import unreal
import bp_bridge as bp

FULL = "/Game/_Scratch/BP_MF_Recipe.BP_MF_Recipe"
gc = unreal.load_object(None, FULL + "_C")

# spawn an instance in the EDITOR world and resolve the custom events dynamically
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
inst = eas.spawn_actor_from_class(gc, unreal.Vector(0, 0, 0))
print("instance:", inst.get_name() if inst else None)
for fn in ("Stow", "Restore"):
    try:
        inst.call_method(fn)          # Rider/Mount null -> harmless Accessed-None
        print("  %s -> RESOLVED + ran" % fn)
    except Exception as e:
        print("  %s -> %s" % (fn, str(e).splitlines()[-1][:90]))
if inst:
    eas.destroy_actor(inst)

# dump the attach node's real pin defaults (loose, no regex assumptions)
bp_ptr, graph_ptr = bp.find_graph(FULL, "EventGraph")
txt = bp.export_nodes(bp.graph_nodes(graph_ptr))
print("\n-- K2_AttachToComponent node pins (verbatim) --")
grab = False
for line in txt.splitlines():
    s = line.strip()
    if "K2_AttachToComponent" in s:
        grab = True
    if grab and s.startswith("CustomProperties Pin") and ("Rule" in s or "SocketName" in s):
        print("   ", s[:150])
    if grab and s.startswith("End Object"):
        grab = False
