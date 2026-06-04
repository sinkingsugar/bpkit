# dev/ — reverse-engineering & journey scripts

These are the scratch scripts used to discover and validate the ctypes bridge:
PE export probing, FString/TSet/TArray layout introspection, the `ExportNodesToText`
crash hunt, and the staged write/read proofs. They're kept for provenance and as a
record of *how* the native struct layouts were nailed down safely.

**They target the pre-refactor API** (`import ue_bp_inject` from a `tools/` path) and
are not maintained against the current `bp_bridge` library — run them only as
reference. The canonical, supported entry points are `bp_bridge.py` and `examples/`.

Highlights:
- `pe_exports` (now at repo root) — dependency-free PE export-table dumper
- `introspect_tset.py` / `introspect_multi.py` / `probe_hashsize.py` — how the TSet
  binary layout was read off live UE-built sets (pure reads, no crashes)
- `isolate_export.py` / `test_overwrite.py` / `test_fmem*.py` — isolating the
  by-value `~TSet` / `FMemory::Free` crash cause and proving the fix
- `read_real_bp.py` — full-blueprint read driver (superseded by
  `examples/read_blueprint.py`)
