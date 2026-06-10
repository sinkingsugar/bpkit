"""Surface a Blueprint's real compile errors. compile_blueprint doesn't raise, so
read the error annotations the compiler writes onto the nodes (bHasCompilerMessage/
ErrorMsg) and report which node + message.
Run: python ue_run.py bpkit/ops/compile_errors.py /Game/Path/BP_Asset [GraphName]
"""
from bpkit import bridge as bp, config as _cfg
import unreal

_args = _cfg.argv()
if not _args:
    raise SystemExit("usage: ue_run.py bpkit/ops/compile_errors.py /Game/Path/BP_Asset [GraphName]")
PATH = _args[0].rstrip("/")
GRAPH = _args[1] if len(_args) > 1 else "EventGraph"
FULL = PATH if "." in PATH else "%s.%s" % (PATH, PATH.rsplit("/", 1)[-1])

bp_obj = unreal.load_asset(PATH.split(".")[0])
if not bp_obj:
    raise SystemExit("no asset at %s" % PATH)
unreal.BlueprintEditorLibrary.compile_blueprint(bp_obj)

bp_ptr, graph_ptr = bp.find_graph(FULL, GRAPH)
txt = bp.export_nodes(bp.graph_nodes(graph_ptr))

# split into node blocks, flag any with a compiler message
import re
blocks = re.split(r'(?=Begin Object Class=)', txt)
flagged = 0
for b in blocks:
    if "bHasCompilerMessage=True" in b or "ErrorMsg" in b or 'ErrorType' in b:
        flagged += 1
        nm = re.search(r'Name="([^"]+)"', b)
        fn = re.search(r'MemberName="([^"]+)"', b)
        em = re.search(r'ErrorMsg="([^"]*)"', b)
        print("NODE:", nm.group(1) if nm else "?",
              "| fn:", fn.group(1) if fn else "-",
              "| ErrorMsg:", em.group(1) if em else "(flagged, see block)")
if not flagged:
    print("%s [%s]: compiled, no per-node error annotations." % (FULL, GRAPH))
