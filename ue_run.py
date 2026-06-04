"""Ship a local Python file into the running editor and print its output.

Usage:
    python ue_run.py <local_script.py>

Runs <local_script.py>'s *source* inside the editor's interpreter via the
remote_execution channel (MODE_EXEC_FILE), so it shares the editor's address
space — `import unreal`, `import ctypes`, and the already-loaded engine DLLs
are all in scope. stdout/stderr from the editor are echoed back here.

Payloads that need the library do `sys.path.insert(...); import bp_bridge`
themselves (see examples/) — MODE_EXEC_FILE is picky about a modified command,
so we ship the file's source verbatim.
"""
import sys, time

PLUGIN_PY = r"C:\Program Files\Epic Games\CEUE5Devkit\Engine\Plugins\Experimental\PythonScriptPlugin\Content\Python"
sys.path.insert(0, PLUGIN_PY)
import remote_execution as remote


def main():
    if len(sys.argv) < 2:
        print("usage: python ue_run.py <script.py>")
        sys.exit(2)
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        src = f.read()

    rec = remote.RemoteExecution()
    rec.start()
    node = None
    for _ in range(40):
        nodes = rec.remote_nodes
        if nodes:
            node = nodes[0]
            break
        time.sleep(0.25)
    if not node:
        print("[!] no editor node found (remote exec off / editor closed)")
        rec.stop()
        sys.exit(1)

    rec.open_command_connection(node["node_id"])
    res = rec.run_command(src, exec_mode=remote.MODE_EXEC_FILE, raise_on_failure=False)
    print("[+] success:", res.get("success"))
    for o in res.get("output") or []:
        print("    [{}] {}".format(o.get("type"), o.get("output", "").rstrip()))
    if res.get("result"):
        print("    result:", res.get("result"))
    rec.close_command_connection()
    rec.stop()


if __name__ == "__main__":
    main()
