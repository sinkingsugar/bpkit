"""forthvm ISA -- the single source of truth shared by the offline compiler, the
Python reference VM, and (later) the bpkit Blueprint generator.

A program is a flat int[] `code` stream (opcodes + inline int operands) plus typed
literal POOLS (float/vec/xform), because an int[] can't hold a float or vector
inline. Typed-literal opcodes carry an int index into the matching pool. The data
stack is TArray<FCell>; a cell is (tag, value) where tag is one of CT_*.
"""

# --- cell type tags (the FCell.Type int) -----------------------------------
CT_INT, CT_FLOAT, CT_BOOL, CT_VEC, CT_ROT, CT_XFORM = range(6)
CT_NAME = {CT_INT: "int", CT_FLOAT: "float", CT_BOOL: "bool",
           CT_VEC: "vec", CT_ROT: "rot", CT_XFORM: "xform"}

# --- opcodes ----------------------------------------------------------------
HALT     = 0
LIT_INT  = 1    # + inline int            -> push int
LIT_FLOAT= 2    # + inline pool index     -> push floatPool[i]
LIT_VEC  = 3    # + inline pool index     -> push vecPool[i]
LIT_BOOL = 4    # + inline 0/1            -> push bool
DUP      = 5
DROP     = 6
SWAP     = 7
ADD      = 8    # polymorphic (+)
SUB      = 9    # polymorphic (-)
MUL      = 10   # polymorphic (*)  incl. scalar*vec, vec*vec (component-wise)
MK_VEC   = 11   # ( x y z -- vec )   numbers -> vector
VEC_XYZ  = 12   # ( vec -- x y z )
PRINT    = 13   # ( a -- )  type-aware print
CALL     = 14   # + inline code addr  -> push IP to return stack, jump
EXIT     = 15   # pop return stack -> IP  (end of a colon def)
BRANCH   = 16   # + inline code addr  -> IP = addr
ZBRANCH  = 17   # ( flag -- ) + inline addr -> if !flag IP = addr

OPNAME = {v: k for k, v in globals().items()
          if k.isupper() and isinstance(v, int) and k not in ("CT_INT", "CT_FLOAT",
          "CT_BOOL", "CT_VEC", "CT_ROT", "CT_XFORM", "CT_NAME")}

# opcodes that carry one inline int operand in the code stream
HAS_OPERAND = {LIT_INT, LIT_FLOAT, LIT_VEC, LIT_BOOL, CALL, BRANCH, ZBRANCH}

# --- primitive words: source token -> opcode (no operand) -------------------
PRIMITIVES = {
    "dup": DUP, "drop": DROP, "swap": SWAP,
    "+": ADD, "-": SUB, "*": MUL,
    "vec3": MK_VEC, "xyz": VEC_XYZ,
    ".": PRINT,
}
