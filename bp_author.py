"""bp_author - build Blueprint copy/paste node text declaratively.

Pairs with bp_bridge: you describe nodes + wires, render() emits the import text,
and bp_bridge.inject() pastes + compiles it. You only specify intent (the
function/event + the pins you care about + the wires); UE reconstructs every
other pin from the signature on import, and matches your pins by name to transfer
literals and links. GUIDs/PinIds are real uuid4 values (never degenerate/zero).

    from bp_author import Graph
    import bp_bridge as bp
    g = Graph()
    ev = g.event("ReceiveBeginPlay")
    pr = g.call("PrintString", "/Script/Engine.KismetSystemLibrary",
                inputs={"InString": "hello"})
    g.wire(ev, "then", pr, "execute")          # exec
    bp.inject("/Game/X.X", g.render())

Data wires use exec=False (UE reconstructs the data pin types by name):
    g.wire(getter, "ReturnValue", pr, "InString", exec=False)
"""
import uuid

_BPG = "/Script/BlueprintGraph."
_CLASS_OBJ = "/Script/CoreUObject.Class'%s'"


def guid():
    return uuid.uuid4().hex.upper()           # 32 uppercase hex, never zero


class Node(object):
    def __init__(self, name, cls, header):
        self.name = name
        self.cls = cls
        self.header = list(header)             # extra property lines
        self.pos = (0, 0)
        self.guid = guid()
        self.pins = {}                         # pinname -> dict

    def pin(self, name, direction=None, cat=None, default=None):
        p = self.pins.get(name)
        if p is None:
            p = self.pins[name] = {"id": guid(), "dir": None, "cat": None,
                                   "default": None, "links": []}
        if direction:
            p["dir"] = direction
        if cat:
            p["cat"] = cat
        if default is not None:
            p["default"] = default
        return p


class Graph(object):
    def __init__(self):
        self.nodes = []
        self._counts = {}

    def _name(self, base):
        self._counts[base] = self._counts.get(base, 0) + 1
        return "K2Node_%s_%d" % (base, self._counts[base])

    # --- node factories -----------------------------------------------------
    def node(self, short_cls, header, base="Node", pos=(0, 0)):
        """Generic node. short_cls e.g. 'K2Node_IfThenElse' (BlueprintGraph) or a
        full '/Script/Mod.Class' path. header = list of property lines."""
        cls = short_cls if short_cls.startswith("/Script/") else _BPG + short_cls
        n = Node(self._name(base), cls, header)
        n.pos = pos
        self.nodes.append(n)
        return n

    def event(self, member, parent="/Script/Engine.Actor", pos=(0, 0)):
        return self.node(
            "K2Node_Event",
            ['EventReference=(MemberParent="%s",MemberName="%s")' % (_CLASS_OBJ % parent, member),
             "bOverrideFunction=True"],
            base="Event", pos=pos)

    def custom_event(self, name, pos=(0, 0)):
        return self.node("K2Node_CustomEvent", ['CustomFunctionName="%s"' % name],
                         base="CustomEvent", pos=pos)

    def call(self, member, parent, inputs=None, pos=(0, 0)):
        n = self.node(
            "K2Node_CallFunction",
            ['FunctionReference=(MemberParent="%s",MemberName="%s")' % (_CLASS_OBJ % parent, member)],
            base="CallFunction", pos=pos)
        for pn, val in (inputs or {}).items():
            n.pin(pn, direction="I", default=str(val))
        return n

    def branch(self, pos=(0, 0)):
        return self.node("K2Node_IfThenElse", [], base="IfThenElse", pos=pos)

    # --- wiring -------------------------------------------------------------
    def wire(self, src, src_pin, dst, dst_pin, exec=True):
        """Connect src.src_pin (output) -> dst.dst_pin (input). exec=True marks
        them as exec pins; for data wires pass exec=False (UE reconstructs the
        data type from the signature by pin name)."""
        cat = "exec" if exec else None
        sp = src.pin(src_pin, direction="O", cat=cat)
        dp = dst.pin(dst_pin, direction="I", cat=cat)
        sp["links"].append((dst, dst_pin))
        dp["links"].append((src, src_pin))

    # --- render -------------------------------------------------------------
    def render(self):
        out = []
        for n in self.nodes:
            out.append('Begin Object Class=%s Name="%s"' % (n.cls, n.name))
            for line in n.header:
                out.append("   " + line)
            out.append("   NodePosX=%d" % n.pos[0])
            out.append("   NodePosY=%d" % n.pos[1])
            out.append("   NodeGuid=%s" % n.guid)
            for pname, p in n.pins.items():
                parts = ["PinId=%s" % p["id"], 'PinName="%s"' % pname]
                if p["dir"] == "O":
                    parts.append('Direction="EGPD_Output"')
                elif p["dir"] == "I":
                    parts.append('Direction="EGPD_Input"')
                if p["cat"]:
                    parts.append('PinType.PinCategory="%s"' % p["cat"])
                if p["default"] is not None:
                    parts.append('DefaultValue="%s"' % p["default"])
                if p["links"]:
                    lt = ",".join("%s %s" % (ln.name, ln.pin(lp)["id"])
                                  for ln, lp in p["links"])
                    parts.append("LinkedTo=(%s,)" % lt)
                out.append("   CustomProperties Pin (%s)" % ",".join(parts))
            out.append("End Object")
        return "\n".join(out) + "\n"
