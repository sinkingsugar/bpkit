# Conan Exiles — live-verified facts

Game/engine-specific knowledge learned by probing the running Conan Exiles
Enhanced Dev Kit (UE 5.6.1). This is the **application** layer — the generic
framework knowledge is in [INTERNALS.md](INTERNALS.md). Most of this was won
building the **mounted-followers** mod (see [JOURNEY.md](JOURNEY.md) and
[`mods/mounted-followers/`](../mods/mounted-followers/)).

Every claim here was verified live; where a claim corrects an earlier assumption,
the correction is noted.

---

## Class model

`mount`, `pet`, and `thrall` are all the **same native C++ class**
`/Script/ConanSandbox.ConanCharacter` with different flags/components:

```
BP_NPC_Mounts_Horse ─▶ BP_NPC_Wildlife_Hooved ─▶ ConanCharacter
BP_*_pet            ─▶ BaseBPWildlife         ─▶ ConanCharacter
humanoid thralls    ─▶                            ConanCharacter
```

The mount/follow logic lives in compiled `ConanSandbox` C++ — not editable, but
fully **reflected** to Python, which is how it was audited.

## Mounting

- **No Blueprint/Python call seats a rider** (player *or* NPC). `mount()`,
  `bp_mount_server`, `replicate_mount`, `bp_post_mount_server_client`, and the real
  trigger `bp_start_mount_process_client` all fail to actually seat from script —
  the `bp_*` functions are **hooks the native code calls**, not performers. The
  native seat runs only through the player input pipeline; an AI rider is refused
  (`bp_start_mount_process_client` → `False`). → For mounted *followers*, use a
  **cosmetic socket-attach**, not the real mount system.
- **`can_mount(rider)` is *not* player-gated** — returns OK (`None`) for an AI
  rider. Eligibility ≠ ability to seat.
- **`get_mount()` on the PLAYER returns `None` even while riding.** Detect mount
  state via the mount's `get_rider() == player` (ground truth: scan following
  horses). `get_mount_input()` lags/flakes — its `BP_MountInput` object is torn
  down and recreated each mount cycle, so `IsValid` reads false for a long window
  on remount.
- **`is_mountable` (creature-type, true = horse) is the discriminator** between a
  following horse and a humanoid thrall — **not** `is_mount` (mount-*state*, flips
  and is true-for-all at mount time).
- `GetEmbeddedSaddleId()` reads `None` even while a player is actively riding —
  **not** a "ridden/has-saddle" signal. Don't gate on it.

## Followers

