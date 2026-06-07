import unreal, os
ld = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_log_dir())
logs = sorted([f for f in os.listdir(ld) if f.endswith(".log")],
              key=lambda f: os.path.getmtime(os.path.join(ld, f)))
print("logdir:", ld)
print("log files:", logs[-3:])
path = os.path.join(ld, logs[-1])
with open(path, "r", errors="ignore") as f:
    lines = f.readlines()
print("total lines:", len(lines), "-- last relevant 60:")
# full untruncated unique error lines + STOW/FOLLOWERS prints
seen = set()
for l in lines[-2000:]:
    s = l.rstrip()
    if any(k in s for k in ("Runtime Error", "STOW A FOLLOWER", "FOLLOWERS:", "MountedFollower")):
        core = s.split("]")[-1]
        if core not in seen:
            seen.add(core)
            print(s)
