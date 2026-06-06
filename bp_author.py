"""Backward-compat shim: `import bp_author` -> bpkit.author.

The canonical module is now bpkit.author; this re-exports its full namespace so
existing in-editor payloads keep working unchanged. New code should
`from bpkit import author`.
"""
from bpkit import author as _m
globals().update({k: v for k, v in vars(_m).items() if not k.startswith("__")})
