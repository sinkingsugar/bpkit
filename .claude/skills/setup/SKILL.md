---
name: setup
description: One-time setup / health check for bpkit — verify the editor remote-exec channel, Python, and Remote Execution are ready. Run after pulling the repo.
disable-model-invocation: true
---

Run the bpkit readiness check and report a short status + the single next action.

1. **Python:** use `bpkit.config.BUNDLED_PYTHON` (or `$env:BPKIT_PYTHON`). On the Conan Dev Kit box, bare `python` hits the disabled Windows Store alias — use the engine's bundled interpreter.
2. **Ping the channel:** `& $py ue_run.py bpkit/ops/ping.py`.
3. **Report based on the output:**
   - Prints `ENGINE_VERSION` → channel is **LIVE**. Tell the user they're ready: `/bp-channel`, `/bp-read <asset>`, `/bp-test`, and `/install` to use these from any project directory.
   - `no editor node found` → editor unreachable. Steps: (1) launch the Dev Kit editor, (2) **Project Settings → Plugins → Python → enable "Remote Execution"**, (3) re-run `/setup`.
   - Python path error → set `$env:BPKIT_PYTHON` to `<UE-install>\Engine\Binaries\ThirdParty\Python3\Win64\python.exe` (or edit `BPKIT_ENGINE_ROOT` in `bpkit/config.py`).
