import bpy
import gpu
import math
from ... import utils
from gpu_extras.presets import draw_circle_2d
from gpu_extras.batch import batch_for_shader
import blf


def screen_to_graph(context, screen_x, screen_y):
    region = context.region
    view2d = region.view2d
    # Convert screen (region) coordinates to graph coordinates (view coordinates)
    view_x, view_y = view2d.region_to_view(screen_x, screen_y)
    return view_x, view_y


def graph_to_screen(context, graph_x, graph_y):
    region = context.region
    view2d = region.view2d
    # Convert graph coordinates (view coordinates) back to screen (region) coordinates
    screen_x, screen_y = view2d.view_to_region(graph_x, graph_y, clip=False)
    return screen_x, screen_y


def get_scale_factors(context):
    region = context.region
    view2d = region.view2d
    bottom_left_view = view2d.region_to_view(0, 0)
    top_right_view = view2d.region_to_view(region.width, region.height)
    view_width_units = top_right_view[0] - bottom_left_view[0]
    view_height_units = top_right_view[1] - bottom_left_view[1]
    scale_x = view_width_units / region.width
    scale_y = view_height_units / region.height
    # utils.dprint(f"Scale X: {scale_x}, Scale Y: {scale_y}")
    # utils.dprint(f"Region Width: {region.width}, Region Height: {region.height}")
    return scale_x, scale_y


class TimeWarpOperator(bpy.types.Operator):
    """Draws a circle on keyframes of the current action"""

    bl_idname = "anim.amp_keyposer_time_warp"
    bl_label = "Time Warp"
    bl_options = {"REGISTER", "UNDO", "BLOCKING"}

    action: bpy.props.EnumProperty(
        items=[("START", "Start", "Start the time warp"), ("FINISH", "Finish", "Finish the time warp")], default="START"
    )

    _timer = None
    _handle = None
    mouse_pos = (0, 0)
    is_dragging = False
    drag_start_mouse_x = 0
    selected_keypose_markers = []
    keypose_markers = []
    has_dragged = False
    drag_threshold = 5

    def _update_selected_keypose_markers_list(self):
        self.selected_keypose_markers = [m for m in self.keypose_markers if m["selected"]]

    def modal(self, context, event):
        context.area.tag_redraw()
        if context.area.type not in {"GRAPH_EDITOR", "DOPESHEET_EDITOR"}:
            return {"PASS_THROUGH"}
        # Check for property to end the modal
        if not context.scene.amp_keyposer_properties.is_time_warper_active:
            self.finish(context)
            return {"CANCELLED"}

        # Update mouse position
        self.mouse_pos = (event.mouse_region_x, event.mouse_region_y)

        modifiers_pressed = event.shift or event.ctrl

        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            # if event.shift or event.ctrl:
            # select_or_deselect_keypose_markers(self, context, self.mouse_pos[0], event)
            self.drag_start_mouse_x = event.mouse_region_x
            self.mouse_pos = (event.mouse_region_x, event.mouse_region_y)
            # Determine if the mouse is over a marker
            if not modifiers_pressed:
                over_marker = self.find_marker_at_pos(context, self.mouse_pos[0])
                if over_marker:
                    if not over_marker["selected"]:
                        # Select the marker if not selected
                        reset_selection(self.keypose_markers)
                        over_marker["selected"] = True
                        self._update_selected_keypose_markers_list()
                    self.is_dragging = True
                else:
                    reset_selection(self.keypose_markers)
                    self._update_selected_keypose_markers_list()

            if not modifiers_pressed and any(m["selected"] for m in self.keypose_markers):

                self.is_dragging = True
                self.drag_start_mouse_x = self.mouse_pos[0]
                # Save original frames for each marker
                for marker in self.keypose_markers:
                    marker["original_frame"] = marker["frame"]

            return {"RUNNING_MODAL"}

        # Handle marker movement during dragging
        # print(f"Dragging: {self.is_dragging}")
        if event.type == "MOUSEMOVE" and self.is_dragging:

            move_selected_keypose_markers(context, self, self.mouse_pos[0])
            dx = abs(event.mouse_region_x - self.drag_start_mouse_x)
            if dx > self.drag_threshold:
                self.has_dragged = True

            return {"RUNNING_MODAL"}

        if event.type == "LEFTMOUSE" and event.value == "RELEASE":
            if not self.has_dragged:
                select_or_deselect_keypose_markers(self, context, self.mouse_pos[0], event)
            self.is_dragging = False
            self.has_dragged = False
            # New addition: Prepare data for NLA layer adjustments
            prepare_nla_adjustments(self, context)
            update_keyframe_position(self, context, self)
            self.drag_start_mouse_x = 0  # Reset for next drag operation

            return {"RUNNING_MODAL"}

        if event.type in {"ESC"}:  # , "RIGHTMOUSE", }:
            self.cancel(context)
            return {"CANCELLED"}

        return {"PASS_THROUGH"}

    def invoke(self, context, event):
        if context.area.type not in {"GRAPH_EDITOR", "DOPESHEET_EDITOR"}:
            self.report({"WARNING"}, "This tool is only available in the Graph Editor or Dope Sheet.")
            return {"CANCELLED"}
        else:
            if self.action == "START":
                self.initialize_modal(context)
                return {"RUNNING_MODAL"}
            elif self.action == "FINISH":
                self.finish(context)
                return {"CANCELLED"}

    def find_marker_at_pos(self, context, mouse_x):
        """Helper to find a marker at a given mouse position."""
        for marker in self.keypose_markers:
            screen_x, _ = graph_to_screen(context, marker["frame"], 0)
            if abs(screen_x - mouse_x) < 10:  # Assuming 10 pixels as a clickable region
                return marker
        return None

    def initialize_modal(self, context):
        # Initialization logic
        props = context.scene.amp_keyposer_properties
        props.is_time_warper_active = True
        self._handle = bpy.types.SpaceGraphEditor.draw_handler_add(
            draw_callback_px, (self, context), "WINDOW", "POST_PIXEL"
        )
        self._timer = context.window_manager.event_timer_add(0.1, window=context.window)
        context.window_manager.modal_handler_add(self)
        initialize_keypose_markers(self, context)

    def cancel(self, context):
        self.finish(context)

    def finish(self, context):
        props = context.scene.amp_keyposer_properties
        props.is_time_warper_active = False
        if self._handle:
            bpy.types.SpaceGraphEditor.draw_handler_remove(self._handle, "WINDOW")
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
        context.area.tag_redraw()


