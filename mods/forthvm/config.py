"""forthvm metadata -- where the generated assets live + the FCell layout.

FCell is the VM's stack element (the load-bearing decision): a tagged variant cell
so float/vector/rotator/transform are first-class from day one, not int-only.
MEMBERS is the authoritative field list -- the human one-time struct setup AND the
bpkit generator both read it, so they can never drift.
"""

OUTPUT_PKG = "/Game/ForthVM"      # writable project content root (not /Game/Mods)
STRUCT = "ST_FCell"               # the FCell asset
VM = "BP_ForthVM"                 # the interpreter Blueprint (generated later)

# FCell fields, each with a DISTINCT Blueprint pin type, so the generator maps every
# MakeStruct/BreakStruct pin to its role *by type* (auto member names are GUID-suffixed
# and non-deterministic, so we never depend on names). 'Float' in UE5 BP is a 64-bit
# double (LWC); 'I' is an exact Integer64 for addresses/counters kept separate from 'F'.
#
# A UserDefinedStruct is created with one mandatory default member (a bool); we REUSE
# that as the bool field 'B' and add the other six -- giving 7 distinct-typed members
# with no need to remove the default. role -> struct-editor type label:
ROLES = {
    "Type": "Integer",     # cell tag: 0=Int 1=Float 2=Bool 3=Vec 4=Rot 5=Xform
    "I":    "Integer64",   # exact int / address / handle
    "F":    "Float",       # double
    "B":    "Boolean",     # == the struct's default member (not added explicitly)
    "V":    "Vector",
    "R":    "Rotator",
    "X":    "Transform",
}
# the six added via AddVariable (B is the default member):
ADD_MEMBERS = [(r, ROLES[r]) for r in ("Type", "I", "F", "V", "R", "X")]


def full(name):
    return "%s/%s.%s" % (OUTPUT_PKG, name, name)
