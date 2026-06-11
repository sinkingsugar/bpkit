"""Deploy manifest for the rcon-echo mod -- consumed by `/deploy` and
bpkit/ops/deploy.py. The cooked-game transport proof for the RCON->Blueprint
receive channel (the LLM-NPC RECV link; docs/CONAN-NOTES.md §Network).

    & $py ue_run.py bpkit/ops/deploy.py rcon-echo

PREREQ: the "RconEcho" mod must exist in the DevKit (Mods tool -> create mod)
and be the ACTIVE mod, else /Game/Mods/RconEcho is not writable. Cook must show
both BPs as (Mod Asset).
"""
import re_config as _cfg

NAME = "rcon-echo"
OUTPUT_PKG = _cfg.OUTPUT_PKG

BUILD = ["01_echo.py"]

ASSETS = []
