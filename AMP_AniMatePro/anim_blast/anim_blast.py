import os
import re
import tempfile
from datetime import datetime

import bpy


def _temp_output_dir():
    return tempfile.gettempdir()


def _blend_name():
    filepath = bpy.data.filepath
    if filepath:
        return os.path.splitext(os.path.basename(filepath))[0]
    return "untitled"


def _timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _clean_filename(filename):
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", filename)
    filename = filename.strip(" .")
    return filename or "playblast"


def expand_filename_pattern(pattern):
    filename = pattern or "{blend_name}_playblast"
    filename = filename.replace("{blend_name}", _blend_name())
    filename = filename.replace("{timestamp}", _timestamp())
    filename = _clean_filename(filename)
    base, ext = os.path.splitext(filename)
    if ext.lower() != ".mp4":
        filename = f"{base or filename}.mp4"
    return filename


def get_output_directory(settings):
    if settings.use_custom_output_path and settings.output_path:
        output_dir = bpy.path.abspath(settings.output_path)
    else:
        output_dir = _temp_output_dir()
    return os.path.normpath(output_dir)


def get_output_filepath(settings):
    return os.path.join(get_output_directory(settings), expand_filename_pattern(settings.filename_pattern))


def get_output_resolution(scene, settings):
    scale = max(1, min(100, settings.resolution_percent)) / 100.0
    width = max(1, round(scene.render.resolution_x * scale))
    height = max(1, round(scene.render.resolution_y * scale))
    return width, height


def _view3d_space(area):
    if not area or area.type != "VIEW_3D":
        return None
    active_space = area.spaces.active
    if active_space and active_space.type == "VIEW_3D":
        return active_space
    return next((space for space in area.spaces if space.type == "VIEW_3D"), None)


def _view3d_region(area):
    if not area:
        return None
    return next((region for region in area.regions if region.type == "WINDOW"), None)


def _iter_view3d_contexts(context):
    screen = getattr(context, "screen", None)
    if not screen:
        return
    for index, area in enumerate((area for area in screen.areas if area.type == "VIEW_3D"), start=1):
        space = _view3d_space(area)
        region = _view3d_region(area)
        if space and region:
            yield index, area, region, space


def resolve_view3d_context(context, source):
    current_area = getattr(context, "area", None)
    current_space = _view3d_space(current_area)
    current_region = _view3d_region(current_area)
    if source in {"AUTO", "ACTIVE_CAMERA"} and current_area and current_area.type == "VIEW_3D":
        if current_space and current_region:
            for index, area in enumerate((area for area in context.screen.areas if area.type == "VIEW_3D"), start=1):
                if area == current_area:
                    return index, current_area, current_region, current_space, True

    for index, area, region, space in _iter_view3d_contexts(context):
        return index, area, region, space, False

    return None, None, None, None, False


def _shading_name(space):
    shading = getattr(space, "shading", None)
    shading_type = getattr(shading, "type", "")
    return {
        "WIREFRAME": "Wireframe",
        "SOLID": "Solid",
        "MATERIAL": "Material",
        "RENDERED": "Rendered",
    }.get(shading_type, shading_type.title() if shading_type else "Viewport")


def get_using_label(context, settings):
    if settings.source == "ACTIVE_CAMERA":
        camera = getattr(context.scene, "camera", None)
        if camera:
            return f"Active Camera ({camera.name})"
        return "Active Camera (None)"

    index, _area, _region, space, is_current = resolve_view3d_context(context, settings.source)
    if not space:
        return "No 3D Viewport Found"

    label = "Current 3D Viewport" if is_current else f"3D Viewport {index}"
    return f"{label} ({_shading_name(space)})"


