# rcon-echo — the RCON→Blueprint receive-channel proof

A two-asset mod that proves the **external-process → server-Blueprint** transport
for the LLM-NPC project (full channel map: `docs/CONAN-NOTES.md` §Network):

- **`BP_RconEchoCmd`** : `RconCommandObject` — registers the RCON command **`bpecho`**;
  its `RconCommand(world, args)` override returns `"ECHO: " + Join(args, " ")` with
  `ReturnValue=true`. The returned string is the RCON response.
- **`BP_RconEchoController`** : `ModController` — exists only to hard-reference the
  command class (CDO var `EchoCmdClass`) so it's in the cooked load chain. Whether
  the plugin's subclass discovery needs this is one of the two open questions this
  mod answers.

**Status: editor-verified** (override compiles clean and a name-dispatched
`call_method("RconCommand", ...)` returns the echo). The cooked-game test below is
the actual deliverable; it settles, in one shot:
1. does RconPlugin discover a mod-BP `RconCommandObject` subclass in the packaged game;
2. does the retail dedicated server ship/enable the RconPlugin at all
   (boot log: `Rcon is ready for client connections on ...` vs `Rcon disabled.`);
3. which wire protocol the plugin speaks (Source RCON vs plaintext — try both client modes);
4. how quoted/multi-word args tokenize.

## Test procedure

1. **DevKit (one-time, UI):** Mods tool → create mod **RconEcho** → make it the
   ACTIVE mod (this makes `/Game/Mods/RconEcho` writable).
2. **Deploy** (Play stopped): `& $py ue_run.py bpkit/ops/deploy.py rcon-echo`
3. **Cook** via the DevKit mod tool — confirm both BPs read **(Mod Asset)** in the
   cook dialog. Verify the pak: `UnrealPak RconEcho.pak -List`.
4. **Server config** — dedicated server's `Game.ini` (or command line):
   ```ini
   RconEnabled=1
   RconPort=25575
   RconPassword=<something>
   ```
   (No password ⇒ the plugin logs `Could not enable Rcon, no chosen Rcon password.`)
5. **Boot the dedicated server** with the mod in `modlist.txt`; grep the log for
   `Rcon is ready for client connections`.
6. **Fire the command:**
   ```
   python gateway/rcon_client.py --password <pw> bpecho hello from outside
   python gateway/rcon_client.py --password <pw> help        # lists commands; bpecho should appear
   python gateway/rcon_client.py --raw bpecho hello          # if Source-mode auth fails
   ```
   Success = `RESPONSE: 'ECHO: hello from outside'`.

## Caveats / known limits

- One RCON connection per source IP (a new one kills the old) and one in-flight
  command per connection; per-IP karma rate limiting (`RconMaxKarma`). It's a
  serial line — fine for LLM cadence, batch payloads rather than parallelizing.
- If the retail server turns out NOT to ship RconPlugin, fallbacks are mapped in
  `docs/CONAN-NOTES.md` §Network (ServerCommandHistory polling, ServerSettings
  mailbox, PlayFab-on-own-title).
