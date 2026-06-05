"""C1 - author the full cosmetic-mount recipe as compiled Blueprint logic on a
scratch Actor BP, as two custom events:

  Stow    : attach Rider's Mesh -> Mount's 'attachrider' socket; freeze (disable
            movement + actor collision off); pose (SINGLE_NODE + loop mounted-idle).
  Restore : reverse (AnimBP mode; SetMovementMode Walking; collision on;
            re-attach Mesh to Rider's capsule).  [transform fidelity = later polish]

Rider/Mount are object-ref(ConanCharacter) member vars, set from Python (and later
by the polling manager). Component accessors (Mesh/CharacterMovement/CapsuleComponent)
are non-self-context VariableGets — GetMesh()/GetCharacterMovement() are unreflected
C++ inlines, not K2 nodes.

Run: python ue_run.py dev/c1_build.py
"""
import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
import unreal
import bp_bridge as bp
import bp_ir as ir
import bp_compact as bc

PKG, NAME = "/Game/_Scratch", "BP_MF_Recipe"
PATH = PKG + "/" + NAME
FULL = PATH + "." + NAME
ANIM = "/Game/Characters/humans/animations/mounted/Horse/A_human_mounted_idle_HORSE.A_human_mounted_idle_HORSE"
CHAR = "/Script/Engine.Character"
SMC = "/Script/Engine.SkeletalMeshComponent"
SCENE = "/Script/Engine.SceneComponent"
CMC = "/Script/Engine.CharacterMovementComponent"
ACTOR = "/Script/Engine.Actor"

# 1) FRESH scratch BP (delete any stale one so old Stow/Restore UFunctions don't
# collide and force the pasted custom events to be renamed). Needs Play STOPPED.
if unreal.EditorAssetLibrary.does_asset_exist(PATH):
    unreal.EditorAssetLibrary.delete_asset(PATH)
    print("deleted stale", PATH)
bp_obj, _ = bp.scratch_blueprint(pkg=PKG, name=NAME)
print("scratch BP:", FULL)
vt = unreal.BlueprintEditorLibrary.get_object_reference_type(unreal.ConanCharacter.static_class())
for vn in ("Rider", "Mount"):
    unreal.BlueprintEditorLibrary.add_member_variable(bp_obj, vn, vt)
# anim is data-driven (per-species pose later): AnimSequence-ref member var
at = unreal.BlueprintEditorLibrary.get_object_reference_type(unreal.AnimSequence.static_class())
unreal.BlueprintEditorLibrary.add_member_variable(bp_obj, "MountIdleAnim", at)
# Transform var: the rider mesh's original relative-to-capsule offset, saved at Stow
# and restored at Restore (else re-attach snaps it to capsule center -> floats/rotates)
tt = unreal.BlueprintEditorLibrary.get_struct_type(unreal.Transform.static_struct())
unreal.BlueprintEditorLibrary.add_member_variable(bp_obj, "SavedMeshXform", tt)
# instance-editable so Python/the poller can set them on a spawned instance
for vn in ("Rider", "Mount", "MountIdleAnim"):
    unreal.BlueprintEditorLibrary.set_blueprint_variable_instance_editable(bp_obj, vn, True)

# 2) author
g = ir.Graph("EventGraph")

# object-ref pin types (VariableGet pins must be fully typed or their links break
# on reconstruction — see memory bp-typed-pin-defaults)
CONAN = "/Script/ConanSandbox.ConanCharacter"
CLS = {
    "Rider": CONAN, "Mount": CONAN,
    "MountIdleAnim": "/Script/Engine.AnimSequence",
    "Mesh": "/Script/Engine.SkeletalMeshComponent",
    "CharacterMovement": "/Script/Engine.CharacterMovementComponent",
    "CapsuleComponent": "/Script/Engine.CapsuleComponent",
}

STRUCTS = {"SavedMeshXform": "/Script/CoreUObject.Transform"}

def type_obj(pin, cls_path):
    pin.set("PinType.PinCategory", '"object"')
    pin.set("PinType.PinSubCategoryObject", "/Script/CoreUObject.Class'%s'" % cls_path)

def type_struct(pin, struct_path):
    pin.set("PinType.PinCategory", '"struct"')
    pin.set("PinType.PinSubCategoryObject", "/Script/CoreUObject.ScriptStruct'%s'" % struct_path)

def type_var_pin(pin, name):
    if name in STRUCTS:
        type_struct(pin, STRUCTS[name])
    else:
        type_obj(pin, CLS[name])

def var_self(name, pos):
    n = g.node("K2Node_VariableGet",
               ['VariableReference=(MemberName="%s",bSelfContext=True)' % name],
               base="VariableGet", pos=pos)
    p = n.pin(name); p.dir = "EGPD_Output"; type_var_pin(p, name)
    return n

