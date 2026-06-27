# licence
"""
Copyright (C) 2018 Ares Deveaux


Created by Ares Deveaux

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from __future__ import annotations
import bpy
import math
from .. import utils
from . import blender_compat

def is_grease_pencil_object(obj) -> bool:
    return blender_compat.is_grease_pencil_object(obj)



group_name = "amp_action"
user_preview_range = {}
user_scene_range = {}


def add_curve3d(context, name, key_amount=0):
    curve_data = bpy.data.curves.new(name, "CURVE")
    spline = curve_data.splines.new("BEZIER")
    if key_amount > 0:
        spline.bezier_points.add(key_amount)
    obj = bpy.data.objects.new(name, curve_data)
    context.collection.objects.link(obj)
    return obj


def new(action_group_name, keys_to_add, key_interp="AUTO_CLAMPED", color=(1, 1, 1)):
    """Adds an F-Curve in the 'amp_anim' action with specified control points"""
    action = utils.set_amp_timeline_tools_action()

    # Create a new F-Curve
    blends_curve = blender_compat.ensure_fcurve(action, data_path="Magnet", index=0, group_name=action_group_name)
    blends_curve.color_mode = "CUSTOM"
    blends_curve.color = color

    # Add keyframe points
    keys = blends_curve.keyframe_points
    keys.add(keys_to_add)

    # Manually set the position for each keyframe point
    # Example positions, adjust as needed for your mask
    if keys_to_add >= 4:
        keys[0].co = (0, 0)
        keys[1].co = (10, 0)
        keys[2].co = (20, 1)
        keys[3].co = (30, 1)

    for k in keys:
        k.handle_left_type = key_interp
        k.handle_right_type = key_interp

    blends_curve.lock = True
    blends_curve.select = True
    blends_curve.update()

    return blends_curve


def create_path(context, fcurves):
    curve_obj = add_curve3d(context, "amp_timeline_tools_path")
    curve_obj.data.dimensions = "3D"
    curve_obj.data.bevel_depth = 0.1

    x = {}
    y = {}
    z = {}
    frames = []
    for fcurve in fcurves:
        if fcurve.data_path == "location":
            for k in fcurve.keyframe_points:
                f = k.co.x
                if f not in frames:
                    frames.append(f)
                if fcurve.array_index == 0:
                    x["curve"] = fcurve
                    x[f] = k.co.y
                elif fcurve.array_index == 1:
                    y["curve"] = fcurve
                    y[f] = k.co.y
                elif fcurve.array_index == 2:
                    z["curve"] = fcurve
                    z[f] = k.co.y
    frames.sort()
    utils.dprint(f"frames: {frames}")
    utils.dprint(f"x: {x}")
    utils.dprint(f"y: {y}")
    utils.dprint(f"z: {z}")
    points = curve_obj.data.splines[0].bezier_points
    points.add(len(frames))
    utils.dprint(f"amount of frames: {len(frames)}")
    n = 0
    for f in frames:
        if x.get(f) is None:
            points[n].co.x = x["curve"].evaluate(f)
        else:
            points[n].co.x = x.get(f)

        if y.get(f) is None:
            points[n].co.y = y["curve"].evaluate(f)
        else:
            points[n].co.y = y.get(f)

        if x.get(f) is None:
            points[n].co.z = z["curve"].evaluate(f)
        else:
            points[n].co.z = z.get(f)

        points[n].handle_left_type = "AUTO"
        points[n].handle_right_type = "AUTO"

        utils.dprint(f"frame: {f}")
        utils.dprint(f"point coordinate: {points[n].co}")
        utils.dprint(f"n: {n}")

        n += 1


def get_selected(fcurves):
    """return selected fcurves in the current action with the exception of the reference fcurves"""

    selected = []

    for fcurve in fcurves:
        if getattr(fcurve.group, "name", None) == group_name:
            continue  # we don't want to add to the list the helper curves we have created

        if fcurve.select:
            selected.append(fcurve)

    return selected


def get_all_fcurves(obj):
    trans_action = obj.animation_data.action
    trans_fcurves = getattr(trans_action, "fcurves", None)
    if trans_fcurves:
        trans_fcurves = trans_fcurves.items()
    else:
        trans_fcurves = []

    if obj.type != "ARMATURE":
        shapes_action = obj.data.shape_keys.animation_data.action
        shapes_fcurves = getattr(shapes_action, "fcurves", None)
        if shapes_fcurves:
            shapes_fcurves = shapes_fcurves.items()
        else:
            shapes_fcurves = []
        return trans_fcurves + shapes_fcurves
    else:
        return trans_fcurves


def remove_helpers(objects):
    """Remove the all the helper curves that have been added to an object action"""

    for obj in objects:
        action = obj.animation_data.action

        for fcurve in all_fcurves(action):
            if getattr(fcurve.group, "name", None) == group_name:
                remove_fcurve_from_action(action, fcurve)


def get_slope(fcurve):
    """Gets the slope of a curve at a specific range"""
    selected_keys = utils.key.get_selected_index(fcurve)
    first_key, last_key = utils.key.first_and_last_selected(fcurve, selected_keys)
    slope = (first_key.co.y**2 - last_key.co.y**2) / (first_key.co.x**2 - last_key.co.x**2)
    return slope


def add_cycle(fcurve, before="MIRROR", after="MIRROR"):
    """Adds cycle modifier to an fcurve"""
    cycle = fcurve.modifiers.new("CYCLES")

    cycle.mode_before = before
    cycle.mode_after = after


def duplicate(fcurve, selected_keys=True, before="NONE", after="NONE", lock=False):
    """Duploicates an fcurve"""

    action = fcurve.id_data
    index = len(all_fcurves(action))

    if selected_keys:
        selected_keys = get_selected(fcurve)
    else:
        selected_keys = fcurve.keyframe_points.items()

    clone_name = "%s.%d.clone" % (fcurve.data_path, fcurve.array_index)

    dup = blender_compat.ensure_fcurve(action, data_path=clone_name, index=index, group_name=group_name)
    dup.keyframe_points.add(len(selected_keys))
    dup.color_mode = "CUSTOM"
    dup.color = (0, 0, 0)

    dup.lock = lock
    dup.select = False

    groups = get_active_groups(action)
    groups[group_name].lock = lock
    groups[group_name].color_set = "THEME10"

    for i, (index, key) in enumerate(selected_keys):
        dup.keyframe_points[i].co = key.co

    add_cycle(dup, before=before, after=after)

    dup.update()

    return dup


def duplicate_from_data(fcurves, global_fcurve, new_data_path, before="NONE", after="NONE", lock=False):
    """Duplicates a curve using the global values"""

    index = len(fcurves) if hasattr(fcurves, "__len__") else 0
    every_key = global_fcurve["every_key"]
    original_keys = global_fcurve["original_keys"]

    action = getattr(fcurves, "id_data", None)
    dup = blender_compat.ensure_fcurve(action, data_path=new_data_path, index=index, group_name=group_name)
    dup.keyframe_points.add(len(every_key))
    dup.color_mode = "CUSTOM"
    dup.color = (0, 0, 0)

    dup.lock = lock
    dup.select = False

    groups = get_active_groups(action)
    groups[group_name].lock = lock
    groups[group_name].color_set = "THEME10"

    i = 0

    for index in every_key:
        dup.keyframe_points[i].co.x = original_keys[index]["x"]
        dup.keyframe_points[i].co.y = original_keys[index]["y"]

        i += 1

    add_cycle(dup, before=before, after=after)

    dup.update()

    return dup


def add_clone(objects, cycle_before="NONE", cycle_after="NONE", selected_keys=False):
    """Create an fcurve clone"""

    for obj in objects:
        fcurves = all_fcurves(obj.animation_data.action)

        for fcurve in fcurves:
            if getattr(fcurve.group, "name", None) == group_name:
                continue  # we don't want to add to the list the helper curves we have created

            if fcurve.hide or not fcurve.select:
                continue

            duplicate(
                fcurve,
                selected_keys=selected_keys,
                before=cycle_before,
                after=cycle_after,
            )

            fcurve.update()


def remove_clone(objects):
    """Removes an fcurve clone"""

    for obj in objects:
        action = obj.animation_data.action
        fcurves = all_fcurves(action)

        amp = bpy.context.scene.amp_timeline_tools
        aclones = amp.clone_data.clones
        clones_n = len(aclones)
        blender_n = len(fcurves) - clones_n

        for n in range(clones_n):
            maybe_clone = fcurves[blender_n]
            if "clone" in maybe_clone.data_path:
                clone = maybe_clone
                remove_fcurve_from_action(action, clone)
                aclones.remove(0)


def move_clone(objects):
    """Moves clone fcurve in time"""

    for obj in objects:
        action = obj.animation_data.action

        amp = bpy.context.scene.amp_timeline_tools
        aclone_data = amp.clone_data
        aclones = aclone_data.clones
        move_factor = aclone_data.move_factor
        fcurves = all_fcurves(action)
        for aclone in aclones:
            clone = fcurves[aclone.fcurve.index]
            fcurve = fcurves[aclone.original_fcurve.index]
            selected_keys = key.get_selected_index(fcurve)
            key1, key2 = key.first_and_last_selected(fcurve, selected_keys)
            amount = abs(key2.co.x - key1.co.x)
            for key in clone.keyframe_points:
                key.co.x = key.co.x + (amount * move_factor)

            clone.update()

            key.attach_selection_to_fcurve(fcurve, clone, is_gradual=False)

            fcurve.update()


def valid_anim(obj):

    anim = obj.animation_data
    action = getattr(anim, "action", None)
    fcurves = getattr(action, "fcurves", None)

    return fcurves


def valid_obj(context, obj, check_ui=True):

    if not valid_anim(obj):
        return False

    if check_ui:
        visible = obj.visible_get()

        if context.area.type != "VIEW_3D":
            if not context.space_data.dopesheet.show_hidden and not visible:
                return False

    return True


def valid_fcurve(context, obj, fcurve, action_type="transfrom_action", check_ui=True):

    if not fcurve:
        return False

    try:
        if action_type == "transfrom_action":
            prop = obj.path_resolve(fcurve.data_path)
        else:
            prop = fcurve.data_path
    except:
        prop = None

    if not prop:
        return False

    if check_ui and context.area.type == "GRAPH_EDITOR":
        if context.space_data.use_only_selected_keyframe_handles and not fcurve.select:
            return False

        # if context.area.type != 'VIEW_3D':
        if fcurve.lock or fcurve.hide:
            return False

    if getattr(fcurve.group, "name", None) == utils.curve.group_name:
        return False  # we don't want to select keys on reference fcurves

    if obj.type == "ARMATURE":

        if getattr(fcurve.group, "name", None) == "Object Transforms":
            # When animating an object, by default its fcurves grouped with this name.
            return False

        elif not fcurve.group:
            transforms = (
                "location",
                "rotation_euler",
                "scale",
                "rotation_quaternion",
                "rotation_axis_angle",
                '["',  # custom property
            )
            if fcurve.data_path.startswith(transforms):
                # fcurve belongs to the  object, so skip it
                return False

        # if fcurve.group.name not in bones_names:
        # return

        split_data_path = fcurve.data_path.split(sep='"')
        if len(split_data_path) > 1:
            bone_name = split_data_path[1]
            bone = obj.pose.bones.get(bone_name)
        else:
            bone = None

        if not bone:
            return False

        if check_ui:
            if bone.hide:
                return False

            if context.area.type == "VIEW_3D":
                if not bone.select:
                    return False
            else:
                only_selected = context.space_data.dopesheet.show_only_selected
                if only_selected and not bone.select:
                    return False

    # if getattr(fcurve.group, 'name', None) == curve.group_name:
    #     return False  # we don't want to select keys on reference fcurves

    return True


def get_selected_keyframes_range_offset(context):
    """
    Returns the range of selected keyframes as (min_frame, max_frame) or None if no keyframes are selected.
    This function targets the Graph Editor context to ensure accuracy in detecting selected keyframes
    for both Object and Pose Mode.
    """
    obj = context.active_object
    if not obj or not obj.animation_data or not obj.animation_data.action:
        return None

    action = obj.animation_data.action
    min_frame, max_frame = float("inf"), -float("inf")
    has_selected_keyframes = False

    if context.mode == "POSE" and obj.type == "ARMATURE":
        # Collect names of selected bones for comparison
        selected_bones_names = {bone.name for bone in context.selected_pose_bones}
        for fcurve in context.visible_fcurves:
            bone_name = fcurve.data_path.split('"')[1] if '"' in fcurve.data_path else None
            if bone_name in selected_bones_names:
                for keyframe in fcurve.keyframe_points:
                    if keyframe.select_control_point:
                        min_frame = min(min_frame, keyframe.co.x)
                        max_frame = max(max_frame, keyframe.co.x)
                        has_selected_keyframes = True
    else:
        # Object Mode, process all F-Curves
        for fcurve in context.visible_fcurves:
            for keyframe in fcurve.keyframe_points:
                if keyframe.select_control_point:
                    min_frame = min(min_frame, keyframe.co.x)
                    max_frame = max(max_frame, keyframe.co.x)
                    has_selected_keyframes = True

    if has_selected_keyframes:
        return (int(min_frame), int(max_frame))
    else:
        return None


def get_selected_keyframes_range(context):
    """
    Returns the range of selected keyframes as (min_frame, max_frame) or None if no keyframes are selected.
    This function targets the Graph Editor context to ensure accuracy in detecting selected keyframes
    for both Object and Pose Mode.
    """
    min_frame, max_frame = float("inf"), -float("inf")
    has_selected_keyframes = False

    for fcurve in context.selected_visible_fcurves:
        for keyframe in fcurve.keyframe_points:
            if keyframe.select_control_point or keyframe.select_left_handle or keyframe.select_right_handle:
                min_frame = min(min_frame, keyframe.co.x)
                max_frame = max(max_frame, keyframe.co.x)
                has_selected_keyframes = True

    if has_selected_keyframes:
        return (int(min_frame), int(max_frame))
    else:
        return None


def get_keyframes_in_range(context, frame_start, frame_end):
    keyframes = set()
    selected_curves = context.selected_visible_fcurves

    for fcurve in selected_curves:
        for keyframe in fcurve.keyframe_points:
            if frame_start <= keyframe.co.x <= frame_end:
                keyframes.add(int(keyframe.co.x))

    return keyframes


def find_closest_keyframe_to_playhead(context):
    """
    Finds the closest keyframe to the playhead for the current action.
    Prefers the previous keyframe if two are equally far away.
    Works in both Object and Pose Modes.
    """
    obj = context.active_object
    # Check for object and animation data existence
    if not obj or not obj.animation_data or not obj.animation_data.action:
        return context.scene.frame_current

    action = obj.animation_data.action
    current_frame = context.scene.frame_current
    closest_keyframe = None
    closest_distance = float("inf")

    # Check for object selection or armature bone selection
    if (context.selected_objects and obj.type != "ARMATURE") or (
        obj.type == "ARMATURE" and context.selected_pose_bones
    ):
        fcurves = all_fcurves(action)
        if context.mode == "POSE" and obj.type == "ARMATURE":
            # Filter for selected bones in Pose Mode
            selected_bones_names = {bone.name for bone in context.selected_pose_bones}
            fcurves = (
                fcurve
                for fcurve in fcurves
                if '"' in fcurve.data_path and fcurve.data_path.split('"')[1] in selected_bones_names
            )

        # Find closest keyframe
        for fcurve in fcurves:
            for keyframe in fcurve.keyframe_points:
                distance = abs(keyframe.co.x - current_frame)
                if distance < closest_distance or (distance == closest_distance and keyframe.co.x <= current_frame):
                    closest_distance = distance
                    closest_keyframe = keyframe.co.x
    else:
        return context.scene.frame_current

    return closest_keyframe


def find_closest_keyframe(fcurve, frame_start, frame_end, to_right):
    """
    Finds the closest keyframe outside of the selected range in the specified direction.
    Returns the keyframe point if found, otherwise None.
    """
    if to_right:
        outside_keyframes = [kp for kp in fcurve.keyframe_points if kp.co.x > frame_end]
        outside_keyframes.sort(key=lambda kp: kp.co.x)
    else:
        outside_keyframes = [kp for kp in fcurve.keyframe_points if kp.co.x < frame_start]
        outside_keyframes.sort(key=lambda kp: kp.co.x, reverse=True)

    return outside_keyframes[0] if outside_keyframes else None


def find_keyframes(context):
    """Collect keyframes from various animation data sources, adapting to the context."""
    keyframes = []
    editors = {"GRAPH_EDITOR", "DOPESHEET_EDITOR", "TIMELINE"}
    # Check for animation editor contexts
    if context.area is not None and context.area.type in editors:
        for fcurve in context.visible_fcurves:
            keyframes.extend([keyframe.co[0] for keyframe in fcurve.keyframe_points])
    else:
        # Handle the object/bone context
        if context.mode == "POSE":
            armature = context.active_object if context.active_object.type == "ARMATURE" else None
            # Ensure the armature has animation data and an action
            if armature.animation_data and armature.animation_data.action:
                # Collect keyframes from selected bones in Pose Mode
                # if bone selected and active:
                if context.selected_pose_bones:
                    for bone in context.selected_pose_bones:
                        # Construct the data path for this bone
                        bone_path = f'pose.bones["{bone.name}"]'
                        for fcurve in all_fcurves(armature.animation_data.action):
                            # Check if this F-curve is associated with the current bone
                            if bone_path in fcurve.data_path:
                                keyframes.extend([keyframe.co[0] for keyframe in fcurve.keyframe_points])
                else:
                    for bone in context.visible_pose_bones:  # armature.pose.bones:
                        # break early if bone not in visible_pose_bones
                        bone_path = f'pose.bones["{bone.name}"]'
                        for fcurve in all_fcurves(armature.animation_data.action):
                            if bone_path in fcurve.data_path:
                                keyframes.extend([keyframe.co[0] for keyframe in fcurve.keyframe_points])

        else:
            # Collect keyframes from selected objects
            for obj in context.selected_objects:
                if obj.animation_data and obj.animation_data.action:
                    for fcurve in all_fcurves(obj.animation_data.action):
                        keyframes.extend([keyframe.co[0] for keyframe in fcurve.keyframe_points])

    return sorted(set(keyframes))


def select_keyframe_in_editors(target_frame, context):
    scene = context.scene
    areas = {"GRAPH_EDITOR", "DOPESHEET_EDITOR", "TIMELINE"}

    if context.area is not None and context.area.type not in areas:
        return
    if context.area is not None:
        if context.visible_fcurves is not None:
            if context.area.type == "GRAPH_EDITOR":
                try:
                    bpy.ops.graph.select_all(action="DESELECT")
                except RuntimeError as e:
                    utils.dprint(e)
            elif context.area.type == ("DOPESHEET_EDITOR" or "TIMELINE"):
                try:
                    bpy.ops.action.select_all(action="DESELECT")
                except RuntimeError as e:
                    utils.dprint(e)

            for fcurve in context.visible_fcurves:
                for keyframe in fcurve.keyframe_points:
                    if target_frame is not None and int(round(keyframe.co[0])) == int(round(target_frame)):
                        keyframe.select_control_point = True
                        for area in context.screen.areas:
                            if area.type in areas:
                                area.tag_redraw()
                        break


def deselect_all_keyframes_in_editors(context):
    areas = {"GRAPH_EDITOR", "DOPESHEET_EDITOR", "TIMELINE"}

    if context.area.type not in areas:
        return

    if context.area.type == "GRAPH_EDITOR":
        try:
            bpy.ops.graph.select_all(action="DESELECT")
        except RuntimeError as e:
            utils.dprint(e)
    elif context.area.type == ("DOPESHEET_EDITOR" or "TIMELINE"):
        bpy.ops.action.select_all(action="DESELECT")

    # Redraw the area to update the UI
    utils.refresh_ui(context)


def has_selected_keyframes(context):
    space_type = context.space_data.type
    active_object = context.active_object

    if active_object is None:
        return False

    if space_type == "GRAPH_EDITOR":
        active_fcurves = context.selected_visible_fcurves

        if active_fcurves:
            for fcurve in active_fcurves:
                for keyframe in fcurve.keyframe_points:
                    if keyframe.select_control_point or keyframe.select_left_handle or keyframe.select_right_handle:
                        return True

    elif space_type == "DOPESHEET_EDITOR":
        animation_data = active_object.animation_data

        if animation_data and animation_data.action:
            for fcurve in all_fcurves(animation_data.action):
                for keyframe in fcurve.keyframe_points:
                    if keyframe.select_control_point:
                        return True

        if is_grease_pencil_object(active_object):
            grease = context.grease_pencil
            for layer in grease.layers:
                for frame in layer.frames:
                    if frame.select:
                        return True

        if hasattr(active_object.data, "materials") and active_object.data.materials:
            for material in active_object.data.materials:
                if (
                    material is not None
                    and material.node_tree
                    and material.node_tree.animation_data
                    and material.node_tree.animation_data.action
                ):
                    action_fcurves = all_fcurves(material.node_tree.animation_data.action)
                    for fcurve in action_fcurves:
                        if "nodes[" in fcurve.data_path and ".inputs[" in fcurve.data_path:
                            for keyframe in fcurve.keyframe_points:
                                if keyframe.select_control_point:
                                    return True

    return False


def delete_keyframes(context, frames_to_delete):

    if frames_to_delete is None:
        frames_to_delete = []
    else:
        frames_to_delete = sorted([round(frame) for frame in frames_to_delete])

    active_fcurves = context.selected_visible_fcurves
    if active_fcurves is not None:
        for fcurve in active_fcurves:
            for keyframe in fcurve.keyframe_points:
                if keyframe.co.x in frames_to_delete:
                    fcurve.keyframe_points.remove(keyframe)


def key_custom_properties(target, frame):
    """
    Keyframe custom properties for the given target at the specified frame.
    Handles objects and bones in pose mode.
    """
    if hasattr(target, "pose") and bpy.context.mode == "POSE":
        for bone in target.pose.bones:
            if bone.select:
                for prop in [p for p in bone.keys() if p not in {"_RNA_UI", "cycles"}]:
                    # Using get() method to safely access properties
                    if hasattr(bone, prop):
                        bone.keyframe_insert(data_path=f'["{prop}"]', frame=frame, group=bone.name)
    else:
        for prop in [p for p in target.keys() if p not in {"_RNA_UI", "cycles"}]:
            # Using get() method to safely access properties
            try:
                if hasattr(target, prop):
                    target.keyframe_insert(data_path=f'["{prop}"]', frame=frame)
            except:
                pass


# def keyframe_targets(
#     self,
#     context,
#     targets,
#     frame,
#     location=False,
#     rotation=False,
#     scale=False,
#     custom=False,
# ):
#     for target in targets:
#         transformations_keyed = location or rotation or scale

#         if location:
#             key_standard_properties(target, "location", frame)
#         if rotation:
#             key_standard_properties(
#                 target,
#                 (
#                     "rotation_quaternion"
#                     if getattr(target, "rotation_mode", "XYZ") == "QUATERNION"
#                     else "rotation_euler"
#                 ),
#                 frame,
#             )
#         if scale:
#             key_standard_properties(target, "scale", frame)

#         # Key all available fcurves if none of the transformations are keyed
#         if not transformations_keyed:
#             key_available_fcurves(self, context, target, frame)

#         if custom:
#             key_custom_properties(target, frame)


def keyframe_fcurves(
    self,
    context,
    fcurves,
    frame,
    location=False,
    rotation=False,
    scale=False,
    custom=False,
):
    for fcurve in fcurves:
        data_path = fcurve.data_path
        transformations_keyed = location or rotation or scale
        if not transformations_keyed:
            # Key all available fcurves because no specific transformation or custom property was requested
            key_fcurve(fcurve, frame)
        else:
            # Determine if the current fcurve is for location, rotation, or scale based on its data_path
            if location and "location" in data_path:
                key_fcurve(fcurve, frame)
            if rotation and ("rotation_quaternion" in data_path or "rotation_euler" in data_path):
                key_fcurve(fcurve, frame)
            if scale and "scale" in data_path:
                key_fcurve(fcurve, frame)

        # Key custom properties
        # Key custom properties, identifying them by exclusion or specific markers in their data paths
        if custom and (
            data_path.startswith('["')
            or not data_path.split(".")[0] in ["location", "rotation_euler", "rotation_quaternion", "scale"]
        ):
            key_fcurve(fcurve, frame)


def key_fcurve(fcurve, frame, value=None):
    # Check if there's already a keyframe on this frame
    # keyframe_points = fcurve.keyframe_points
    # existing_keyframe = next((point for point in keyframe_points if point.co[0] == frame), None)

    # if existing_keyframe:
    #     # Optional: Update the existing keyframe's value if 'value' is not None
    #     if value is not None:
    #         existing_keyframe.co[1] = value
    # else:
    #     # Insert a new keyframe. If 'value' is None, defaults to the current value of the fcurve at 'frame'
    if value is not None:
        fcurve.keyframe_points.insert(frame, value, options={"FAST"})
    else:
        # Evaluate the current value of the F-Curve at this frame and insert a keyframe
        current_value = fcurve.evaluate(frame)
        fcurve.keyframe_points.insert(frame, current_value, options={"FAST"})


def key_available_fcurves(self, context, target, frame):
    """
    Insert keyframes for all animatable properties (fcurves) of the target at the specified frame.
    Updated to avoid TypeError by removing the use of a non-existent 'find' method.
    """

    selected_fcurves = context.selected_visible_fcurves

    if selected_fcurves is not None:
        for fcurve in selected_fcurves:
            if isinstance(target, bpy.types.PoseBone):
                bone_path = 'pose.bones["{}"]'.format(target.name)
                if not fcurve.data_path.startswith(bone_path):
                    continue

            # if fcurve.lock or fcurve.hide:
            #     continue

            # Manually search for a keyframe at the specified frame
            keyframe_point = next((kp for kp in fcurve.keyframe_points if int(kp.co.x) == frame), None)

            if keyframe_point is not None:
                # Keyframe exists, update its value
                keyframe_point.co.y = fcurve.evaluate(frame)
            else:
                # Keyframe does not exist, insert a new one
                fcurve.keyframe_points.insert(frame, fcurve.evaluate(frame)).interpolation = "BEZIER"
    else:
        self.report({"WARNING"}, "No keyframes selected.")
        return {"CANCELLED"}


def key_standard_properties(target, data_path, frame):
    """
    Insert keyframe for standard properties (location, rotation, scale) at the given frame.
    The object's current value for the property is used.
    """
    current_frame = bpy.context.scene.frame_current
    bpy.context.scene.frame_set(frame)

    try:
        target.keyframe_insert(data_path=data_path, frame=frame)
    finally:
        bpy.context.scene.frame_set(current_frame)


def find_range_between_selected_keyframes(context):
    min_frame, max_frame = float("inf"), -float("inf")

    selected_curves = context.selected_visible_fcurves
    for fcurve in selected_curves:
        for keyframe_point in fcurve.keyframe_points:
            if keyframe_point.select_control_point:
                frame = keyframe_point.co.x
                if frame < min_frame:
                    min_frame = frame
                if frame > max_frame:
                    max_frame = frame

    if min_frame == float("inf") or max_frame == -float("inf"):
        utils.dprint("No keyframes selected.")
        return (0, 0)

    min_frame = math.floor(min_frame)

    if not max_frame.is_integer():
        max_frame = math.ceil(max_frame)
    else:
        max_frame = math.floor(max_frame)

    return (int(min_frame), int(max_frame))


def determine_frame_range_priority(self, context):
    if has_selected_keyframes(context):
        return find_range_between_selected_keyframes(context)
    elif context.scene.use_preview_range:
        return (context.scene.frame_preview_start, context.scene.frame_preview_end)
    else:
        return (context.scene.frame_start, context.scene.frame_end)


def determine_frame_range(self, context):
    if self.range_options == "SELECTED":
        selected_range = find_range_between_selected_keyframes(context)
        return selected_range
    elif self.range_options == "PREVIEW":
        return (context.scene.frame_preview_start, context.scene.frame_preview_end)
    else:
        return (context.scene.frame_start, context.scene.frame_end)


def determine_insertion_frames(self, frame_start, frame_end):
    frame_start = int(frame_start)
    frame_end = int(frame_end)

    frame_step = max(int(self.frame_step), 1)
    frame_start_range = self.frame_start_range

    frames_to_insert = []

    if self.insertion_type == "ON_MARKERS":
        markers = bpy.context.scene.timeline_markers
        frames_to_insert = [marker.frame for marker in markers if frame_start <= marker.frame <= frame_end]

    elif self.insertion_type == "FRAME_STEP":
        frames_to_insert = list(range(frame_start + frame_start_range, frame_end + 1, frame_step))

    elif self.insertion_type == "ON_MARKERS_AND_FRAME_STEP":
        markers = bpy.context.scene.timeline_markers
        marker_frames = {marker.frame for marker in markers if frame_start <= marker.frame <= frame_end}
        step_frames = set(range(frame_start + frame_start_range, frame_end + 1, frame_step))
        frames_to_insert = sorted(marker_frames.union(step_frames))

    if frame_start not in frames_to_insert:
        frames_to_insert.insert(0, frame_start)
    if frame_end not in frames_to_insert:
        frames_to_insert.append(frame_end)

    return frames_to_insert


def update_frame_start_range(self, context):
    """
    Update callback for frame_start_range to ensure it's smaller than frame_step.
    """

    if self.frame_step <= self.frame_start_range:
        self.frame_start_range = self.frame_step - 1


def update_frame_step(self, context):
    """
    Update callback for frame_start_range to ensure it's smaller than frame_step.
    """

    if self.frame_step < self.frame_start_range:
        self.frame_step = self.frame_start_range + 1


def update_frame_range_start_frame(self, context):
    if self.end_range > context.scene.frame_end:
        self.end_range = context.scene.frame_end
    if self.end_range <= self.start_range:
        self.start_range = self.end_range - 1


def update_frame_range_end_frame(self, context):

    if self.start_range < context.scene.frame_start:
        self.start_range = context.scene.frame_start
    if self.end_range < self.start_range:
        self.end_range = self.start_range + 1


def is_close_to_whole_frame(value, epsilon=1e-9):
    return abs(round(value) - value) < epsilon


def clear_other_keyframes(context, fcurves, frames_to_keep, frame_range):
    frame_start, frame_end = frame_range

    for fcurve in fcurves:
        # Check if the F-Curve is relevant based on the target type
        keyframe_points_to_remove = [
            kp for kp in fcurve.keyframe_points if frame_start <= kp.co.x <= frame_end and kp.co.x not in frames_to_keep
        ]

        # Create a list to collect the indices of keyframe points to remove
        indices_to_remove = []
        for kp in keyframe_points_to_remove:
            # Find the index of the keyframe point to remove
            index = [i for i, point in enumerate(fcurve.keyframe_points) if point == kp]
            if index:
                indices_to_remove.extend(index)

        # Remove keyframes in reverse order to maintain correct indices
        for index in sorted(indices_to_remove, reverse=True):
            fcurve.keyframe_points.remove(fcurve.keyframe_points[index])

        keys_to_remove = [kp for kp in fcurve.keyframe_points if not is_close_to_whole_frame(kp.co.x)]
        for kp in keys_to_remove:
            fcurve.keyframe_points.remove(kp)
        fcurve.update()


def correct_offset(fcurve, original_first_frame):
    """
    Corrects the offset of all keyframes in an F-Curve based on the shift
    from the original first frame to the new first frame position.

    Parameters:
    - fcurve (bpy.types.FCurve): The F-Curve to correct.
    - original_first_frame (float): The original x position of the first keyframe.
    """
    if original_first_frame is not None:
        new_first_frame = fcurve.keyframe_points[0].co.x
        shift = new_first_frame - original_first_frame

        # Step 4: Adjust all keyframes if there's a shift
        if shift != 0:
            for keyframe in fcurve.keyframe_points:
                keyframe.co.x -= shift
                keyframe.handle_left.x -= shift
                keyframe.handle_right.x -= shift


def smart_preserve_fcurves(fcurves, original_first_frame=0, shift_offset=True):
    """
    Preserves the F-Curves by inserting keyframes at whole frames and optionally correcting
    the offset to maintain the original animation start position.

    Parameters:
    - fcurves (list of bpy.types.FCurve): The F-Curves to process.
    - original_first_frame (float): The x position of the first keyframe before retiming.
    - shift_offset (bool): Whether to correct the offset after processing.
    """
    for fcurve in fcurves:
        whole_frames = set()

        subframe_keyframes = []

        for keyframe in fcurve.keyframe_points:
            frame = keyframe.co.x
            if frame == round(frame):
                whole_frames.add(round(frame))
            else:
                subframe_keyframes.append(keyframe)

        # Insert keyframes at the nearest whole frame for subframe keyframes
        for keyframe in subframe_keyframes:
            if keyframe.co.x is not None:
                nearest_whole_frame = round(keyframe.co.x)

            # Only insert a new keyframe if there isn't already one at this frame
            if nearest_whole_frame not in whole_frames:
                # Evaluate the fcurve at this frame to get the correct value
                value = fcurve.evaluate(nearest_whole_frame)
                new_keyframe = fcurve.keyframe_points.insert(nearest_whole_frame, value, options={"NEEDED", "FAST"})
                # Set the handle types for the new keyframe
                # new_keyframe.interpolation = keyframe.interpolation
                # new_keyframe.handle_left_type = keyframe.handle_left_type
                # new_keyframe.handle_right_type = keyframe.handle_right_type

                new_keyframe.interpolation = "BEZIER"
                new_keyframe.handle_left_type = "AUTO_CLAMPED"
                new_keyframe.handle_right_type = "AUTO_CLAMPED"

                whole_frames.add(nearest_whole_frame)

        # Second pass: Remove the original subframe keyframes
        if shift_offset:
            delete_subframe_keyframes(fcurve)

        correct_offset(fcurve, original_first_frame)


def delete_subframe_keyframes(fcurve):
    """
    Deletes keyframes that are not on whole frames from the specified F-Curve.

    Parameters:
    - fcurve (bpy.types.FCurve): The F-Curve from which to remove subframe keyframes.
    """
    indexes_to_remove = []

    for index, keyframe in enumerate(fcurve.keyframe_points):
        if keyframe.co.x != round(keyframe.co.x):
            indexes_to_remove.append(index)

    indexes_to_remove.sort(reverse=True)

    for index in indexes_to_remove:
        fcurve.keyframe_points.remove(fcurve.keyframe_points[index])

    utils.dprint(f"Removed {len(indexes_to_remove)} subframe keyframe(s) from the F-Curve.")


def find_owner(fcurve):
    id_data = getattr(fcurve, "id_data", None)
    if isinstance(id_data, bpy.types.Action):
        if blender_compat.is_action_layered(id_data):
            target_bag_name = None
            for layer in id_data.layers:
                for strip in layer.strips:
                    for bag_name, bag in strip.channelbags.items():
                        if fcurve in list(bag.fcurves):
                            target_bag_name = bag_name
                            break
                    if target_bag_name: break
                if target_bag_name: break
            
            if target_bag_name:
                for obj in bpy.data.objects:
                    if obj.animation_data and obj.animation_data.action == id_data:
                        slot = getattr(obj.animation_data, "action_slot", None)
                        if slot and slot.name == target_bag_name:
                            return obj
                            
        for obj in bpy.data.objects:
            if obj.animation_data and obj.animation_data.action == id_data:
                return obj
        return None
    else:
        return id_data


def is_fcurve_in_radians(fcurve):
    """Converts the value to degrees if the F-Curve represents rotation in radians."""
    data_path = fcurve.data_path

    if ("rotation_euler" or "delta_rotation_euler") in data_path:
        return True

    if any(key in data_path for key in ["location", "scale", "rotation_quaternion", "delta_rotation_quaternion"]):

        return False

    path_parts = data_path.rsplit(".", 1)
    if len(path_parts) == 2:
        owner_path, property_name = path_parts
    else:
        owner_path = ""
        property_name = path_parts[0]

    owner = find_owner(fcurve)
    if owner is None:
        return False

    try:
        if owner_path:
            owner = owner.path_resolve(owner_path)

        prop_def = owner.bl_rna.properties.get(property_name)

        if prop_def:
            unit = getattr(prop_def, "unit", None)
            if unit == "ROTATION":
                return True
    except Exception:
        pass

    return False


def get_nla_strip_offset(obj, fcurve=None):
    """
    Returns the starting frame offset of the active NLA strip for the given object.

    This function checks the active NLA track and its associated strips to find the
    frame start value corresponding to the current action or, optionally, the action
    linked to the provided FCurve. If no active strip is found, or if the object
    lacks animation data, the function returns 0.

    Args:
        obj (bpy.types.Object): The Blender object whose NLA data is examined.
        fcurve (bpy.types.FCurve, optional): Optional FCurve used to determine the
            action from its id_data. Defaults to None.

    Returns:
        float: Starting frame of the matching NLA strip, or 0 if no valid strip
        is found.
    """
    if not obj or not obj.animation_data:
        return 0

    active_track = obj.animation_data.nla_tracks.active
    if not active_track or not active_track.strips:
        return 0

    if fcurve is not None:
        action = fcurve.id_data
    else:
        action = obj.animation_data.action

    for strip in active_track.strips:
        if strip.action == action:
            return strip.frame_start_ui

    active_strip = getattr(bpy.context, "active_nla_strip", None)
    if active_strip:
        return active_strip.frame_start_ui

    return 0


from typing import Iterable, Tuple, Any


def get_active_groups(action: bpy.types.Action):
    """
    Return a dictionary of active F-Curve groups for the entire action,
    merging groups from all slots, layers, and strips.
    """
    groups = {}
    for group in blender_compat.iter_action_groups(action, include_all_slots=True):
        groups[group.name] = group
    return groups


def all_fcurves(action: bpy.types.Action):
    """Return all FCurves from an action, handling legacy and slotted actions."""
    yield from blender_compat.iter_action_fcurves(action, include_all_slots=True)


def selected_fcurves() -> Iterable[bpy.types.FCurve]:
    """Return selected visible FCurves from the built-in context."""
    return bpy.context.selected_visible_fcurves


def visible_fcurves() -> Iterable[bpy.types.FCurve]:
    """Return visible FCurves from the built-in context."""
    return bpy.context.visible_fcurves


def selected_keys() -> Iterable[Tuple[bpy.types.FCurve, Any]]:
    """Iterate over editable FCurves, yielding (fcurve, keyframe) tuples for selected keyframes.

    Checks standard FCurve selection flags and also a generic 'select' flag for cases like
    grease pencil frames.
    """
    for f in bpy.context.editable_fcurves:
        for kp in f.keyframe_points:
            if (
                hasattr(kp, "select_control_point")
                and (kp.select_control_point or kp.select_left_handle or kp.select_right_handle)
            ) or getattr(kp, "select", False):
                yield f, kp


def scene_fcurves() -> Iterable:
    added_actions = set()
    scene = bpy.context.scene

    # Process actions from objects, shape keys, and materials only once
    for obj in scene.objects:

        # Objects
        if obj.animation_data and obj.animation_data.action:
            act = obj.animation_data.action
            if act not in added_actions:
                added_actions.add(act)
                for fcu in all_fcurves(act):
                    yield fcu

        # Shape keys
        if hasattr(obj.data, "shape_keys") and obj.data.shape_keys:
            sk = obj.data.shape_keys
            if sk.animation_data and sk.animation_data.action:
                act = sk.animation_data.action
                if act not in added_actions:
                    added_actions.add(act)
                    for fcu in all_fcurves(act):
                        yield fcu

        # Materials
        if hasattr(obj.data, "materials") and obj.data.materials:
            for mat in obj.data.materials:
                if mat and mat.animation_data and mat.animation_data.action:
                    act = mat.animation_data.action
                    if act not in added_actions:
                        added_actions.add(act)
                        for fcu in all_fcurves(act):
                            yield fcu
                if mat and hasattr(mat, "node_tree") and mat.node_tree:
                    if mat.node_tree.animation_data and mat.node_tree.animation_data.action:
                        act = mat.node_tree.animation_data.action
                        if act not in added_actions:
                            added_actions.add(act)
                            for fcu in all_fcurves(act):
                                yield fcu

def gather_grease_pencil_frames(scope: str, context) -> list:
    """Gather Grease Pencil frames based on the given scope."""
    frames = []
    if scope == "SCENE":
        for obj in context.scene.objects:
            if blender_compat.is_grease_pencil_object(obj) and hasattr(obj.data, "layers"):
                for layer in obj.data.layers:
                    for frame in layer.frames:
                        frames.append(blender_compat.GreasePencilFrameRef(
                            object=obj, layer=layer, frame=frame,
                            frame_number=getattr(frame, "frame_number", getattr(frame, "frame", 0)),
                            selected=getattr(frame, "select", False)
                        ))
    elif scope == "SELECTED_ELEMENTS":
        for obj in context.selected_objects:
            if blender_compat.is_grease_pencil_object(obj) and hasattr(obj.data, "layers"):
                for layer in obj.data.layers:
                    for frame in layer.frames:
                        frames.append(blender_compat.GreasePencilFrameRef(
                            object=obj, layer=layer, frame=frame,
                            frame_number=getattr(frame, "frame_number", getattr(frame, "frame", 0)),
                            selected=getattr(frame, "select", False)
                        ))
    return frames


def get_active_fcurves_obj(obj) -> Iterable[bpy.types.FCurve]:
    # If obj is an Action, yield its fcurves directly.
    if isinstance(obj, bpy.types.Action):
        yield from blender_compat.iter_action_fcurves(obj, include_all_slots=True)
        return
    anim = getattr(obj, "animation_data", None)
    if not anim:
        return
    slot = getattr(anim, "action_slot", None)
    if slot and anim.action:
        yield from blender_compat.iter_action_fcurves(anim.action, slot=slot)
    elif anim.action:
        yield from all_fcurves(anim.action)


def selected_elements_fcurves(context) -> Iterable[bpy.types.FCurve]:
    """Yield fcurves from selected elements using the active animation slot.
    • In Pose Mode: FCurves from the active object's slot that belong to selected bones.
    • In Object Mode: FCurves from each selected object's active slot.
    """
    if context.mode == "POSE":
        fcurves = list(get_active_fcurves_obj(context.active_object))
        if fcurves:
            selected_names = {bone.name for bone in context.selected_pose_bones}
            for f in fcurves:
                if any(bone_name in f.data_path for bone_name in selected_names):
                    yield f
    else:
        for obj in context.selected_objects:
            for f in get_active_fcurves_obj(obj):
                yield f


def gather_fcurve_keyframes(scope: str, context) -> list:
    """
    Gather keyframes from fcurves based on the given scope.
      • "SCENE": from all fcurves in the scene.
      • "ACTION": from all fcurves of the active object's action.
      • "SELECTED_ELEMENTS": from animation data of any selected element (Object Mode or selected bones in Pose Mode).
      • "VISIBLE_FCURVES": from all visible fcurves.
      • "SELECTED_KEYS": selected keyframes in editable fcurves.
    """
    if scope == "SCENE":
        return [kf for fcu in scene_fcurves() for kf in fcu.keyframe_points]
    elif scope == "ACTION":
        act = context.active_object.animation_data.action
        return [kf for fcu in all_fcurves(act) for kf in fcu.keyframe_points]
    elif scope == "SELECTED_ELEMENTS":
        kf_list = []
        for fcu in selected_elements_fcurves(context):
            kf_list.extend(fcu.keyframe_points)
        return kf_list
    elif scope == "VISIBLE_FCURVES":
        return [kf for fcu in visible_fcurves() for kf in fcu.keyframe_points]
    elif scope == "SELECTED_KEYS":
        return [key for fcu, key in selected_keys()]
    else:
        return []


def remove_fcurve_from_action(action, fcurve):
    """
    Remove an fcurve from its container.

    - In Blender 4.4+ (with slotted actions), search through action.layers → strips → channelbags.
    - In legacy actions (pre‑4.4) remove directly from action.fcurves.
    """
    try:
        blender_compat.remove_fcurve(action, fcurve)
        return True
    except Exception as e:
        print("Removal failed:", e)
        return False


def gather_fcurves(scope: str, context) -> list:
    """
    Gather fcurves based on the given scope using the same mechanisms as gather_fcurve_keyframes.
      • "SCENE": from all fcurves in the scene.
      • "ACTION": from all fcurves of the active object's action.
      • "SELECTED_ELEMENTS": from fcurves of selected elements.
      • "VISIBLE_FCURVES": from all visible fcurves.
      • "SELECTED_KEYS": unique fcurves containing the selected keyframes.
    """
    if scope == "SCENE":
        return list(scene_fcurves())
    elif scope == "ACTION":
        act = (
            context.active_object.animation_data.action
            if context.active_object and context.active_object.animation_data
            else None
        )
        return list(all_fcurves(act)) if act else []
    elif scope == "SELECTED_ELEMENTS":
        return list(selected_elements_fcurves(context))
    elif scope == "VISIBLE_FCURVES":
        return list(visible_fcurves())
    elif scope == "SELECTED_KEYS":
        unique_fcurves = {}
        for fcu, _ in selected_keys():
            key = (id(fcu.id_data), fcu.data_path, fcu.array_index)
            unique_fcurves[key] = fcu
        return list(unique_fcurves.values())
    else:
        return []