class AMP_PG_AnimBlastSettings(bpy.types.PropertyGroup):
    source: bpy.props.EnumProperty(
        name="Source",
        items=[
            (
                "AUTO",
                "Auto (First 3D Viewport)",
                "Use the current 3D Viewport, or the first available 3D Viewport from animation editors",
                "VIEW3D",
                0,
            ),
            (
                "ACTIVE_CAMERA",
                "Active Camera",
                "Use the scene active camera with the selected viewport settings",
                "CAMERA_DATA",
                1,
            ),
        ],
        default="AUTO",
    )
    resolution_percent: bpy.props.IntProperty(
        name="Playblast Resolution %",
        default=50,
        min=1,
        max=100,
        subtype="PERCENTAGE",
    )
    use_custom_output_path: bpy.props.BoolProperty(name="Custom Output Path", default=False)
    output_path: bpy.props.StringProperty(
        name="Output Path",
        default=_temp_output_dir(),
        subtype="DIR_PATH",
    )
    filename_pattern: bpy.props.StringProperty(
        name="Filename Pattern",
        default="{blend_name}_playblast",
    )
    auto_open: bpy.props.BoolProperty(name="Auto Open After Render", default=True)


def draw_anim_blast_settings(layout, context):
    settings = context.scene.anim_blast_settings
    scene = context.scene
    output_width, output_height = get_output_resolution(scene, settings)

    layout.use_property_split = True
    layout.use_property_decorate = False

    col = layout.column(align=True)
    col.label(text="Viewport Settings:")
    col.prop(settings, "source", text="Source")
    col.label(text=f"Using: {get_using_label(context, settings)}")

    layout.separator()

    col = layout.column(align=True)
    col.label(text="Render Settings:")
    col.prop(settings, "resolution_percent", text="Playblast Resolution %", slider=True)
    col.label(
        text=(
            f"Output: {output_width} x {output_height} "
            f"(Scene: {scene.render.resolution_x} x {scene.render.resolution_y})"
        )
    )

    layout.separator()

    col = layout.column(align=True)
    col.label(text="Output Settings:")
    col.prop(settings, "use_custom_output_path", text="Custom Output Path")
    path_col = col.column(align=True)
    path_col.enabled = settings.use_custom_output_path
    path_col.prop(settings, "output_path", text="")
    col.prop(settings, "filename_pattern", text="Filename Pattern")

    tags = col.column(align=True)
    tags.label(text="{blend_name} Current blend file name")
    tags.label(text="{timestamp} Current date and time")

    col.prop(settings, "auto_open", text="Auto Open After Render")

    layout.separator()

    col = layout.column(align=True)
    col.label(text="Preview Output:")
    col.label(text=get_output_filepath(settings))


def draw_anim_blast_panel(self, context):
    layout = self.layout
    layout.operator("anim.amp_anim_blast", text="Anim Blast", icon="RENDER_ANIMATION")
    layout.separator()
    draw_anim_blast_settings(layout, context)


class AMP_OT_AnimBlast(bpy.types.Operator):
    """Render a viewport playblast to MP4"""

    bl_idname = "anim.amp_anim_blast"
    bl_label = "Anim Blast"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return bool(getattr(context, "scene", None))

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=420)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Anim Blast", icon="RENDER_ANIMATION")
        draw_anim_blast_settings(layout, context)

    def execute(self, context):
        scene = context.scene
        settings = scene.anim_blast_settings

        if settings.source == "ACTIVE_CAMERA" and scene.camera is None:
            self.report({"ERROR"}, "Anim Blast needs an active scene camera for Active Camera source")
            return {"CANCELLED"}

        index, area, region, space, _is_current = resolve_view3d_context(context, settings.source)
        if not area or not region or not space:
            self.report({"ERROR"}, "Anim Blast could not find a 3D Viewport to render")
            return {"CANCELLED"}

        output_path = get_output_filepath(settings)
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)

        render = scene.render
        image_settings = render.image_settings
        ffmpeg = render.ffmpeg
        saved = {
            "filepath": render.filepath,
            "resolution_percentage": render.resolution_percentage,
            "use_file_extension": render.use_file_extension,
            "file_format": image_settings.file_format,
            "ffmpeg_format": ffmpeg.format,
            "ffmpeg_codec": ffmpeg.codec,
            "ffmpeg_audio_codec": ffmpeg.audio_codec,
            "frame_current": scene.frame_current,
        }

        region_3d = getattr(space, "region_3d", None)
        saved_perspective = getattr(region_3d, "view_perspective", None)

        try:
            render.filepath = output_path
            render.resolution_percentage = settings.resolution_percent
            render.use_file_extension = True
            image_settings.file_format = "FFMPEG"
            ffmpeg.format = "MPEG4"
            ffmpeg.codec = "H264"
            ffmpeg.audio_codec = "NONE"

            if settings.source == "ACTIVE_CAMERA" and region_3d:
                region_3d.view_perspective = "CAMERA"

            override = {
                "window": context.window,
                "screen": context.screen,
                "area": area,
                "region": region,
                "space_data": space,
                "scene": scene,
            }
            with context.temp_override(**override):
                bpy.ops.render.opengl(animation=True, view_context=True)

            if settings.auto_open:
                bpy.ops.wm.path_open(filepath=output_path)

        except Exception as exc:
            self.report({"ERROR"}, f"Anim Blast failed: {exc}")
            return {"CANCELLED"}
        finally:
            if region_3d and saved_perspective:
                region_3d.view_perspective = saved_perspective
            render.filepath = saved["filepath"]
            render.resolution_percentage = saved["resolution_percentage"]
            render.use_file_extension = saved["use_file_extension"]
            image_settings.file_format = saved["file_format"]
            ffmpeg.format = saved["ffmpeg_format"]
            ffmpeg.codec = saved["ffmpeg_codec"]
            ffmpeg.audio_codec = saved["ffmpeg_audio_codec"]
            scene.frame_set(saved["frame_current"])

        self.report({"INFO"}, f"Anim Blast rendered: {output_path}")
        return {"FINISHED"}


