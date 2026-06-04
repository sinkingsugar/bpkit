"""Offline: prove bp_ir round-trips. For every graph in a dump:
parse -> render -> re-parse and check the compact views are identical, i.e. the
IR reproduces the graph faithfully. No editor needed."""
import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
import bp_ir

text = open(sys.argv[1], encoding="utf-8").read()
graphs = bp_ir.Graph.parse(text)
ok = 0
for name, g in graphs.items():
    c1 = g.compact()
    g2 = bp_ir.Graph.parse_one(g.render(), name)
    g2.name = name                       # render drops ExportPath-derived grouping
    c2 = g2.compact()
    same = c1 == c2
    ok += same
    flag = "OK " if same else "DIFF"
    print("%s %-30s nodes=%d" % (flag, name, len(g.nodes)))
    if not same:
        # show first differing line
        a, b = c1.splitlines(), c2.splitlines()
        for i in range(max(len(a), len(b))):
            x = a[i] if i < len(a) else "<none>"
            y = b[i] if i < len(b) else "<none>"
            if x != y:
                print("   first diff @%d:\n   1: %s\n   2: %s" % (i, x, y)); break
print("\n%d/%d graphs round-trip identical" % (ok, len(graphs)))
