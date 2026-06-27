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

import bpy
import os
import gpu
from gpu_extras.batch import batch_for_shader
from bpy.types import SpaceGraphEditor
from .. import utils

from .. import __package__ as base_package

# Anim_transform global variables
user_preview_range = {}
user_scene_range = {}
global_values = {}
last_op = None


# ---------- Main Tool ------------


_magnet_update_scheduled = False
_is_mutating_internally = False

def deferred_magnet_update():
    global _magnet_update_scheduled, last_op, _is_mutating_internally
    _magnet_update_scheduled = False
    
    _is_mutating_internally = True
    try:
    
        context = bpy.context
        scene = context.scene

        context = bpy.context

        # Check if the current context is the Graph Editor
        if context.area is None or context.area.type == "GRAPH_EDITOR":
            # utils.dprint("Graph Editor")
            return  # Do not run the function if in the Graph Editor or in headless context

        external_op = context.active_operator

        if context.scene.tool_settings.use_keyframe_insert_auto or (context.mode != "OBJECT" and context.mode != "POSE"):

            utils.amp_draw_header_handler(action="REMOVE")
            anim_offset = scene.amp_timeline_tools.anim_offset
            if anim_offset.mask_in_use:
                remove_mask(context)
                reset_timeline_mask(context)

            if magnet_handlers in bpy.app.handlers.depsgraph_update_post:
                bpy.app.handlers.depsgraph_update_post.remove(magnet_handlers)
            utils.remove_message()
            return

        amp_timeline_tools = context.scene.amp_timeline_tools
        anim_offset = amp_timeline_tools.anim_offset

        preferences = context.preferences
        pref = preferences.addons[base_package].preferences

        if anim_offset.mask_in_use:
            scene = context.scene
            cur_frame = scene.frame_start + int((scene.frame_end - scene.frame_start) / 2)
            # cur_frame = context.scene.frame_current
            if cur_frame < scene.frame_start or cur_frame > scene.frame_end:
                if anim_offset.insert_outside_keys:
                    add_keys(context)
                return

        # Doesn't refresh if fast mask is selected:
        # Each time an operator is used is a different one, so this tests
        # if any transform on an object is steel been applied

        # if external_op is last_op and anim_offset.fast_mask:
        if external_op is last_op and pref.ao_fast_offset:
            return
        last_op = context.active_operator

        # context.scene.tool_settings.use_keyframe_insert_auto = False

        selected_objects = context.selected_objects

        for obj in selected_objects:
            action = getattr(obj.animation_data, "action", None)

            for fcurve in utils.curve.all_fcurves(action):
                if fcurve.data_path.endswith("rotation_mode"):
                    continue  # added exception
                magnet(context, obj, fcurve)

            bpy.context.evaluated_depsgraph_get().update()
    finally:
        _is_mutating_internally = False

    return None

def magnet_handlers(scene):
    """Function to be run by the anim_offset Handler"""
    global _magnet_update_scheduled, _is_mutating_internally
    if _is_mutating_internally:
        return
    if not _magnet_update_scheduled:
        _magnet_update_scheduled = True
        bpy.app.timers.register(deferred_magnet_update, first_interval=0.01)
    return


def magnet(context, obj, fcurve):
    """Modify all the keys in every fcurve of the current object proportionally to the change in transformation
    on the current frame by the user"""

    scene = context.scene

    # Exit conditions
    if fcurve.lock:
        return
    if getattr(fcurve.group, "name", None) == "amp_action":
        return  # Skip reference fcurves

    # Prepare for change detection
    changes_detected = False  # Flag to track if any changes were made

    blends_action = bpy.data.actions.get("amp_action")
    blends_curves = list(utils.blender_compat.iter_action_fcurves(blends_action))

    delta_y = get_delta(context, obj, fcurve)

    for k in fcurve.keyframe_points:
        # Determine the factor for modification
        if not context.scene.amp_timeline_tools.anim_offset.mask_in_use:
            factor = 1
        elif scene.frame_start <= k.co.x <= scene.frame_end:
            factor = 1
        elif blends_curves is not None and len(blends_curves) > 0:
            blends_curve = blends_curves[0]
            factor = blends_curve.evaluate(k.co.x)
        else:
            factor = 0

        # Calculate the new value
        new_y = k.co_ui.y + (delta_y * factor)

        # Check if the new value is different from the current one
        if k.co_ui.y != new_y:
            k.co_ui.y = new_y  # Apply the change
            changes_detected = True  # Mark that a change was detected

    # Update the fcurve only if changes were detected
    if changes_detected:
        fcurve.update()


