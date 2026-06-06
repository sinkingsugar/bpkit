"""Backward-compat shim: `import bp_bridge` -> bpkit.bridge.

The canonical module is now bpkit.bridge; this re-exports its full namespace so
existing in-editor payloads keep working unchanged. New code should
`from bpkit import bridge`.
"""
from bpkit import bridge as _m
globals().update({k: v for k, v in vars(_m).items() if not k.startswith("__")})
