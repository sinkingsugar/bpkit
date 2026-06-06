"""bpkit.config -- install paths + remote-execution endpoints.

Everything here is overridable via environment variables so the framework is not
welded to one engine install. The defaults target the Conan Exiles Enhanced Dev
Kit (UE 5.6.1) on this machine; point the BPKIT_* vars at another UE project to
reuse the whole toolchain elsewhere.

These values are HOST-SIDE (used by bpkit.remote / ue_run.py and the example
launchers). Code shipped into the editor doesn't need them -- it already runs in
the engine's address space.
"""
import os


def _env(key, default):
    return os.environ.get(key, default)


# Repo root = this package's parent dir. ue_run injects it onto the editor's
# sys.path so in-editor payloads can `import bpkit` / `import bp_bridge` without
# hardcoding an absolute path in every script.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The UE install (managed Epic Dev Kit). Override: BPKIT_ENGINE_ROOT.
ENGINE_ROOT = _env("BPKIT_ENGINE_ROOT", r"C:\Program Files\Epic Games\CEUE5Devkit")

# The editor's BUNDLED interpreter -- version-matched to PythonScriptPlugin. Bare
# `python` on this box hits the (disabled) Windows Store alias, so standalone
# clients and ue_run must use this. Override: BPKIT_PYTHON.
BUNDLED_PYTHON = _env(
    "BPKIT_PYTHON",
    os.path.join(ENGINE_ROOT, r"Engine\Binaries\ThirdParty\Python3\Win64\python.exe"))

# remote_execution.py ships with PythonScriptPlugin; host clients import it from
# here. Override: BPKIT_PLUGIN_PY.
PLUGIN_PY = _env(
    "BPKIT_PLUGIN_PY",
    os.path.join(ENGINE_ROOT,
                 r"Engine\Plugins\Experimental\PythonScriptPlugin\Content\Python"))

# Remote-execution endpoints (UE defaults; same-machine ready). Override:
# BPKIT_MCAST_GROUP / BPKIT_MCAST_PORT / BPKIT_CMD_PORT.
MULTICAST_GROUP = _env("BPKIT_MCAST_GROUP", "239.0.0.1")
MULTICAST_PORT = int(_env("BPKIT_MCAST_PORT", "6766"))
COMMAND_PORT = int(_env("BPKIT_CMD_PORT", "6776"))
