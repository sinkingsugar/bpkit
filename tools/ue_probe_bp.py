import sys, time
PLUGIN_PY = r"C:\Program Files\Epic Games\CEUE5Devkit\Engine\Plugins\Experimental\PythonScriptPlugin\Content\Python"
sys.path.insert(0, PLUGIN_PY)
import remote_execution as remote

PROBE = r'''
import unreal

def line(s): print(s)

line("=== A. load the Bat Demon spell BP (the one from the chat) ===")
P = "/Game/Sorcery/Spells/Bat_Demon_Glider/BP_Spell_BatDemon_Glider"
bp = None
try:
    exists = unreal.EditorAssetLibrary.does_asset_exist(P)
    line("exists: %s" % exists)
    if exists:
        bp = unreal.load_asset(P)
        line("loaded type: %s" % type(bp).__name__)
        line("parent class: %s" % unreal.BlueprintEditorLibrary.get_blueprint_class(bp))
except Exception as e:
    line("ERR load: %r" % e)

line("")
line("=== B. graph/node editing classes reflected to Python? ===")
for key in ("K2Node","EdGraph","KismetEditor","BlueprintEditorLibrary","GraphEditor"):
    hits = [c for c in dir(unreal) if key.lower() in c.lower()]
    line("%-22s -> %d  %s" % (key, len(hits), hits[:6]))

line("")
line("=== C. BlueprintEditorLibrary methods (node/graph/var/func/compile) ===")
ms = [m for m in dir(unreal.BlueprintEditorLibrary) if not m.startswith("_")]
for kw in ("node","graph","variable","function","compile","event"):
    line("  %-9s: %s" % (kw, [m for m in ms if kw in m.lower()]))

line("")
line("=== D. can we read the function graphs off the bp object? ===")
if bp:
    for prop in ("function_graphs","uber_graph_pages","ubergraph_pages","new_variables"):
        try:
            v = bp.get_editor_property(prop)
            line("  %s -> OK (%s)" % (prop, type(v).__name__))
        except Exception as e:
            line("  %s -> %r" % (prop, e))

line("")
line("=== E. compile + variable APIs callable? ===")
for path in ("unreal.BlueprintEditorLibrary.compile_blueprint",
             "unreal.BlueprintEditorLibrary.add_member_variable",
             "unreal.KismetEditorUtilities",
             "unreal.AssetToolsHelpers.get_asset_tools",
             "unreal.SubobjectDataSubsystem"):
    try:
        obj = eval(path)
        line("  %-55s -> present" % path)
    except Exception as e:
        line("  %-55s -> MISSING (%r)" % (path, e))

line("")
line("=== F. anything anywhere with 'spawn'/'node'/'pin' for graphs? ===")
cand = [c for c in dir(unreal) if any(k in c for k in ("Kismet","Blueprint","Graph","K2"))]
line("  candidate classes: %s" % cand[:25])
line("=== PROBE DONE ===")
'''

rec = remote.RemoteExecution(); rec.start()
node = None
for _ in range(40):
    n = rec.remote_nodes
    if n: node = n[0]; break
    time.sleep(0.25)
if not node:
    print("[!] no editor node"); rec.stop(); sys.exit(1)
rec.open_command_connection(node["node_id"])
res = rec.run_command(PROBE, exec_mode=remote.MODE_EXEC_FILE, raise_on_failure=False)
print("success:", res.get("success"))
for o in res.get("output") or []:
    print(o.get("output","").rstrip())
rec.close_command_connection(); rec.stop()