def select_or_deselect_keypose_markers(operator, context, view_x, event):
    props = context.scene.amp_keyposer_properties
    keypose_marker_radius = props.keypose_marker_radius
    keypose_marker_text_size = props.keypose_marker_text_size
    keypose_marker_top_offset = props.keypose_marker_top_offset
    region_height = context.region.height
    y_pos = region_height - keypose_marker_top_offset
    handled = False
    marker_under_mouse = None
    marker_index_under_mouse = None

    if not operator.is_dragging:
        # Detect the marker under the mouse and its index
        for index, marker in enumerate(operator.keypose_markers):

            x_pos, _ = graph_to_screen(context, marker["frame"], 0)
            if is_keypose_highlighted(operator.mouse_pos, (x_pos, y_pos), keypose_marker_radius):
                marker_under_mouse = marker
                marker_index_under_mouse = index
                break

        if marker_under_mouse:
            if event.shift:
                # Shift-click to add to selection without removing others
                if not marker_under_mouse["selected"]:  # Only add if not already selected

                    # Find existing selected markers
                    selected_indices = [i for i, m in enumerate(operator.keypose_markers) if m["selected"]]

                    if selected_indices:
                        # Extend the selection to include all markers between the first and last selection
                        first_selected_index = min(selected_indices)
                        last_selected_index = max(selected_indices)
                        start = min(marker_index_under_mouse, first_selected_index)
                        end = max(marker_index_under_mouse, last_selected_index)
                        for i in range(start, end + 1):
                            operator.keypose_markers[i]["selected"] = True
                    else:
                        marker_under_mouse["selected"] = True  # Just select this one if no others were selected
            else:
                # Regular click, select only this one and deselect others
                reset_selection(operator.keypose_markers)
                marker_under_mouse["selected"] = True
            handled = True

        if not handled:
            # If no marker was clicked, clear selection unless shift or ctrl was pressed
            if not event.shift:
                reset_selection(operator.keypose_markers)

        operator._update_selected_keypose_markers_list()


