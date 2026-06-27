import bpy
from bpy.props import IntProperty, EnumProperty
from bpy.types import Operator, Panel, PropertyGroup
from .. import utils
import math
import numpy as np


class AnimNudgerSettings(PropertyGroup):
    frames_to_nudge: IntProperty(
        name="Frames to Nudge",
        description="Number of frames to nudge the keyframes",
        default=1,
        min=1,
        max=1000,
        options={"HIDDEN"},
    )


class AMP_OT_anim_nudger(Operator):
    bl_idname = "anim.timeline_anim_nudger"
    bl_label = "Anim Nudger"
    bl_options = {"REGISTER", "UNDO"}
    bl_description = """Nudge keyframes:
- If keyframes are selected, nudge only the selected keyframes.
- If no keyframes are selected, nudge the keyframes on or to the current frame
- Nudge them by the specified number of frames"""

    direction: EnumProperty(
        name="Direction",
        description="Direction to nudge the keyframes",
        items=[
            ("LEFT", "Left", ""),
            ("RIGHT", "Right", ""),
        ],
        default="RIGHT",
    )

    def execute(self, context):
        settings = context.scene.anim_nudger_settings
        frames_to_nudge = settings.frames_to_nudge
        direction = self.direction

        utils.dprint(f"[DEBUG] Executing AnimNudger: Direction={direction}, Frames={frames_to_nudge}")

        editor_type = context.area.type
        if editor_type not in {"GRAPH_EDITOR", "DOPESHEET_EDITOR"}:
            self.report({"INFO"}, "Can only Nudge in Graph Editor or Dope Sheet.")
            return {"CANCELLED"}

        if self.are_keyframes_selected(context):
            self.nudge_selected_keyframes(context, direction, frames_to_nudge)
        else:
            if self.has_keyframes_on_current_frame(context):
                self.move_current_frame_keyframes_and_playhead(context, direction, frames_to_nudge)
            else:
                self.snap_nearest_keyframes(context, direction)

        for fcurve in context.visible_fcurves:
            fcurve.update()

        context.area.tag_redraw()

        return {"FINISHED"}

    def are_keyframes_selected(self, context):
        action = (
            context.active_object.animation_data.action
            if context.active_object and context.active_object.animation_data
            else None
        )
        editor_type = context.area.type
        if not action:
            return False
        fcurves = context.visible_fcurves if editor_type == "GRAPH_EDITOR" else utils.curve.get_active_fcurves_obj(context.active_object)
        for fcurve in fcurves:
            for keyframe in fcurve.keyframe_points:
                if keyframe.select_control_point:
                    return True
        return False

    def get_fcurves_keyframes(self, fcurves, only_selected=False, frame_filter=None):
        all_keyframes = []
        all_handles_left = []
        all_handles_right = []
        refs = []
        fcurve_map = []
        for f in fcurves:
            frames = []
            handles_l = []
            handles_r = []
            key_refs = []
            for k in f.keyframe_points:
                if only_selected and not k.select_control_point:
                    continue
                if frame_filter and not frame_filter(k.co.x):
                    continue
                frames.append(k.co.x)
                handles_l.append(k.handle_left.x)
                handles_r.append(k.handle_right.x)
                key_refs.append(k)
            if frames:
                all_keyframes.append(frames)
                all_handles_left.append(handles_l)
                all_handles_right.append(handles_r)
                refs.append(key_refs)
                fcurve_map.append(f)
        return fcurve_map, refs, all_keyframes, all_handles_left, all_handles_right

    def set_fcurves_keyframes(self, fcurve_map, refs, frames_arr, handles_left_arr, handles_right_arr):
        for f, f_refs, f_frames, f_hl, f_hr in zip(fcurve_map, refs, frames_arr, handles_left_arr, handles_right_arr):
            for k, frame, hl, hr in zip(f_refs, f_frames, f_hl, f_hr):
                old_x = k.co.x
                k.co.x = frame
                k.handle_left.x = hl
                k.handle_right.x = hr
                utils.dprint(f"[DEBUG] Moved keyframe from {old_x} to {k.co.x}")
        if fcurve_map:
            fcurve_map[0].id_data.update_tag()

    def nudge_selected_keyframes(self, context, direction, frames):
        action = (
            context.active_object.animation_data.action
            if context.active_object and context.active_object.animation_data
            else None
        )
        if not action:
            return
        delta = -frames if direction == "LEFT" else frames
        editor_type = context.area.type
        fcurves = context.visible_fcurves
        visible_fcurves = [f for f in fcurves if (editor_type != "GRAPH_EDITOR" or not f.hide)]
        fmap, refs, frames_arr, hl_arr, hr_arr = self.get_fcurves_keyframes(visible_fcurves, only_selected=True)
        if not frames_arr:
            return

        for i in range(len(frames_arr)):
            frames_arr[i] = np.array(frames_arr[i], dtype=float)
            hl_arr[i] = np.array(hl_arr[i], dtype=float)
            hr_arr[i] = np.array(hr_arr[i], dtype=float)
            frames_arr[i] += delta
            hl_arr[i] += delta
            hr_arr[i] += delta

        self.set_fcurves_keyframes(fmap, refs, frames_arr, hl_arr, hr_arr)

    def has_keyframes_on_current_frame(self, context):
        playhead = context.scene.frame_current
        editor_type = context.area.type
        fcurves = context.visible_fcurves
        visible_fcurves = [f for f in fcurves if (editor_type != "GRAPH_EDITOR" or not f.hide)]
        for fcurve in visible_fcurves:
            for keyframe in fcurve.keyframe_points:
                if math.isclose(keyframe.co.x, playhead, abs_tol=0.1):
                    return True
        return False

    def move_current_frame_keyframes_and_playhead(self, context, direction, frames):
        action = (
            context.active_object.animation_data.action
            if context.active_object and context.active_object.animation_data
            else None
        )
        if not action:
            return
        delta = -frames if direction == "LEFT" else frames
        playhead = context.scene.frame_current

        def frame_filter(x):
            return math.isclose(x, playhead, abs_tol=0.1)

        fmap, refs, frames_arr, hl_arr, hr_arr = self.get_fcurves_keyframes(
            context.visible_fcurves, only_selected=False, frame_filter=frame_filter
        )
        for i in range(len(frames_arr)):
            frames_arr[i] = np.array(frames_arr[i], dtype=float)
            hl_arr[i] = np.array(hl_arr[i], dtype=float)
            hr_arr[i] = np.array(hr_arr[i], dtype=float)
            frames_arr[i] += delta
            hl_arr[i] += delta
            hr_arr[i] += delta

        self.set_fcurves_keyframes(fmap, refs, frames_arr, hl_arr, hr_arr)

        new_playhead = playhead + delta
        context.scene.frame_current = new_playhead

    def snap_nearest_keyframes(self, context, direction):
        playhead = context.scene.frame_current
        action = (
            context.active_object.animation_data.action
            if context.active_object and context.active_object.animation_data
            else None
        )
        if not action:
            return

        editor_type = context.area.type
        fcurves = context.visible_fcurves
        visible_fcurves = [f for f in fcurves if (editor_type != "GRAPH_EDITOR" or not f.hide)]

        kfs = []
        for f in visible_fcurves:
            for k in f.keyframe_points:
                kfs.append(k.co.x)
        kfs = sorted(set(kfs))
        if not kfs:
            return

        if direction == "RIGHT":
            nearest = None
            for kf in reversed(kfs):
                if kf < playhead:
                    nearest = kf
                    break
            if nearest is not None:
                self.move_keyframes(context, nearest, playhead)
        else:
            nearest = None
            for kf in kfs:
                if kf > playhead:
                    nearest = kf
                    break
            if nearest is not None:
                self.move_keyframes(context, nearest, playhead)

    def move_keyframes(self, context, from_frame, to_frame):
        action = (
            context.active_object.animation_data.action
            if context.active_object and context.active_object.animation_data
            else None
        )
        if not action:
            return
        delta = to_frame - from_frame

        def frame_filter(x):
            return math.isclose(x, from_frame, abs_tol=0.1)

        fmap, refs, frames_arr, hl_arr, hr_arr = self.get_fcurves_keyframes(
            context.visible_fcurves, frame_filter=frame_filter
        )
        for i in range(len(frames_arr)):
            frames_arr[i] = np.array(frames_arr[i], dtype=float)
            hl_arr[i] = np.array(hl_arr[i], dtype=float)
            hr_arr[i] = np.array(hr_arr[i], dtype=float)
            frames_arr[i] += delta
            hl_arr[i] += delta
            hr_arr[i] += delta

        self.set_fcurves_keyframes(fmap, refs, frames_arr, hl_arr, hr_arr)


