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

**Most of the gotchas below are encapsulated in the library now — reach for those
first.** `ir.Graph` carries typed node-builders (`cast` / `get_all_actors` /
`array_fn` / `array_get` / `array_var` / `var_get` / `var_set` / `foreach` /
`chain`) that bake in the correct PinTypes, and `build.build_graph()` does the
whole inject → auto-relink dropped wires → compile → scan tail in one call
(`inject(relink=True)` self-heals the `GetArrayItem.Output` drop). Conan/gameplay
builders (comp_of / attach / detach / HUD) live in `mods/mounted-followers/mf_nodes.py`.
Hand-author raw node text only for a node the builders don't cover; the notes
below explain *why* the builders are shaped the way they are. What bites:

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
  / `Output`). **`GetArrayItem.Output` is a WILDCARD that won't take a paste-link to
  a TYPED consumer** — the wire silently drops on import (no orphan, no error; the
  consumer keeps its default). Either avoid the link (guard with an
  `int < Array_Length` range test instead of `IsValid`), or re-make it live after
  inject with `connect_pins` (the v39 `dc MFHorses N` arg parsed `""`→0 for exactly
  this reason: `GetItem.Output → Conv_StringToInt.InString` dropped).
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
- **Paste silently DROPS authored WIRES too, not just nodes** (the wildcard
  `GetArrayItem.Output` case above). The node-count tell can't see a missing *wire*
  between two surviving nodes, and orphan/compile scans miss it (the unwired input
  is a legal default). The tell is a **link diff**:
  `bridge.missing_links(rendered_text, final_export)` returns every wire present in
  what you pasted but absent from the live graph. `inject` runs it automatically and
  returns `result["dropped_links"]` (matched by node+pin NAME, **case-insensitive** —
  the engine recanonicalizes pin casing on reconstruct, e.g. `Title`→`title`). Re-make
  each drop with `connect_pins`, then re-check (expect empty); fail the build on a
  non-empty post-fix diff.

## 9. Function OVERRIDES + cross-set wiring (worked out 2026-06-11, rcon-echo)

Overriding a native function **with a return value** (e.g.
`RconCommandObject.RconCommand`) cannot be done by paste, period:

