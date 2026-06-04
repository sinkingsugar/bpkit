import sys, time

PLUGIN_PY = r"C:\Program Files\Epic Games\CEUE5Devkit\Engine\Plugins\Experimental\PythonScriptPlugin\Content\Python"
sys.path.insert(0, PLUGIN_PY)

import remote_execution as remote

rec = remote.RemoteExecution()
rec.start()
print("[*] searching for editor nodes (multicast 239.0.0.1:6766)...")

node = None
for _ in range(40):                      # ~10s
    nodes = rec.remote_nodes
    if nodes:
        node = nodes[0]
        break
    time.sleep(0.25)

if not node:
    print("[!] NO NODE FOUND -- editor not listening / remote exec off / endpoint mismatch")
    rec.stop()
    sys.exit(1)

print("[+] found node:", node)
rec.open_command_connection(node["node_id"])

cmd = (
    "import unreal\n"
    "unreal.log('>>> hello from external python (smoke test) <<<')\n"
    "print('ENGINE_VERSION', unreal.SystemLibrary.get_engine_version())\n"
    "print('PROJECT_DIR', unreal.Paths.project_dir())\n"
)
res = rec.run_command(cmd, exec_mode=remote.MODE_EXEC_FILE, raise_on_failure=False)

print("[+] success:", res.get("success"))
for o in res.get("output") or []:
    print("    [{}] {}".format(o.get("type"), o.get("output", "").rstrip()))
if res.get("result"):
    print("    result:", res.get("result"))

rec.close_command_connection()
rec.stop()
print("[*] done")
