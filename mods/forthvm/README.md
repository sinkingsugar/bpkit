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
- ✅ In-editor mechanics — `test_vm.py`, **7/7**: typed cell Make/Break round-trip, typed stack
  push / read-back / length (the atomic ops the dispatch composes).
- ✅ **VM executes bytecode (floats + vectors)** — `build_vm.py` generates `BP_ForthVM` (a
  one-instruction `Step`: IP fetch → **Branch-chain dispatch** → stack ops) and runs programs via
  Python-driven Step, matching the oracle: `5.0 .` → `5.0`, `5.0 dup * .` → `25.0`, and
  `1.0 2.0 3.0 vec3 .` → `(1,2,3)`. Opcodes live: `LIT_FLOAT`, `DUP`, `MUL` (float), `MK_VEC`,
  `PRINT` (float+vec), `HALT`. 0 orphans, clean compile.
- ⏳ Remaining: **polymorphic** `+ - *` (vec+vec, scalar×vec, int→float promotion) + `LIT_INT`
  for the rest of the vector oracle cases, then `CALL`/`EXIT` for colon defs. The dispatch +
  arithmetic + vector-construction patterns are all proven — this is more handlers, not new unknowns.

> Two gotchas baked in: build `FVector` with the **`MakeVector` function**, not `MakeStruct`
> (`MakeStruct(FVector)` injects but fails to compile — "not a BlueprintType"); and graph-level
> compile errors don't appear on nodes — the spawn+call+assert is the real check (an inert Step
> that hits the step cap = a silent compile failure; grep `Saved/Logs/*.log` for `[Compiler]`).

> Dispatch is a Branch chain (`Equal_IntInt` + `IfThenElse` per opcode), not `SwitchInteger`:
> a switch's per-case pins can't be authored via paste (reconstruction drops them).

## Run (Play stopped, bundled `$py` — see the [root README](../../README.md))
```powershell
& $py ue_run.py mods/forthvm/00_create_fcell.py   # build ST_FCell (once per fresh editor session)
& $py mods/forthvm/test_offline.py                # offline VM spec (no editor)
& $py ue_run.py mods/forthvm/test_vm.py           # in-editor mechanics
& $py ue_run.py mods/forthvm/build_vm.py          # generate BP_ForthVM + run programs (5.0 .→5.0, 5.0 dup *.→25.0)
```

## Files
| file | role |
|---|---|
| `isa.py` | shared ISA: cell tags + opcodes (compiler / vm_ref / generator all import it) |
| `compiler.py` | Forth source → flat bytecode + typed literal pools (offline) |
| `vm_ref.py` | Python reference interpreter — the oracle the Blueprint must match |
| `config.py` | FCell layout + asset names / package |
| `00_create_fcell.py` | builds the `ST_FCell` struct programmatically (idempotent per session) |
| `build_vm.py` | **generates `BP_ForthVM`** (the interpreter) + runs bytecode programs and asserts vs the oracle |
| `test_offline.py` | offline VM spec (no editor) |
| `test_vm.py` | in-editor mechanics (spawn+call+assert) |
