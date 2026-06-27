##################
##    utils     ##
## operators.py ##
##################

import bpy
from .api import dprint
from .. import utils
from . import customIcons

from .. import __package__ as base_package


class AMP_OT_ResetGraphEditorFlag_LMB(bpy.types.Operator):
    bl_idname = "anim.amp_reset_graph_editor_flags"
    bl_label = "Reset Graph Editor Flags"
    bl_description = "Reset flags to False"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        prefs = bpy.context.preferences.addons[base_package].preferences
        if prefs.jump_already_made:
            prefs.jump_already_made = False
            dprint("Persistent flags reset to False.")
        return {"FINISHED"}


class AMP_OT_CallHelpPanel(bpy.types.Operator):

    bl_idname = "anim.amp_call_help_panel"
    bl_label = "Instructions"
    bl_description = "Press to get more detail about this section"

    panel_name: bpy.props.StringProperty()

    def execute(self, context):
        if self.panel_name in dir(bpy.types):
            panel_class = getattr(bpy.types, self.panel_name)
            if hasattr(panel_class, "bl_idname"):
                bpy.ops.wm.call_panel(name=panel_class.bl_idname)
                return {"FINISHED"}
        self.report({"WARNING"}, "Panel not found: " + self.panel_name)
        return {"CANCELLED"}


class AMP_OT_ReloadIcons(bpy.types.Operator):
    bl_idname = "anim.amp_reload_icons"
    bl_label = "Reload Custom Icons"
    bl_description = "Reload the addon custom icons"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        customIcons.reload_icons()
        return {"FINISHED"}


class AMP_OT_AnimationEditors(bpy.types.Operator):

    bl_idname = "space.amp_animation_editors"
    bl_label = "Animation Editors"
    bl_options = {"REGISTER", "UNDO"}
    bl_description = """
    - Graph Editor.
    - Dope Sheet.
    - Drivers Editor.
    - Shape Key Editor.
    - Grease Pencil.
    - Mask Editor.
    - NLA Editor."""


    space_type: bpy.props.EnumProperty(
        name="Space Type",
        description="The type of animation editor space to switch to",
        items=[
            ("DOPESHEET_EDITOR", "Dope Sheet", "Switch to Dope Sheet Editor"),
            ("GRAPH_EDITOR", "Graph Editor", "Switch to Graph Editor"),
            ("NLA_EDITOR", "NLA Editor", "Switch to NLA Editor"),
            ("DRIVERS_EDITOR", "Drivers", "Switch to Drivers Editor"),
        ],
    )

    subspace_type: bpy.props.EnumProperty(
        name="Subspace Type",
        description="The subspace mode to switch to within the specified editor",
        items=[
            ("DOPESHEET", "Dope Sheet", "Basic Dope Sheet"),
            ("ACTION", "Action Editor", "Action Editor"),
            ("SHAPEKEY", "Shape Key Editor", "Shape Key Editor"),
            ("GPENCIL", "Grease Pencil", "Grease Pencil"),
            ("MASK", "Mask", "Mask Editor"),
            ("CACHEFILE", "Cache File", "Cache File Editor"),
            ("NONE", "None", "No Subspace"),
        ],
        default="NONE",
    )

    @classmethod
    def poll(cls, context):
        return context.area is not None

    def execute(self, context):
        area = context.area

        if not area:
            self.report({"WARNING"}, "No active area found.")
            return {"CANCELLED"}

        # Map our custom enum values to Blender's recognized ui_type.
        ui_type_map = {
            "DOPESHEET_EDITOR": "DOPESHEET",
            "GRAPH_EDITOR": "FCURVES",
            "NLA_EDITOR": "NLA_EDITOR",
            "DRIVERS_EDITOR": "DRIVERS",
        }
        mapped_ui_type = ui_type_map.get(self.space_type, "DOPESHEET")

        if area.ui_type != mapped_ui_type:
            area.ui_type = mapped_ui_type
            self.report({"INFO"}, f"Changed area type to {mapped_ui_type}.")
        else:
            self.report({"INFO"}, f"Area type is already {mapped_ui_type}.")

        # After changing ui_type, re-fetch the active space
        space = area.spaces.active

        # Proceed only if the space has a 'mode' property and a subspace_type is specified
        if hasattr(space, 'mode') and self.subspace_type and self.subspace_type != "NONE":
            valid_modes = [item.identifier for item in space.bl_rna.properties['mode'].enum_items]
            target_subspace = self.subspace_type
            if target_subspace == "GPENCIL" and "GPENCIL" not in valid_modes:
                if "GREASEPENCIL" in valid_modes:
                    target_subspace = "GREASEPENCIL"
                elif "GREASE_PENCIL" in valid_modes:
                    target_subspace = "GREASE_PENCIL"
                    
            if target_subspace in valid_modes:
                if space.mode != target_subspace:
                    space.mode = target_subspace
                    self.report({"INFO"}, f"Set {self.space_type.replace('_', ' ').title()} mode to {target_subspace.replace('_', ' ').title()}.")
                else:
                    self.report({"INFO"}, f"{self.space_type.replace('_', ' ').title()} mode is already {target_subspace.replace('_', ' ').title()}.")

        return {"FINISHED"}


classes = (
    AMP_OT_CallHelpPanel,
    AMP_OT_ResetGraphEditorFlag_LMB,
    AMP_OT_ReloadIcons,
    AMP_OT_AnimationEditors,
)


def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except (RuntimeError, AttributeError):
            utils.dprint("Class already registered, skiping...")


def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except (RuntimeError, AttributeError):
            utils.dprint("Class not found, skiping...")


##################
##    utils     ##
## operators.py ##
##################
