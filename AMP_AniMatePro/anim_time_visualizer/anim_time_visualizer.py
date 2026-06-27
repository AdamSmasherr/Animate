"""
Time Visualizer (View category)

Draws visual time aids over the Dope Sheet / Timeline (and optionally the Graph
Editor): per second tick lines, alternating checker bands and per frame ticks,
with optional second / timecode labels. Helps animators read spacing in real
time units directly on the time axis.

Rendering uses the modern ``gpu`` module (UNIFORM_COLOR builtin shader) and
``blf`` for labels, mapping frames to pixels through ``region.view2d``. A single
persistent POST_PIXEL draw handler per editor type is installed once and gated
by the per scene ``enabled`` toggle, so there is no add / remove churn and no
handler leak.
"""

import math

import bpy
import blf
import gpu
from gpu_extras.batch import batch_for_shader
from bpy.types import PropertyGroup, Operator, Panel
from bpy.props import (
    BoolProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    PointerProperty,
)
from bpy.utils import register_class, unregister_class


# ----------------------------------------------------------------------------
# Draw handler state
# ----------------------------------------------------------------------------

_handles = {}          # space_type_name -> draw handler
_shader = None


def _get_shader():
    global _shader
    if _shader is None:
        _shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    return _shader


def get_settings(scene):
    return getattr(scene, "amp_time_visualizer", None)


def _fps(scene):
    base = scene.render.fps_base or 1.0
    return scene.render.fps / base


# ----------------------------------------------------------------------------
# Low level drawing helpers
# ----------------------------------------------------------------------------

def _draw_rect(x0, x1, y0, y1, color):
    shader = _get_shader()
    verts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    batch = batch_for_shader(shader, "TRI_FAN", {"pos": verts})
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)


def _draw_lines(coords, color):
    if not coords:
        return
    shader = _get_shader()
    batch = batch_for_shader(shader, "LINES", {"pos": coords})
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)


def _format_timecode(seconds, fps):
    """Whole second value -> mm:ss label."""
    seconds = int(round(seconds))
    minutes = seconds // 60
    rem = seconds % 60
    return "{:d}:{:02d}".format(minutes, rem)


# ----------------------------------------------------------------------------
# Main draw callback
# ----------------------------------------------------------------------------

def _draw_callback():
    context = bpy.context
    scene = context.scene
    st = get_settings(scene)
    if st is None or not st.enabled:
        return

    area = context.area
    region = context.region
    if area is None or region is None or region.type != "WINDOW":
        return

    if area.type == "GRAPH_EDITOR" and not st.in_graph_editor:
        return

    v2d = region.view2d
    width = region.width
    height = region.height
    if width <= 0 or height <= 0:
        return

    fps = _fps(scene)
    if fps <= 0:
        return

    # Visible frame range for this region.
    left_frame = v2d.region_to_view(0, 0)[0]
    right_frame = v2d.region_to_view(width, 0)[0]
    if right_frame <= left_frame:
        return

    opacity = max(0.0, min(1.0, st.opacity))
    if opacity <= 0.0:
        return

    pixels_per_frame = (
        v2d.view_to_region(left_frame + 1.0, 0.0, clip=False)[0]
        - v2d.view_to_region(left_frame, 0.0, clip=False)[0]
    )

    y0, y1 = 0, height

    gpu.state.blend_set("ALPHA")

    # --- Checker bands (one band == checker_step frames, default one second) ---
    step = st.checker_step if st.checker_step > 0 else fps
    if st.show_checker and step > 0:
        col = (
            st.checker_color[0],
            st.checker_color[1],
            st.checker_color[2],
            st.checker_color[3] * opacity,
        )
        first_idx = int(math.floor(left_frame / step))
        last_idx = int(math.ceil(right_frame / step))
        # Cap the band count so an extremely zoomed out view never explodes.
        if (last_idx - first_idx) <= 4000:
            for idx in range(first_idx, last_idx + 1):
                if idx % 2 != 0:
                    continue
                x0 = v2d.view_to_region(idx * step, 0.0, clip=False)[0]
                x1 = v2d.view_to_region((idx + 1) * step, 0.0, clip=False)[0]
                _draw_rect(x0, x1, y0, y1, col)

    # --- Per frame minor ticks (only when zoomed in enough to be readable) ---
    if st.show_frame_ticks and pixels_per_frame >= 6.0:
        tick_col = (
            st.tick_color[0],
            st.tick_color[1],
            st.tick_color[2],
            st.tick_color[3] * opacity,
        )
        coords = []
        f0 = int(math.floor(left_frame))
        f1 = int(math.ceil(right_frame))
        if (f1 - f0) <= 4000:
            for f in range(f0, f1 + 1):
                x = v2d.view_to_region(f, 0.0, clip=False)[0]
                coords.append((x, y0))
                coords.append((x, min(y0 + 10, y1)))
            _draw_lines(coords, tick_col)

    # --- Per second tick lines ---
    sec_first = int(math.floor(left_frame / fps))
    sec_last = int(math.ceil(right_frame / fps))
    second_coords = []
    if st.show_seconds_lines and (sec_last - sec_first) <= 4000:
        line_col = (
            st.seconds_line_color[0],
            st.seconds_line_color[1],
            st.seconds_line_color[2],
            st.seconds_line_color[3] * opacity,
        )
        for s in range(sec_first, sec_last + 1):
            x = v2d.view_to_region(s * fps, 0.0, clip=False)[0]
            second_coords.append((x, y0))
            second_coords.append((x, y1))
        _draw_lines(second_coords, line_col)

    gpu.state.blend_set("NONE")

    # --- Second / timecode labels ---
    if st.show_second_labels and (sec_last - sec_first) <= 2000:
        font_id = 0
        text_size = max(6, st.text_size)
        blf.size(font_id, text_size)
        blf.color(font_id, *st.text_color)
        label_y = height - text_size - 4
        for s in range(sec_first, sec_last + 1):
            x = v2d.view_to_region(s * fps, 0.0, clip=False)[0]
            if x < -20 or x > width + 20:
                continue
            label = _format_timecode(s, fps) if st.timecode else "{:d}s".format(s)
            blf.position(font_id, x + 3, label_y, 0)
            blf.draw(font_id, label)


