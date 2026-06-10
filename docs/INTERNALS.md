# Internals — the ctypes bridge

How `bpkit.bridge` reads and writes Blueprint graphs by calling the editor's
exported C++ functions in-process. This is the hard-won core; read
[ARCHITECTURE.md](ARCHITECTURE.md) first for the why.

Everything here was probed and validated live against **UE 5.6.1**
(`5.6.1-364449+++exiles+release`, content-only Conan Exiles Enhanced Dev Kit).
Offsets/signatures are engine-version-specific; re-derive them on a different UE.

---

## 1. Transport: the remote-execution channel

The editor ships Epic's `PythonScriptPlugin` **compiled**, with Remote Execution
available (Project Settings → Plugins → Python → *Enable Remote Execution*). A
host client talks to it over `remote_execution.py` (multicast `239.0.0.1:6766`,
command `127.0.0.1:6776` by default; see `bpkit.config`). Code sent this way runs
**inside** the editor process — the prerequisite for everything below.

Two distinct usage patterns — **don't cross them**:
- **Standalone client** (`examples/smoketest.py`) — opens its own
  `remote_execution` connection and runs a payload.
- **`ue_run.py <payload>`** — ships `<payload>`'s *source* into the editor
  (`MODE_EXEC_FILE`) and echoes output. `<payload>` must be editor-side code
  (`import unreal`, …). `ue_run` first sends a tiny idempotent setup command that
  puts the repo root on the editor's `sys.path`, so payloads can `import bpkit`
  with no hardcoded path.

Gotchas that cost real time:
- **Which Python.** Bare `python` on the dev box hits the (disabled) Windows Store
  alias. Always use the editor's **bundled** interpreter (`bpkit.config.BUNDLED_PYTHON`)
  for both `ue_run` and standalone clients, so versions match the plugin.
- **Don't double-wrap.** `ue_run.py examples/smoketest.py` runs the *client*
  inside the editor, which then multicast-discovers nothing and prints
  `NO NODE FOUND` — looks like a dead channel but isn't. If `ue_run` echoes any
  `[Info]` lines, the channel is fine. Liveness check: `ue_run.py bpkit/ops/ping.py`.
- **Module cache.** The long-lived editor caches imported modules across `ue_run`
  calls, so after editing a `bpkit` lib a payload gets the **stale** version.
  Force a reload at the top of the payload:
  ```python
  import sys
  for m in list(sys.modules):
      if m == "bpkit" or m.startswith("bpkit."):
          sys.modules.pop(m, None)
  ```
  (or `importlib.reload` in dependency order: compact → ir → bridge).
- **Never author/compile a Blueprint during PIE.** It breaks live instances'
  function resolution. Author + compile with Play stopped; only read/call during
  Play. Check first: `unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor()`.

## 2. Resolving the exported functions

`bpkit.pe` is a dependency-free PE export-table dumper — point it at a loaded
editor DLL to find the **exact MSVC-decorated symbol names**:

```
python -m bpkit.pe "<dll path>" ImportNodesFromText ExportNodesToText
```

`bpkit.bridge.resolve(key)` then does `GetModuleHandleW(dll)` + `GetProcAddress(name)`
and caches the address; `proc(key, restype, *argtypes)` wraps it in a cached
`ctypes.CFUNCTYPE`. The symbols used (decorated names in `bridge.SYM`):

| Purpose | DLL | C++ signature |
|---|---|---|
| find object by path/subobject | CoreUObject | `StaticFindObject(UClass*, UObject* outer, const TCHAR*, bool exact)` |
| enumerate children | CoreUObject | `GetObjectsWithOuter(const UObjectBase*, TArray<UObject*>&, bool, …)` |
| all graphs of a BP | Engine | `UBlueprint::GetAllGraphs(TArray<UEdGraph*>&) const` |
| paste oracle (non-mutating) | UnrealEd | `FEdGraphUtilities::CanImportNodesFromText(const UEdGraph*, const FString&)` |
| paste (mutating) | UnrealEd | `FEdGraphUtilities::ImportNodesFromText(UEdGraph*, const FString&, TSet<UEdGraphNode*>&)` |
| serialize nodes | UnrealEd | `FEdGraphUtilities::ExportNodesToText(TSet<UObject*> /*byval*/, FString&)` |
| mark dirty | UnrealEd | `FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(UBlueprint*)` |
| delete a node | UnrealEd | `FBlueprintEditorUtils::RemoveNode(UBlueprint*, UEdGraphNode*, bool)` |
| UE allocator | Core | `FMemory::Malloc(SIZE_T, uint32 alignment)` |