def var_set(name, pos):
    """K2Node_VariableSet of a self member var. Value input pin == var name."""
    n = g.node("K2Node_VariableSet",
               ['VariableReference=(MemberName="%s",bSelfContext=True)' % name],
               base="VariableSet", pos=pos)
    p = n.pin(name); p.dir = "EGPD_Input"; type_var_pin(p, name)
    return n

def comp_of(target, target_pin, comp_var, pos, parent=CHAR):
    """Read component var (Mesh/CharacterMovement/CapsuleComponent) off `target`.
    Both the target ('self') pin and the output pin are fully typed so links hold."""
    n = g.node("K2Node_VariableGet",
               ['VariableReference=(MemberName="%s",MemberParent="/Script/CoreUObject.Class\'%s\'",bSelfContext=False)'
                % (comp_var, parent)], base="VariableGet", pos=pos)
    sp = n.pin("self"); sp.dir = "EGPD_Input"; type_obj(sp, parent)
    op = n.pin(comp_var); op.dir = "EGPD_Output"; type_obj(op, CLS[comp_var])
    g.wire(target, target_pin, n, "self", exec=False)
    return n

# enum object paths for typed defaults (see memory bp-typed-pin-defaults)
ENUM = {
    "EAttachmentRule": "/Script/CoreUObject.Enum'/Script/Engine.EAttachmentRule'",
    "EAnimationMode":  "/Script/CoreUObject.Enum'/Script/Engine.EAnimationMode'",
    "EMovementMode":   "/Script/CoreUObject.Enum'/Script/Engine.EMovementMode'",
}

def set_default(node, pin, value, category, enum=None):
    """Set an input default WITH a matching PinType so it merges into the canonical
    pin instead of orphaning. category: byte/name/bool/etc; enum: key in ENUM."""
    p = node.pin(pin); p.dir = "EGPD_Input"
    p.set("PinType.PinCategory", '"%s"' % category)
    if enum:
        p.set("PinType.PinSubCategoryObject", ENUM[enum])
    p.set("DefaultValue", '"%s"' % value)

def set_obj_default(node, pin, cls_path, asset_path):
    p = node.pin(pin); p.dir = "EGPD_Input"
    p.set("PinType.PinCategory", '"object"')
    p.set("PinType.PinSubCategoryObject", "/Script/CoreUObject.Class'%s'" % cls_path)
    p.set("DefaultObject", asset_path)

def bare_call(member, parent, pos):
    """A call node with NO input defaults (defaults set via set_default after)."""
    return g.call(member, parent, pos=pos)

class Chain(object):
    """Sequential exec-wiring helper."""
    def __init__(self, start_node, start_pin):
        self.node, self.pin = start_node, start_pin
    def then(self, call_node, in_pin="execute", out_pin="then"):
        g.wire(self.node, self.pin, call_node, in_pin, exec=True)
        self.node, self.pin = call_node, out_pin
        return call_node

def attach_node(pos, socket, rules="SnapToTarget"):
    """K2_AttachToComponent with canonical pins: self, Parent, SocketName,
    Location/Rotation/ScaleRule (byte/EAttachmentRule), bWeldSimulatedBodies."""
    n = bare_call("K2_AttachToComponent", SCENE, pos)
    set_default(n, "SocketName", socket, "name")
    for r in ("LocationRule", "RotationRule", "ScaleRule"):
        set_default(n, r, rules, "byte", enum="EAttachmentRule")
    set_default(n, "bWeldSimulatedBodies", "false", "bool")
    return n

def build_stow():
    ev = g.custom_event("Stow", pos=(0, 0))
    rider = var_self("Rider", (-300, 250))
    mount = var_self("Mount", (-300, 450))
    rMesh = comp_of(rider, "Rider", "Mesh", (0, 250))
    mMesh = comp_of(mount, "Mount", "Mesh", (0, 450))
    rMove = comp_of(rider, "Rider", "CharacterMovement", (0, 650))

    chain = Chain(ev, "then")

    # save the rider mesh's original relative-to-capsule transform BEFORE reparenting
    getX = bare_call("GetRelativeTransform", SCENE, pos=(150, 800))
    gxp = getX.pin("ReturnValue"); gxp.dir = "EGPD_Output"; type_struct(gxp, "/Script/CoreUObject.Transform")
    g.wire(rMesh, "Mesh", getX, "self", exec=False)
    saveX = var_set("SavedMeshXform", pos=(150, 1000))
    g.wire(getX, "ReturnValue", saveX, "SavedMeshXform", exec=False)
    chain.then(saveX)

    attach = attach_node((300, 0), "attachrider")
    g.wire(rMesh, "Mesh", attach, "self", exec=False)
    g.wire(mMesh, "Mesh", attach, "Parent", exec=False)   # canonical name is 'Parent'
    chain.then(attach)

    disable = bare_call("DisableMovement", CMC, (600, 0))
    g.wire(rMove, "CharacterMovement", disable, "self", exec=False)
    chain.then(disable)

    nocol = bare_call("SetActorEnableCollision", ACTOR, (900, 0))
    set_default(nocol, "bNewActorEnableCollision", "false", "bool")
    g.wire(rider, "Rider", nocol, "self", exec=False)
    chain.then(nocol)

    mode = bare_call("SetAnimationMode", SMC, (1200, 0))
    set_default(mode, "InAnimationMode", "AnimationSingleNode", "byte", enum="EAnimationMode")
    g.wire(rMesh, "Mesh", mode, "self", exec=False)
    chain.then(mode)

    play = bare_call("PlayAnimation", SMC, (1500, 0))
    set_default(play, "bLooping", "true", "bool")
    animGet = var_self("MountIdleAnim", (1200, 300))
    g.wire(animGet, "MountIdleAnim", play, "NewAnimToPlay", exec=False)
    g.wire(rMesh, "Mesh", play, "self", exec=False)
    chain.then(play)

