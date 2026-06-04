"""In-editor payload: MINIMAL careful validation of the FMemory-backed set-of-1
export. Exports a few nodes one at a time, ABORTING on the first fault. Success
= zero faults AND every export non-empty. Keep blast radius tiny."""
import sys, ctypes
sys.path.insert(0, r"C:\Users\sugar\devel\conan\tools")
import importlib, ue_bp_inject as bpi
importlib.reload(bpi)

bp, full = bpi.scratch_blueprint(name="BP_FMemCareful")
g = bpi.find_object("EventGraph", outer=bpi.find_object(full))
for i in range(3):
    bpi.import_nodes(g, 'Begin Object Class=/Script/UnrealEd.EdGraphNode_Comment '
                        'Name="FC_%d"\n   NodeComment="FCMARK-%d"\nEnd Object\n' % (i, i))

nodes = bpi.objects_with_outer(g, include_nested=False)
print("graph has %d nodes; exporting one at a time..." % len(nodes))

exp = bpi._export_nodes()
malloc = bpi._fmemory_malloc()
faults = 0
empties = 0
for i, p in enumerate(nodes):
    try:
        t = bpi._make_set1_uemem(p, malloc)
        out = bpi.FString()
        exp(ctypes.byref(t), ctypes.byref(out))
        txt = bpi.read_fstring(out)
        print("  node[%d] ptr=%s -> %d chars %s"
              % (i, hex(p), len(txt), "(EMPTY!)" if not txt else ""))
        if not txt:
            empties += 1
    except OSError as e:
        faults += 1
        print("  node[%d] -> FAULT %s  ** ABORTING **" % (i, e))
        break

print("RESULT: faults=%d empties=%d of %d" % (faults, empties, len(nodes)))
print("VERDICT:", "FIX WORKS" if (faults == 0 and empties == 0) else "STILL BROKEN")
