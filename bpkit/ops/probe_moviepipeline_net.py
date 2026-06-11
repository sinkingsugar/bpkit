"""Read-only: the MovieRenderPipeline executor's socket/HTTP surface -- the only
BP-assignable network-recv delegate found in the whole build. Dump its BP API and
module provenance to judge shippability."""
import unreal

def doc(o, n=1):
    d = (getattr(o, "__doc__", "") or "").strip().splitlines()
    return " | ".join(d[:n]) if d else ""

OBJ_BASE = set(dir(unreal.Object))

for cname in ("MoviePipelineExecutorBase", "MoviePipelinePythonHostExecutor",
              "MoviePipelineLinearExecutorBase"):
    cls = getattr(unreal, cname, None)
    print("######## %s: %s" % (cname, "FOUND" if cls else "missing"))
    if not cls:
        continue
    print((cls.__doc__ or "").strip()[:600])
    print("  ---- attrs ----")
    for n in sorted(set(dir(cls)) - OBJ_BASE):
        if n.startswith("_"):
            continue
        print("   %-44s %s" % (n, doc(getattr(cls, n, None))[:170]))

# close the HTTP angle too: any reflected type with http/request in the name that has delegates
import re
print("\n######## http-ish types with delegate attrs ########")
pat = re.compile(r"http|webrequest|restful|curl", re.I)
for n in dir(unreal):
    if n.startswith("_") or not pat.search(n):
        continue
    t = getattr(unreal, n, None)
    if not isinstance(t, type):
        continue
    dlgs = []
    for a in dir(t):
        if a.startswith("_"):
            continue
        d = getattr(getattr(t, a, None), "__doc__", "") or ""
        if "MulticastDelegate" in d[:60] or d.startswith("(Delegate"):
            dlgs.append(a)
    print("  %-52s delegates: %s" % (n, dlgs if dlgs else "-"))
    print("      %s" % doc(t)[:140])
print("DONE")
