import bpy
import gpu
import blf
from bpy.types import Scene
from gpu_extras.batch import batch_for_shader
import math
from math import radians
import numpy as np
from ..utils.curve import is_fcurve_in_radians
from ..utils import ensure_alpha, refresh_ui
from ..utils.customIcons import get_icon
from .. import __package__ as base_package

addon_keymaps = []


def draw_gui_help_text(context, x, y):
    """Draw GUI help text in the Graph Editor."""

    prefs = bpy.context.preferences.addons[base_package].preferences

    blf.enable(0, blf.SHADOW)
    blf.shadow(0, 6, 0, 0, 0, 1)
    blf.shadow_offset(0, 2, -2)
    font_id = 0
    blf.size(font_id, 12)

    safe_text_color = ensure_alpha(prefs.text_color)
    blf.color(0, *safe_text_color)

    props = bpy.context.scene.keyframe_lattice_settings

    if prefs.timeline_gui_toggle:

        lines = [
            "______________________",
            "Anim Lattice Help:",
            "______________________",
            "",
            "Drag Control points to scale",
            "",
            "______________________",
            "Snap to Full Frames (F)",
            "______________________",
            "",
            "ESC, Enter, Right Click - Exit",
        ]

        if props.snap_lattice_to_full_frames:
            lines[7] = "Snap to Full Frames (F) - Enabled"
        else:
            lines[7] = "Snap to Full Frames (F) - Disabled"

        for line in reversed(lines):
            text_width, text_height = blf.dimensions(font_id, line)
            blf.position(font_id, x, y, 0)
            blf.draw(font_id, line)
            y += text_height + 5
    else:
        blf.position(0, 20, 30, 0)
        blf.draw(0, "GUI Help (H)")

    blf.disable(0, blf.SHADOW)


