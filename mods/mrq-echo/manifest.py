"""Deploy manifest for the mrq-echo mod -- consumed by `/deploy` and
bpkit/ops/deploy.py. The cooked-game proof for the MRQ TCP push channel
(external process -> Blueprint recv; docs/CONAN-NOTES.md §Network).

    & $py ue_run.py bpkit/ops/deploy.py mrq-echo

PREREQ: the "MrqEcho" mod must exist in the DevKit (Mods tool -> create mod)
and be the ACTIVE mod, else /Game/Mods/MrqEcho is not writable (the build step
then dry-runs into /Game/_Scratch). Cook must show the BP as (Mod Asset).
"""
import me_config as _cfg

NAME = "mrq-echo"
OUTPUT_PKG = _cfg.OUTPUT_PKG

BUILD = ["01_mrq.py"]

ASSETS = []
