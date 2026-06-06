"""Backward-compat shim: `import bp_ir` -> bpkit.ir.

The canonical module is now bpkit.ir; this re-exports its full namespace so
existing in-editor payloads keep working unchanged. New code should
`from bpkit import ir`.
"""
from bpkit import ir as _m
globals().update({k: v for k, v in vars(_m).items() if not k.startswith("__")})