def reset_selection(markers):
    for marker in markers:
        marker["selected"] = False


def initialize_keypose_markers(self, context, update=False):
    # Store the current selection status before clearing markers
    existing_selections = {m["frame"]: m["selected"] for m in self.keypose_markers} if update else {}

    self.keypose_markers.clear()
    action = context.active_object.animation_data.action if context.active_object.animation_data else None
    if action:
        for fcurve in utils.curve.all_fcurves(action):
            for keyframe_point in fcurve.keyframe_points:
                frame = keyframe_point.co.x
                if frame not in [m["frame"] for m in self.keypose_markers]:  # Check to avoid duplicates
                    # Apply existing selection if updating, default to False otherwise
                    is_selected = existing_selections.get(frame, update)
                    self.keypose_markers.append({"frame": frame, "original_frame": frame, "selected": is_selected})
    self._update_selected_keypose_markers_list()


def update_keyframe_position(self, context, operator):
    action = context.active_object.animation_data.action
    if action:
        needs_update = False
        min_frame = float("inf")
        max_frame = float("-inf")

        needs_update = False
        # Iterate through all keypose markers
        for marker in operator.keypose_markers:
            if marker["selected"]:
                # Snap the frame to the nearest whole number
                new_frame = round(marker["frame"])
                # Update the marker to the new snapped frame
                marker["frame"] = new_frame
                # Find and update the corresponding fcurve keyframe
                for fcurve in utils.curve.all_fcurves(action):
                    for keyframe in fcurve.keyframe_points:
                        # Match the keyframe by the original frame position before dragging
                        if round(keyframe.co.x) == round(marker["original_frame"]):
                            # Move the keyframe to the new snapped position
                            keyframe.co.x = new_frame
                            # Optionally adjust handles
                            keyframe.handle_left.x = new_frame
                            keyframe.handle_right.x = new_frame
                            needs_update = True
                            # Break out of the loop once the correct keyframe is adjusted
                            break
                    if needs_update:
                        fcurve.update()  # Ensure to update fcurve if a change was made

        # Update scene frame start and end if necessary
        if min_frame != float("inf") and min_frame < context.scene.frame_start:
            context.scene.frame_start = min_frame
        if max_frame != float("-inf") and max_frame > context.scene.frame_end:
            context.scene.frame_end = max_frame

        # If any updates were made, update the action to reflect changes
        if needs_update:
            action.update_tag()  # Tag the action for an update
            context.scene.frame_set(context.scene.frame_current)  # Force refresh

            # Reinitialize markers to reflect the new positions
            initialize_keypose_markers(self, context, update=True)

            # Force update all views to reflect changes
            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    area.tag_redraw()

        # Update 'original_frame' for all selected markers to the new frame to prevent snapping back
        for marker in operator.keypose_markers:
            if marker["selected"]:
                marker["original_frame"] = marker["frame"]


def prepare_nla_adjustments(self, context):
    """Prepare and call the function to update NLA layers based on keypose markers' movements."""
    # Gather all keypose markers' positions for complete segment calculations
    all_positions = sorted(marker["frame"] for marker in self.keypose_markers)
    print(f"All Key Pose Marker Positions: {all_positions}")

    # Create dictionaries for original and new positions including all keypose markers
    original_positions = {marker["original_frame"]: marker["original_frame"] for marker in self.keypose_markers}
    new_positions = {marker["original_frame"]: marker["frame"] for marker in self.keypose_markers}

    print(f"Original positions: {original_positions}")
    print(f"New positions: {new_positions}")

    # Determine the range of affected frames (start and end of all movements)
    affected_frame_start = min(new_positions.values(), default=0)
    affected_frame_end = max(new_positions.values(), default=0)

    # Ensure the start and end frames are captured
    if affected_frame_start > min(all_positions):
        affected_frame_start = min(all_positions)
    if affected_frame_end < max(all_positions):
        affected_frame_end = max(all_positions)

    print(f"Affected frames: from {affected_frame_start} to {affected_frame_end}")

    # Call function to update NLA tracks
    update_keyframe_positions_in_layers(
        context, original_positions, new_positions, (affected_frame_start, affected_frame_end)
    )