## 3. Marshalling UE containers with ctypes

- **`FString`** == `TArray<TCHAR>`: `{ TCHAR* data; int32 num; int32 max }` where
  `num`/`max` **include** the null terminator. `FString.make(s)` pins a
  `create_unicode_buffer`; an empty `FString()` is the valid zeroed out-param.
- **`TArray<T*>`** == `{ ptr; int32 num; int32 max }`. Read back with the helper
  that decodes `ptr`+`num` into a Python list of addresses.
- **`TSet<T*>`** is the tricky one — needed because `ImportNodesFromText` takes an
  out-`TSet&` and `ExportNodesToText` takes a `TSet` **by value**. Layout read off
  live UE-built sets (a value-zeroed `TSet` is the valid empty state):

  | offset | field |
  |---|---|
  | 0 | `Elements.Data.ptr` |
  | 8 | `Num` |
  | 12 | `Max` |
  | 16–31 | inline `TBitArray` (AllocationFlags) words |
  | 32 | bit-array secondary ptr |
  | 40 | `NumBits` |
  | 44 | `MaxBits` |
  | 48 | `FirstFreeIndex` |
  | 52 | `NumFreeIndices` |
  | 56 | hash bucket head (→ element 0) |
  | 72 | `HashSize` |

  Element stride is 16 bytes: `ptr` at +0, then two `int32` (`HashNextId`,
  `HashIndex`).

## 4. The crash that had to be defeated (read path)

`ExportNodesToText` takes its `TSet` **by value** and runs `~TSet` on return,
which `FMemory::Free`s the set's element buffer. A hand-built set whose element
buffer is **ctypes memory** makes UE free a pointer it never `malloc`'d →
**heap corruption + a *delayed* crash** (the editor dies seconds later, somewhere
unrelated — it cost two editor crashes to diagnose).

**Fix:** the set's element buffer must be allocated with the engine's exported
`FMemory::Malloc` (`bridge._make_set1_fmemory`). Then UE's destructor frees memory
it legitimately owns.

**Safety discipline:** a pure `memcmp` of a hand-built set against a real UE set
**cannot crash** — always byte-compare everything except `Data.ptr` (`[8:76]`)
*before* ever calling `ExportNodesToText`.

**Why per-node sets-of-1.** `bridge.export_nodes` serializes each node as its own
`FMemory`-backed set-of-1 and concatenates the results. This is crash-safe *and*
lossless: `LinkedTo` references are embedded per node (by node name + pin GUID),
so concatenated single-node exports reproduce the full multi-node text.

## 5. READ flow

`read_blueprint(path)` → for every graph from `GetAllGraphs`:
- **`graph_nodes(graph)`** reads `UEdGraph::Nodes` (a `TArray`) **directly** — the
  authoritative live node list. The `Nodes` offset is discovered once by scanning
  the object for the first `TArray<ptr>` whose elements all look like UObjects
  (vtable + `ClassPrivate`), then cached process-wide.
- `objects_with_outer(graph)` is the *fallback* enumerator (children by ownership).
  Avoid it as the primary reader: after `RemoveNode`, detached nodes linger in the
  transaction (undo) buffer until GC, so it surfaces **orphans**; `graph_nodes`
  reflects the real list immediately.
- `export_nodes(node_ptrs)` serializes them (§4).

## 6. WRITE flow

`inject(bp_path, text, graph_name=...)`:
1. `can_import(graph, text)` — non-mutating schema oracle; bail if it rejects.
2. `import_nodes(graph, text)` — the actual paste (== `Ctrl+V`); returns the count
   from the out-`TSet`.
3. `mark_structurally_modified(bp)`.
4. `compile_blueprint` (reflected API) — **the validator**.
5. `save_asset`.

## 7. EDIT flow (the "replace" pattern)

`ImportNodesFromText` cross-links **only within the pasted set** — a fresh node
can't wire to a *pre-existing* one. So to rewire an existing graph
(`examples/edit_graph.py`):

read graph → `bpkit.ir.Graph.parse` → mutate (the new wire is now intra-set) →
`bridge.clear_graph` (snapshot + `RemoveNode` each + GC so reads stay clean) →
re-import `Graph.render()` as one set → compile.

## 8. Authoring node text — the gotchas