class AMP_PT_AnimBlastGraph(bpy.types.Panel):
    bl_label = "Anim Blast"
    bl_idname = "AMP_PT_AnimBlastGraph"
    bl_parent_id = "AMP_PT_AniMateProGraph"
    bl_space_type = "GRAPH_EDITOR"
    bl_region_type = "UI"
    bl_options = {"DEFAULT_CLOSED"}
    bl_category = "Animation"

    def draw_header(self, context):
        self.layout.label(text="", icon="RENDER_ANIMATION")

    def draw(self, context):
        draw_anim_blast_panel(self, context)


class AMP_PT_AnimBlastDope(bpy.types.Panel):
    bl_label = "Anim Blast"
    bl_idname = "AMP_PT_AnimBlastDope"
    bl_parent_id = "AMP_PT_AniMateProDope"
    bl_space_type = "DOPESHEET_EDITOR"
    bl_region_type = "UI"
    bl_options = {"DEFAULT_CLOSED"}
    bl_category = "Animation"

    def draw_header(self, context):
        self.layout.label(text="", icon="RENDER_ANIMATION")

    def draw(self, context):
        draw_anim_blast_panel(self, context)


class AMP_PT_AnimBlastView(bpy.types.Panel):
    bl_label = "Anim Blast"
    bl_idname = "AMP_PT_AnimBlastView"
    bl_parent_id = "AMP_PT_AniMateProView"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {"DEFAULT_CLOSED"}
    bl_category = "Animation"

    def draw_header(self, context):
        self.layout.label(text="", icon="RENDER_ANIMATION")

    def draw(self, context):
        draw_anim_blast_panel(self, context)


class AMP_PT_AnimBlastNLA(bpy.types.Panel):
    bl_label = "Anim Blast"
    bl_idname = "AMP_PT_AnimBlastNLA"
    bl_parent_id = "AMP_PT_AniMateProNLA"
    bl_space_type = "NLA_EDITOR"
    bl_region_type = "UI"
    bl_options = {"DEFAULT_CLOSED"}
    bl_category = "Animation"

    def draw_header(self, context):
        self.layout.label(text="", icon="RENDER_ANIMATION")

    def draw(self, context):
        draw_anim_blast_panel(self, context)


classes = (
    AMP_PG_AnimBlastSettings,
    AMP_OT_AnimBlast,
    AMP_PT_AnimBlastGraph,
    AMP_PT_AnimBlastDope,
    AMP_PT_AnimBlastView,
    AMP_PT_AnimBlastNLA,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.anim_blast_settings = bpy.props.PointerProperty(type=AMP_PG_AnimBlastSettings)


def unregister():
    if hasattr(bpy.types.Scene, "anim_blast_settings"):
        del bpy.types.Scene.anim_blast_settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