def get_delta(context, obj, fcurve):
    """Determine the transformation change by the user of the current object"""
    cur_frame = context.scene.frame_current
    nla_frame = int(context.active_object.animation_data.nla_tweak_strip_time_to_scene(cur_frame))
    nla_dif = nla_frame - cur_frame
    curve_value = fcurve.evaluate(cur_frame - nla_dif)

    try:
        prop = obj.path_resolve(fcurve.data_path)
    except:
        print(f"Failed to resolve path: {fcurve.data_path}")
        return 0

    if prop:
        try:
            target = prop[fcurve.array_index]
        except TypeError:
            target = prop

        # Enhanced type check with debug information
        if isinstance(target, (int, float)):
            return target - curve_value
        else:
            return 0
    else:
        return 0


# ----------- Mask -----------


def add_blends():
    """Add a curve with 4 control points to an action called 'amp_anim' that would act as a mask for anim_offset"""
    action = utils.set_amp_timeline_tools_action()
    # Clear existing F-Curves to ensure a fresh start
    fcurves = utils.curve.all_fcurves(action)
    # fcurves.clear()
    for fc in fcurves:
        utils.curve.remove_fcurve_from_action(action, fc)
    # Add a new F-Curve with four control points
    return utils.curve.new("Magnet", 4)


def remove_mask(context):
    """Removes the fcurve and action that are been used as a mask for anim_offset"""

    anim_offset = context.scene.amp_timeline_tools.anim_offset
    blends_action = bpy.data.actions.get("amp_action")
    blends_curves = list(utils.blender_compat.iter_action_fcurves(blends_action))

    if blends_curves and len(blends_curves) > 0:
        utils.blender_compat.remove_fcurve(blends_action, blends_curves[0])
        # reset_timeline_mask(context)

    # delete action
    if blends_action is not None:

        bpy.data.actions.remove(blends_action)

    anim_offset.mask_in_use = False

    return


def set_blend_values(context):
    """Modify the position of the fcurve 4 control points that is been used as mask to anim_offset"""

    scene = context.scene
    blends_action = bpy.data.actions.get("amp_action")
    blends_curves = list(utils.blender_compat.iter_action_fcurves(blends_action))

    if blends_curves:
        blend_curve = blends_curves[0]
        keys = blend_curve.keyframe_points

        if len(keys) < 4:
            utils.dprint(f"Error: Not enough keyframe points in the F-Curve. {len(keys)} points found.")
            utils.dprint(f"{keys}")
            # Optionally, add missing keyframe points here
            return

        left_blend = scene.frame_preview_start
        left_margin = scene.frame_start
        right_margin = scene.frame_end
        right_blend = scene.frame_preview_end

        keys[0].co.x = left_blend
        keys[0].co.y = 0
        keys[1].co.x = left_margin
        keys[1].co.y = 1
        keys[2].co.x = right_margin
        keys[2].co.y = 1
        keys[3].co.x = right_blend
        keys[3].co.y = 0

        mask_interpolation(keys, context)


def mask_interpolation(keys, context):
    anim_offset = context.scene.amp_timeline_tools.anim_offset
    interp = anim_offset.interp
    easing = anim_offset.easing

    oposite = None

    if easing == "EASE_IN":
        oposite = "EASE_OUT"
    elif easing == "EASE_OUT":
        oposite = "EASE_IN"
    elif easing == "EASE_IN_OUT":
        oposite = "EASE_IN_OUT"

    keys[0].interpolation = interp
    keys[0].easing = easing
    keys[1].interpolation = "LINEAR"
    keys[1].easing = "EASE_IN_OUT"
    keys[2].interpolation = interp
    keys[2].easing = oposite


def add_keys(context):
    selected_objects = context.selected_objects

    for obj in selected_objects:
        action = getattr(obj.animation_data, "action", None)

        for fcurve in utils.curve.all_fcurves(action):

            if fcurve.lock:
                return

            if getattr(fcurve.group, "name", None) == "amp_timeline_tools":
                return  # we don't want to select keys on reference fcurves

            keys = fcurve.keyframe_points
            cur_index = utils.key.on_current_frame(fcurve)
            delta_y = get_delta(context, obj, fcurve)

            if not cur_index:
                cur_frame = context.scene.frame_current
                y = fcurve.evaluate(cur_frame) + delta_y
                utils.key.insert_key(keys, cur_frame, y)
            else:
                key = keys[cur_index]
                key.co_ui.y += delta_y


# -------- For mask interface -------


def set_timeline_ranges(context, left_blend, left_margin, right_margin, right_blend):
    """Use the timeline playback and preview ranges to represent the mask"""

    scene = context.scene
    scene.use_preview_range = True

    scene.frame_preview_start = left_blend
    scene.frame_start = left_margin
    scene.frame_end = right_margin
    scene.frame_preview_end = right_blend