# ----------------------------------------------------------------------------
# Property group
# ----------------------------------------------------------------------------

def _redraw_editors(context):
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type in {"DOPESHEET_EDITOR", "GRAPH_EDITOR"}:
                area.tag_redraw()


def _on_update(self, context):
    _redraw_editors(context)


class AMP_PG_TimeVisualizer(PropertyGroup):
    """Per scene settings for the Time Visualizer overlay."""

    enabled: BoolProperty(
        name="Enable Time Visualizer",
        description="Draw time aids over the Dope Sheet / Timeline",
        default=False,
        update=_on_update,
    )

    show_checker: BoolProperty(
        name="Checker Bands",
        description="Draw alternating shaded bands, one band per step",
        default=True,
        update=_on_update,
    )
    show_seconds_lines: BoolProperty(
        name="Second Lines",
        description="Draw a vertical line at every whole second",
        default=True,
        update=_on_update,
    )
    show_second_labels: BoolProperty(
        name="Second Labels",
        description="Draw a text label at every whole second",
        default=True,
        update=_on_update,
    )
    show_frame_ticks: BoolProperty(
        name="Frame Ticks",
        description="Draw a small tick at every frame (only shown when zoomed in)",
        default=False,
        update=_on_update,
    )
    timecode: BoolProperty(
        name="Timecode",
        description="Label seconds as mm:ss instead of a plain second count",
        default=False,
        update=_on_update,
    )
    in_graph_editor: BoolProperty(
        name="Also In Graph Editor",
        description="Draw the overlay in the Graph Editor as well",
        default=False,
        update=_on_update,
    )

    checker_step: IntProperty(
        name="Step",
        description="Band width in frames. 0 uses the scene FPS so each band is one second",
        default=0,
        min=0,
        soft_max=240,
        update=_on_update,
    )
    opacity: FloatProperty(
        name="Opacity",
        description="Global opacity multiplier for the overlay",
        default=1.0,
        min=0.0,
        max=1.0,
        subtype="FACTOR",
        update=_on_update,
    )
    text_size: IntProperty(
        name="Text Size",
        description="Size of the second labels",
        default=11,
        min=6,
        max=48,
        update=_on_update,
    )

    checker_color: FloatVectorProperty(
        name="Checker Color",
        subtype="COLOR",
        size=4,
        default=(1.0, 1.0, 1.0, 0.04),
        min=0.0,
        max=1.0,
        update=_on_update,
    )
    seconds_line_color: FloatVectorProperty(
        name="Second Line Color",
        subtype="COLOR",
        size=4,
        default=(0.4, 0.7, 1.0, 0.4),
        min=0.0,
        max=1.0,
        update=_on_update,
    )
    tick_color: FloatVectorProperty(
        name="Frame Tick Color",
        subtype="COLOR",
        size=4,
        default=(1.0, 1.0, 1.0, 0.25),
        min=0.0,
        max=1.0,
        update=_on_update,
    )
    text_color: FloatVectorProperty(
        name="Label Color",
        subtype="COLOR",
        size=4,
        default=(0.7, 0.85, 1.0, 0.9),
        min=0.0,
        max=1.0,
        update=_on_update,
    )


