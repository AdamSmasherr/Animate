##################
## operators.py ##
##################
from . import __package__ as base_package
import bpy
from .utils.insert_keyframes import (
    get_3d_view_items,
    get_graph_editor_items,
    get_timeline_dopesheet_items,
)


class AMP_OT_deactivate_other_keymaps_for_operator(bpy.types.Operator):
    """Deactivate all other keymaps that match the key and modifiers of the specified operator"""

    bl_idname = "wm.deactivate_other_keymaps_for_operator"
    bl_label = "Deactivate Other Keymaps for Operator"

    operator_idname: bpy.props.StringProperty(
        name="Operator ID Name",
        description="ID name of the operator to match keymaps for",
    )

    def find_keymap_items(self, operator_idname):
        """Find all keymap items for a specific operator across all keymaps"""
        wm = bpy.context.window_manager
        found_items = []

        for km in wm.keyconfigs.user.keymaps.values():
            for kmi in km.keymap_items:
                if kmi.idname == operator_idname:
                    # Append both the keymap and the keymap item for later use
                    found_items.append((km, kmi))
        return found_items

    def execute(self, context):
        wm = bpy.context.window_manager
        target_kmis = self.find_keymap_items(self.operator_idname)

        if not target_kmis:
            self.report({"INFO"}, "No keymap items found for the specified operator.")
            return {"CANCELLED"}

        # Deactivate conflicting keymaps
        deactivated_count = 0
        for km, target_kmi in target_kmis:
            target_key = target_kmi.type
            target_modifiers = (
                target_kmi.shift,
                target_kmi.ctrl,
                target_kmi.alt,
                target_kmi.oskey,
            )
            target_space_type = km.space_type
            target_region_type = km.region_type

            for other_km in wm.keyconfigs.user.keymaps.values():
                if other_km.space_type == target_space_type and other_km.region_type == target_region_type:
                    for kmi in other_km.keymap_items:
                        if (
                            kmi.type == target_key
                            and (kmi.shift, kmi.ctrl, kmi.alt, kmi.oskey) == target_modifiers
                            and kmi.idname != self.operator_idname
                        ):
                            kmi.active = False
                            deactivated_count += 1

        self.report(
            {"INFO"},
            f"Deactivated {deactivated_count} conflicting keymaps for the specified operator.",
        )
        return {"FINISHED"}


class AMP_OT_CaptureKeyInput(bpy.types.Operator):
    """Capture Key Input"""

    bl_idname = "anim.amp_capture_key_input"
    bl_label = "Capture Key Input"
    action_id: bpy.props.StringProperty()

    action_modifiers: bpy.props.BoolProperty(
        name="Include Modifiers",
        description="Include modifiers in the key combination",
        default=True,
    )

    @staticmethod
    def update_ui():
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()

    def modal(self, context, event):
        if event.type == "TIMER":
            return {"PASS_THROUGH"}

        # Handle BACKSPACE to reset to default
        if event.type == "BACKSPACE" and event.value == "PRESS":
            prefs = bpy.context.preferences.addons[base_package].preferences
            default_value = getattr(prefs, f"default_{self.action_id}")
            setattr(prefs, self.action_id, default_value)
            self.report(
                {"INFO"},
                f"Key for {self.action_id.replace('_', ' ').title()} reset to default",
            )
            context.area.header_text_set(None)  # Clear the header text
            self.update_ui()
            return {"FINISHED"}

        if event.value == "PRESS" and event.type not in {"ESC", "TIMER", "MOUSEMOVE"}:
            modifiers = []
            if self.action_modifiers:
                if event.shift:
                    modifiers.append("SHIFT")
                if event.ctrl:
                    modifiers.append("CTRL")
                if event.alt:
                    modifiers.append("ALT")
                if event.oskey:
                    modifiers.append("OSKEY")

            # Combine modifiers with the key (if it's not a modifier key itself)
            if event.type not in {
                "LEFT_SHIFT",
                "RIGHT_SHIFT",
                "LEFT_CTRL",
                "RIGHT_CTRL",
                "LEFT_ALT",
                "RIGHT_ALT",
                "OSKEY",
            }:
                key_identifier = "+".join(modifiers + [event.type])
                prefs = bpy.context.preferences.addons[base_package].preferences
                setattr(prefs, self.action_id, key_identifier)
                self.report(
                    {"INFO"},
                    f"Key set to {key_identifier} for {self.action_id.replace('_', ' ').title()}",
                )
                context.area.header_text_set(None)  # Clear the header text
                self.finish_capture(context)
                self.update_ui()
                return {"FINISHED"}

        context.area.header_text_set("Press a key (ESC or BACKSPACE to cancel)")
        return {"RUNNING_MODAL"}

    def invoke(self, context, event):
        prefs = bpy.context.preferences.addons[base_package].preferences
        prefs.capturing_key = self.action_id
        wm = context.window_manager
        wm.modal_handler_add(self)
        context.area.header_text_set("Press a key (ESC or BACKSPACE to cancel)")
        return {"RUNNING_MODAL"}

    def finish_capture(self, context):
        prefs = bpy.context.preferences.addons[base_package].preferences
        prefs.capturing_key = ""
        self.update_ui()

    def cancel(self, context):
        prefs = bpy.context.preferences.addons[base_package].preferences
        prefs.capturing_key = ""
        context.area.header_text_set(None)  # Clear the header text
        self.update_ui()


