"""Pull specific node blocks from a dump and print only the meaningful lines:
the function/member name + each pin's name, default literal, and links.
Offline, pure stdlib."""
import re, sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
import bp_ir

DUMP = r"C:\Users\sugar\devel\conan\dump_BP_Ritual_RaiseDead.txt"
WANT = sys.argv[1:] or [
    "CallFunction_2685", "CallFunction_2686", "CallFunction_1337",  # SetIntStat/GetIntStat/LevelUpTo
    "CallFunction_3245", "CallFunction_149", "CallFunction_167",     # SetupSourceNPC/GetThrallTableRow/ConfigureSpawnedNPC
    "CallFunction_234", "CallFunction_665", "CallFunction_505",      # SpawnThrallItem/SetIntStat(init)/SetLifeSpan
    "AsyncAction_7", "BreakStruct_0", "GetDataTableRow_0",
]

with open(DUMP, "r", encoding="utf-8") as f:
    graphs = bp_ir.Graph.parse(f.read())

allnodes = {}
for g in graphs.values():
    for n in g.nodes:
        allnodes[n.name] = n
        allnodes[re.sub(r"^K2Node_", "", n.name)] = n   # also key by compact-style name

def member(n):
    for k, v in n.header:
        if k in ("FunctionReference", "EventReference", "VariableReference",
                 "DataTable", "RowName", "TargetType", "MacroGraph", "ProxyFactoryFunctionName"):
            return "%s=%s" % (k, v)
    return ""

for name in WANT:
    n = allnodes.get(name)
    if not n:
        print("?? %s not found" % name); continue
    cls = n.cls.rsplit(".", 1)[-1]
    print("\n### %s  [%s]  %s" % (name, cls, member(n)))
    for p in n.pins:
        d = p.get("DefaultValue"); dob = p.get("DefaultObject")
        lit = d if (d not in (None, '""', '"None"')) else (dob if dob not in (None, '""', '"None"') else None)
        if p.links:
            tgt = ", ".join("%s" % nm for nm, _ in p.links)
            print("   %-3s %-26s -> %s" % (p.dir or "", p.name, tgt))
        elif lit is not None:
            print("   %-3s %-26s = %s" % (p.dir or "", p.name, lit))