# ----------------------------------------------------------------------------
# Operators
# ----------------------------------------------------------------------------

class AMP_OT_TimeVisualizerToggle(Operator):
    """Toggle the Time Visualizer overlay on the Dope Sheet / Timeline"""

    bl_idname = "anim.amp_time_visualizer_toggle"
    bl_label = "Toggle Time Visualizer"
    bl_options = {"REGISTER"}

    def execute(self, context):
        st = get_settings(context.scene)
        if st is None:
            self.report({"WARNING"}, "Time Visualizer settings not available")
            return {"CANCELLED"}
        st.enabled = not st.enabled
        _redraw_editors(context)
        return {"FINISHED"}


# ----------------------------------------------------------------------------
# Popover settings panel + header button
# ----------------------------------------------------------------------------

class AMP_PT_TimeVisualizer(Panel):
    bl_label = "Time Visualizer"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_ui_units_x = 13

    def draw(self, context):
        layout = self.layout
        st = get_settings(context.scene)
        if st is None:
            layout.label(text="Unavailable", icon="ERROR")
            return

        layout.prop(st, "enabled", text="Enabled", toggle=True, icon="TIME")
        col = layout.column()
        col.active = st.enabled

        box = col.box()
        box.label(text="Checker Bands")
        row = box.row(align=True)
        row.prop(st, "show_checker", text="")
        sub = row.row(align=True)
        sub.active = st.show_checker
        sub.prop(st, "checker_step")
        sub.prop(st, "checker_color", text="")

        box = col.box()
        box.label(text="Seconds")
        row = box.row(align=True)
        row.prop(st, "show_seconds_lines", text="Lines")
        row.prop(st, "seconds_line_color", text="")
        row = box.row(align=True)
        row.prop(st, "show_second_labels", text="Labels")
        row.prop(st, "text_color", text="")
        row = box.row(align=True)
        row.active = st.show_second_labels
        row.prop(st, "timecode")
        row.prop(st, "text_size")

        box = col.box()
        box.label(text="Frames")
        row = box.row(align=True)
        row.prop(st, "show_frame_ticks", text="Ticks")
        row.prop(st, "tick_color", text="")

        col.separator()
        col.prop(st, "opacity")
        col.prop(st, "in_graph_editor")


def TimeVisualizerButton(layout, context):
    """Header button for the View section: toggle + settings popover."""
    if context.area.type not in {"GRAPH_EDITOR", "DOPESHEET_EDITOR"}:
        layout.label(text="", icon="TIME")
        return
    st = get_settings(context.scene)
    enabled = bool(st and st.enabled)
    row = layout.row(align=True)
    row.operator(
        "anim.amp_time_visualizer_toggle",
        text="",
        icon="TIME",
        depress=enabled,
    )
    row.popover("AMP_PT_TimeVisualizer", text="")


# ----------------------------------------------------------------------------
# Register
# ----------------------------------------------------------------------------

classes = (
    AMP_PG_TimeVisualizer,
    AMP_OT_TimeVisualizerToggle,
    AMP_PT_TimeVisualizer,
)

_DRAW_SPACES = ("SpaceDopeSheetEditor", "SpaceGraphEditor")


def _add_handlers():
    for space_name in _DRAW_SPACES:
        if space_name in _handles:
            continue
        space_type = getattr(bpy.types, space_name, None)
        if space_type is None:
            continue
        _handles[space_name] = space_type.draw_handler_add(
            _draw_callback, (), "WINDOW", "POST_PIXEL"
        )


def _remove_handlers():
    for space_name in list(_handles.keys()):
        space_type = getattr(bpy.types, space_name, None)
        handle = _handles.pop(space_name, None)
        if space_type is not None and handle is not None:
            try:
                space_type.draw_handler_remove(handle, "WINDOW")
            except (ValueError, ReferenceError):
                pass


def register():
    for cls in classes:
        register_class(cls)
    bpy.types.Scene.amp_time_visualizer = PointerProperty(type=AMP_PG_TimeVisualizer)
    _add_handlers()


def unregister():
    _remove_handlers()
    if hasattr(bpy.types.Scene, "amp_time_visualizer"):
        del bpy.types.Scene.amp_time_visualizer
    for cls in reversed(classes):
        try:
            unregister_class(cls)
        except RuntimeError:
            pass
    global _shader
    _shader = None