class AMP_OT_anim_pusher(Operator):
    bl_idname = "anim.anim_pusher"
    bl_label = "Anim Pusher"
    bl_options = {"REGISTER", "UNDO"}
    bl_description = """Push the keyframes to the left or right of the playhead by 1 frame:
- Adding will shift all keyframes head of the playhead and the and the scene range by 1.
- Removing will shift all keyframes head of the playhead and the scene range by -1.
- If keyframes are present on the current frame, can't remove the in-between frame"""

    operation: EnumProperty(
        name="Operation",
        description="Add or Remove an in-between frame",
        items=[
            ("ADD", "Add", ""),
            ("REMOVE", "Remove", ""),
        ],
        default="ADD",
    )

    def execute(self, context):
        operation = self.operation
        playhead = context.scene.frame_current
        scene = context.scene

        if operation == "ADD":
            self.add_inbetween(context, playhead)
        elif operation == "REMOVE":
            if self.has_keyframes_on_frame(context, playhead):
                self.report({"WARNING"}, "Can't remove in-between with keyframes on the current frame")
                return {"CANCELLED"}
            self.remove_inbetween(context, playhead)

        context.area.tag_redraw()
        return {"FINISHED"}

    def add_inbetween(self, context, playhead):
        for obj in context.selected_objects:
            if not obj.animation_data or not obj.animation_data.action:
                continue
            fcurves = list(utils.curve.get_active_fcurves_obj(obj))
            self.shift_keyframes_numpy(fcurves, playhead, 1)
        context.scene.frame_end += 1

    def remove_inbetween(self, context, playhead):
        for obj in context.selected_objects:
            if not obj.animation_data or not obj.animation_data.action:
                continue
            fcurves = list(utils.curve.get_active_fcurves_obj(obj))
            self.shift_keyframes_numpy(fcurves, playhead, -1, strictly_greater=True)

        if context.scene.frame_end > playhead:
            context.scene.frame_end -= 1

    def has_keyframes_on_frame(self, context, frame):
        # editor_type = context.area.type
        # fcurves = utils.curve.all_fcurves(context.active_object.animation_data.action)
        # visible_fcurves = [f for f in fcurves if (editor_type != "GRAPH_EDITOR" or not f.hide)]
        visible_fcurves = utils.curve.visible_fcurves()
        for fcurve in visible_fcurves:
            for keyframe in fcurve.keyframe_points:
                if math.isclose(keyframe.co.x, frame, abs_tol=0.1):
                    return True
        return False

    def shift_keyframes_numpy(self, fcurves, pivot_frame, delta, strictly_greater=False):
        def frame_filter(x):
            return x > pivot_frame if strictly_greater else x >= pivot_frame

        frames_list = []
        hl_list = []
        hr_list = []
        refs_list = []
        f_map = []
        for f in fcurves:
            frames = []
            hl = []
            hr = []
            refs = []
            for k in f.keyframe_points:
                if frame_filter(k.co.x):
                    frames.append(k.co.x)
                    hl.append(k.handle_left.x)
                    hr.append(k.handle_right.x)
                    refs.append(k)
            if frames:
                frames_list.append(np.array(frames, dtype=float))
                hl_list.append(np.array(hl, dtype=float))
                hr_list.append(np.array(hr, dtype=float))
                refs_list.append(refs)
                f_map.append(f)

        for i in range(len(frames_list)):
            old_frames = frames_list[i].copy()
            frames_list[i] += delta
            hl_list[i] += delta
            hr_list[i] += delta
            for old, new in zip(old_frames, frames_list[i]):
                utils.dprint(f"[DEBUG] Moved keyframe from {old} to {new}")

        for f, r, fr, hl, hr in zip(f_map, refs_list, frames_list, hl_list, hr_list):
            for k, ff, hll, hrr in zip(r, fr, hl, hr):
                k.co.x = ff
                k.handle_left.x = hll
                k.handle_right.x = hrr
            f.id_data.update_tag()