def build_restore():
    ev = g.custom_event("Restore", pos=(0, 1000))
    rider = var_self("Rider", (-300, 1250))
    rMesh = comp_of(rider, "Rider", "Mesh", (0, 1250))
    rMove = comp_of(rider, "Rider", "CharacterMovement", (0, 1450))
    rCap = comp_of(rider, "Rider", "CapsuleComponent", (0, 1650))

    chain = Chain(ev, "then")

    mode = bare_call("SetAnimationMode", SMC, (300, 1000))
    set_default(mode, "InAnimationMode", "AnimationBlueprint", "byte", enum="EAnimationMode")
    g.wire(rMesh, "Mesh", mode, "self", exec=False)
    chain.then(mode)

    walk = bare_call("SetMovementMode", CMC, (600, 1000))
    set_default(walk, "NewMovementMode", "MOVE_Walking", "byte", enum="EMovementMode")
    g.wire(rMove, "CharacterMovement", walk, "self", exec=False)
    chain.then(walk)

    col = bare_call("SetActorEnableCollision", ACTOR, (900, 1000))
    set_default(col, "bNewActorEnableCollision", "true", "bool")
    g.wire(rider, "Rider", col, "self", exec=False)
    chain.then(col)

    reattach = attach_node((1200, 1000), "")   # re-parent mesh to own capsule
    g.wire(rMesh, "Mesh", reattach, "self", exec=False)
    g.wire(rCap, "CapsuleComponent", reattach, "Parent", exec=False)
    chain.then(reattach)

    # restore the saved relative-to-capsule transform (fixes float/rotate on dismount)
    setX = bare_call("K2_SetRelativeTransform", SCENE, pos=(1500, 1000))
    g.wire(rMesh, "Mesh", setX, "self", exec=False)
    savedX = var_self("SavedMeshXform", pos=(1200, 1300))
    g.wire(savedX, "SavedMeshXform", setX, "NewTransform", exec=False)
    chain.then(setX)

build_stow()
build_restore()
text = g.render()

# 3) clear + inject + compile
bp_ptr, graph_ptr = bp.find_graph(FULL, "EventGraph")
print("cleared %d existing nodes" % bp.clear_graph(bp_ptr, graph_ptr))
res = bp.inject(FULL, text, graph_name="EventGraph")
print("inject ->", res)

# bake a default MountIdleAnim on the CDO (poller overrides per-species later)
gc = unreal.load_object(None, FULL + "_C")
anim_obj = unreal.load_object(None, ANIM)
if gc and anim_obj:
    try:
        unreal.get_default_object(gc).set_editor_property("MountIdleAnim", anim_obj)
        unreal.EditorAssetLibrary.save_asset(PATH)
        print("CDO MountIdleAnim default set:", anim_obj.get_name())
    except Exception as e:
        print("CDO set err:", e)

# 4) readback + ORPHAN CHECK (zero orphans => all defaults/wires merged)
bp_ptr, graph_ptr = bp.find_graph(FULL, "EventGraph")
txt = bp.export_nodes(bp.graph_nodes(graph_ptr))
import re
orphans = re.findall(r'PinName="([^"]+)"[^)]*?bOrphanedPin=True', txt)
print("\nORPHANED PINS:", len(orphans), orphans if orphans else "(none - clean)")
# show the merged defaults that matter
print("\n-- canonical defaults after merge --")
for pin in ("SocketName", "LocationRule", "InAnimationMode", "bLooping",
            "NewMovementMode", "bNewActorEnableCollision"):
    vals = re.findall(r'PinName="%s"[^)]*?DefaultValue="([^"]*)"' % pin, txt)
    # filter to canonical (non-orphan) occurrences
    print("   %-26s %s" % (pin, vals))