def reset_timeline_mask(context):
    """Resets the timeline playback and preview ranges to what the user had it as"""

    scene = context.scene
    anim_offset = scene.amp_timeline_tools.anim_offset

    scene.frame_preview_start = anim_offset.user_preview_start
    scene.frame_preview_end = anim_offset.user_preview_end
    scene.use_preview_range = anim_offset.user_preview_use
    scene.frame_start = anim_offset.user_scene_start
    scene.frame_end = anim_offset.user_scene_end
    # scene.tool_settings.use_keyframe_insert_auto = anim_offset.user_scene_auto


def reset_timeline_blends(context):
    """Resets the timeline playback and preview ranges to what the user had it as"""

    scene = context.scene
    anim_offset = scene.amp_timeline_tools.anim_offset

    scene.frame_preview_start = anim_offset.user_preview_start
    scene.frame_preview_end = anim_offset.user_preview_end
    scene.use_preview_range = anim_offset.user_preview_use


def store_user_timeline_ranges(context):
    """Stores the timeline playback and preview ranges"""

    scene = context.scene
    anim_offset = scene.amp_timeline_tools.anim_offset

    anim_offset.user_preview_start = scene.frame_preview_start
    anim_offset.user_preview_end = scene.frame_preview_end
    anim_offset.user_preview_use = scene.use_preview_range
    anim_offset.user_scene_start = scene.frame_start
    anim_offset.user_scene_end = scene.frame_end
    # anim_offset.user_scene_auto = scene.tool_settings.use_keyframe_insert_auto


# ---------- Functions for Operators ------------


def poll(context):
    """Poll for all the anim_offset related operators"""

    objects = context.selected_objects
    area = context.area.type
    return (
        objects
        is not None
        # and area == "GRAPH_EDITOR"
        # or area == "DOPESHEET_EDITOR"
        # or area == "VIEW_3D"
    )


def get_anim_offset_globals(context, obj):
    """Get global values for the anim_offset"""
    anim = obj.animation_data
    if anim is None:
        return
    # Convert generator to list since .items() isn't available
    fcurves = list(utils.curve.all_fcurves(anim.action))
    if not fcurves:
        return

    curves = {}

    for index, fcurve in enumerate(fcurves):
        if fcurve.lock is True:
            continue

        cur_frame = context.scene.frame_current
        cur_frame_y = fcurve.evaluate(cur_frame)
        values = {"x": cur_frame, "y": cur_frame_y}

        curves[index] = {"current_frame": values}

    global_values[obj.name] = curves


def update_blend_range(self, context):
    scene = context.scene
    anim_offset = scene.amp_timeline_tools.anim_offset
    ao_blend_range = anim_offset.ao_blend_range

    if anim_offset.mask_in_use:

        # Calculate new preview range
        new_preview_start = max(scene.frame_start - ao_blend_range, 0)  # Ensure it doesn't go below 0
        new_preview_end = scene.frame_end + ao_blend_range

        # Set the new preview range
        scene.use_preview_range = True
        scene.frame_preview_start = new_preview_start
        scene.frame_preview_end = new_preview_end

        set_blend_values(context)


def update_mask_range(self, context):
    scene = context.scene
    anim_offset = scene.amp_timeline_tools.anim_offset
    ao_mask_range = anim_offset.ao_mask_range
    reference_frame = anim_offset.reference_frame

    if anim_offset.mask_in_use:

        # Calculate new preview range
        new_frame_start = max(reference_frame - ao_mask_range, 0)  # Ensure it doesn't go below 0
        new_frame_end = reference_frame + ao_mask_range

        scene.frame_start = new_frame_start
        scene.frame_end = new_frame_end
        # set_blend_values(context)

        update_blend_range(self, context)


def autokeying_changed_anim_offset(*args):
    context = bpy.context
    scene = bpy.context.scene
    anim_offset = scene.amp_timeline_tools.anim_offset

    if scene.tool_settings.use_keyframe_insert_auto:

        # bpy.ops.anim.amp_deactivate_anim_offset
        if magnet_handlers in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.remove(magnet_handlers)
            utils.remove_message()

        scene = context.scene
        anim_offset = scene.amp_timeline_tools.anim_offset

        if anim_offset.mask_in_use:
            remove_mask(context)
            reset_timeline_mask(context)

        # scene.tool_settings.use_keyframe_insert_auto = anim_offset.user_scene_auto

        for area in bpy.context.screen.areas:
            area.tag_redraw()

        bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)

        utils.amp_draw_header_handler(action="REMOVE")


def subscribe_to_autokeying_changes_anim_offset():
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.ToolSettings, "use_keyframe_insert_auto"),
        owner="AUTOKEYING_ANIM_OFFSET",
        args=(),
        notify=autokeying_changed_anim_offset,
        options={"PERSISTENT"},
    )


def unsubscribe_from_property_anim_offset():
    bpy.msgbus.clear_by_owner("AUTOKEYING_ANIM_OFFSET")
