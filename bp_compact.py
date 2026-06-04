"""bp_compact - compress Unreal Blueprint copy/paste node text into a dense,
token-cheap, navigable outline for an LLM to reason over.

The raw export from bp_bridge.export_nodes / read_blueprint is enormous (~20
boilerplate flags per pin line; a single blueprint is megabytes). This collapses
it to a structural view: per node a one-line header (name / type / semantic
label) plus only the *connected* pins as edges and any non-default literal
inputs. Unconnected default pins and all the boilerplate flags are dropped.

Lossy by design -- it's the NAVIGATION layer. When exact text for a node is
needed, re-export just that node losslessly (bp_bridge.export_nodes([ptr])).

Pure stdlib, no unreal/ctypes -> runs offline on a dump file or on text returned
from the editor. CLI:

    python bp_compact.py <dump.txt>              # BP summary + every graph
    python bp_compact.py <dump.txt> --summary    # just the BP/graph overview
    python bp_compact.py <dump.txt> --graph NAME  # one graph, compact
    python bp_compact.py <dump.txt> --node NAME   # which graph + raw-ish detail

Output legend (per node):
    <name>  <Type>  <label>
      o:<pin> -> <target>.<pin>[, ...]     outgoing link(s) from an output pin
      i:<pin> <- <source>.<pin>[, ...]     incoming link(s) into an input pin
      i:<pin> = <literal>                  non-default literal on an input pin
"""
import os
import re
import sys

# ----------------------------------------------------------------------------
# parsing
# ----------------------------------------------------------------------------
_NODE_PREFIXES = ("K2Node_", "EdGraphNode_", "AnimGraphNode_")


def _short_class(cls):
    name = cls.rsplit(".", 1)[-1]
    for p in _NODE_PREFIXES:
        if name.startswith(p):
            return name[len(p):]
    return name


def _short_name(name):
    for p in _NODE_PREFIXES:
        if name.startswith(p):
            return name[len(p):]
    return name


def _split_top(s):
    """Split on commas at paren-depth 0 outside quotes (UE prop lists nest)."""
    parts, depth, inq, cur = [], 0, False, []
    for ch in s:
        if ch == '"':
            inq = not inq
        elif not inq and ch == "(":
            depth += 1
        elif not inq and ch == ")":
            depth -= 1
        elif not inq and ch == "," and depth == 0:
            parts.append("".join(cur)); cur = []; continue
        cur.append(ch)
    if cur:
        parts.append("".join(cur))
    return parts


def _kv(token):
    i = token.find("=")
    return (token[:i].strip(), token[i + 1:].strip()) if i >= 0 else (token.strip(), "")


def _unquote(v):
    return v[1:-1] if len(v) >= 2 and v[0] == '"' and v[-1] == '"' else v


def _parse_pin(body):
    """body = inside of 'CustomProperties Pin (...)'. Returns a pin dict."""
    pin = {"name": "", "dir": "?", "cat": "", "links": [], "default": None}
    for k, v in (_kv(t) for t in _split_top(body)):
        if k == "PinName":
            pin["name"] = _unquote(v)
        elif k == "Direction":
            pin["dir"] = "O" if "Output" in v else "I"
        elif k == "PinType.PinCategory":
            pin["cat"] = _unquote(v)
        elif k == "LinkedTo":
            inner = v.strip()
            if inner.startswith("("):
                inner = inner[1:-1] if inner.endswith(")") else inner[1:]
            for ref in _split_top(inner):
                ref = ref.strip()
                if not ref:
                    continue
                nm, _, guid = ref.partition(" ")
                pin["links"].append((nm.strip(), guid.strip()))
        elif k in ("DefaultValue", "DefaultObject", "DefaultTextValue"):
            dv = _unquote(v)
            if dv not in ("", "None"):
                pin["default"] = dv
    return pin


class Node(object):
    __slots__ = ("name", "cls", "graph", "props", "pins", "x", "y")

    def __init__(self, name, cls, graph):
        self.name = name
        self.cls = cls
        self.graph = graph
        self.props = []
        self.pins = []
        self.x = self.y = 0


def parse_nodes(text):
    """Parse all 'Begin Object ... End Object' node blocks. Groups by graph via
    each node's ExportPath. Returns a list of Node."""
    nodes = []
    cur = None
    depth = 0
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("Begin Object"):
            depth += 1
            if depth == 1:
                cls = re.search(r'Class=(\S+)', line)
                nm = re.search(r'Name="([^"]+)"', line)
                gp = re.search(r":([^.\']+)\.", line)        # ...:GraphName.NodeName'
                cur = Node(nm.group(1) if nm else "?",
                           cls.group(1) if cls else "?",
                           gp.group(1) if gp else "?")
                nodes.append(cur)
            continue
        if line.startswith("End Object"):
            depth -= 1
            if depth == 0:
                cur = None
            continue
        if cur is None or depth != 1:
            continue
        if line.startswith("CustomProperties Pin"):
            lp = line.find("("); rp = line.rfind(")")
            if lp >= 0 and rp > lp:
                cur.pins.append(_parse_pin(line[lp + 1:rp]))
        else:
            cur.props.append(line)
            m = re.match(r'NodePos([XY])=(-?\d+)', line)
            if m:
                setattr(cur, "x" if m.group(1) == "X" else "y", int(m.group(2)))
    return nodes


# ----------------------------------------------------------------------------
# semantics
# ----------------------------------------------------------------------------
def _last_seg(path):
    return re.split(r"[./']", path.strip("'"))[-1]


