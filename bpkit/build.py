"""bpkit.build - one-call build+verify harness for authored graphs.

Consolidates the inject -> (auto-relink dropped wires) -> cross-set fixups ->
compile -> save -> scan tail that every mod build script used to copy-paste. Pairs
with bpkit.ir (author the graph) and bpkit.bridge (the low-level write).

    from bpkit import ir, build
    g = ir.Graph("EventGraph")
    ...author nodes/wires...
    rep = build.build_graph("/Game/Mods/X/BP_Y.BP_Y", g)
    # rep["ok"] is True iff: full paste, no dropped wires (after auto-relink),
    # no orphaned pins, no stray wildcards, no error nodes.

`post(graph_ptr)` is an optional hook that runs after inject (and auto-relink) but
before compile -- use it for CROSS-SET wiring the paste can't make (e.g. a
function-entry 'then' -> a pasted node's 'execute' via bridge.connect_pins).
"""
import re
from bpkit import bridge as bp


def scan(graph_ptr):
    """Static scan of a live graph. Returns dict(orphans, wildcards, errors):
      - orphans:   pins with bOrphanedPin=True (a default/wire that failed to merge)
      - wildcards: unresolved wildcard pins on non-macro nodes (a dead loop / undet. type)
      - errors:    nodes carrying ErrorMsg / bHasCompilerMessage
    Empty lists == clean. (compile_blueprint's "compiled" flag is NOT trustworthy;
    this scan + the inject dropped-wire check are the real verdict.)"""
    txt = bp.export_nodes(bp.graph_nodes(graph_ptr))
    orphans = re.findall(r'PinName="([^"]+)"[^)]*?bOrphanedPin=True', txt)
    wildcards, errors = [], []
    for blk in re.split(r'(?=Begin Object Class=)', txt):
        if not blk.strip():
            continue
        nm = (re.search(r'Name="([^"]+)"', blk) or [None, "?"])[1]
        is_macro = "K2Node_MacroInstance" in blk
        for pin in re.findall(r'CustomProperties Pin \((.*)\)', blk):
            if 'PinCategory="wildcard"' in pin and not is_macro:
                pn = (re.search(r'PinName="([^"]+)"', pin) or [None, "?"])[1]
                wildcards.append("%s.%s" % (nm, pn))
        if "ErrorMsg=" in blk or 'bHasCompilerMessage=True' in blk:
            errors.append(nm)
    return {"orphans": orphans, "wildcards": wildcards, "errors": errors}


def build_graph(full, graph, graph_name="EventGraph", post=None, verbose=True):
    """Render `graph`, clear + inject into <full>'s <graph_name> (inject auto-relinks
    any wire dropped on paste), run the optional post(graph_ptr) cross-set hook,
    compile, save, then scan. `full` is the object path '/Game/X.X'. Returns a report
    dict and (verbose) prints a standard summary + BUILD OK / BUILD HAS ISSUES."""
    import unreal
    text = graph.render()
    authored = text.count("Begin Object Class=")
    bp_ptr, graph_ptr = bp.find_graph(full, graph_name)
    if not bp_ptr or not graph_ptr:
        raise ValueError("graph %r not found in %s" % (graph_name, full))
    bp.clear_graph(bp_ptr, graph_ptr)
    res = bp.inject(full, text, graph_name=graph_name, compile=False, save=False)
    rep = {"authored": authored, "pasted": res.get("pasted"),
           "relinked": res.get("relinked", []),
           "dropped_links": res.get("dropped_links", [])}
    rep["dropped_nodes"] = authored - (res.get("pasted") or 0)
    if post:
        post(graph_ptr)
    asset_path = full.split(".")[0]
    bp_obj = unreal.load_asset(asset_path)
    bp.mark_structurally_modified(bp_ptr)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp_obj)
    rep["saved"] = bool(unreal.EditorAssetLibrary.save_asset(asset_path))
    rep.update(scan(graph_ptr))
    rep["ok"] = not (rep["dropped_nodes"] or rep["dropped_links"]
                     or rep["orphans"] or rep["wildcards"] or rep["errors"])
    if verbose:
        print("inject: pasted %d/%d | relinked %d | dropped_links %s"
              % (rep["pasted"], rep["authored"], len(rep["relinked"]),
                 rep["dropped_links"] or "(none)"))
        print("scan: orphans %s | wildcards %s | errors %s"
              % (rep["orphans"] or "(clean)", rep["wildcards"] or "(clean)",
                 rep["errors"] or "(clean)"))
        print("BUILD OK" if rep["ok"] else "BUILD HAS ISSUES")
    return rep
