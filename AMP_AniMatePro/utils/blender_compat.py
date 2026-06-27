import bpy
from dataclasses import dataclass
from typing import Any

try:
    from bpy_extras import anim_utils
except ImportError:
    anim_utils = None

BLENDER_VERSION = bpy.app.version

def has_layered_actions():
    return BLENDER_VERSION >= (4, 3, 0)

@dataclass
class GreasePencilFrameRef:
    object: Any
    layer: Any
    frame: Any
    frame_number: int
    selected: bool = False

def has_grease_pencil_v3():
    return BLENDER_VERSION >= (4, 3, 0)

def is_action_layered(action):
    return getattr(action, "is_action_layered", False)

def is_grease_pencil_object(obj):
    if not obj:
        return False
    if has_grease_pencil_v3():
        return obj.type == "GREASEPENCIL"
    return obj.type == "GPENCIL"

def get_action_slot(animated_id):
    if not animated_id or not getattr(animated_id, "animation_data", None):
        return None
    return getattr(animated_id.animation_data, "action_slot", None)

def get_channelbag(action, slot=None, *, ensure=False):
    """Get the channelbag for a slot, handling both layered and legacy actions."""
    if not action:
        return None
        
    if is_action_layered(action):
        if not slot:
            return None
            
        if ensure:
            if anim_utils and hasattr(anim_utils, "action_ensure_channelbag_for_slot"):
                return anim_utils.action_ensure_channelbag_for_slot(action, slot)
            else:
                if not action.layers:
                    action.layers.new("Layer")
                layer = action.layers[0]
                if not layer.strips:
                    layer.strips.new()
                strip = layer.strips[0]
                bag = strip.channelbags.get(slot.name)
                if not bag:
                    bag = strip.channelbags.new(slot.name)
                return bag
        else:
            if anim_utils and hasattr(anim_utils, "action_get_channelbag_for_slot"):
                return anim_utils.action_get_channelbag_for_slot(action, slot)
            else:
                if not action.layers:
                    return None
                layer = action.layers[0]
                if not layer.strips:
                    return None
                return layer.strips[0].channelbags.get(slot.name) if slot else None
    else:
        # Legacy action
        return action

def iter_action_fcurves(action, *, slot=None, include_all_slots=False):
    if not action:
        return
        
    if is_action_layered(action):
        if include_all_slots:
            for layer in action.layers:
                for strip in layer.strips:
                    for bag in strip.channelbags.values():
                        if hasattr(bag, "fcurves"):
                            yield from bag.fcurves
        else:
            bag = get_channelbag(action, slot, ensure=False)
            if bag and hasattr(bag, "fcurves"):
                yield from bag.fcurves
    else:
        if hasattr(action, "fcurves"):
            yield from action.fcurves

def iter_action_groups(action, *, slot=None, include_all_slots=False):
    if not action:
        return
        
    if is_action_layered(action):
        if include_all_slots:
            for layer in action.layers:
                for strip in layer.strips:
                    for bag in strip.channelbags.values():
                        if hasattr(bag, "groups"):
                            yield from bag.groups
        else:
            bag = get_channelbag(action, slot, ensure=False)
            if bag and hasattr(bag, "groups"):
                yield from bag.groups
    else:
        if hasattr(action, "groups"):
            yield from action.groups

