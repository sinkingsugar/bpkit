"""bpkit -- drive Unreal Engine Blueprint graphs from outside the editor.

Read, author, edit and compile UE5 Blueprint node graphs over the Python
remote-execution channel + an in-process ctypes bridge to the editor's exported
C++ entrypoints -- no C++ compilation, no editor UI, no clipboard, no focus.

Engine-agnostic core; the only install-specific knowledge lives in bpkit.config
(every value overridable via BPKIT_* environment variables). Defaults target the
Conan Exiles Enhanced Dev Kit (UE 5.6.1), but the framework itself is generic.

Public modules:
    bridge   -- the ctypes engine (read_blueprint / inject / export_nodes / ...).
                Runs INSIDE the editor (ship it with bpkit.remote / ue_run.py).
    ir       -- Graph IR: parse <-> edit <-> render <-> author. Pure stdlib.
    compact  -- navigable compaction of exported node text (~23x). Pure stdlib.
    pe       -- dependency-free PE export-table dumper (find symbol names).
    remote   -- host-side: ship a local .py into the running editor.
    config   -- paths + remote-exec endpoints (override via BPKIT_* env vars).

Root-level bp_bridge / bp_ir / bp_author / bp_compact / pe_exports modules remain
as thin compatibility shims so existing in-editor payloads keep importing them.
"""
__version__ = "0.1.0"