- **`K2Node_FunctionEntry` can never be pasted into an override.** Its
  `PostPasteNode` unconditionally rewrites `FunctionReference` to a
  **self-function named after the containing graph** (MemberParent wiped,
  `bIsEditable` flipped) — so the compiler sees a new user function colliding
  with the parent ("Cannot override '::X' … declared in a parent with a
  different signature"). Hand-matching the signature with `UserDefinedPins`
  (even with exact `bIsReference`/`bIsConst` flags) still compiles down the
  new-function path and fails the same way.
- **`BlueprintEditorLibrary.add_function_graph` / `rename_graph` auto-uniquify**
  a parent-colliding name (`RconCommand` → `RconCommand_0`/`_1`), and a compile
  re-syncs the graph name back from the entry node — you can't sneak the name in.
- **The way that works** (`bridge.create_function_override`): create a function
  graph with a throwaway name (so it's registered in the BP), `clear_graph` it,
  **UObject-`rename()`** it to the function name (raw rename skips the K2
  validators; legal on an empty graph), then call the editor's own
  **`UEdGraphSchema_K2::CreateFunctionGraphTerminators(UEdGraph&, UClass*)`**
  (exported from `UnrealEditor-BlueprintGraph.dll`) with the parent class. It
  builds the canonical entry+result from the parent signature — MemberParent
  kept, real pins (the true lowercase param names), exec pre-wired, return-bool
  pins you didn't know existed included.
- **Wiring logic into the terminators**: paste can't link to pre-existing nodes,
  but **`UEdGraphSchema_K2::TryCreateConnection(UEdGraphPin*, UEdGraphPin*)`** +
  **`UEdGraphNode::FindPin(TCHAR*, dir)`** (both exported) wire live pins across
  sets — `bridge.find_pin` / `bridge.connect_pins`. This retires the old
  "re-import the whole graph to rewire" constraint wherever the replace flow
  would re-mangle terminators.
- **Multi-node paste of UNWIRED nodes can silently drop all but one** (3 bare
  CallFunction nodes in one text → 1 pasted; same nodes one-import-each → all
  fine). Unclear why (wired sets of 148 paste fine). Paste one node per import
  when they aren't wired to each other, and always assert the pasted count.
- **Smoke-testing an override from editor Python**: `inst.method_name(...)`
  binds the NATIVE UFunction directly and **skips the BP override** (returns the
  native default — looks like your BP "doesn't run"). Use
  `inst.call_method("FuncName", (args…))` — name dispatch on the instance's
  class, same as the engine's own call sites.

Delegate-bind / custom-event lessons (MRQ recv probe, 2026-06-11):

- **Custom event WITH parameters pastes fine** — give the `K2Node_CustomEvent` a
  `CustomProperties UserDefinedPin (PinName="Message",PinType=(PinCategory="string"),
  DesiredPinDirection=EGPD_Output)` header line and verify the pin exists post-paste
  with `find_pin`. **Bind Event is just a pasted `K2Node_AddDelegate`** with
  `DelegateReference=(MemberParent=…,MemberName="…")`; wire
  `CustomEvent.OutputDelegate → AddDelegate.Delegate` with `connect_pins` (the
  schema validates signature compatibility — a refusal is itself the answer).
- **Compile immediately after `clear_graph` before re-pasting same-named custom
  events** — the stale GeneratedClass function map makes PostPasteNode uniquify
  the names (`MRQBindNow` → `MRQBindNow_0`). Classify by prefix and capture the
  real `CustomFunctionName` for later `call_method`.
- **`set_editor_property` on a spawned instance's BP variable** needs
  `BlueprintEditorLibrary.set_blueprint_variable_instance_editable(bp, name, True)`
  first ("cannot be edited on instances" otherwise).
- **Editor-world actors silently drop BP script fired outside Python**: the
  `AActor::ProcessEvent` gate blocks non-native script in a not-begun-play world
  unless inside an editor-script guard (Python calls are) or the function has
  `CallInEditor` — so a delegate broadcast from the engine's frame pump runs your
  python `add_callable` but NOT your bound BP event. Header `bCallInEditor=True`
  on the custom event fixes the editor test; game worlds don't have the gate.

Protected-to-one-function calls + function-graph paste limits (mounted-followers `dc`, 2026-06-13):

- **A UFunction can be BlueprintCallable ONLY inside one specific override.** Conan's
  `ModController.MergeDataTables`/`ClearDataTable`/`RemoveDataTableRows` (and all
  `DataTableFunctionLibrary` writes) **drop on paste in the event graph** (and in isolation, both
  `bSelfContext` and `MemberParent` forms — authored 2 pasted 1). They resolve **only inside the
  `ModDataTableOperations` override**. Recipe: `create_function_override(bp, "ModDataTableOperations",
  "/Script/DreamworldMods.ModController")`, inject the call inside it (`bSelfContext=True`), then
  `connect_pins(entry."then", call."execute")`. (Reflected ≠ BlueprintCallable-as-a-free-node — a
  Python-callable UFunction may still drop on paste; the paste-drop count is the only tell.)
- **★ Self-context `VariableGet` DROPS on paste into a function/override graph** (it SURVIVES in the
  EventGraph). Verified: a lone `var_get("Tbl")` → pasted 2/2 in EventGraph, **pasted 0/1 in
  `ModDataTableOperations`**. So you cannot read a member var inside an authored override-function graph
  via paste. Workarounds: feed the inputs as pin **DefaultObject** asset refs instead, or live-spawn.
- **★ Object-pin `DefaultObject` (asset ref) must be the QUOTED object path.**
  `DefaultObject="/Game/.../Asset.Asset"` is the editor's canonical **resolved** form: setting
  `Class'/Game/...'` *normalizes to* the quoted path (proof the editor parsed+resolved it), and the
  **unquoted** path is **cleared** as unresolvable. (Class-WRAPPER pins like
  `GetAllActorsOfClass.ActorClass`, `bIsUObjectWrapper=True`, also take the quoted path.) Post-compile
  the pin showing the quoted path == a resolved ref; the default *absent* == it failed to resolve
  (silent null at runtime — the same "compiles-but-does-nothing" trap). `CreateSaveGameObject(<Cls>)`
  auto-narrows `ReturnValue` to `<Cls>` — wire it straight to the subclass-var consumer, no cast (a
  cast errors "already a …").
- **Don't assume library getters are pure.** `DoesSaveGameExist` / `LoadGameFromSlot` are **impure**
  (have exec pins). Wire them into the exec chain or they're "pruned because its Exec pin is not
  connected" and `ReturnValue` reads the default (false/null) — the branch then always takes the wrong
  path. Int `Max`/`Min` on `KismetMathLibrary` are named `Max`/`Min` (not `Max_IntInt`).
- **★ Scratch hygiene — `scratch_blueprint` pollutes the ACTIVE MOD's cook.** With a mod active,
  `/Game/_Scratch` resolves into that mod's content dir on disk
  (`…\UE4\Content\Mods\<ActiveMod>\Content\_Scratch\`), so probe/test BPs created by `scratch_blueprint`
  get **saved there and cook into the mod as (Base Asset)s** (which Conan then culls — and they show in
  the "Select Content For Mod" dialog). Editor `delete_asset` reports success but **leaves the `.uasset`
  ghost on disk** (it only drops the in-memory/registry entry). **Sweep after probing**: close the
  editor and `Remove-Item -Recurse` the `_Scratch` dir(s)
  (`Get-ChildItem <Content> -Recurse -Directory -Filter _Scratch`). Everything under `_Scratch` is
  throwaway by convention (regenerable by re-running the example/test/probe), so nuking the dir is safe.

## 10. Hidden UFunctions: full reflected surface + raw FunctionFlags (2026-06-11)

The Python layer (and the BP editor) only show UFunctions with BP flags — a class
can carry reflected functions you can't see (e.g. `WebSocketConnectionManager`'s
`OnReceiveData`). Two tools to get the truth:

- **The plugin DLL's exports are the full function list**: every UFUNCTION gets an
  `exec<Name>` thunk (`?execOnReceiveData@UWebSocketConnectionManager@@…`), and
  BlueprintNativeEvents additionally get `<Name>_Implementation`. String-scan the
  module DLL for `exec` thunks to enumerate what reflection has that Python hides.
- **Raw `EFunctionFlags` via the bridge**: `find_object` resolves a UFunction by
  path (`/Script/Pkg.Class:Func`); the `FunctionFlags` u32 sits at offset **0xd0**
  in this build's UFunction — calibrate, don't hardcode: scan offsets until one
  matches the expected patterns of three knowns with distinct flags (a BIE like
  `Actor:ReceiveBeginPlay`, a static lib func like `KSL:PrintString`, a BNE).
  `bpkit/ops/probe_ws_flags.py` is the worked example. `Final` in the flags ⇒ no
  BP override can ever compile; no BP flags ⇒ unreachable from graphs.

## 11. UMG: reading & authoring widget trees (2026-06-17)

The `unreal` Python API in this build does **not** expose the UMG widget tree
(`WidgetBlueprint.widget_tree` isn't a reflected property; `WidgetTree` /
`WidgetBlueprintLibrary` aren't bound; `UserWidget` has no `initialize`). So you
can neither author a widget hierarchy nor even create+init a widget instance from
Python. But the **UMG designer's own copy/paste IS exported** — the widget analogue
of `Im/ExportNodesToText` — so bpkit drives it the same way it drives graphs:

- `FWidgetBlueprintEditorUtils::ExportWidgetsToText(TArray<UWidget*> /*byval*/, FString&)`
  → `bridge.export_widgets(widget_ptrs) -> text`. The `TArray` is **by value** (`~TArray`
  on return frees its buffer), so the element buffer is `FMemory::Malloc`'d — the same
  crash-safety contract as the by-value `TSet` in `export_nodes`. x64 MSVC passes a
  >8-byte by-value struct by hidden pointer, so `byref(tarray)` is the right ABI.
- `FWidgetBlueprintEditorUtils::ImportWidgetsFromText(UWidgetBlueprint*, const FString&,
  TSet<UWidget*>& out, TMap<FName,UWidgetSlotPair*>& out)` → `bridge.import_widgets(wbp, text)`.
  Creates real `UWidget`s parented to the WBP's widget tree; returns the count.

Get the tree (a subobject, findable even though unreflected) with `bridge.widget_tree(wbp)`
/ `bridge.tree_widgets(wbp)`. The exported text is the canonical designer clipboard format
(`Begin Object Class=/Script/UMG.CanvasPanel … CanvasPanelSlot … Content="…TextBlock'Body'"`),
so you can hand-craft or template it. **Caveat:** `ImportWidgetsFromText` populates the tree
but does **not** set `WidgetTree.RootWidget` (the designer's `PasteWidgets` does placement
separately) — author-from-scratch needs a `RootWidget` write. Live-verified: round-tripped a
CanvasPanel+TextBlock from one WBP into a fresh blank WBP (0→2 widgets, intact hierarchy).

Showing a widget at runtime is a *separate, graph-side* problem, also solved: `WidgetBlueprintLibrary.Create`
is **not** paste-resolvable (it drops silently), so use **`ir.Graph.create_widget(wbp_class_path)`** — it
authors the specialized **`K2Node_CreateWidget`** node (pins `execute`/`then`/`Class`/`OwningPlayer`/
`ReturnValue`; format verified against the shipped `BaseHUD`/`FunCombat_PlayerController`). Wire a
PlayerController into `OwningPlayer`, then `AddToViewport` the `ReturnValue` (give it a high `ZOrder` to
sit above the game HUD). Two gotchas when feeding it: `UserWidget.GetWidgetFromName`'s `Name` is a
`const FName&` → it must be **wired** (`MakeLiteralName`), a literal default is rejected; and a cast to
`TextBlock` exposes its success pin as **`AsText`** (UMG's display name for `UTextBlock` is "Text").
Live-verified end-to-end: a bpkit-authored overlay rendering on screen in PIE (2026-06-17).

See [CONAN-NOTES.md](CONAN-NOTES.md) for the engine/game-specific node patterns
discovered while building the mounted-followers mod, and [JOURNEY.md](JOURNEY.md)
for how all of the above was reverse-engineered.