def update_keyframe_positions_in_layers(context, original_positions, new_positions, affected_frames):
    obj = context.active_object
    if not obj.animation_data:
        return

    active_action = obj.animation_data.action if obj.animation_data else None
    start_frame, end_frame = affected_frames

    # Calculate the full range of segments including all keypose markers
    all_positions = sorted(set(original_positions.keys()).union(new_positions.keys()))
    if start_frame not in all_positions:
        all_positions.insert(0, start_frame)
    if end_frame not in all_positions:
        all_positions.append(end_frame)

    print(f"Segments calculated from: {all_positions}")

    for track in obj.animation_data.nla_tracks:
        for strip in track.strips:
            action = strip.action
            if action == active_action or not action:
                continue

            print(f"Processing action: {action.name}")

            for fcurve in utils.curve.all_fcurves(action):
                keyframe_points = fcurve.keyframe_points
                for keyframe in keyframe_points:
                    kf_frame = keyframe.co.x
                    # Determine the segment the keyframe belongs to and apply transformation
                    for i in range(len(all_positions) - 1):
                        seg_start = all_positions[i]
                        seg_end = all_positions[i + 1]
                        if seg_start <= kf_frame < seg_end:
                            apply_segment_transformation(
                                keyframe, seg_start, seg_end, original_positions, new_positions
                            )
                fcurve.update()

    print("Updated keyframe positions in NLA layers based on main timeline adjustments.")


def apply_segment_transformation(keyframe, seg_start, seg_end, original_positions, new_positions):
    """Apply proportional transformation to a keyframe based on the segment's start and end."""
    original_start = original_positions.get(seg_start, seg_start)
    original_end = original_positions.get(seg_end, seg_end)
    new_start = new_positions.get(seg_start, seg_start)
    new_end = new_positions.get(seg_end, seg_end)

    # Calculate the proportional position within the segment
    original_length = original_end - original_start
    if original_length == 0:
        proportion = 0
    else:
        proportion = (keyframe.co.x - original_start) / original_length

    # Calculate the new position based on the proportion
    new_frame = new_start + proportion * (new_end - new_start)

    # Update the keyframe position
    keyframe.co.x = new_frame
    keyframe.handle_left.x = new_frame
    keyframe.handle_right.x = new_frame


def move_selected_keypose_markers(context, operator, mouse_x):
    # Step 1: Calculate the change in mouse position in screen coordinates
    mouse_delta_x = mouse_x - operator.drag_start_mouse_x

    # Step 2: Convert this pixel delta into Blender's graph view delta using the scale factor
    scale_x, _ = get_scale_factors(context)
    graph_delta_x = mouse_delta_x * scale_x

    # Step 3: Organize all markers by their frame value for easier manipulation and boundary checks
    sorted_markers = sorted(operator.keypose_markers, key=lambda m: m["frame"])

    # Step 4: Extract only those markers that are currently selected
    selected_markers = [m for m in sorted_markers if m["selected"]]
    if not selected_markers:
        return  # Exit if there are no selected markers to move

    # Step 5: Calculate the minimum and maximum frame values of the selected markers
    min_frame = min(m["frame"] for m in selected_markers)
    max_frame = max(m["frame"] for m in selected_markers)

    # Step 6: Identify movement boundaries based on nearest non-selected markers
    left_bound = (
        max((m["frame"] for m in sorted_markers if m["frame"] < min_frame and not m["selected"]), default=float("-inf"))
        + 1
    )
    right_bound = (
        min((m["frame"] for m in sorted_markers if m["frame"] > max_frame and not m["selected"]), default=float("inf"))
        - 1
    )

    # Step 7: Calculate the maximum possible movement in both directions without crossing other markers
    max_left_move = min_frame - left_bound
    max_right_move = right_bound - max_frame

    # Step 8: Adjust the movement delta to ensure it doesn't exceed the calculated boundaries
    adjusted_delta = max(min(graph_delta_x, max_right_move), -max_left_move)

    # Step 9: Apply the adjusted movement to the frame value of each selected marker
    for marker in selected_markers:
        marker["frame"] += adjusted_delta

    # Step 10: Update the start position for dragging to ensure smooth continuous dragging
    operator.drag_start_mouse_x = mouse_x

    # Additional: Update the 'original_frame' after moving to fix the resetting issue
    # This should occur once mouse is released or periodically to confirm the new positions
    if not operator.is_dragging:
        for marker in selected_markers:
            marker["original_frame"] = marker["frame"]


