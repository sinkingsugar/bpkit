# forthvm — a typed bytecode VM that runs as a Blueprint

A Forth-style stack VM authored entirely with [`bpkit`](../../README.md) so it runs as a
**compiled Blueprint** — in-game scripting (a console, data-driven behaviour, sandboxed
player scripts) with **no native code, no injection, no anti-cheat exposure**, fully
distributable as content. It's the inverse of poking the live game from outside: you build
the scripting layer *up* from sanctioned Blueprint primitives.

## Why a typed cell (the load-bearing decision)
It's a game, so `float`, `vector`, `rotator` and `transform` are first-class from day one,
not bolted on. The stack element is **`ST_FCell`** — a tagged variant struct with 7
**distinct-typed** fields (`Type:int`, plus `int64`, `real`, `bool`, `Vector`, `Rotator`,
`Transform`), so the generator maps each Make/Break pin to its role *by type*. The struct is
authored **fully programmatically** (no manual struct editor) via the ctypes bridge
(`bridge.add_struct_variable` → `FStructureEditorUtils::AddVariable`).

## Architecture
- **Offline** (`isa` / `compiler` / `vm_ref`): the ISA, a Forth→bytecode compiler (typed
  literal pools), and a Python **reference VM** that is the executable spec/oracle
  (polymorphic `+ - *`, int→float promotion, scalar×vector, step-budget coroutine).
  Compilation happens off-editor; the Blueprint only runs bytecode.
- **In-editor** (the VM Blueprint): `ST_FCell` stacks (`TArray<ST_FCell>`), an instruction
  pointer, and a **`Step` that executes one instruction** (Switch-on-opcode dispatch). The
  loop is "call `Step` until `Running=false`" — a Tick in-game, Python in tests — which keeps
  the hardest-to-author piece (a back-wired BP loop) out of the graph.

## Status
- ✅ Offline VM — `test_offline.py`, **16/16** (the oracle: `5.0 DUP * → 25.0`, vec add, scalar×vec).
- ✅ `ST_FCell` built fully programmatically — `00_create_fcell.py` (7 distinct-typed members, saved).
- ✅ In-editor mechanics — `test_vm.py`, **7/7**: typed cell Make/Break round-trip, and typed
  stack push / read-back / length (the atomic ops the dispatch composes).
- ⏳ Remaining: the `Switch`-on-int dispatch with polymorphic `+ - *`, the rest of the opcodes
  (pop/dup/swap/print/mk_vec…), and integration running a compiled program end-to-end
  (Python-driven `Step`). All authoring unknowns (struct authoring, typed cells, typed
  struct-array ops, pin names) are resolved — this is sizeable but de-risked graph-gen.

## Run (Play stopped, bundled `$py` — see the [root README](../../README.md))
```powershell
& $py ue_run.py mods/forthvm/00_create_fcell.py   # build ST_FCell (once per fresh editor session)
& $py mods/forthvm/test_offline.py                # offline VM spec (no editor)
& $py ue_run.py mods/forthvm/test_vm.py           # in-editor mechanics
```

## Files
| file | role |
|---|---|
| `isa.py` | shared ISA: cell tags + opcodes (compiler / vm_ref / generator all import it) |
| `compiler.py` | Forth source → flat bytecode + typed literal pools (offline) |
| `vm_ref.py` | Python reference interpreter — the oracle the Blueprint must match |
| `config.py` | FCell layout + asset names / package |
| `00_create_fcell.py` | builds the `ST_FCell` struct programmatically (idempotent per session) |
| `test_offline.py` | offline VM spec (no editor) |
| `test_vm.py` | in-editor mechanics (spawn+call+assert) |