def ensure_fcurve(action_or_animated_id, data_path, index=0, group_name=None, slot=None):
    """For new helper curves and clones."""
    if hasattr(action_or_animated_id, "animation_data"): # animated_id
        action = action_or_animated_id.animation_data.action
        slot = get_action_slot(action_or_animated_id)
    else:
        action = action_or_animated_id

    if not action:
        return None

    if is_action_layered(action):
        if not slot:
            if not action.slots:
                id_type = getattr(action_or_animated_id, "bl_rna", None)
                id_type_name = id_type.name.upper() if id_type else "OBJECT"
                if id_type_name not in ['ACTION', 'ARMATURE', 'BRUSH', 'CACHEFILE', 'CAMERA', 'COLLECTION', 'CURVE', 'CURVES', 'FONT', 'GREASEPENCIL', 'GREASEPENCIL_V3', 'IMAGE', 'KEY', 'LATTICE', 'LIBRARY', 'LIGHT', 'LIGHT_PROBE', 'LINESTYLE', 'MASK', 'MATERIAL', 'MESH', 'META', 'MOVIECLIP', 'NODETREE', 'OBJECT', 'PAINTCURVE', 'PALETTE', 'PARTICLE', 'POINTCLOUD', 'SCENE', 'SCREEN', 'SOUND', 'SPEAKER', 'TEXT', 'TEXTURE', 'VOLUME', 'WINDOWMANAGER', 'WORKSPACE', 'WORLD']:
                    id_type_name = "OBJECT"
                slot = action.slots.new(id_type_name, name="Slot")
                if hasattr(action_or_animated_id, "animation_data") and action_or_animated_id.animation_data:
                    action_or_animated_id.animation_data.action_slot = slot
            else:
                slot = action.slots[0]
            
        bag = get_channelbag(action, slot, ensure=True)
        if not bag:
            return None
            
        fcu = bag.fcurves.find(data_path=data_path, index=index)
        if not fcu:
            if group_name:
                fcu = bag.fcurves.new(data_path=data_path, index=index, group_name=group_name)
            else:
                fcu = bag.fcurves.new(data_path=data_path, index=index)
        elif group_name and not fcu.group:
            group = bag.groups.get(group_name)
            if not group:
                group = bag.groups.new(group_name)
            fcu.group = group
        return fcu
    else:
        if hasattr(action, "fcurves"):
            fcu = action.fcurves.find(data_path=data_path, index=index)
            if not fcu:
                if group_name:
                    fcu = action.fcurves.new(data_path=data_path, index=index, action_group=group_name)
                else:
                    fcu = action.fcurves.new(data_path=data_path, index=index)
            elif group_name and not fcu.group:
                group = action.groups.get(group_name)
                if not group:
                    group = action.groups.new(group_name)
                fcu.group = group
            return fcu
    return None

def remove_fcurve(action, fcurve):
    """Remove fcurve from current channelbag or legacy action."""
    if not action or not fcurve:
        return
        
    if is_action_layered(action):
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags.values():
                    for fcu in bag.fcurves:
                        if fcu == fcurve:
                            bag.fcurves.remove(fcurve)
                            return
    else:
        if hasattr(action, "fcurves"):
            action.fcurves.remove(fcurve)

def iter_grease_pencil_layers(obj):
    if not is_grease_pencil_object(obj):
        return
    if has_grease_pencil_v3():
        if hasattr(obj.data, "layers"):
            yield from obj.data.layers
    else:
        if hasattr(obj.data, "layers"):
            yield from obj.data.layers

def iter_grease_pencil_frames(obj_or_scene):
    if hasattr(obj_or_scene, "objects"):
        objects = obj_or_scene.objects
    else:
        objects = [obj_or_scene]
        
    for obj in objects:
        for layer in iter_grease_pencil_layers(obj):
            for frame in layer.frames:
                yield GreasePencilFrameRef(
                    object=obj,
                    layer=layer,
                    frame=frame,
                    frame_number=getattr(frame, "frame_number", getattr(frame, "frame", 0)),
                    selected=getattr(frame, "select", False)
                )

def get_grease_pencil_frame(layer, frame_number):
    if hasattr(layer, "get_frame_at"):
        return layer.get_frame_at(frame_number)
    else:
        for frame in layer.frames:
            if getattr(frame, "frame_number", getattr(frame, "frame", 0)) == frame_number:
                return frame
    return None

def copy_grease_pencil_frame(layer, source_frame_number, target_frame_number):
    if hasattr(layer.frames, "copy"):
        layer.frames.copy(source_frame_number, target_frame_number)
    else:
        pass

def move_grease_pencil_frame(layer, old_frame_number, new_frame_number):
    if hasattr(layer.frames, "move"):
        layer.frames.move(old_frame_number, new_frame_number)
    else:
        pass

