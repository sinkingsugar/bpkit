"""Ship a local Python file into the running editor and print its output.

Usage:
    python ue_run.py <local_script.py> [args...]

Runs <local_script.py>'s *source* inside the editor's interpreter via the
remote_execution channel (MODE_EXEC_FILE), so it shares the editor's address
space -- `import unreal`, `import ctypes`, and the already-loaded engine DLLs
are all in scope. stdout/stderr from the editor are echoed back here.

Before the payload runs, a separate setup command (the payload itself ships
verbatim) (1) drops any cached `bpkit*` modules so the payload always gets the
current library, (2) puts the repo root on the editor's sys.path so payloads can
`import bpkit` with NO hardcoded path, and (3) forwards any args after the script
name -- the payload reads them via `bpkit.config.argv()`.
Engine/endpoint paths come from bpkit.config (override via BPKIT_* env vars).
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # repo root -> import bpkit
from bpkit import config

sys.path.insert(0, config.PLUGIN_PY)
import remote_execution as remote


def _find_node(rec, timeout=10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if rec.remote_nodes:
            return rec.remote_nodes[0]
        time.sleep(0.25)
    return None


def main():
    if len(sys.argv) < 2:
        print("usage: python ue_run.py <script.py> [args...]")
        sys.exit(2)
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        src = f.read()

    rec = remote.RemoteExecution()
    rec.start()
    try:
        node = _find_node(rec)
        if not node:
            print("[!] no editor node found (remote exec off / editor closed)")
            sys.exit(1)
        rec.open_command_connection(node["node_id"])

        # Make the repo importable inside the editor (persists across calls in the
        # long-lived editor; idempotent). Shipped as its own command so the payload
        # below is still sent verbatim (MODE_EXEC_FILE is picky about a doctored cmd).
        boot = ("import sys, os\n"
                "for _m in list(sys.modules):\n"
                "    if _m == 'bpkit' or _m.startswith('bpkit.'):\n"
                "        sys.modules.pop(_m, None)\n"
                "_r = r'%s'\n"
                "if _r not in sys.path:\n"
                "    sys.path.insert(0, _r)\n"
                "os.environ['BPKIT_ARGV'] = %s\n"
                % (config.REPO_ROOT, repr(json.dumps(sys.argv[2:]))))
        rec.run_command(boot, exec_mode=remote.MODE_EXEC_FILE, raise_on_failure=False)

        res = rec.run_command(src, exec_mode=remote.MODE_EXEC_FILE, raise_on_failure=False)
        print("[+] success:", res.get("success"))
        for o in res.get("output") or []:
            print("    [{}] {}".format(o.get("type"), o.get("output", "").rstrip()))
        if res.get("result"):
            print("    result:", res.get("result"))
        rec.close_command_connection()
    finally:
        rec.stop()


if __name__ == "__main__":
    main()
