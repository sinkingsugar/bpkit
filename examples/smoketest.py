"""Remote-execution connectivity smoke test (standalone client).

    python examples/smoketest.py

Opens its OWN remote_execution connection (does NOT go through ue_run) and runs
a tiny payload in the editor. Paths/endpoints come from bpkit.config
(override via BPKIT_* env vars).
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root
from bpkit import config

sys.path.insert(0, config.PLUGIN_PY)
import remote_execution as remote

rec = remote.RemoteExecution()
rec.start()
print("[*] searching for editor nodes (multicast %s:%d)..."
      % (config.MULTICAST_GROUP, config.MULTICAST_PORT))

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
