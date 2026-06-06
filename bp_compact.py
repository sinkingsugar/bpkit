"""Backward-compat shim: `import bp_compact` -> bpkit.compact.

The canonical module is now bpkit.compact; this re-exports its full namespace so
existing payloads keep working unchanged, and preserves the CLI
(`python bp_compact.py <dump.txt> ...`). New code should `from bpkit import compact`
or `python -m bpkit.compact`.
"""
from bpkit import compact as _m
globals().update({k: v for k, v in vars(_m).items() if not k.startswith("__")})

if __name__ == "__main__":
    import sys
    _m._main(sys.argv[1:])