The verbose copy/paste text has ~20 default flags per pin. You only need to
specify *intent*; UE reconstructs the rest on import by matching pin **names**.
What bites:

- **Typed-pin orphan trap.** A default or data wire only *merges* into a node's
  canonical pin if the authored pin carries a matching `PinType`. A typeless pin
  **orphans** (`bOrphanedPin=True`) and the engine's autogenerated default
  silently wins. So type every non-string default and every VariableGet/Set pin:
  `pin.typed("byte", enum_path("/Script/Engine.EAttachmentRule"))`,
  `typed_input(n, "SocketName", "attachrider", "name")`. **Verify after inject:
  zero `bOrphanedPin=True` pins == every default/wire merged.**
- **Bool defaults silently revert to the autogen value — WIRE them, don't default.**
  Even a correctly-typed `bool` pin default (`set_default`/`typed_input`, no orphan)
  can be overwritten by the UFunction's `AutogeneratedDefaultValue` on reconstruction:
  it merges cleanly yet **ships the autogen, not your value.** Cost a 3-build hunt:
  `SetAnimationMode`'s `bForceInitAnimScriptInstance` shipped as `true` (autogen)
  despite being authored `false`, so the cosmetic loop re-inited *every* character's
  AnimBP *every tick* and broke all animations. When a bool must hold a value that
  differs from its autogen default, **wire a literal** (`MakeLiteralBool` → the pin) —
  a linked pin can't revert. Verify with `LinkedTo=(` on the pin, not just "no orphan".
  (`bp-ir` gap; the orphan scan does **not** catch this — the value is just wrong.)
- **Component getters** (`GetMesh`, `GetCharacterMovement`) are unreflected C++
  inlines — author them as a non-self-context `VariableGet` of the component
  member (both pins typed), not as a call node.
- **Array nodes** must be `K2Node_CallArrayFunction` (not `CallFunction`) with a
  fully-typed `TargetArray` (`ContainerType=Array`, `bIsReference`, hidden `self`
  defaulted to `Default__KismetArrayLibrary`), else "Target Array is undetermined"
  compile fail. Indexed read = `K2Node_GetArrayItem` (pins: `Array` / `Dimension 1`
  / `Output`). `IsValid` won't merge onto a `GetArrayItem.Output` pin via paste —
  guard with an `int < Array_Length` range test instead.
- **ForEach** is a wildcard macro: a pasted `ForEachLoop` compiles clean but does
  **nothing** unless it has a `ResolvedWildcardType` header **and** its (impure)
  array source is exec-wired into the chain (`bpkit.ir.Graph.foreach` handles
  this). Isolation-test loops with a Count/Done counter.
- **`GetAllActorsOfClass`**: the `ActorClass` pin's `DefaultObject` **must be a
  quoted class path** in node text; unquoted → `ActorClass=null` → 0 results →
  silent empty loop.
- **`compile_blueprint` doesn't raise, and "compiled" ≠ "no errors".** A BP can
  report clean yet fail (unwired self pin, unresolved wildcard) and gate every PIE.
  Verify by scanning the exported graph for `wildcard` pins (excluding ForEach
  macros) + `ErrorMsg`/`bHasCompilerMessage` markers, or read the log for
  "undetermined" / "[Compiler] Error" (`dev`-era `c1_errors.py` pattern).
- **Paste silently DROPS nodes whose function ref doesn't resolve on this build.**
  `ImportNodesFromText` discards an authored `K2Node_CallFunction` whose
  `FunctionReference` names a function that isn't a UFUNCTION here — **no orphan,
  no compile error**; downstream pins just lose their links (an `IsValid` fed by
  the dropped node reads an unwired null pin → false forever). Wire-level scans
  cannot catch a node that isn't there. The **only tell is the count**: compare
  `render().count("Begin Object Class=")` to inject's `pasted` and fail the build
  on mismatch. (Cost a dead release build: `Pawn.GetPlayerState` is a UPROPERTY
  but **not** a UFUNCTION in Conan's 5.6 — every authored GetPlayerState node had
  silently vanished; the fix was `IsPlayerControlled`, which does reflect. When
  unsure a function exists, probe `hasattr(obj, "snake_case_name")` live first.)

See [CONAN-NOTES.md](CONAN-NOTES.md) for the engine/game-specific node patterns
discovered while building the mounted-followers mod, and [JOURNEY.md](JOURNEY.md)
for how all of the above was reverse-engineered.
