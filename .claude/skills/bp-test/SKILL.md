---
name: bp-test
description: Run the bpkit test suites — the offline library tests (no editor) and, if the editor is up, the in-editor authoring tests.
---

1. **Offline suite** (no editor needed): `& $py tests/test_offline.py` — reports `N/N passed`.
2. **In-editor suite** (only if the channel is live — quick-check `bpkit/ops/ping.py` first, and only with **Play stopped**): `& $py ue_run.py tests/test_bp_authoring.py`.
3. Report pass/fail counts for each suite and surface any failing assertion lines. If the editor isn't up, run the offline suite only and say the in-editor suite was skipped.

(`$py` = `bpkit.config.BUNDLED_PYTHON` or `$env:BPKIT_PYTHON`.)