class ControlPoint:
    # def __init__(self, index, position, operator, shape="square", section=(0, 0)):

    def __init__(self, index, position, operator, shape="square", section=(0, 0), *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.index = index
        self.position = position
        self.size = 10
        self.is_hovered = False
        self.shape = shape
        self.section = section
        self.operator = operator

    def draw(self):
        cp_color = (1.0, 0.5, 0.0, 1.0) if self.is_hovered else (1.0, 1.0, 1.0, 1.0)
        lcp_color = (1.0, 0.5, 0.0, 1.0) if self.is_hovered else (1.0, 0.5, 0.0, 0.5)
        shader = gpu.shader.from_builtin("UNIFORM_COLOR")
        # Convert position to screen space using operator's method
        screen_pos = self.operator.graph_to_screen(*self.position)
        if self.shape == "circle":
            draw_circle(shader, screen_pos, self.size / 2, cp_color)
        elif self.shape == "rhomboid":
            draw_rhomboid(shader, screen_pos, self.size, lcp_color)
        else:
            half_size = self.size / 2
            x, y = screen_pos
            vertices = [
                (x - half_size, y - half_size),
                (x + half_size, y - half_size),
                (x + half_size, y + half_size),
                (x - half_size, y + half_size),
            ]

            shader = gpu.shader.from_builtin("UNIFORM_COLOR")
            batch = batch_for_shader(shader, "TRI_FAN", {"pos": vertices})
            shader.bind()
            shader.uniform_float("color", cp_color)
            batch.draw(shader)

    def check_hover(self, mouse_x, mouse_y):
        screen_x, screen_y = self.operator.graph_to_screen(*self.position)
        half_size = self.size / 2
        is_now_hovered = (
            screen_x - half_size <= mouse_x <= screen_x + half_size
            and screen_y - half_size <= mouse_y <= screen_y + half_size
        )
        hovered = False

        if is_now_hovered and not self.is_hovered:
            self.is_hovered = True
            bpy.context.window.cursor_set("SCROLL_XY")
            hovered = True
        elif not is_now_hovered and self.is_hovered:
            self.is_hovered = False
            bpy.context.window.cursor_set("DEFAULT")

        return hovered


class LoopControlPoint(ControlPoint):
    # def __init__(
    #     self, index, position, operator, shape="rhomboid", section=(0, 0), orientation="horizontal", associated_cp=None
    # ):
    #     super().__init__(index, position, operator, shape, section)
    def __init__(
        self,
        index,
        position,
        operator,
        shape="rhomboid",
        section=(0, 0),
        orientation="horizontal",
        associated_cp=None,
        *args,
        **kwargs,
    ):
        super().__init__(index, position, operator, shape, section, *args, **kwargs)
        self.orientation = orientation  # 'horizontal' or 'vertical'
        self.associated_cp = associated_cp  # The CP this LCP is associated with
        self.display_distance = self.size * 20  # Display when mouse is within this distance
        self.is_displayed = False

    def draw(self):
        if not self.is_displayed:
            return
        super().draw()

    def check_hover(self, mouse_x, mouse_y):
        # Convert control point position to screen space using operator's method
        screen_x, screen_y = self.operator.graph_to_screen(*self.position)
        half_size = self.size / 2

        # Larger area for displaying the control point
        display_half_size = self.display_distance / 2

        mouse_distance = math.hypot(mouse_x - screen_x, mouse_y - screen_y)
        if mouse_distance <= display_half_size:
            self.is_displayed = True
        else:
            self.is_displayed = False

        if not self.is_displayed:
            self.is_hovered = False
            return False

        # Check hover over the actual control point area
        is_now_hovered = (
            screen_x - half_size <= mouse_x <= screen_x + half_size
            and screen_y - half_size <= mouse_y <= screen_y + half_size
        )
        hovered = False

        if is_now_hovered and not self.is_hovered:
            self.is_hovered = True
            bpy.context.window.cursor_set("SCROLL_XY")
            hovered = True

        elif not is_now_hovered and self.is_hovered:
            self.is_hovered = False
            bpy.context.window.cursor_set("DEFAULT")

        return hovered


class AMP_OT_anim_lattice(bpy.types.Operator):
    bl_idname = "anim.amp_anim_lattice"
    bl_label = "Anim Lattice"
    bl_options = {"REGISTER"}
    bl_description = """Drag control points to scale keyframes proportionally within a bounding box.
Hold Shift to launch with the options panel."""

    snap_lattice_to_full_frames: bpy.props.BoolProperty(
        name="Snap to Full Frames",
        description="Snap keyframe frames to the nearest integer value",
        default=True,
    )
    zoom_out_times: bpy.props.IntProperty(
        name="Zoom Out Times",
        description="Extra zoom out factor when normalization is on",
        default=10,
        min=1,
        max=100,
    )
    # Define padding constants
    VERTICAL_PADDING = 0.0001  # Value
    HORIZONTAL_PADDING = 1  # Frame

    _handle = None
    _is_running = False
    _active_instance = None

    @classmethod
    def poll(cls, context):
        return context.area is not None and context.area.type == "GRAPH_EDITOR"  # and not context.space_data.use_normalization

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        props = bpy.context.scene.keyframe_lattice_settings
        self.current_mode = props.mode
        self.previous_lattice_x = props.lattice_x
        self.previous_lattice_y = props.lattice_y
        self.control_points = []
        self.loop_control_points = []
        self.mouse_x = 0
        self.mouse_y = 0
        self.mouse_graph_x = 0.0
        self.mouse_graph_y = 0.0
        self.dragging_control_point = None
        self.initial_mouse_x = 0
        self.initial_mouse_y = 0
        self.initial_mouse_graph_x = 0.0
        self.initial_mouse_graph_y = 0.0
        self.initial_keyframes = []
        self.initial_bounds = None
        self.initial_control_point_positions = {}
        self.fcurves_to_update = set()
        self.undo_stack = []
        self.context = None
        self.initial_selected_keyframes = []

        # Initialize NumPy arrays
        self.fcurves_array = None
        self.indices_array = None
        self.is_rotation_curve_array = None
        self.initial_co_array = None
        self.initial_handle_left_array = None
        self.initial_handle_right_array = None
        self.relative_co = None
        self.relative_handle_left = None
        self.relative_handle_right = None
        self.relative_co_cell_list = []
        self.relative_handle_left_cell_list = []
        self.relative_handle_right_cell_list = []

        # Checks for normalization on start and end
        self.initial_use_normalization = False
        self.initial_view_settings = {}

    def invoke(self, context, event):
        if event.shift:
            wm = context.window_manager
            return wm.invoke_props_dialog(self)

        return self.execute(context)

    def init_tool(self, context):
        self.context = context

        self.fcurves_to_update = set()

        self.collect_initial_keyframe_data()

        if not len(self.initial_co_array):
            self.report({"WARNING"}, "No keyframes selected")
            return {"CANCELLED"}

        self.initial_bounds = self.get_initial_bounds()
        if not self.initial_bounds:
            self.report({"WARNING"}, "Unable to determine keyframe bounds")
            return {"CANCELLED"}

        self.compute_relative_positions()

        self.init_control_points(context)

        args = (self, context)
        self._handle = bpy.types.SpaceGraphEditor.draw_handler_add(self.draw_callback, args, "WINDOW", "POST_PIXEL")
        context.area.tag_redraw()

        self.push_undo(context)

        return {"RUNNING_MODAL"}

    def graph_to_screen(self, graph_x, graph_y):
        view2d = self.context.region.view2d
        obj = bpy.context.active_object
        # If in NLA tweak mode, do not apply any offset.
        offset = 0 #if (obj.animation_data and obj.animation_data.nla_tweak) else get_nla_strip_offset(obj)
        screen_x, screen_y = view2d.view_to_region(graph_x + offset, graph_y, clip=False)
        return screen_x, screen_y

    def screen_to_graph(self, screen_x, screen_y):
        view2d = self.context.region.view2d
        obj = bpy.context.active_object
        offset = 0 #if (obj.animation_data and obj.animation_data.nla_tweak) else get_nla_strip_offset(obj)
        gx, gy = view2d.region_to_view(screen_x, screen_y)
        return gx - offset, gy

    def push_undo(self, context):
        """Push the current state to the undo stack, including keyframes and control points positions."""
        # Store keyframes state
        co_array = np.zeros_like(self.initial_co_array)
        handle_left_array = np.zeros_like(self.initial_handle_left_array)
        handle_right_array = np.zeros_like(self.initial_handle_right_array)

        for i in range(len(self.indices_array)):
            fcurve = self.fcurves_array[i]
            index = self.indices_array[i]
            is_rotation_curve = self.is_rotation_curve_array[i]
            kf = fcurve.keyframe_points[index]
            x_value = kf.co[0]
            y_value = math.degrees(kf.co[1]) if is_rotation_curve else kf.co[1]
            handle_left_x = kf.handle_left[0]
            handle_left_y = math.degrees(kf.handle_left[1]) if is_rotation_curve else kf.handle_left[1]
            handle_right_x = kf.handle_right[0]
            handle_right_y = math.degrees(kf.handle_right[1]) if is_rotation_curve else kf.handle_right[1]
            co_array[i] = [x_value, y_value]
            handle_left_array[i] = [handle_left_x, handle_left_y]
            handle_right_array[i] = [handle_right_x, handle_right_y]

        # Store control points positions in graph editor space
        control_point_indices = []
        control_point_positions = []

        for cp in self.control_points + self.loop_control_points:
            control_point_indices.append(cp.index)
            control_point_positions.append([cp.position[0], cp.position[1]])

        # Now create the state as a dict of arrays
        state = {
            "co_array": co_array.copy(),
            "handle_left_array": handle_left_array.copy(),
            "handle_right_array": handle_right_array.copy(),
            "control_point_indices": np.array(control_point_indices),
            "control_point_positions": np.array(control_point_positions),
        }

        self.undo_stack.append(state)

        # **Update initial keyframe arrays to reflect the new state**
        self.initial_co_array = co_array.copy()
        self.initial_handle_left_array = handle_left_array.copy()
        self.initial_handle_right_array = handle_right_array.copy()

    def pop_undo(self, context):
        """Pop the last state from the undo stack and restore keyframes and control points."""
        # If there's only one state in the stack, we can't undo further
        if len(self.undo_stack) < 2:
            self.report({"INFO"}, "Nothing to undo")
            return

        # Pop the last state
        self.undo_stack.pop()
        # Now the previous state is the one to restore
        state = self.undo_stack[-1]

        # Restore keyframes
        co_array = state["co_array"]
        handle_left_array = state["handle_left_array"]
        handle_right_array = state["handle_right_array"]

        for i in range(len(self.indices_array)):
            fcurve = self.fcurves_array[i]
            index = self.indices_array[i]
            is_rotation_curve = self.is_rotation_curve_array[i]
            kf = fcurve.keyframe_points[index]
            kf.co[0] = co_array[i][0]
            kf.co[1] = radians(co_array[i][1]) if is_rotation_curve else co_array[i][1]
            kf.handle_left[0] = handle_left_array[i][0]
            kf.handle_left[1] = radians(handle_left_array[i][1]) if is_rotation_curve else handle_left_array[i][1]
            kf.handle_right[0] = handle_right_array[i][0]
            kf.handle_right[1] = radians(handle_right_array[i][1]) if is_rotation_curve else handle_right_array[i][1]

        # Restore control points
        control_point_indices = state["control_point_indices"]
        control_point_positions = state["control_point_positions"]
        for idx, pos in zip(control_point_indices, control_point_positions):
            cp = next((cp for cp in self.control_points + self.loop_control_points if cp.index == idx), None)
            if cp:
                cp.position = (pos[0], pos[1])

        # Update initial keyframe arrays to reflect restored state
        self.initial_co_array = co_array.copy()
        self.initial_handle_left_array = handle_left_array.copy()
        self.initial_handle_right_array = handle_right_array.copy()

        # Update initial bounds and recompute relative positions
        self.initial_bounds = self.get_initial_bounds()
        self.compute_relative_positions()

        # Trigger UI redraw
        context.area.tag_redraw()

    def restore_from_buffer(self, context):
        """Restore control points positions from the latest undo buffer in graph editor space."""
        if not self.undo_stack:
            return
        latest_state = self.undo_stack[-1]
        control_point_indices = latest_state["control_point_indices"]
        control_point_positions = latest_state["control_point_positions"]

        for idx, pos in zip(control_point_indices, control_point_positions):
            cp = next((cp for cp in self.control_points if cp.index == idx), None)
            if cp:
                cp.position = (pos[0], pos[1])
        # Force redraw to reflect changes
        context.area.tag_redraw()

    def init_control_points(self, context):
        min_x, max_x, min_y, max_y = self.initial_bounds
        props = bpy.context.scene.keyframe_lattice_settings
        lattice_x = props.lattice_x
        lattice_y = props.lattice_y

        self.control_points = []
        self.loop_control_points = []

        if props.mode == "WARP":
            # Create grid based on lattice_x and lattice_y
            index_counter = 0
            for row in range(lattice_y + 1):
                for col in range(lattice_x + 1):

                    # Calculate normalized positions
                    u = col / lattice_x if lattice_x != 0 else 0.0
                    v = row / lattice_y if lattice_y != 0 else 0.0

                    # Calculate graph positions
                    x = min_x + u * (max_x - min_x)
                    y = min_y + v * (max_y - min_y)
                    index = index_counter
                    index_counter += 1
                    self.control_points.append(ControlPoint(index, (x, y), self, shape="circle", section=(row, col)))

            # Create LoopControlPoints outside the grid with fixed screen space offset
            lcp_index_counter = 1000  # Start index after all control points
            offset_pixels = 20  # Fixed offset in screen space (pixels)

            # Precompute the offset in graph space for horizontal and vertical LCPs
            # We'll use average scaling for simplicity.
            avg_scale_x = (max_x - min_x) / context.region.width
            avg_scale_y = (max_y - min_y) / context.region.height

            # Loop through each CP to create associated LCPs
            for row in range(lattice_y + 1):
                for col in range(lattice_x + 1):
                    cp = self.control_points[row * (lattice_x + 1) + col]
                    cp_x, cp_y = cp.position

                    # Convert CP position to screen space
                    screen_x, screen_y = self.graph_to_screen(cp_x, cp_y)

                    # Left LCPs
                    if col == 0:
                        # Left edge, create LCP to the left
                        lcp_screen_x = screen_x - offset_pixels
                        lcp_screen_y = screen_y
                        lcp_x, lcp_y = self.screen_to_graph(lcp_screen_x, lcp_screen_y)
                        index = lcp_index_counter
                        lcp_index_counter += 1
                        self.loop_control_points.append(
                            LoopControlPoint(
                                index,
                                (lcp_x, lcp_y),
                                self,
                                orientation="horizontal",
                                section=("row", row),
                                associated_cp=cp,
                            )
                        )
                    # Right LCPs
                    if col == lattice_x:
                        # Right edge, create LCP to the right
                        lcp_screen_x = screen_x + offset_pixels
                        lcp_screen_y = screen_y
                        lcp_x, lcp_y = self.screen_to_graph(lcp_screen_x, lcp_screen_y)
                        index = lcp_index_counter
                        lcp_index_counter += 1
                        self.loop_control_points.append(
                            LoopControlPoint(
                                index,
                                (lcp_x, lcp_y),
                                self,
                                orientation="horizontal",
                                section=("row", row),
                                associated_cp=cp,
                            )
                        )

                    # Bottom LCPs
                    if row == 0:
                        # Bottom edge, create LCP below
                        lcp_screen_x = screen_x
                        lcp_screen_y = screen_y - offset_pixels
                        lcp_x, lcp_y = self.screen_to_graph(lcp_screen_x, lcp_screen_y)
                        index = lcp_index_counter
                        lcp_index_counter += 1
                        self.loop_control_points.append(
                            LoopControlPoint(
                                index,
                                (lcp_x, lcp_y),
                                self,
                                orientation="vertical",
                                section=("col", col),
                                associated_cp=cp,
                            )
                        )
                    # Top LCPs
                    if row == lattice_y:
                        # Top edge, create LCP above
                        lcp_screen_x = screen_x
                        lcp_screen_y = screen_y + offset_pixels
                        lcp_x, lcp_y = self.screen_to_graph(lcp_screen_x, lcp_screen_y)
                        index = lcp_index_counter
                        lcp_index_counter += 1
                        self.loop_control_points.append(
                            LoopControlPoint(
                                index,
                                (lcp_x, lcp_y),
                                self,
                                orientation="vertical",
                                section=("col", col),
                                associated_cp=cp,
                            )
                        )
        else:
            # Existing normal mode control points
            positions = [
                (0, (min_x, min_y)),  # Bottom-left corner
                (1, (max_x, min_y)),  # Bottom-right corner
                (2, (max_x, max_y)),  # Top-right corner
                (3, (min_x, max_y)),  # Top-left corner
                (4, ((min_x + max_x) / 2, min_y)),  # Midpoint of bottom edge
                (5, (max_x, (min_y + max_y) / 2)),  # Midpoint of right edge
                (6, ((min_x + max_x) / 2, max_y)),  # Midpoint of top edge
                (7, (min_x, (min_y + max_y) / 2)),  # Midpoint of left edge
            ]
            self.control_points = [ControlPoint(index, pos, self) for index, pos in positions]

    def modal(self, context, event):
        if not self._is_running:
            return self.cancel(context)

        props = bpy.context.scene.keyframe_lattice_settings
        current_mode = props.mode
        screen = context.screen

        if current_mode != self.current_mode or (
            current_mode == "WARP"
            and (props.lattice_x != self.previous_lattice_x or props.lattice_y != self.previous_lattice_y)
        ):
            self.current_mode = current_mode
            self.undo_stack.clear()
            self.initial_bounds = self.get_initial_bounds()
            if not self.initial_bounds:
                self.report({"WARNING"}, "Unable to determine keyframe bounds after mode change")
                return {"CANCELLED"}
            self.compute_relative_positions()
            self.init_control_points(context)
            self.push_undo(context)
            context.area.tag_redraw()

        if event.type == "ESC" and event.value == "PRESS" and screen.is_animation_playing:
            bpy.ops.screen.animation_cancel(restore_frame=True)
            return {"RUNNING_MODAL"}

        if (
            event.type in {"ESC", "RET"}
            and event.value == "PRESS"
            or (event.type == "Y" and event.shift and event.value == "PRESS")
        ):
            for fcurve in self.fcurves_to_update:
                fcurve.update()
            return self.cancel(context)

        if event.type == "RIGHTMOUSE" and event.value == "PRESS":
            bpy.ops.wm.call_panel(name="AMP_PT_AnimLatticeOptions", keep_open=True)
            context.window.cursor_modal_set("DEFAULT")
            return {"RUNNING_MODAL"}

        if event.type == "MOUSEMOVE":

            if (
                not self.context
                or not getattr(self.context, "region", None)
                or not getattr(self.context.region, "view2d", None)
            ):
                return self.cancel(context)
            self.mouse_x = event.mouse_region_x
            self.mouse_y = event.mouse_region_y
            self.mouse_graph_x, self.mouse_graph_y = self.screen_to_graph(self.mouse_x, self.mouse_y)
            if self.dragging_control_point is not None:
                self.handle_mouse_move_drag(context, event)
            else:
                self.handle_mouse_move_hover(context, event)
            context.area.tag_redraw()
            return {"PASS_THROUGH"}

        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            for cp in self.control_points + self.loop_control_points:
                if cp.is_hovered:
                    context.window.cursor_set("SCROLL_XY")
                    self.dragging_control_point = cp.index
                    self.initial_mouse_x = event.mouse_region_x
                    self.initial_mouse_y = event.mouse_region_y
                    self.initial_mouse_graph_x, self.initial_mouse_graph_y = self.screen_to_graph(
                        self.initial_mouse_x, self.initial_mouse_y
                    )
                    self.initial_control_point_positions = {
                        cp_.index: cp_.position for cp_ in self.control_points + self.loop_control_points
                    }
            context.area.tag_redraw()
            return {"RUNNING_MODAL"}

        if event.type == "LEFTMOUSE" and event.value == "RELEASE":
            context.window.cursor_set("DEFAULT")
            if self.dragging_control_point is not None:
                if not props.snap_lattice_to_full_frames:
                    for fcurve in self.fcurves_to_update:
                        fcurve.update()
                self.dragging_control_point = None
                self.push_undo(context)
                if props.mode != "WARP":
                    self.initial_bounds = self.get_initial_bounds()
                    self.compute_relative_positions()
                context.area.tag_redraw()
            return {"RUNNING_MODAL"}

        if event.type == "F" and event.value == "PRESS":
            props.snap_lattice_to_full_frames = not props.snap_lattice_to_full_frames
            context.area.tag_redraw()
            return {"RUNNING_MODAL"}

        if event.type == "H" and event.value == "PRESS":
            prefs = bpy.context.preferences.addons[base_package].preferences
            prefs.timeline_gui_toggle = not prefs.timeline_gui_toggle
            context.area.tag_redraw()
            return {"RUNNING_MODAL"}

        if (event.type == "Z" and (event.ctrl or event.oskey)) and event.value == "PRESS":
            self.pop_undo(context)
            context.area.tag_redraw()
            return {"RUNNING_MODAL"}

        self.previous_lattice_x = props.lattice_x
        self.previous_lattice_y = props.lattice_y

        context.area.tag_redraw()
        return {"PASS_THROUGH"}

    def handle_mouse_move_hover(self, context, event):
        hovered_any = False
        for cp in self.control_points + self.loop_control_points:
            if cp.check_hover(self.mouse_x, self.mouse_y):
                hovered_any = True

    def handle_mouse_move_drag(self, context, event):
        cp = next(
            (cp_ for cp_ in self.control_points + self.loop_control_points if cp_.index == self.dragging_control_point),
            None,
        )
        if not cp:
            return

        props = bpy.context.scene.keyframe_lattice_settings
        delta_x = self.mouse_graph_x - self.initial_mouse_graph_x
        delta_y = self.mouse_graph_y - self.initial_mouse_graph_y
        lock_active = event.shift or props.lock_direction

        if lock_active and props.mode == "WARP":
            dx = self.mouse_x - self.initial_mouse_x
            dy = self.mouse_y - self.initial_mouse_y
            if abs(dx) > abs(dy):
                delta_y = 0
            else:
                delta_x = 0

        if props.mode == "WARP":
            self.handle_drag_warp(cp, delta_x, delta_y)
        else:
            self.handle_drag_normal(cp, delta_x, delta_y)

        self.update_bounding_box_and_keyframes(context)

    def handle_drag_warp(self, cp, delta_x, delta_y):
        props = bpy.context.scene.keyframe_lattice_settings
        if isinstance(cp, LoopControlPoint):
            if cp.orientation == "vertical":
                col = cp.section[1]
                affected = [p for p in self.control_points if p.section[1] == col]
            else:
                row = cp.section[1]
                affected = [p for p in self.control_points if p.section[0] == row]
            for p in affected:
                ix, iy = self.initial_control_point_positions[p.index]
                p.position = (ix + delta_x, iy + delta_y)
            for p in affected:
                assoc = [lcp for lcp in self.loop_control_points if lcp.associated_cp == p]
                for lcp in assoc:
                    icp_x, icp_y = self.initial_control_point_positions[p.index]
                    ilcp_x, ilcp_y = self.initial_control_point_positions[lcp.index]
                    ox = ilcp_x - icp_x
                    oy = ilcp_y - icp_y
                    lcp.position = (p.position[0] + ox, p.position[1] + oy)
        else:
            ix, iy = self.initial_control_point_positions[cp.index]
            cp.position = (ix + delta_x, iy + delta_y)
            assoc = [lcp for lcp in self.loop_control_points if lcp.associated_cp == cp]
            for lcp in assoc:
                icp_x, icp_y = self.initial_control_point_positions[cp.index]
                ilcp_x, ilcp_y = self.initial_control_point_positions[lcp.index]
                ox = ilcp_x - icp_x
                oy = ilcp_y - icp_y
                lcp.position = (cp.position[0] + ox, cp.position[1] + oy)

    def handle_drag_normal(self, cp, delta_x, delta_y):
        ix, iy = self.initial_control_point_positions[cp.index]
        cp.position = (ix + delta_x, iy + delta_y)
        assoc = [lcp for lcp in self.loop_control_points if lcp.associated_cp == cp]
        for lcp in assoc:
            icp_x, icp_y = self.initial_control_point_positions[cp.index]
            ilcp_x, ilcp_y = self.initial_control_point_positions[lcp.index]
            ox = ilcp_x - icp_x
            oy = ilcp_y - icp_y
            lcp.position = (cp.position[0] + ox, cp.position[1] + oy)

    def execute(self, context):
        if not self.__class__._is_running:

            self.initial_use_normalization = context.space_data.use_normalization
            if self.initial_use_normalization:
                context.space_data.use_normalization = False

                # Zoom out to fit all keyframes in the view
                bpy.ops.graph.view_selected()

                for _ in range(self.zoom_out_times):
                    bpy.ops.view2d.zoom_out()

            result = self.init_tool(context)
            if result == {"CANCELLED"}:
                self.cancel(context)
                return {"CANCELLED"}
            context.window_manager.modal_handler_add(self)
            self.__class__._is_running = True
            self.__class__._active_instance = self
            return {"RUNNING_MODAL"}
        else:
            # Operator is already running, cancel it
            active = self.__class__._active_instance
            if active is not None and active is not self:
                return active.cancel(context)
            return self.cancel(context)

    def cancel(self, context):
        if self.initial_use_normalization:
            context.space_data.use_normalization = True

        self.__class__._is_running = False
        self.__class__._active_instance = None
        if self._handle is not None:
            try:
                bpy.types.SpaceGraphEditor.draw_handler_remove(self._handle, "WINDOW")
            except ValueError:
                pass
            self._handle = None

        if context.area:
            context.area.tag_redraw()
        return {"CANCELLED"}

    def draw(self, context):
        layout = self.layout
        props = bpy.context.scene.keyframe_lattice_settings
        layout.prop(props, "mode", text="Mode")
        if props.mode == "WARP":
            layout.prop(props, "lattice_x", text="Columns")
            layout.prop(props, "lattice_y", text="Rows")
        layout.prop(props, "snap_lattice_to_full_frames", text="Snap to Full Frames")
        layout.prop(props, "lock_direction", text="Lock Direction")

    def draw_callback(self, _self, context):
        props = bpy.context.scene.keyframe_lattice_settings
        shader = gpu.shader.from_builtin("UNIFORM_COLOR")
        gpu.state.blend_set("ALPHA")

        if props.mode == "WARP":
            lattice_x = props.lattice_x
            lattice_y = props.lattice_y
            min_x, max_x, min_y, max_y = self.initial_bounds

            cp_positions = {cp.index: cp.position for cp in self.control_points}

            # Draw vertical and horizontal grid lines
            for row in range(lattice_y + 1):
                for col in range(lattice_x):
                    start_cp_index = row * (lattice_x + 1) + col
                    end_cp_index = row * (lattice_x + 1) + (col + 1)
                    if start_cp_index in cp_positions and end_cp_index in cp_positions:
                        start_pos = self.graph_to_screen(*cp_positions[start_cp_index])
                        end_pos = self.graph_to_screen(*cp_positions[end_cp_index])
                        batch_obj = batch_for_shader(shader, "LINES", {"pos": [start_pos, end_pos]})
                        shader.bind()
                        shader.uniform_float("color", (0.5, 0.5, 0.5, 0.5))
                        batch_obj.draw(shader)

            for col in range(lattice_x + 1):
                for row in range(lattice_y):
                    start_cp_index = row * (lattice_x + 1) + col
                    end_cp_index = (row + 1) * (lattice_x + 1) + col
                    if start_cp_index in cp_positions and end_cp_index in cp_positions:
                        start_pos = self.graph_to_screen(*cp_positions[start_cp_index])
                        end_pos = self.graph_to_screen(*cp_positions[end_cp_index])
                        batch_obj = batch_for_shader(shader, "LINES", {"pos": [start_pos, end_pos]})
                        shader.bind()
                        shader.uniform_float("color", (0.5, 0.5, 0.5, 0.5))
                        batch_obj.draw(shader)

        # Draw the rectangle (bounding box)
        if props.mode != "WARP":
            corner_indices = [0, 1, 2, 3]
            vertices = [
                self.graph_to_screen(*self.control_points[i].position)
                for i in corner_indices
                if i < len(self.control_points)
            ]

            shader.bind()
            shader.uniform_float("color", (1.0, 1.0, 1.0, 1.0))
            batch_obj = batch_for_shader(shader, "LINE_LOOP", {"pos": vertices})
            batch_obj.draw(shader)

        # Draw control points
        for cp in self.control_points + self.loop_control_points:
            cp.draw()

        # Draw help text
        text_x, text_y = 30, 40
        draw_gui_help_text(context, text_x, text_y)

        gpu.state.blend_set("NONE")

    def collect_initial_keyframe_data(self):
        """Collect initial keyframe data and store in NumPy arrays."""
        self.initial_selected_keyframes = []  # Initialize the list
        selected_fcurves = bpy.context.selected_editable_fcurves
        props = bpy.context.scene.keyframe_lattice_settings
        self.fcurves_to_update = set()

        # Lists to collect data before converting to NumPy arrays
        fcurves_list = []
        indices_list = []
        is_rotation_curve_list = []
        initial_co_list = []
        initial_handle_left_list = []
        initial_handle_right_list = []
        relative_co_cell_list = []
        relative_handle_left_cell_list = []
        relative_handle_right_cell_list = []

        for fcurve in selected_fcurves:
            for idx, kf in enumerate(fcurve.keyframe_points):
                if kf.select_control_point:
                    self.fcurves_to_update.add(fcurve)

                    is_rotation_curve = is_fcurve_in_radians(fcurve)

                    if is_rotation_curve:
                        y_value = math.degrees(kf.co[1])
                        handle_left_y = math.degrees(kf.handle_left[1])
                        handle_right_y = math.degrees(kf.handle_right[1])
                    else:
                        y_value = kf.co[1]
                        handle_left_y = kf.handle_left[1]
                        handle_right_y = kf.handle_right[1]

                    fcurves_list.append(fcurve)
                    indices_list.append(idx)
                    is_rotation_curve_list.append(is_rotation_curve)
                    initial_co_list.append([kf.co[0], y_value])
                    initial_handle_left_list.append([kf.handle_left[0], handle_left_y])
                    initial_handle_right_list.append([kf.handle_right[0], handle_right_y])

                    # Initialize relative positions with empty dicts
                    relative_co_cell_list.append({})
                    relative_handle_left_cell_list.append({})
                    relative_handle_right_cell_list.append({})

                    self.initial_selected_keyframes.append(kf)

        # Convert lists to NumPy arrays
        self.fcurves_array = np.array(fcurves_list, dtype=object)
        self.indices_array = np.array(indices_list, dtype=int)
        self.is_rotation_curve_array = np.array(is_rotation_curve_list, dtype=bool)
        self.initial_co_array = np.array(initial_co_list, dtype=float)
        self.initial_handle_left_array = np.array(initial_handle_left_list, dtype=float)
        self.initial_handle_right_array = np.array(initial_handle_right_list, dtype=float)

        # These are lists of dicts; we keep them as is
        self.relative_co_cell_list = relative_co_cell_list
        self.relative_handle_left_cell_list = relative_handle_left_cell_list
        self.relative_handle_right_cell_list = relative_handle_right_cell_list

        # Initialize the list to store relative_keys per keyframe
        self.relative_keys = [None] * len(self.indices_array)

    def restore_initial_selection(self):
        pass

    def compute_relative_positions(self):
        min_x0, max_x0, min_y0, max_y0 = self.initial_bounds
        props = bpy.context.scene.keyframe_lattice_settings
        lattice_x = props.lattice_x
        lattice_y = props.lattice_y

        # Reset relative_keys when recomputing relative positions
        self.relative_keys = [None] * len(self.indices_array)

        if props.mode == "WARP":
            # WARP mode requires per-keyframe computations
            for i in range(len(self.indices_array)):
                init_x, init_y = self.initial_co_array[i]
                init_handle_left_x, init_handle_left_y = self.initial_handle_left_array[i]
                init_handle_right_x, init_handle_right_y = self.initial_handle_right_array[i]

                if lattice_x == 0 or lattice_y == 0:
                    # Avoid division by zero
                    continue

                # Determine which cell the keyframe belongs to
                col = min(int((init_x - min_x0) / (max_x0 - min_x0) * lattice_x), lattice_x - 1)
                row = min(int((init_y - min_y0) / (max_y0 - min_y0) * lattice_y), lattice_y - 1)

                # Calculate cell boundaries
                cell_min_x = min_x0 + (col / lattice_x) * (max_x0 - min_x0)
                cell_max_x = min_x0 + ((col + 1) / lattice_x) * (max_x0 - min_x0)
                cell_min_y = min_y0 + (row / lattice_y) * (max_y0 - min_y0)
                cell_max_y = min_y0 + ((row + 1) / lattice_y) * (max_y0 - min_y0)

                # Compute relative positions within the cell
                u = (init_x - cell_min_x) / (cell_max_x - cell_min_x) if cell_max_x != cell_min_x else 0.0
                v = (init_y - cell_min_y) / (cell_max_y - cell_min_y) if cell_max_y != cell_min_y else 0.0

                handle_left_u = (
                    (init_handle_left_x - cell_min_x) / (cell_max_x - cell_min_x) if cell_max_x != cell_min_x else 0.0
                )
                handle_left_v = (
                    (init_handle_left_y - cell_min_y) / (cell_max_y - cell_min_y) if cell_max_y != cell_min_y else 0.0
                )

                handle_right_u = (
                    (init_handle_right_x - cell_min_x) / (cell_max_x - cell_min_x) if cell_max_x != cell_min_x else 0.0
                )
                handle_right_v = (
                    (init_handle_right_y - cell_min_y) / (cell_max_y - cell_min_y) if cell_max_y != cell_min_y else 0.0
                )

                # Store relative positions in the lists
                self.relative_co_cell_list[i][(row, col)] = (u, v)
                self.relative_handle_left_cell_list[i][(row, col)] = (handle_left_u, handle_left_v)
                self.relative_handle_right_cell_list[i][(row, col)] = (handle_right_u, handle_right_v)
        else:
            # NORMAL mode
            denom_x = max_x0 - min_x0
            denom_y = max_y0 - min_y0

            if denom_x == 0:
                u_array = np.zeros(len(self.indices_array))
                handle_left_u_array = np.zeros(len(self.indices_array))
                handle_right_u_array = np.zeros(len(self.indices_array))
            else:
                u_array = (self.initial_co_array[:, 0] - min_x0) / denom_x
                handle_left_u_array = (self.initial_handle_left_array[:, 0] - min_x0) / denom_x
                handle_right_u_array = (self.initial_handle_right_array[:, 0] - min_x0) / denom_x

            if denom_y == 0:
                v_array = np.zeros(len(self.indices_array))
                handle_left_v_array = np.zeros(len(self.indices_array))
                handle_right_v_array = np.zeros(len(self.indices_array))
            else:
                v_array = (self.initial_co_array[:, 1] - min_y0) / denom_y
                handle_left_v_array = (self.initial_handle_left_array[:, 1] - min_y0) / denom_y
                handle_right_v_array = (self.initial_handle_right_array[:, 1] - min_y0) / denom_y

            # Store relative positions
            self.relative_co = np.column_stack((u_array, v_array))
            self.relative_handle_left = np.column_stack((handle_left_u_array, handle_left_v_array))
            self.relative_handle_right = np.column_stack((handle_right_u_array, handle_right_v_array))

    def get_initial_bounds(self):
        if len(self.initial_co_array) == 0:
            return None
        min_x = np.min(self.initial_co_array[:, 0])
        max_x = np.max(self.initial_co_array[:, 0])
        min_y = np.min(self.initial_co_array[:, 1])
        max_y = np.max(self.initial_co_array[:, 1])
        return min_x, max_x, min_y, max_y

    def update_bounding_box_and_keyframes(self, context):
        if self.dragging_control_point is None:
            return

        # Get initial bounds
        min_x0, max_x0, min_y0, max_y0 = self.initial_bounds
        props = bpy.context.scene.keyframe_lattice_settings

        # Get the positions of the control points
        cp_positions = {cp.index: cp.position for cp in self.control_points}

        if props.mode == "WARP":
            # Handle grid-based warp without clamping to initial bounds
            lattice_x = props.lattice_x
            lattice_y = props.lattice_y

            # Ensure lattice_x and lattice_y are greater than 0 to avoid division by zero
            if lattice_x == 0 or lattice_y == 0:
                self.report({"ERROR"}, "Lattice divisions must be greater than 0 in WARP mode.")
                return

            # Iterate over each keyframe to update its position based on control points
            for i in range(len(self.indices_array)):
                fcurve = self.fcurves_array[i]
                index = self.indices_array[i]
                kf = fcurve.keyframe_points[index]
                is_rotation_curve = self.is_rotation_curve_array[i]

                # Determine which cell the keyframe belongs to based on initial relative positions
                relative_key = self.relative_keys[i]
                if relative_key is None:
                    # Calculate relative cell based on initial positions
                    init_x, init_y = self.initial_co_array[i]
                    col = min(
                        int(
                            (init_x - self.initial_bounds[0])
                            / (self.initial_bounds[1] - self.initial_bounds[0])
                            * lattice_x
                        ),
                        lattice_x - 1,
                    )
                    row = min(
                        int(
                            (init_y - self.initial_bounds[2])
                            / (self.initial_bounds[3] - self.initial_bounds[2])
                            * lattice_y
                        ),
                        lattice_y - 1,
                    )
                    relative_key = (row, col)
                    self.relative_keys[i] = relative_key  # Cache for future use

                if relative_key not in self.relative_co_cell_list[i]:
                    self.report(
                        {"WARNING"},
                        f"Keyframe at index {index} missing relative position in cell {relative_key}.",
                    )
                    continue  # Skip if relative positions are missing

                u, v = self.relative_co_cell_list[i][relative_key]
                handle_left_u, handle_left_v = self.relative_handle_left_cell_list[i][relative_key]
                handle_right_u, handle_right_v = self.relative_handle_right_cell_list[i][relative_key]

                row, col = relative_key

                # Get current positions of the four control points defining the cell
                try:
                    Q00 = cp_positions[row * (lattice_x + 1) + col]
                    Q10 = cp_positions[row * (lattice_x + 1) + (col + 1)]
                    Q11 = cp_positions[(row + 1) * (lattice_x + 1) + (col + 1)]
                    Q01 = cp_positions[(row + 1) * (lattice_x + 1) + col]
                except KeyError:
                    self.report({"ERROR"}, f"Missing control point for cell ({row}, {col}).")
                    continue  # Skip this cell

                # Compute new position in quadrilateral for keyframe based on current control points
                new_x = (1 - u) * (1 - v) * Q00[0] + u * (1 - v) * Q10[0] + u * v * Q11[0] + (1 - u) * v * Q01[0]
                new_y = (1 - u) * (1 - v) * Q00[1] + u * (1 - v) * Q10[1] + u * v * Q11[1] + (1 - u) * v * Q01[1]

                # Compute new positions for handles
                new_handle_left_x = (
                    (1 - handle_left_u) * (1 - handle_left_v) * Q00[0]
                    + handle_left_u * (1 - handle_left_v) * Q10[0]
                    + handle_left_u * handle_left_v * Q11[0]
                    + (1 - handle_left_u) * handle_left_v * Q01[0]
                )
                new_handle_left_y = (
                    (1 - handle_left_u) * (1 - handle_left_v) * Q00[1]
                    + handle_left_u * (1 - handle_left_v) * Q10[1]
                    + handle_left_u * handle_left_v * Q11[1]
                    + (1 - handle_left_u) * handle_left_v * Q01[1]
                )

                new_handle_right_x = (
                    (1 - handle_right_u) * (1 - handle_right_v) * Q00[0]
                    + handle_right_u * (1 - handle_right_v) * Q10[0]
                    + handle_right_u * handle_right_v * Q11[0]
                    + (1 - handle_right_u) * handle_right_v * Q01[0]
                )
                new_handle_right_y = (
                    (1 - handle_right_u) * (1 - handle_right_v) * Q00[1]
                    + handle_right_u * (1 - handle_right_v) * Q10[1]
                    + handle_right_u * handle_right_v * Q11[1]
                    + (1 - handle_right_u) * handle_right_v * Q01[1]
                )

                if props.snap_lattice_to_full_frames:
                    new_x = round(new_x)
                    new_handle_left_x = round(new_handle_left_x)
                    new_handle_right_x = round(new_handle_right_x)

                # Set new positions
                kf.co[0] = new_x
                kf.co[1] = radians(new_y) if is_rotation_curve else new_y

                kf.handle_left[0] = new_handle_left_x
                kf.handle_left[1] = radians(new_handle_left_y) if is_rotation_curve else new_handle_left_y

                kf.handle_right[0] = new_handle_right_x
                kf.handle_right[1] = radians(new_handle_right_y) if is_rotation_curve else new_handle_right_y

        else:
            # Handle NORMAL mode
            cp_positions = {cp.index: cp.position for cp in self.control_points}

            # Determine which bounds to update based on the dragged control point
            min_x, max_x, min_y, max_y = min_x0, max_x0, min_y0, max_y0

            if self.dragging_control_point in [1, 2, 5]:  # Right side
                max_x = cp_positions[self.dragging_control_point][0]
            if self.dragging_control_point in [2, 3, 6]:  # Top side
                max_y = cp_positions[self.dragging_control_point][1]
            if self.dragging_control_point in [0, 3, 7]:  # Left side
                min_x = cp_positions[self.dragging_control_point][0]
            if self.dragging_control_point in [0, 1, 4]:  # Bottom side
                min_y = cp_positions[self.dragging_control_point][1]

            # Apply clamping based on padding
            if max_x - min_x < self.HORIZONTAL_PADDING:
                if self.dragging_control_point in [0, 7]:  # Left side being dragged
                    min_x = max_x - self.HORIZONTAL_PADDING
                elif self.dragging_control_point in [1, 2, 5]:  # Right side being dragged
                    max_x = min_x + self.HORIZONTAL_PADDING

            if max_y - min_y < self.VERTICAL_PADDING:
                if self.dragging_control_point in [0, 1, 4]:  # Bottom side being dragged
                    min_y = max_y - self.VERTICAL_PADDING
                elif self.dragging_control_point in [2, 3, 6]:  # Top side being dragged
                    max_y = min_y + self.VERTICAL_PADDING

            if max_x == min_x:
                max_x += 0.0001
            if max_y == min_y:
                max_y += 0.0001

            denom_x = max_x - min_x
            denom_y = max_y - min_y

            new_x_array = min_x + self.relative_co[:, 0] * denom_x
            new_y_array = min_y + self.relative_co[:, 1] * denom_y

            new_handle_left_x_array = min_x + self.relative_handle_left[:, 0] * denom_x
            new_handle_left_y_array = min_y + self.relative_handle_left[:, 1] * denom_y

            new_handle_right_x_array = min_x + self.relative_handle_right[:, 0] * denom_x
            new_handle_right_y_array = min_y + self.relative_handle_right[:, 1] * denom_y

            if props.snap_lattice_to_full_frames:
                new_x_array = np.round(new_x_array)
                new_handle_left_x_array = np.round(new_handle_left_x_array)
                new_handle_right_x_array = np.round(new_handle_right_x_array)

            for i in range(len(self.indices_array)):
                fcurve = self.fcurves_array[i]
                index = self.indices_array[i]
                kf = fcurve.keyframe_points[index]
                is_rotation_curve = self.is_rotation_curve_array[i]

                kf.co[0] = new_x_array[i]
                kf.co[1] = radians(new_y_array[i]) if is_rotation_curve else new_y_array[i]

                kf.handle_left[0] = new_handle_left_x_array[i]
                kf.handle_left[1] = (
                    radians(new_handle_left_y_array[i]) if is_rotation_curve else new_handle_left_y_array[i]
                )

                kf.handle_right[0] = new_handle_right_x_array[i]
                kf.handle_right[1] = (
                    radians(new_handle_right_y_array[i]) if is_rotation_curve else new_handle_right_y_array[i]
                )

            positions = {
                0: (min_x, min_y),
                1: (max_x, min_y),
                2: (max_x, max_y),
                3: (min_x, max_y),
                4: ((min_x + max_x) / 2, min_y),
                5: (max_x, (min_y + max_y) / 2),
                6: ((min_x + max_x) / 2, max_y),
                7: (min_x, (min_y + max_y) / 2),
            }

            for cp in self.control_points:
                if cp.index != self.dragging_control_point:
                    cp.position = positions.get(cp.index, cp.position)


class AMP_PG_AnimLatticeSettings(bpy.types.PropertyGroup):
    snap_lattice_to_full_frames: bpy.props.BoolProperty(
        name="Snap to Full Frames",
        description="Snap keyframe frames to the nearest integer value",
        default=True,
    )

    display_values: bpy.props.BoolProperty(
        name="Display Values",
        description="Display the values of the control points",
        default=False,
    )

    mode: bpy.props.EnumProperty(
        name="Mode",
        description="Mode of the lattice",
        items=(
            ("NORMAL", "Normal", "Normal mode"),
            ("WARP", "Warp", "Warp mode"),
        ),
        default="NORMAL",
    )

    lattice_x: bpy.props.IntProperty(
        name="Lattice X",
        description="Number of divisions in the X-axis",
        default=1,
        min=1,
        max=10,
    )

    lattice_y: bpy.props.IntProperty(
        name="Lattice Y",
        description="Number of divisions in the Y-axis",
        default=1,
        min=1,
        max=10,
    )

    lock_direction: bpy.props.BoolProperty(
        name="Lock Direction",
        description="Lock control point movement to the dominant axis (X or Y)",
        default=False,
    )


class AMP_PT_AnimLatticeOptions(bpy.types.Panel):
    bl_label = ""
    bl_idname = "AMP_PT_AnimLatticeOptions"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_context = ""
    bl_ui_units_x = 20

    def draw(self, context):
        layout = self.layout
        props = context.scene.keyframe_lattice_settings

        layout.use_property_split = True
        layout.use_property_decorate = False

        layout.label(text="Anim Lattice Options", icon="MOD_LATTICE")

        ui_column = layout.column()
        ui_column.separator(factor=2)

        box = ui_column.box()
        container = box.column(align=False)

        container.prop(props, "snap_lattice_to_full_frames", text="Snap to full frames")
        container.prop(props, "display_values", text="Display values")

        container.separator()

        mode_container = container.column()
        mode_container.prop(props, "mode", text="Mode")

        lattice_container = container.column()
        lattice_container.active = True if props.mode == "WARP" else False
        lattice_container.prop(props, "lock_direction", text="Lock Direction")
        lattice_container.prop(props, "lattice_x", text="Lattice X")
        lattice_container.prop(props, "lattice_y", text="Lattice Y")


def draw_circle(shader, center, radius, color, num_segments=16):
    from math import pi, cos, sin

    vertices = []
    for i in range(num_segments + 1):
        angle = 2 * pi * i / num_segments
        x = center[0] + cos(angle) * radius
        y = center[1] + sin(angle) * radius
        vertices.append((x, y))
    batch = batch_for_shader(shader, "TRI_FAN", {"pos": vertices})
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)