def draw_line(shader, start_pos, end_pos, color):
    """Draw a line using the given shader, start and end positions, and color."""
    vertices = [start_pos, end_pos]
    batch = batch_for_shader(shader, "LINES", {"pos": vertices})
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)


def draw_filled_circle(shader, position, radius, color):
    """Draw a filled circle using TRI_FAN."""
    segments = 16
    circle_vertices = []

    for i in range(segments + 1):
        angle = math.radians(float(i) / segments * 360.0)
        x = position[0] + math.cos(angle) * radius
        y = position[1] + math.sin(angle) * radius
        circle_vertices.append((x, y))

    # Directly use batch_for_shader to create and draw the batch
    batch = batch_for_shader(shader, "TRI_FAN", {"pos": circle_vertices})
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)


def is_keypose_highlighted(mouse_pos, circle_pos, radius):
    x_pos, y_pos = circle_pos
    mouse_x, mouse_y = mouse_pos
    # Check if the mouse is within the circle's bounding box
    return (x_pos - radius <= mouse_x <= x_pos + radius) and y_pos  # (y_pos - radius <= mouse_y <= y_pos + radius)


def draw_text(context, text, x, y, color=(0, 1, 1, 1, 1), size=8):
    font_id = 0
    blf.size(font_id, size)
    text_width, text_height = blf.dimensions(font_id, text)
    x = x - (text_width / 2)
    y = y - (text_height / 2)
    blf.position(font_id, x, y, 0)
    blf.color(font_id, 1, 1, 1, 1)
    blf.draw(font_id, text)


def draw_callback_px(self, context):
    region_height = context.region.height
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    props = context.scene.amp_keyposer_properties
    keypose_marker_radius = props.keypose_marker_radius
    keypose_marker_text_size = props.keypose_marker_text_size
    keypose_marker_top_offset = props.keypose_marker_top_offset
    gpu.state.blend_set("ALPHA")

    for marker in self.keypose_markers:
        screen_x, _ = graph_to_screen(context, marker["frame"], 0)
        y_pos = region_height - keypose_marker_top_offset

        # Determine color based on selection and highlight state
        if marker in self.selected_keypose_markers:
            color = (1, 0.5, 0, 1)  # Orange for selected
            text_color = (0, 0, 0, 1)  # black for highlighted

        elif is_keypose_highlighted(self.mouse_pos, (screen_x, y_pos), keypose_marker_radius) and not self.is_dragging:
            color = (0.5, 0.5, 0, 1)  # Yellow for highlighted
            text_color = (0, 0, 0, 1)  # black for highlighted

        else:
            color = (0.5, 0, 0, 0.5)  # Dark red for unselected
            text_color = (1, 1, 1, 1)  # White for unselected

        ### Draw the keypose marker ###

        draw_filled_circle(shader, (screen_x, y_pos), keypose_marker_radius, color)
        draw_line(shader, (screen_x, 0), (screen_x, region_height), color)
        draw_text(context, str(int(marker["frame"])), screen_x, y_pos, color=text_color, size=keypose_marker_text_size)

    gpu.state.blend_set("NONE")


# def AnimTimeWarperButton(layout, context, text="", icon="MOD_WARP"):
# layout.operator("anim.amp_keyposer_time_warp", text=text, icon=icon)


def AnimTimeWarperButton(layout, context, text="", icon="MOD_WARP"):
    props = context.scene.amp_keyposer_properties
    action = "FINISH" if props.is_time_warper_active else "START"
    icon = "CANCEL" if props.is_time_warper_active else icon
    layout.operator("anim.amp_keyposer_time_warp", text=text, icon=icon).action = action


def register():
    bpy.utils.register_class(TimeWarpOperator)


def unregister():
    bpy.utils.unregister_class(TimeWarpOperator)


if __name__ == "__main__":
    register()
