# mrq-echo — cooked-game proof of the MRQ TCP push channel

Proves that a shipped Conan mod's Blueprint can **receive** data pushed by an external
process, via `MoviePipelineExecutorBase`'s socket (the only BP-bindable network-recv
delegate in the build — `docs/CONAN-NOTES.md` §Network, "Full-duplex TCP with BP RECV").

One asset: `BP_MrqEchoController` (ModController).

- **BeginPlay** — Construct `MoviePipelinePythonHostExecutor` → `Ex` var → Bind Event
  `SocketMessageRecievedDelegate` → `OnSockMsg`.
- **Tick** — if not connected: `ConnectSocket(127.0.0.1:9777)`; on success sends
  `hello from MrqEcho v1 (cooked)` and shows a HUD banner. Per-tick retry, so the
  gateway can be (re)started any time.
- **OnSockMsg(Message)** — sends back `ack:<Message>` and shows `MRQ RECV: <Message>`
  in the HUD event feed (Shipping-safe; PrintString is compiled out).

## Build + cook (DevKit box)

1. DevKit Mods tool → **create mod `MrqEcho` and make it ACTIVE** (no API for this;
   without it the build dry-runs into `/Game/_Scratch`).
2. `& $py ue_run.py mods/mrq-echo/01_mrq.py` (Play stopped) — must print `BUILD OK`
   with no `[DRY RUN]` suffix.
3. Cook in the mod tool — confirm the BP reads **(Mod Asset)** in the cook dialog.
4. Verify the pak (`UnrealPak <Mod>.pak -List`, then the `-Windows.utoc -List` for
   the asset list — `.ucas` is Oodle-compressed, text grep finds nothing).

## Test (game machine)

1. Copy the pak into the game's `ConanSandbox/Mods/` and enable the mod.
2. Start the gateway console (any Python 3, stdlib only):
   `python mods/mrq-echo/gateway/mrq_console.py`
3. Launch the game, load into single-player.
4. Expect on the console: `game connected from ...` then `GAME> hello from MrqEcho v1 (cooked)`;
   in-game: `MRQ: gateway connected` in the HUD event feed.
5. Type a line in the console → in-game HUD shows `MRQ RECV: <line>`, console shows
   `GAME> ack:<line>`. That round-trip is the proof.

**Why not netcat:** the channel is framed — 4-byte little-endian length + UTF-8.
Raw netcat input gets read as a (huge) length prefix and the game waits forever;
`mrq_console.py` frames for you. (Receiving with netcat sort of works — you'll see
the text with 4 bytes of binary length glued to the front.)

## Status

- Editor build: clean (22 nodes, no errors/orphans). 2026-06-11
- PIE smoke: **PASSED** 2026-06-11 — controller connected, sent the framed hello,
  and acked every pushed message (sustained bidirectional, frames reassembled
  across split TCP reads). Two PIE instances connected (net-mode dependent);
  production managers should gate on HasAuthority.
- Cooked SP run: **pending** — this mod is the verification vehicle.