def draw_rhomboid(shader, center, size, color):
    """
    Draws a rhombus centered at 'center' with the given 'size' and 'color' using the provided 'shader'.

    Parameters:
    - shader: The shader program to use for rendering.
    - center: A tuple (x, y) representing the center position of the rhombus.
    - size: The length of the diagonals of the rhombus.
    - color: A tuple or list representing the color (e.g., (r, g, b, a)).
    """
    x, y = center
    half_size = size / 2
    angles = [0, 90, 180, 270]
    vertices = []

    for angle in angles:
        rad = math.radians(angle)
        vx = x + math.cos(rad) * half_size
        vy = y + math.sin(rad) * half_size
        vertices.append((vx, vy))

    vertices.append(vertices[0])

    batch = batch_for_shader(shader, "TRI_FAN", {"pos": vertices})

    shader.bind()
    shader.uniform_float("color", color)

    batch.draw(shader)


classes = (
    AMP_PG_AnimLatticeSettings,
    AMP_OT_anim_lattice,
    AMP_PT_AnimLatticeOptions,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    # Add the property group to the Scene
    Scene.keyframe_lattice_settings = bpy.props.PointerProperty(type=AMP_PG_AnimLatticeSettings)


def unregister():
    # Remove the property group from the Scene
    del Scene.keyframe_lattice_settings

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
