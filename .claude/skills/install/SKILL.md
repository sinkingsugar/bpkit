---
name: install
description: Install the bpkit slash-commands into your personal ~/.claude/skills so they work from any project directory, not just this repo. Run once after pulling the repo (and again after repo updates).
disable-model-invocation: true
---

Install the bpkit skills for cross-project use:

`& $py bpkit/ops/install_skills.py`  ($py = `bpkit.config.BUNDLED_PYTHON` or `$env:BPKIT_PYTHON`)

This copies each skill in `.claude/skills/` to `~/.claude/skills/`, stamped with this repo's absolute path so the commands resolve from anywhere. Report what was installed, then tell the user: `/setup`, `/bp-channel`, `/bp-read <asset>`, and `/bp-test` now work in any project; if `~/.claude/skills` didn't exist before, restart Claude Code so the new directory is watched.