class AnimNudger_PT_Panel(Panel):
    bl_label = "AnimNudger"
    bl_idname = "ANIMNUDGER_PT_panel"
    bl_space_type = "GRAPH_EDITOR"
    bl_region_type = "UI"
    bl_category = "AnimNudger"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.anim_nudger_settings

        row = layout.row(align=True)
        row.operator(
            "anim.timeline_anim_nudger", text="", **utils.customIcons.get_icon("AMP_anim_nudge_L")
        ).direction = "LEFT"
        row.operator(
            "anim.timeline_anim_nudger", text="", **utils.customIcons.get_icon("AMP_anim_nudge_R")
        ).direction = "RIGHT"
        row = row.row(align=True)
        row.prop(settings, "frames_to_nudge", text="Frames")

        layout.separator()

        row = layout.row(align=True)
        row.operator("anim.anim_pusher", text="", **utils.customIcons.get_icon("AMP_inbetweener_ADD")).operation = "ADD"
        row.operator("anim.anim_pusher", text="", **utils.customIcons.get_icon("AMP_inbetweener_REMOVE")).operation = (
            "REMOVE"
        )


classes = (
    AnimNudgerSettings,
    AMP_OT_anim_nudger,
    AMP_OT_anim_pusher,
    # AnimNudger_PT_Panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.anim_nudger_settings = bpy.props.PointerProperty(type=AnimNudgerSettings)
    utils.dprint("AnimNudger addon registered.")


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.anim_nudger_settings
    utils.dprint("AnimNudger addon unregistered.")


if __name__ == "__main__":
    register()
