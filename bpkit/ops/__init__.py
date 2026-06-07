"""bpkit.ops -- operational tooling for driving the editor (not graph I/O).

Reusable on any UE project: editor liveness ping, PIE play/stop/state control
(via `pie`), host-side Slate-modal rescue, scratch-asset cleanup, log tail, and a
compile-error scanner.

- `ping` / `pie_play` / `pie_end` / `pie_state` / `cleanup_scratch` / `read_log`
  / `compile_errors` are ue_run payloads (run inside the editor).
- `dismiss_modal` is HOST-SIDE (run with the bundled python while a Slate modal
  has frozen the remote-execution channel).
- `pie` is the importable PIE-control helper the pie_* payloads use.

Reminder: do NOT start Play yourself unless asked -- the user controls PIE.
"""
