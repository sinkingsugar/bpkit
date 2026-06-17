"""mf_nodes - mounted-followers shared node helpers (Conan/gameplay-specific).

Built on the bpkit.ir primitives. These are the Conan-flavoured builders the mod's
graphs reuse (the engine-generic ones -- cast/get_all_actors/array_*/var_*/chain --
now live on ir.Graph). Each function takes the live graph `g` as its first arg.

    import mf_nodes as mf
    n = mf.comp_of(g, target, "AsConan Character", "Mesh", pos)
    a = mf.attach_actor(g, pos, "attachrider")
"""
from bpkit import ir

# --- class paths --------------------------------------------------------------
CONAN  = "/Script/ConanSandbox.ConanCharacter"
CHAR   = "/Script/Engine.Character"
SMC    = "/Script/Engine.SkeletalMeshComponent"
SCENE  = "/Script/Engine.SceneComponent"
CMC    = "/Script/Engine.CharacterMovementComponent"
ACTOR  = "/Script/Engine.Actor"
CAPSULE = "/Script/Engine.CapsuleComponent"
ANIMSEQ = "/Script/Engine.AnimSequence"
USERWIDGET = "/Script/UMG.UserWidget"
KSL    = "/Script/Engine.KismetSystemLibrary"
KTL    = "/Script/Engine.KismetTextLibrary"

# component-var -> declared component class (for comp_of's typed output pin)
CLS = {"Mesh": SMC, "CharacterMovement": CMC, "CapsuleComponent": CAPSULE,
       "PlayerMount": CONAN, "MountIdleAnim": ANIMSEQ, "OverlayWidget": USERWIDGET}
STRUCTS = {}
ENUM = {
    "EAttachmentRule": ir.enum_path("/Script/Engine.EAttachmentRule"),
    "EAnimationMode":  ir.enum_path("/Script/Engine.EAnimationMode"),
    "EMovementMode":   ir.enum_path("/Script/Engine.EMovementMode"),
    "EDetachmentRule": ir.enum_path("/Script/Engine.EDetachmentRule"),
}


# --- pin typing (Conan var maps) ---------------------------------------------
def type_obj(pin, cls_path):
    pin.typed("object", ir.obj_path(cls_path))

def type_struct(pin, struct_path):
    pin.typed("struct", ir.struct_path(struct_path))

def type_var_pin(pin, name):
    type_struct(pin, STRUCTS[name]) if name in STRUCTS else type_obj(pin, CLS[name])

def set_default(node, pin, value, category, enum=None):
    """Typed input default; enum -> the EAttachmentRule/etc. PinSubCategoryObject."""
    p = node.pin(pin); p.dir = "EGPD_Input"
    p.set("PinType.PinCategory", '"%s"' % category)
    if enum:
        p.set("PinType.PinSubCategoryObject", ENUM[enum])
    p.set("DefaultValue", '"%s"' % value)


# --- variable get/set typed off the Conan CLS map ----------------------------
def var_self(g, name, pos):
    n = g.node("K2Node_VariableGet", ['VariableReference=(MemberName="%s",bSelfContext=True)' % name],
               base="VariableGet", pos=pos)
    p = n.pin(name); p.dir = "EGPD_Output"; type_var_pin(p, name)
    return n

def var_set_m(g, name, pos):
    n = g.node("K2Node_VariableSet", ['VariableReference=(MemberName="%s",bSelfContext=True)' % name],
               base="VariableSet", pos=pos)
    p = n.pin(name); p.dir = "EGPD_Input"; type_var_pin(p, name)
    return n

def comp_of(g, target, target_pin, comp_var, pos, parent=CHAR):
    """Read a component (Mesh/CharacterMovement/Capsule) off `target`'s output pin."""
    n = g.node("K2Node_VariableGet",
               ['VariableReference=(MemberName="%s",MemberParent="%s",bSelfContext=False)'
                % (comp_var, ir.obj_path(parent))], base="VariableGet", pos=pos)
    sp = n.pin("self"); sp.dir = "EGPD_Input"; type_obj(sp, parent)
    op = n.pin(comp_var); op.dir = "EGPD_Output"; type_obj(op, CLS[comp_var])
    g.wire(target, target_pin, n, "self", exec=False)
    return n


# --- attach / detach (Actor + component) -------------------------------------
def attach_component(g, pos, socket, rules="SnapToTarget"):
    """SceneComponent::K2_AttachToComponent -- component/mesh attach (does NOT
    replicate; cosmetic-only). Use attach_actor for the replicated rider attach."""
    n = g.call("K2_AttachToComponent", SCENE, pos=pos)
    set_default(n, "SocketName", socket, "name")
    for r in ("LocationRule", "RotationRule", "ScaleRule"):
        set_default(n, r, rules, "byte", enum="EAttachmentRule")
    set_default(n, "bWeldSimulatedBodies", "false", "bool")
    return n

def attach_actor(g, pos, socket, rules="SnapToTarget"):
    """AActor::K2_AttachToComponent -- attaches the ACTOR (root) to a parent
    component. Actor attachment REPLICATES (unlike component attach), so clients
    see the rider."""
    n = g.call("K2_AttachToComponent", ACTOR, pos=pos)
    set_default(n, "SocketName", socket, "name")
    for r in ("LocationRule", "RotationRule", "ScaleRule"):
        set_default(n, r, rules, "byte", enum="EAttachmentRule")
    set_default(n, "bWeldSimulatedBodies", "false", "bool")
    return n

def detach_actor(g, pos, rules="KeepWorld"):
    """AActor::K2_DetachFromActor -- the BP-callable detach (matches
    K2_AttachToComponent). Plain 'DetachFromActor' is the C++ name and silently
    does nothing here -- cost the dismount bug."""
    n = g.call("K2_DetachFromActor", ACTOR, pos=pos)
    for r in ("LocationRule", "RotationRule", "ScaleRule"):
        set_default(n, r, rules, "byte", enum="EDetachmentRule")
    return n


# --- HUD / diagnostics --------------------------------------------------------
def dbg(g, msg, pos, version=None):
    """PrintString beacon (PIE-only; compiled out of Shipping). version stamps
    'MF v<N>: ' onto the message. Wire exec via execute/then. Call only under DEBUG."""
    p = g.call("PrintString", KSL, pos=pos)
    text = ("MF v%d: %s" % (version, msg)) if version is not None else msg
    g.typed_input(p, "InString", text, "string")
    return p

def txt_lit(g, s, pos):
    c = g.call("Conv_StringToText", KTL, pos=pos)
    g.typed_input(c, "InString", s, "string")
    return c

def fifo(g, txt_node, pos):
    """SHIP-VISIBLE banner: ConanCharacter.HUDShowFIFO(FText) -> the local client's
    scrolling event feed; survives Shipping. WorldContextObject is AUTO-MANAGED
    (manual links to it are DROPPED on paste). Call only under HUD_DIAG."""
    f = g.call("HUDShowFIFO", CONAN, pos=pos)
    g.wire(txt_node, "ReturnValue", f, "Text", exec=False)
    return f
