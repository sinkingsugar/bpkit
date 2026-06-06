"""Backward-compat shim: `import pe_exports` -> bpkit.pe.

The canonical module is now bpkit.pe; this re-exports its full namespace so
existing scripts keep working unchanged, and preserves the CLI
(`python pe_exports.py <dll> [substr ...]`). New code should `from bpkit import pe`
or `python -m bpkit.pe`.
"""
from bpkit import pe as _m
globals().update({k: v for k, v in vars(_m).items() if not k.startswith("__")})

if __name__ == "__main__":
    _m.main()
