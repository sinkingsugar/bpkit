---
name: bp-channel
description: Quick check that the Unreal editor remote-exec channel is live. Use before driving the editor, or when in-editor calls seem to hang.
---

Run `& $py ue_run.py bpkit/ops/ping.py` (where `$py` = `bpkit.config.BUNDLED_PYTHON` or `$env:BPKIT_PYTHON`) and report whether the channel is up — an `ENGINE_VERSION` line means live. If it prints `no editor node found`, point the user at `/setup` (editor not running or Remote Execution off).