- **Follower caps are per named group** on the player's `BP_ThrallSystemComponent`:
  groups include `Mount`, `Warrior`, `Crafter`, `Bearer`, `Performer`, `Archer`.
  Mounts live in their own `Mount` group, so a generic follower-count mod won't
  cover them. Raise a cap with `add_thrall_group_limit_adjustment("<Group>", N)`
  (additive, mod-safe). Default `Warrior`/`Crafter` cap was 1 (a 2nd thrall swapped
  out the 1st). **Runtime adjustments don't persist** — re-apply each session
  (the mod does it in the ModController's guarded init).
  - **ONLY touch the group you own.** A follower mod that raises `Warrior/Crafter/etc.`
    stacks additively on *other* follower mods (e.g. Better Thralls) every session →
    they fight to reset it → per-tick churn → **server-FPS tank + "your mod overwrites
    my limit"** (the AstroCat report, 2026-06-13). Mounted-followers raises **only** `Mount`.
  - **No cap GETTER exists** (verified 2026-06-13). The component exposes the follower
    *count* (`get_follower_group_counts`→`Map[Name,int]`, `get_num_following_thralls`,
    `get_number_following_thralls_in_group`) and a bool `is_below_thrall_limit()`, but the
    cap/limit number itself is **unreadable**. There is also no vanilla *per-player*
    follower-limit ServerSetting to read (the `get_minion_population_*` settings are
    server-wide NPC caps, not per-player follow caps).
  - **SET the cap idempotently with `reset_thrall_group_limit_adjustment(g)` + `add(g, N)`.**
    `reset` zeroes *this mod's* adjustment on group `g`, then `add` re-applies exactly N —
    converges to N, never stacks, relog/re-apply safe. Better than a guarded one-time `add`
    (you don't need to read the cap to assert it). `remove_thrall_group_limit_adjustment(g, N)`
    also exists (subtract a known amount).
- Follow tuning: `set_additional_follow_distance(N)` staggers followers into a
  trailing line (avoids clustering/bumping at one follow point).
- AI controllers: humanoid thralls → `HumanAIController`; creatures/mounts →
  `CreatureAIControllerHooved`. Follow logic drives the follower's *own*
  `CharacterMovementComponent` — there is no native path where a follower drives a
  separate mount pawn (the exact gap that makes mounted followers unshipped).
- **Followers leash / catch-up.** The follower AI recalls a follower that falls too far
  behind (`is_ai_controller_leashing`; mounted catch-up: `wait_for_catch_up_time` /
  `has_time_catched_up` / `try_resume_from_catch_up_time` / `teleport`) by **re-enabling its
  `CharacterMovement`** (`MOVE_None`→`Walking`) and sometimes teleporting it. This silently
  undoes a *one-shot* movement freeze on a stowed/seated follower — see the cosmetic-rider
  recipe's freeze bullet. **Triggers in the cooked game, rarely in PIE** (PIE's small
  always-loaded world keeps followers close enough to never trip it).

### Manager tick performance — don't `GetAllActorsOfClass` every tick (v41, 2026-06-13)
- **`GetAllActorsOfClass(ConanCharacter)` is O(every player + thrall + NPC)** and runs the whole
  collection each call; doing it per tick (×3 iterations: cosmetic loop + player-find + global sweep),
  on the server AND every client, **even when nobody is riding**, is a real server-FPS cost that scales
  with total population, not riders (the AstroCat "still has FPS issues" report). It works (quoted
  `ActorClass` default — see Packaging), it's just the wrong tool for a hot path.
- **Enumerate players cheaply** via `GameState.PlayerArray` (`GetGameState` → `PlayerArray` VariableGet,
  O(players)) → `PlayerState.GetPawn`. PlayerArray entries ARE players (no `IsPlayerControlled` filter
  needed). The per-player passes already use each player's follower list (O(followers)), so once the
  player-find is off `PlayerArray` the whole per-player pass is cheap and can run every tick (keep cap
  init un-gated, or new un-mounted players never get the cap raised to claim horses → deadlock).
- **Split the two all-actor consumers and gate each by ROLE, not by a replicated flag** (BP variable
  replication is NOT exposable via `BlueprintEditorLibrary` — no setter — so there's no server→client
  gate flag to lean on; and the mod never replicated custom state, it recomputes per-instance from
  native attach/`get_rider` replication):
  - **COSMETIC loop** (applies the seated single-node anim): runs on every RENDER-capable instance —
    clients + listen host + SP — **ungated**, so each instance re-derives EVERY player's seated-follower
    pose. Only a **dedicated server skips it** (`KismetSystemLibrary.IsDedicatedServer` — no render, the
    anim is invisible there and doesn't replicate). It gets its OWN `GetAllActorsOfClass`, run only in
    the not-dedicated branch.
  - **GLOBAL restore sweep** (server-authoritative cleanup): gets its OWN `GetAllActorsOfClass`, gated on
    `SweepRun = AnyMounted OR WasMounted` (a 1-tick trailing so a just-dismounted / orphaned seat is
    still restored the tick after the last mount). `AnyMounted` is set in the server per-player
    `GetRider` detect.
  - Result: an **idle dedicated server does ZERO `GetAllActorsOfClass`** (cosmetic skipped, sweep gated
    off) — the server-FPS win — while clients/listen-host keep full visuals with no trade-off.
- **★ DON'T gate the CLIENT cosmetic on "is the local player mounted"** (the rejected v40 approach): the
  cosmetic is exactly what draws OTHER players' seated followers on your screen, so gating it locally
  means you only see others' followers while you're also riding — a visible MP glitch. Gate the client
  cosmetic only by render-capability (`is_dedicated_server`), never by local mount state.
  Verified in PIE: v41 manager spawns, idle → `AnyMounted`/`SweepRun` false (sweep skipped),
  `is_dedicated_server`=false in PIE so the cosmetic runs.

## Mod-configurable values — console commands, SaveGame, ServerSettings (2026-06-13)

How a **content-only** mod (no C++) lets a server admin / SP player change a value at runtime, and
make it stick. Mapped exhaustively while making the mounted-followers Mount limit configurable.

### Custom console commands — `DataActorCommand` (THE working path)
Conan's documented custom-console-command system; works in a content mod. (Funcom wiki: *Custom
Console Commands* + *Data Table Merging Operations*.)
- **The handler:** subclass `DataActorCommand` (a singleton Actor) and implement its
  BlueprintImplementableEvent **`DoCommand(parameters: Array<str>, calling_player_controller, world)`**.
  Parse `parameters[0]` yourself (`KismetStringLibrary.Conv_StringToInt`, clamp with
  `KismetMathLibrary.Max`/`Min` — note the BP names are `Max`/`Min`, **not** `Max_IntInt`). Avoid the
  deprecated `DataCommand` base (no world context).
- **Registration row:** add a `BlueprintCommandDataRow` to the game's
  `/Game/Systems/Cheats/CustomConsoleCommandsDataTable`. Row fields: `CommandActorClass` (your
  `..._C`), `RequireAdmin` (bool — admins in MP; SP players ARE admin so it works in SP too),
  `RunOnServer`/`RunOnClient` (bools — set **RunOnServer=true** for anything server-authoritative like
  follower caps; the client just needs the row present to route).
- **Invoke in-game:** `DataCmd <Name> <args>` or `dc <Name> <args>`. One actor instance per server+client.
- **★ Registration GOTCHA (cost ~an afternoon):** you CANNOT add the row from the event graph.
  `MergeDataTables`/`ClearDataTable`/`RemoveDataTableRows` (on `ModController`) and ALL
  `DataTableFunctionLibrary` writes (`Fill…`, `Export…`) are **NOT BlueprintCallable as free nodes** —
  they silently DROP on paste (and there's no auto-merge property for command tables; only
  `additional_gameplay_tag_tables`/`additional_sublevels` auto-merge). They are **BlueprintProtected to
  one specific override**: the ModController function **`ModDataTableOperations`**. Override THAT
  (`bridge.create_function_override(bp, "ModDataTableOperations", "/Script/DreamworldMods.ModController")`),
  and `MergeDataTables` resolves *inside it* (self-call). The base ModController calls
  `ModDataTableOperations` at mod-init on every instance (server + clients) — exactly when/where the row
  must register. Build it (mounted-followers): create the override, inject the merge as a pasted set,
  then `connect_pins(entry."then", merge."execute")` (cross-set; paste won't link to the editor-made
  entry). See `bpkit/INTERNALS` for the two authoring gotchas this hit (function-graph VariableGet
  drop; object-pin DefaultObject must be the quoted path).
- **Build a control table** for column-selective merges (`Merge Data Tables With Control Table` +
  `DataTableMergeControlRow`: `MergeControl_Default` row, `ColumnsToOverride`,
  `ColumnsWithRowsToInsert/Remove`) — preserves compat when several mods edit the same rows. Not needed
  for adding a brand-new row.

### Persistence — UE `SaveGame` (survives restarts; safe)
Runtime cap adjustments reset each session AND in-memory values die on restart, so a console-set value
won't stick on its own. To persist: subclass `SaveGame` (one var), and in the command
`GameplayStatics.CreateSaveGameObject(<SaveGameClass>)` → set the var → `SaveGameToSlot(obj, "<Slot>", 0)`;
the manager reloads it on init (`DoesSaveGameExist`/`LoadGameFromSlot` — **both IMPURE, exec-wire them**).
- **No save conflict.** UE SaveGame slots are `…/Saved/SaveGames/<Slot>.sav`; Conan's real persistence is
  the SQLite **`game_0.db`** (+ `game_0_backup_*`). Different system, different file — they never touch.
  `Saved/SaveGames/` doesn't even exist until first write. Namespace the slot name to avoid other mods.
  Failure mode is benign (missing/bad `.sav` → fall back to default; can't corrupt the world DB).
- `CreateSaveGameObject(<Class>)` **auto-narrows** its `ReturnValue` to that class — no cast needed
  before reading/writing the subclass var (a cast errors: "already a …").

### Apply LIVE, mid-game (no restart)
The command must (a) re-apply to all connected players immediately (so existing players see it now), and
(b) write the SaveGame (so it survives restart) — both, every invocation. A command that only saves
"does nothing mid-game" until relog. Caps are **server-authoritative** → the command MUST run server-side
(`RunOnServer`); a client-side run can't change the real cap. Gate to admins via `RequireAdmin` +
`ConanPlayerController.is_admin()`.

### Dead ends (don't re-derive)
- **Custom CVars / `[ConsoleVariables]` ini:** `SystemLibrary.get_console_variable_int_value(name)` +
  `execute_console_command` ARE runtime/ship-safe, BUT a custom cvar reads 0 unless **C++-registered**
  (verified round-trip: registered `r.ScreenPercentage` 77→77; custom `MountedFollowers.Horses` 7→0).
  No BP node reads an arbitrary ini key either. So a content mod can't use a custom cvar/ini value.
- **ServerSettings panel:** `unreal.ServerSettings` is ~hundreds of hardcoded native getters with NO
  register-by-name / add-custom API; `ModController` has no settings hook. Can't add your own admin slider.
- **In-game UMG settings UI** (`ModMenuBase`/`SettingsWidgetBase` exist, with a field-value framework):
  possible, but authoring a WIDGET TREE is unproven in this toolkit, and *surfacing* it (how the player
  opens it) has no verified ModController/PC hook. The `DataActorCommand` console command is simpler and
  covers SP + admins, so it's the chosen path; the UI is a future-polish option.

## Persistent mod logic — the ModController hook

Persistent mod logic = a **`DreamworldMods.ModController` subclass** (an Actor with
`BeginPlay` + `Tick`). The framework auto-spawns any ModController subclass on play
— but **before the player exists**, so do player-dependent init on `Tick` guarded
by an `Initialized` bool, *not* in `BeginPlay`. Conan's stock template to inspect:
`/Game/Items/Example_modcontroller`. Stamp a version int on the CDO (e.g.
`MgrVersion`) so you can tell which class actually spawned (stale-class detection).

- **What actually gates the packaged auto-spawn is (Mod Asset) placement, NOT
  `bRequiresLoadOnStartup`.** The "spawns only if loaded at boot" theory was the packaging
  bringup's red herring: empirically a ModController cooked as a **(Mod Asset)** registers and
  spawns in the packaged game with the flag at its default `false` (live-verified, cooked game,
  2026-06-10). See §Packaging below.

## Cosmetic mounted rider — the working recipe

Attach + freeze + pose, all content-only and scriptable from Blueprint:

- **Attach the rider's skeletal MESH** to the horse's **`attachrider`** socket
  (fallback `saddleSocket`) with `SnapToTarget`. Attaching the *actor/capsule*
  instead lands the body ~90u low and yaw-rotated −90° (the standard Character
  mesh-vs-capsule offset).
- **Freeze non-destructively** (never `Destroy` a persistent follower): unpossess +
  `disable_movement` (MOVE_NONE) + capsule collision off + actor collision off +
  physics off. **Keep the skeletal-mesh component ticking** — disabling its tick
  freezes animation evaluation. Use runtime setters on live components, not
  `set_editor_property`.
- **The freeze must be RE-ASSERTED every (server) tick, not done once.** A stowed follower is
  still AI-possessed, and Conan's follower **catch-up/leash** (see §Followers) re-enables its
  `CharacterMovement` once you ride far enough — `CharacterMovement` then walks the *still-
  attached* pawn to the ground (the actor never detaches, so the cosmetic pose stays → a saddle-
  posed thrall jogging beside you). A one-shot `disable_movement()` at stow is reversible. Fix:
  a per-tick **server** (`HasAuthority`) pass that re-pins `MOVE_None` **and** re-asserts the
  saddle relative loc/rot on every seated follower (trigger-agnostic — also corrects a
  teleport/recall drift). If the AI still jitters, escalate to `ConanPlayerController.
  command_follower(follower, loc, AIFollowerOrderType.HOLD)` to stop it at the source.
  **Cook-ONLY repro** (never PIE) → test packaged, with `HUDShowFIFO` not `PrintString`.
  (live-verified v32, cooked SP 2026-06-09)
- **Pose:** force a seated single-node anim over the AnimBP —
  `set_animation_mode(ANIMATION_SINGLE_NODE)` + `play_animation(anim, loop=True)`
  after `stop_all_montages`. Idle clip:
  `/Game/Characters/humans/animations/mounted/Horse/A_human_mounted_idle_HORSE`
  (matches `SK_human_Skeleton`). 404 mounted/riding sequences ship in the kit.
- **Restore:** reverse — `ANIMATION_BLUEPRINT`, `MOVE_Walking`, collision on,
  re-attach mesh → capsule, and **restore the saved relative transform** (save
  `mesh.GetRelativeTransform()` *before* reparenting; re-attaching with
  `SnapToTarget` snaps to the capsule center → rider floats ~96u up). Run Stow
  **once** per mount — re-running while stowed re-saves the (attached, ~zero)
  transform and corrupts the restore.
- **Never call `SetAnimationMode(AnimationBlueprint)` with force-init each tick.** The
  client-side un-seat loop runs over *every* `ConanCharacter` every frame; the reset
  branch flips non-seated ones back to `AnimationBlueprint`. `SetAnimationMode`'s
  `bForceInitAnimScriptInstance` defaults **true**, which **re-inits the AnimBP even
  when the mode is unchanged** → it reinitialized *every* character's AnimBP every
  frame and broke all animations (player + thralls + NPCs). Pass `false` so it's a real
  no-op for already-AnimBP characters (only a still-SingleNode follower actually
  switches). And because a bool *default* silently reverts to autogen on paste, **wire**
  the `false` (`MakeLiteralBool`), don't default it — see INTERNALS §typed-pin.

## Multiplayer / replication (the crux of the MP build)

- **Relevancy first.** A logic-only actor (hidden root, no collision, no position —
  a typical ModController manager) is **never relevant to clients**, so it never
  replicates there: its `Tick`, Multicast RPCs, and replicated vars are all **dead
  on clients** even with `RemoteRole == SimulatedProxy`. This was the root cause of
  every "host-only" symptom. Fix: CDO `always_relevant = True`.
- **ModController does not tick on clients** unless made relevant → apply cosmetics
  (the seated single-node pose) **locally on each client** in a non-gated loop from
  replicated state; keep gameplay server-only behind `HasAuthority`. Add a reset
  branch (not-attached → restore AnimBP) so clients un-pose on dismount.
- **Actor-attach replicates; component/mesh-attach does NOT.** Attach the follower
  **actor** (`AActor::K2_AttachToComponent`, parent = horse mesh) → clients see it
  ride. Mesh-attach desyncs (host mounted, clients at origin). Relative loc/rot set
  after an actor-attach replicate with it.
- **BP attach/detach need the `K2_` prefix.** `K2_AttachToComponent` /
  `K2_DetachFromActor` are the BlueprintCallable versions; the plain C++ names
  (`DetachFromActor`) compile clean but **silently no-op** (this caused the whole
  dismount bug). Python method names drop the prefix (`detach_from_actor`).
- **Server-side animation does NOT auto-replicate.** `PlayAnimMontage` replicates;
  a single-node `play_animation` and a *transient/dynamic* slot montage do **not** —
  confirmed even on the host *player*. A replicating seated full-body pose needs a
  **real (saved) AnimMontage on the `Fullbody3rd` slot**, not a dynamic montage.
- **Emotes replicate:** `EmoteController.start_emote` multicasts and reaches clients
  (e.g. `CharacterEmotes.SIT_ON_GROUND`) — a promising replicated-pose path.
- Exclude **mountable creatures** (horses) and **other players**
  (`GetPlayerState` valid; `IsPlayerControlled` is false for other players'
  sim-proxies) from any "seat the attached characters" loop, or you apply human
  anims to horse skeletons.

## Spawning & PIE control

- **Spawn into the live game world with the `Summon <ClassPath>_C` console
  command** (deferred a frame; `load_object` the class first so it resolves).
  `EditorActorSubsystem.spawn_actor_from_class` lands actors in the **editor**
  world, not the PIE world. Summoned NPCs are under-initialized (no auto AI
  controller — possess one manually). Finite-lifespan NPCs (undead) vaporize when
  summoned ownerless; use a persistent follower.
- **PIE surface:** `LevelEditorSubsystem.is_in_play_in_editor` /
  `editor_request_begin_play` / `editor_request_end_play`;
  `UnrealEditorSubsystem.get_game_world()` (None when not playing);
  `editor_play_simulate` ticks AI+navmesh without a player pawn. **Do not start
  Play yourself — the user controls Play** (driving PIE once dropped the user into a
  bad session and cost trust). Read/experiment only in the user's own session.
- **Slate modals freeze the channel** (they block the game thread). Rescue from a
  *separate host process* over Win32: the editor's main `UnrealWindow` is DISABLED
  while the modal dialog window stays ENABLED+foreground → post Enter/Esc to the
  enabled one (`dev`-era `dismiss_modal.py`).

## Packaging & shipping a mod (cook → pak)

`/deploy` (bpkit) only authors Blueprints into the **editor** project (`/Game/<Mod>`).
The real game runs a separate **cook → pak** from the Dev Kit's mod tool, e.g.
`...\CEUE5Devkit\UE4\Saved\Mods\<Mod>\Output\<Mod>.pak`. Editor success ≠ packaged success.

- **Mod assets MUST live under `/Game/Mods/<ModName>/` — THE one that actually bit us (2026-06-08).**
  The cook's "Select Content For Mod" dialog tags each asset **(Mod Asset)** (it lives under
  `/Game/Mods/<mod>/`) or **(Base Asset)** (anywhere else). Conan only **registers ModControllers
  that are Mod Assets**; a ModController cooked as a **Base Asset loads but is culled as
  `[1]Invalid class`** (no `AddActiveModControllerClass` line) → runs in PIE, dead in the packaged
  game. So `mf_config.OUTPUT_PKG` must be the mod's own content root (`/Game/Mods/<mod>`), which is
  writable in the DevKit when that mod is the **ACTIVE** mod. Authoring into a scratch root like
  `/Game/<Mod>` is editor-test-only and ships a dead controller. After deploy, confirm in the cook
  dialog the BPs read **(Mod Asset)**, and delete any stray base-asset copies.
- **`bRequiresLoadOnStartup` is NOT needed (and was NOT our bug).** A ModController mod registers
  and spawns in the packaged game with the flag at its default `false`, as long as the controller
  is a **(Mod Asset)** (live-verified, cooked game, 2026-06-10). The flag ("Requires Load On
  Startup" in the Dev Kit mod settings → `modinfo.json`) was chased first during the bringup and
  was a red herring; reserve it for mods that genuinely need their content loaded at boot.
  `unreal.ModInfo` exposes `load_on_startup` / `requires_load_on_startup` /
  `was_loaded_on_startup` / `load_order`.
- **Pak layout.** The shipped `<Mod>.pak` is a "fat" pak (mount `../../../ConanSandbox/Mods/`)
  holding `modinfo.json` + `manifest.json` (per-file MD5s) + **per-platform IoStore triplets**
  `<Mod>-{Windows,WindowsServer,LinuxServer}.{pak,ucas,utoc}`. The actual cooked assets live in
  the inner IoStore containers. Single-player/listen uses the client (`-Windows`) content (it has
  authority); a dedicated server uses `-WindowsServer`/`-LinuxServer` — the manager must be cooked
  into the server side too (it is, by default; the server triplet is just smaller because it omits
  the Steam `preview` image).
- **Ghost duplicates: `delete_asset` doesn't flush disk, and the DevKit has overlapping
  mounts.** `/Game` is served by several physical roots — a `conan` dev-mount
  (`Content/Mods/conan/Content/` → `/Game/...`), each mod's mount
  (`Content/Mods/<mod>/Content/` + a `Local/` write-remap), etc. So one logical path can be
  backed by several files, and authoring to a scratch root like `/Game/MountedFollowers`
  leaves copies in more than one. `EditorAssetLibrary.delete_asset` clears the **registry**
  (`does_asset_exist`→False *in-session*) but often **does not remove the on-disk `.uasset`**,
  so a content rescan / editor restart **resurrects** it — and it still spawns (a ModController
  subclass auto-spawns from any **loaded class**, even if the registry entry is gone). `on_disk`
  via `get_assets_by_package_name(..., include_only_on_disk_assets=True)` is **unreliable** here
  (read 0 while a real file existed). To truly remove a stale BP: close the editor, **delete the
  physical `.uasset` files** (find them with a filesystem scan — `system_path` returns the
  *canonical* `/Game→Content` path, not the real mounted one, so glob by name), reopen, then
  re-deploy. Clean-slate (delete every copy + one fresh deploy) beats whack-a-mole.
  - **Where `/Game/_Scratch` really lives (mapped 2026-06-12):** the ACTIVE mod's disk folder
    serves TWO mounts — `Content/Mods/<mod>/Local/` ↔ `/Game/Mods/<mod>/` (the mod's own
    content), and `Content/Mods/<mod>/Content/` ↔ `/Game/` itself (the base-asset overlay).
    So any scratch authored at `/Game/_Scratch` while a mod is active physically lands INSIDE
    that mod's folder (`Content/Mods/<mod>/Content/_Scratch/`) and travels with it. Cleanup
    recipe that worked editor-open: `delete_asset` the `/Game/_Scratch/...` paths (clears
    registry + live mount), then immediately delete the surviving `.uasset` ghosts under
    `Content/Mods/<mod>/Content/_Scratch/` on the filesystem — verified gone both sides,
    manager BP unaffected.
- **Inspect a pak — never trust the cook silently.** UnrealPak =
  `C:\Program Files\Epic Games\CEUE5Devkit\Engine\Binaries\Win64\UnrealPak.exe`.
  `UnrealPak <Mod>.pak -List` shows the outer files; `-Extract <dir>` then
  `UnrealPak <Mod>-Windows.utoc -List` lists the **inner cooked asset paths** (e.g.
  `.../Content/<Mod>/BP_<X>.uasset`). IoStore `.ucas` chunks are **Oodle-compressed** → a raw
  string/byte grep finds nothing (false negative); use `-List`.
- **Quick no-recook flag test:** extract the outer pak, flip `bRequiresLoadOnStartup` in
  `modinfo.json`, update that file's MD5 in `manifest.json`, then `UnrealPak <out>.pak
  -Create=<filelist>` (lines `"<src>" "../../../ConanSandbox/Mods/<name>"`, uncompressed). Drop the
  rebuilt pak in and test before committing to a full DevKit re-cook. (Re-cook reverts the flag
  unless you also tick the checkbox.)
- **Diagnostics that survive Shipping:** `PrintString` and the `GetAll` console command are
  compiled out of Shipping (screen + log + console show nothing). Use Conan HUD funcs instead:
  `ConanCharacter.HUDShowFIFO(text)` — static, prints to the **local** client's event feed (runs
  wherever the actor ticks; pair with an Always-Relevant manager for client visibility);
  `ConanCharacter.ClientHUDShowNotification(text, positive)` — instance **Client RPC** (call
  server-side on the player char → banner on that client). Both take FText → `Conv_StringToText`.

## Network egress / ingress from content BP (the LLM-NPC channel map, 2026-06-11)

A content-only mod can talk to the outside world; the asymmetry is direction.
**Outbound is easy, BP-readable inbound was the bottleneck — solved by RCON.**

### Outbound (server BP → external process)
- **FLS WebSocket:** `WebSocketConnectionManager` (FuncomLiveServices, runtime, ships —
  retail UTF-16 string verified 2026-06-11) — `init() / connect(ConnectionSettings) /
  send_message(str) / close()`. `ConnectionSettings` = `m_protocol` / `m_server_url` /
  `m_upgrade_headers` (Map[str,str]) → arbitrary `wss://` + auth headers.
  **Send-only at the BP layer — now DEFINITIVE (2026-06-11), not just "sweep found
  nothing":** the plugin DLL's exec-thunk exports reveal four HIDDEN reflected
  UFunctions — `OnReceiveData(FString)`, `OnConnectionComplete/Closed/Error` — and
  their raw FunctionFlags (read via the bridge, `bpkit/ops/probe_ws_flags.py`) are
  `Final|Native|Private` (0x00040401): `Final` ⇒ the BP compiler refuses any
  override/shadow, no BP flags ⇒ invisible to graphs, and the class has ZERO
  reflected properties/delegates, so the received string never touches anything BP
  can reach. (Funcom reflects them only for native name-binding.) Fun fact:
  `Init/Connect/SendMessage/Close` are BlueprintNativeEvents — the class was built
  for BP *sending* only. Recv probes: `bpkit/ops/probe_ws_recv.py` (build-wide
  sweep v2 incl. BIE visibility ground-truth), `examples/ws_echo_server.py`
  (stdlib RFC6455 server for future outbound tests).
- `AsyncTaskDownloadImage` (UMG): HTTP GET beacon; response is only ever a Texture2D, and
  dedicated servers run nullrhi → useless beyond fire-and-forget.

### Full-duplex TCP with BP RECV: **`MoviePipelineExecutorBase`** ★ (found 2026-06-11)
The ONLY BP-bindable network-receive delegate in the entire build lives on the Movie
Render Queue executor (`MovieRenderPipelineCore`, engine plugin, **Runtime** module) —
built for render-farm orchestration, perfectly generic in practice.
- **BP API** (construct the concrete child `MoviePipelinePythonHostExecutor` via
  Construct Object From Class; keep it in a UPROPERTY var or GC eats it):
  `connect_socket(host, port) -> bool`, `send_socket_message(str) -> bool`,
  `is_socket_connected()`, `disconnect_socket()`, and
  **`socket_message_recieved_delegate` — BlueprintAssignable** (Bind Event compiles;
  schema-validated live-wire accepted). Bonus HTTP pair on the same class:
  `send_http_request(url, verb, message, headers Map) -> index` +
  `http_response_recieved_delegate(index, code, message)` (reflected-verified,
  not yet live-tested).
- **Wire framing (hexdump-verified):** 4-byte **little-endian** length prefix +
  UTF-8 payload, both directions. Test server: `examples/mrq_tcp_probe_server.py`.
- **Recv pump is automatic** every engine frame on an idle instance (no render job
  required); `on_begin_frame()` is BP-callable as a manual pump fallback.
- **LIVE-VERIFIED end-to-end in-editor (2026-06-11):** authored scratch BP
  (Bind Event → custom event(Message:String) → Set LastMsg), pointed at a live
  executor, server pushed a message → BP var held the payload. (The one-shot
  probe chain was cleaned up post-verification — git history has it at
  `0e1a812`; `mods/mrq-echo/01_mrq.py` is the living worked example.)
- **PIE-VERIFIED in a live game world (2026-06-11):** `mods/mrq-echo/`'s
  ModController (BeginPlay construct+bind, Tick reconnect, OnSockMsg ack+HUD) ran
  in PIE: connected out, sent the framed hello, and **acked every message the
  server pushed back** — sustained bidirectional delivery, including frames split
  across TCP segments (the executor reassembles). No `CallInEditor` needed in a
  begun-play world. Note: PIE ran TWO controller instances (net-mode dependent) —
  a production manager should gate the connection on `HasAuthority`. And don't
  pair this mod with a dumb echo server: BP acks the echo, the echo returns the
  ack → infinite `ack:ack:…` ping-pong (the gateway console doesn't auto-echo).
- **Editor-world gotcha:** the frame-pump broadcast won't run actor BP script in an
  editor world unless the bound custom event has `CallInEditor`
  (`AActor::ProcessEvent` gate); irrelevant in a begun-play game world.
- **Ships in retail:** `ConanSandbox-Win64-Shipping.exe` contains
  `MoviePipelinePythonHostExecutor`, `ConnectSocket`, `SendSocketMessage`,
  `SocketMessageRecievedDelegate`, `SendHTTPRequest` (ASCII + UTF-16, 2026-06-11) —
  monolithic builds only link ENABLED plugin modules, so the module loads; runtime
  registration still wants a cooked-run confirmation (`mods/mrq-echo/` is the
  verification vehicle). Unlike RCON (dedicated-server-only listener), this class
  exists in the **client** binary too ⇒ usable in SP/listen, and it's true PUSH
  (no poll loop) — which is why it supersedes RCON as the gateway recv channel.

### Inbound (external process → server BP): **`RconCommandObject`** ★
RconPlugin (runtime module, enabled, ships) lets a mod **define custom RCON commands in
Blueprint** — its own docstring: "Blueprint object so you can make rcon commands in blueprint."
- BP-subclass `RconCommandObject`; class defaults `rcon_command_name` (Name) and
  `rcon_help_string` (str); override `rcon_command(world, args: Array[str]) -> str` —
  args = the tokenized command line, **the returned string is the RCON response**.
- Server config (ini/cmdline): `RconEnabled`, `RconPassword`, `RconPort` (no password ⇒
  "Could not enable Rcon"). Commands are logged to `RconCommandLog.log`.
- **It's a serial line:** one connection per source IP (a new connection from the same
  address kills the old one) and one in-flight command per connection ("Still processing
  previous command"), plus a per-IP karma rate limiter (`RconMaxKarma`). Half-duplex
  request/response over local TCP — fine for any LLM-cadence loop; tune karma on your own box.
- Gateway pattern (all gateway-initiated, so no BP receive needed anywhere):
  `poll` → BP returns pending NPC requests as JSON; gateway runs the LLM;
  `reply <id> <json>` → BP parses and routes. JSON build/parse in BP via **`PlayFabJsonObject`**
  (`encode_json`/`decode_json` — pure utility class, ships, no backend dependency).
- **EDITOR-VERIFIED (2026-06-11):** a BP subclass with the `RconCommand(world,
  args: Array[str]) -> (Output str, ReturnValue bool)` override authored via
  `bridge.create_function_override` compiles clean and returns the echo when
  name-dispatched (`call_method`). The proof mod `mods/rcon-echo/` (`bpecho`
  command + load-chain ModController + a Source-RCON gateway client) was
  **retired 2026-06-11** — superseded by the MRQ channel above for recv; git
  history has it as-built at `0e1a812` if dedicated-server RCON is ever needed.
  Authoring traps live in `docs/INTERNALS.md` §9 (FunctionEntry paste mangling,
  unwired multi-node paste drop, bound-method-vs-call_method dispatch).
- **RETAIL SHIPS IT (verified 2026-06-11):** the retail Shipping client binary
  `ConanSandbox-Win64-Shipping.exe` contains `RconEnabled`, `Rcon is ready for
  client connections`, `Rcon disabled.`, AND `RconCommandName` (the BP property)
  — so RconPlugin and the BP command property are compiled into the shipped game.
- **RCON listener is DEDICATED-SERVER-ONLY (verified 2026-06-11).** The plugin
  DLL defines a file-local `StaticDedicatedServerCheck()` and reads
  `UWorld::InternalGetNetMode`; empirically a PIE **listen server** (which runs
  IN the editor process) logs `LogRcon: Display: Rcon disabled.` at every PIE
  start regardless of config or `-RconEnabled=1 -RconPort -RconPassword` launch
  params. A separate-process PIE `-server` (still the editor binary) never opens
  the socket either. **You CANNOT test the RCON channel in PIE or on a listen
  server — only a true Conan *Dedicated Server* (separate Steam tool, appid
  443030) starts the listener.** In-memory `GConfig` set of
  `[RconPlugin]`/`[ServerSettings] RconEnabled/RconPort/RconPassword` does not
  help (the gate is the build/run target, not the config).
- **UNVERIFIED (and now moot unless MRQ falls through):** how the plugin discovers
  BP subclasses (a controller hard class-ref covers the load half); wire protocol
  (Source RCON vs plaintext — the retired rcon-echo's `gateway/rcon_client.py` at
  `0e1a812` does both); arg tokenization of quoted JSON (worst case: base64).

### Fallback inbound channels (verified reflected, weaker)
- `ConanGameState.get_server_command_history()` → `ServerCommandHistory.command_log:
  Array[ServerConsoleCommandLogEntry{caller, command_string}]` — BP-readable log of every
  server command; a free poll-based inbox even without the Rcon hook.
- `ServerSettings` is a **replicated actor** with hundreds of R/W props; RCON
  `SetServerSetting <key> <value>` writes them → usable as a string mailbox cell.
- PlayFab SDK (rides in via FLS, fully reflected incl. `ExecuteCloudScript` whose response
  JSON arrives in a BP delegate) — works, but `set_play_fab_settings` repoints a
  **process-global static** (hijacks the game's own FLS); acceptable only on a dedicated
  server you own. Superseded by RCON.

### Dead ends (don't re-derive)
- No BP-reachable **websocket** receive path, definitively (see the FLS bullet:
  hidden `Final|Native|Private` callbacks, zero reflected surface). The one and only
  socket-recv delegate in the build is the MRQ executor's (Full-duplex TCP above).
- `ChatWindow` is pure client UMG (no server-side chat read hook surfaced).
- `SystemLibrary.clipboard_copy/paste`, `get_environment_variable`, `load_string_from_file`:
  **not in this build**. `get_console_variable_string_value` exists but content mods can't
  create cvars.
- Dreamworld persistence is save-pipeline only (no live read-key API).
- `ChatGptApiClient` (DialoguePlugin) is **editor-module only** — a dev-time GPT
  dialogue-tree generator; does not ship. (Fun: Funcom's own tooling already does
  LLM-authored dialogue at edit time.)

## Formation system (backburnered — a v2 path)

Native formations make mounted followers move as a smooth group. Activate via
`set_formation_leader_row("…")` on the player + `set_formation_criteria_row("…",
autojoin=True)` on each follower; widen slots via the leader component's
`formation_template_data`. Tables: `FormationsTemplateTable`,
`FormationCriteriaTable`; component `BP_FormationLeaderComponent`. Open issues:
slot rotation, tight-spot fail-safe, BP-baking.

## Finding native signatures — never fire blind

Calling a native UFunction with guessed/empty args to make the error "reveal" the
signature can **null-deref and crash the whole editor** (cost two PIE sessions).
Unreal's reflection already has every signature — read it instead:
- **Docstring:** every reflected function auto-generates a typed `__doc__`, e.g.
  `unreal.ConanCharacter.bp_mount_server.__doc__`. For a BP class:
  `t = type(unreal.get_default_object(cls)); print(t.start_emote.__doc__)`.
- **Enums:** `dir(unreal.CharacterEmotes)`; `<Enum>.<VALUE>.get_display_name()`.
- **BP graphs:** `bpkit.bridge.read_blueprint(path)` — the `K2Node_FunctionEntry`
  node lists typed param pins (PIE-independent, read-only).

Only after you know the real param **types**, make one call with correct args.
