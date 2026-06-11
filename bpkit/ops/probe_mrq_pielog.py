"""Read-only: what happened in the last PIE session? Pull PIE lifecycle lines,
script errors, MrqEcho mentions, and socket/MoviePipeline lines from the live log."""
import unreal, os

ld = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_log_dir())
logs = sorted([f for f in os.listdir(ld) if f.endswith(".log")],
              key=lambda f: os.path.getmtime(os.path.join(ld, f)))
path = os.path.join(ld, logs[-1])
with open(path, "r", errors="ignore") as f:
    lines = f.readlines()
print("log:", path, "| total lines:", len(lines))

KEYS = ("PlayLevel", "PIE:", "LogPlayLevel", "MrqEcho", "MoviePipeline", "ConnectSocket",
        "Runtime Error", "Blueprint Runtime", "LogScript", "AccessNone", "Access None",
        "BeginPlay", "LogNet", "LogSockets", "Ensure", "Fatal", "Assertion")
hits = []
for i, l in enumerate(lines[-4000:]):
    s = l.rstrip()
    if any(k in s for k in KEYS):
        hits.append(s)
# dedupe consecutive-ish, keep last 80
seen = set()
out = []
for s in hits:
    core = s.split("]")[-1].strip()
    if core in seen:
        continue
    seen.add(core)
    out.append(s)
for s in out[-80:]:
    print(s[:240])