def node_label(node):
    """A short semantic label for the node (the 'what it does')."""
    p = "\n".join(node.props)
    c = node.cls

    def member():
        m = re.search(r'MemberName="([^"]+)"', p)
        return m.group(1) if m else None

    if "Comment" in c:
        m = re.search(r'NodeComment="((?:[^"\\]|\\.)*)"', p)
        t = (m.group(1).split("\\n")[0] if m else "").strip()
        return ('"%s"' % (t[:48] + ("..." if len(t) > 48 else ""))) if t else "comment"
    if "IfThenElse" in c:
        return "branch"
    if "Knot" in c:
        return "reroute"
    if "CustomEvent" in c:
        m = re.search(r'CustomFunctionName="([^"]+)"', p)
        return m.group(1) if m else "event"
    if c.endswith("K2Node_Event") or c.endswith(".Event"):
        return member() or "event"
    if "DynamicCast" in c:
        m = re.search(r"TargetType=[^']*'([^']+)'", p)
        return "as " + _last_seg(m.group(1)) if m else "cast"
    if "MacroInstance" in c:
        m = re.search(r"MacroGraph=[^\"']*[\"']([^\"']+)[\"']", p)
        return _last_seg(m.group(1)) if m else "macro"
    if "FunctionEntry" in c:
        return (member() or "entry") + " <entry>"
    if "FunctionResult" in c:
        return "return"
    if "VariableGet" in c:
        return "get " + (member() or "?")
    if "VariableSet" in c:
        return "set " + (member() or "?")
    if "CommutativeAssociativeBinaryOperator" in c or "PromotableOperator" in c:
        return member() or "op"
    if "CallFunction" in c or "CallArrayFunction" in c or "CallDataTableFunction" in c:
        return member() or "call"
    return member() or ""


def is_entry(node):
    c = node.cls
    return ("Event" in c and "EventReference" in "\n".join(node.props)) \
        or "CustomEvent" in c or "FunctionEntry" in c or "Tunnel" in c and "FunctionEntry" in c


# ----------------------------------------------------------------------------
# emit
# ----------------------------------------------------------------------------
def compact_graph(nodes, name):
    g = [n for n in nodes if n.graph == name]
    if not g:
        return "== %s == (empty)\n" % name
    entries = [_short_name(n.name) for n in g if is_entry(n)]
    out = ["== %s == %d nodes%s"
           % (name, len(g), ("  entry: " + ", ".join(entries)) if entries else "")]
    for n in g:
        label = node_label(n)
        out.append("%s  %s%s" % (_short_name(n.name), _short_class(n.cls),
                                 "  " + label if label else ""))
        for pin in n.pins:
            tag = "o:" if pin["dir"] == "O" else "i:"
            if pin["links"]:
                arrow = " -> " if pin["dir"] == "O" else " <- "
                tgts = ", ".join(_short_name(nm) for nm, _ in pin["links"])
                out.append("  %s%s%s%s" % (tag, pin["name"], arrow, tgts))
            elif pin["default"] is not None and pin["dir"] == "I":
                out.append("  i:%s = %s" % (pin["name"], pin["default"]))
    return "\n".join(out) + "\n"


def summary(nodes):
    graphs = {}
    for n in nodes:
        graphs.setdefault(n.graph, []).append(n)
    out = ["BP SUMMARY: %d graphs, %d nodes" % (len(graphs), len(nodes))]
    for gname, g in graphs.items():
        entries = [node_label(n) for n in g if is_entry(n)]
        types = {}
        for n in g:
            types[_short_class(n.cls)] = types.get(_short_class(n.cls), 0) + 1
        top = ", ".join("%sx%d" % (t, c) for t, c in
                        sorted(types.items(), key=lambda kv: -kv[1])[:4])
        out.append("  %-28s %3d nodes  [%s]%s"
                   % (gname, len(g), top,
                      ("  entry: " + ", ".join(entries)) if entries else ""))
    return "\n".join(out) + "\n"


def graph_names(nodes):
    seen = []
    for n in nodes:
        if n.graph not in seen:
            seen.append(n.graph)
    return seen


def _main(argv):
    if not argv:
        print(__doc__)
        return
    path = argv[0]
    opts = argv[1:]
    with open(path, "r", encoding="utf-8") as f:
        nodes = parse_nodes(f.read())

    if "--split" in opts:
        d = opts[opts.index("--split") + 1]
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "_summary.txt"), "w", encoding="utf-8") as f:
            f.write(summary(nodes))
        names = graph_names(nodes)
        for g in names:
            safe = re.sub(r"[^A-Za-z0-9_.-]", "_", g) or "graph"
            with open(os.path.join(d, safe + ".txt"), "w", encoding="utf-8") as f:
                f.write(compact_graph(nodes, g))
        print("wrote _summary.txt + %d graph files to %s/" % (len(names), d))
        return
    if "--summary" in opts:
        print(summary(nodes)); return
    if "--graph" in opts:
        g = opts[opts.index("--graph") + 1]
        print(compact_graph(nodes, g)); return
    if "--node" in opts:
        target = opts[opts.index("--node") + 1]
        for n in nodes:
            if _short_name(n.name) == target or n.name == target:
                print("graph: %s" % n.graph)
                print(compact_graph([n], n.graph))
                return
        print("node not found:", target); return

    print(summary(nodes))
    for g in graph_names(nodes):
        print(compact_graph(nodes, g))


if __name__ == "__main__":
    _main(sys.argv[1:])
