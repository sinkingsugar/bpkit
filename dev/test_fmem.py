"""In-editor payload: validate FMemory-backed set-of-1 export. First a controlled
batch on a scratch graph, then the real graph[5] that crashed before."""
import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan\tools")
import importlib, ue_bp_inject as bpi
importlib.reload(bpi)
import unreal

# --- controlled batch ---
bp, full = bpi.scratch_blueprint(name="BP_FMem")
g = bpi.find_object("EventGraph", outer=bpi.find_object(full))
for i in range(5):
    bpi.import_nodes(g, 'Begin Object Class=/Script/UnrealEd.EdGraphNode_Comment '
                        'Name="FM_%d"\n   NodeComment="FMARK-%d"\nEnd Object\n' % (i, i))
nodes = bpi.objects_with_outer(g, include_nested=False)
text = bpi.export_pointers_individually(nodes)
got = sum(("FMARK-%d" % i) in text for i in range(5))
print("controlled: %d nodes, %d Begin Object, %d/5 markers, chars=%d"
      % (len(nodes), text.count("Begin Object"), got, len(text)))

# --- the previously-fatal real graph[5] ---
ASSET = "/Game/Sorcery/Glider/BP_BatDemonGlider"
FULL = ASSET + "." + ASSET.rsplit("/", 1)[1]
unreal.EditorAssetLibrary.load_asset(ASSET)
graphs = bpi.get_all_graphs(bpi.find_object(FULL))
g5 = graphs[5]
n5 = bpi.objects_with_outer(g5, include_nested=False)
t5 = bpi.export_pointers_individually(n5)
print("real graph[5]: %d nodes, %d Begin Object, chars=%d"
      % (len(n5), t5.count("Begin Object"), len(t5)))