def draw_insert_menu(context, layout):
    prefs = bpy.context.preferences.addons[base_package].preferences

    # Determine context and set items accordingly
    if context.area.type == "VIEW_3D":
        method = prefs.default_3d_view_insert_keyframe
        items = get_3d_view_items(None, context)
    elif context.area.type == "GRAPH_EDITOR":
        method = prefs.default_graph_editor_insert_keyframe
        items = get_graph_editor_items(None, context)
    elif context.area.type in ["DOPESHEET_EDITOR", "TIMELINE"]:
        method = prefs.default_timeline_dopesheet_insert_keyframe
        items = get_timeline_dopesheet_items(None, context)
    else:
        # Default or unsupported context
        items = []
        method = ""

    row = layout.row(align=True)
    split = row.split(factor=0.4)
    column = split.column(align=True)
    column.alignment = "RIGHT"
    column.label(text="Default Keying")
    column2 = split.column(align=True)
    # Dynamically create menu items
    for item in items:
        row = column2.row(align=True)
        op = row.operator(
            "wm.context_set_enum",
            text=item[1],
            # icon="CHECKBOX_HLT" if (method == item[0]) else "CHECKBOX_DEHLT",
            depress=(method == item[0]),
        )
        if context.area.type == "VIEW_3D":
            op.data_path = f"preferences.addons['{base_package}'].preferences.default_3d_view_insert_keyframe"
        elif context.area.type == "GRAPH_EDITOR":
            op.data_path = f"preferences.addons['{base_package}'].preferences.default_graph_editor_insert_keyframe"
        elif context.area.type in ["DOPESHEET_EDITOR", "TIMELINE"]:
            op.data_path = (
                f"preferences.addons['{base_package}'].preferences.default_timeline_dopesheet_insert_keyframe"
            )
        op.value = item[0]


class AMP_PT_InsertKeyPreferencesVIEW(bpy.types.Panel):
    bl_idname = "AMP_PT_InsertKeyPreferencesVIEW"
    bl_label = ""
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_context = ""
    bl_order = 0
    bl_options = {"HIDE_HEADER"}
    bl_ui_units_x = 20

    def draw(self, context):
        layout = self.layout
        width = context.region.width
        ui_scale = context.preferences.system.ui_scale
        is_wide = width > (350 * ui_scale)

        layout.use_property_split = True
        layout.use_property_decorate = False

        row = layout.row()
        if is_wide:
            row.label()

        col = row.column()
        col.ui_units_x = 100

        if is_wide:
            row.label()
        userpref_panel = bpy.types.USERPREF_PT_animation_keyframes
        userpref_panel.draw_centered(self, context, col)


class AMP_PT_InsertKeyPreferencesGraph(bpy.types.Panel):
    bl_idname = "AMP_PT_InsertKeyPreferencesGraph"
    bl_label = ""
    bl_space_type = "GRAPH_EDITOR"
    bl_region_type = "WINDOW"
    bl_context = ""
    bl_order = 0
    bl_options = {"HIDE_HEADER"}
    bl_ui_units_x = 20

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        row = layout.row()

        row.label()

        col = row.column()
        col.ui_units_x = 100

        row.label()
        col2 = col.column(heading="Default Keying:", align=True)
        draw_insert_menu(context, col2)
        userpref_panel = bpy.types.USERPREF_PT_animation_fcurves
        userpref_panel.draw_centered(self, context, col)


class AMP_PT_InsertKeyPreferencesDope(bpy.types.Panel):
    bl_idname = "AMP_PT_InsertKeyPreferencesDope"
    bl_label = ""
    bl_space_type = "DOPESHEET_EDITOR"
    bl_region_type = "WINDOW"
    bl_context = ""
    bl_order = 0
    bl_options = {"HIDE_HEADER"}
    bl_ui_units_x = 20

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        row = layout.row()
        row.label()

        col = row.column()
        col.ui_units_x = 100

        col2 = col.column(heading="Default Keying:", align=True)
        draw_insert_menu(context, col2)
        userpref_panel = bpy.types.USERPREF_PT_animation_timeline
        userpref_panel.draw_centered(self, context, col)


classes = (
    AMP_OT_deactivate_other_keymaps_for_operator,
    AMP_OT_CaptureKeyInput,
    AMP_PT_InsertKeyPreferencesVIEW,
    AMP_PT_InsertKeyPreferencesGraph,
    AMP_PT_InsertKeyPreferencesDope,
)


# Register classes and properties
def register():
    for cls in classes:
        bpy.utils.register_class(cls)


# Unregister classes and properties
def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


##################
## operators.py ##
##################
