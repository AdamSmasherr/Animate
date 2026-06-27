###########
## ui.py ##
###########

import bpy
import bpy.utils.previews
from ..anim_curves.anim_curves import AMP_OT_isolate_selected_fcurves
from .. import utils

from .. import __package__ as base_package
from rna_prop_ui import PropertyPanel
import bl_ui

# ** from bl_ui.space_dopesheet import dopesheet_filter
# ** from bl_ui.space_graph import GRAPH_HT_header, GRAPH_MT_editor_menus
# ** from bl_ui.space_dopesheet import DOPESHEET_HT_editor_buttons

# Blender Native UI


class GRAPH_HT_header(bpy.types.Header):
    bl_space_type = "GRAPH_EDITOR"

    def draw(self, context):
        layout = self.layout
        tool_settings = context.tool_settings

        st = context.space_data

        layout.template_header()

        bl_ui.space_graph.GRAPH_MT_editor_menus.draw_collapsible(context, layout)

        # AniMatePro: HIDE NORMALIZATION
        # row = layout.row(align=True)
        # row.prop(st, "use_normalization", icon='NORMALIZE_FCURVES', text="Normalize", toggle=True)
        # sub = row.row(align=True)
        # sub.active = st.use_normalization
        # sub.prop(st, "use_auto_normalization", icon='FILE_REFRESH', text="", toggle=True)

        layout.separator_spacer()

        bl_ui.space_dopesheet.dopesheet_filter(layout, context)

        row = layout.row(align=True)
        if st.has_ghost_curves:
            row.operator("graph.ghost_curves_clear", text="", icon="X")
        else:
            row.operator("graph.ghost_curves_create", text="", icon="FCURVE_SNAPSHOT")

        layout.popover(
            panel="GRAPH_PT_filters",
            text="",
            icon="FILTER",
        )

        layout.prop(st, "pivot_point", icon_only=True)

        row = layout.row(align=True)
        if getattr(st, "mode", "") == 'DRIVERS':
            row.prop(tool_settings, "use_snap_driver", text="")
            sub = row.row(align=True)
            sub.popover(
                panel="GRAPH_PT_driver_snapping",
                text="",
            )
        else:
            row.prop(tool_settings, "use_snap_anim", text="")
            sub = row.row(align=True)
            sub.popover(
                panel="GRAPH_PT_snapping",
                text="",
            )

        row = layout.row(align=True)
        row.prop(tool_settings, "use_proportional_fcurve", text="", icon_only=True)
        sub = row.row(align=True)
        sub.active = tool_settings.use_proportional_fcurve
        sub.prop_with_popover(
            tool_settings,
            "proportional_edit_falloff",
            text="",
            icon_only=True,
            panel="GRAPH_PT_proportional_edit",
        )


class DOPESHEET_HT_header(bpy.types.Header):
    bl_space_type = "DOPESHEET_EDITOR"

    def draw(self, context):
        layout = self.layout

        st = context.space_data

        layout.template_header()

        if getattr(st, "mode", "") != "TIMELINE":
            layout.prop(st, "ui_mode", text="")

        if hasattr(bl_ui.space_dopesheet, "DOPESHEET_MT_editor_menus"):
            bl_ui.space_dopesheet.DOPESHEET_MT_editor_menus.draw_collapsible(context, layout)
        DOPESHEET_HT_editor_buttons.draw_header(context, layout)


class DOPESHEET_HT_editor_buttons:

    @classmethod
    def draw_header(cls, context, layout):
        st = context.space_data

        if getattr(st, "mode", "") == "TIMELINE":
            if hasattr(bl_ui.space_dopesheet, "playback_controls"):
                bl_ui.space_dopesheet.playback_controls(layout, context)
            layout.separator()
            cls._draw_overlay_selector(context, layout)
            return

        if getattr(st, "mode", "") in {"ACTION", "SHAPEKEY"} and context.object:
            layout.separator_spacer()
            cls._draw_action_selector(context, layout)

        # Layer management
        if getattr(st, "mode", "") in {"GPENCIL", "GREASEPENCIL"}:
            ob = context.active_object

            enable_but = ob is not None and ob.type in {"GREASEPENCIL", "GPENCIL"}

            row = layout.row(align=True)
            row.enabled = enable_but
            row.operator("grease_pencil.layer_add", icon="ADD", text="")
            row.operator("grease_pencil.layer_remove", icon="REMOVE", text="")
            row.menu("GREASE_PENCIL_MT_grease_pencil_add_layer_extra", icon="DOWNARROW_HLT", text="")

            row = layout.row(align=True)
            row.enabled = enable_but
            row.operator("anim.channels_move", icon="TRIA_UP", text="").direction = "UP"
            row.operator("anim.channels_move", icon="TRIA_DOWN", text="").direction = "DOWN"

            row = layout.row(align=True)
            row.enabled = enable_but
            row.operator("grease_pencil.layer_isolate", icon="RESTRICT_VIEW_ON", text="").affect_visibility = True
            row.operator("grease_pencil.layer_isolate", icon="LOCKED", text="").affect_visibility = False

        layout.separator_spacer()

        if getattr(st, "mode", "") in {"DOPESHEET", "ACTION"}:
            bl_ui.space_dopesheet.dopesheet_filter(layout, context)
        elif getattr(st, "mode", "") in {"GPENCIL", "GREASEPENCIL"}:
            row = layout.row(align=True)
            row.prop(st.dopesheet, "show_only_selected", text="")
            row.prop(st.dopesheet, "show_hidden", text="")

        layout.popover(
            panel="DOPESHEET_PT_filters",
            text="",
            icon="FILTER",
        )

        tool_settings = context.tool_settings

        # Grease Pencil mode doesn't need snapping, as it's frame-aligned only
        if getattr(st, "mode", "") not in {"GPENCIL", "GREASEPENCIL"}:
            row = layout.row(align=True)
            row.prop(tool_settings, "use_snap_anim", text="")
            sub = row.row(align=True)
            sub.popover(
                panel="DOPESHEET_PT_snapping",
                text="",
            )

        row = layout.row(align=True)
        row.prop(tool_settings, "use_proportional_action", text="", icon_only=True)
        sub = row.row(align=True)
        sub.active = tool_settings.use_proportional_action
        sub.prop_with_popover(
            tool_settings,
            "proportional_edit_falloff",
            text="",
            icon_only=True,
            panel="DOPESHEET_PT_proportional_edit",
        )
        
        cls._draw_overlay_selector(context, layout)

    @classmethod
    def _draw_overlay_selector(cls, context, layout):
        st = context.space_data
        if not hasattr(st, "overlays"):
            return
        overlays = st.overlays
        row = layout.row(align=True)
        row.prop(overlays, "show_overlays", text="", icon="OVERLAY")
        sub = row.row(align=True)
        sub.popover(panel="DOPESHEET_PT_overlay", text="")
        sub.active = overlays.show_overlays

    @classmethod
    def _draw_action_selector(cls, context, layout):
        animated_id = cls._get_animated_id(context)
        if not animated_id:
            return

        row = layout.row()
        if animated_id.animation_data and animated_id.animation_data.use_tweak_mode:
            row.enabled = False

        row.template_action(animated_id, new="action.new", unlink="action.unlink")

        adt = animated_id and animated_id.animation_data
        if not adt or getattr(adt, "action", None) is None:
            return

        if hasattr(adt, "action_suitable_slots"):
            row.context_pointer_set("animated_id", animated_id)
            row.template_search(
                adt, "action_slot",
                adt, "action_suitable_slots",
                new="anim.slot_new_for_id",
                unlink="anim.slot_unassign_from_id",
            )
        elif hasattr(adt, "action_slots"):
            row.context_pointer_set("animated_id", animated_id)
            row.template_search(
                adt, "action_slot",
                adt, "action_slots",
                new="anim.slot_new_for_id",
                unlink="anim.slot_unassign_from_id",
            )

    @staticmethod
    def _get_animated_id(context):
        st = context.space_data
        mode = getattr(st, "mode", "")
        if mode == "ACTION":
            return context.object
        elif mode == "SHAPEKEY":
            return getattr(context.object.data, "shape_keys", None)
        else:
            print("Dope Sheet mode '{:s}' not expected to have an Action selector".format(mode))
            return context.object


amp_graph_classes = (
    GRAPH_HT_header,
    # GRAPH_MT_editor_menus,
)

bl_graph_classes = (
    bl_ui.space_graph.GRAPH_HT_header,
    # bl_ui.space_graph.GRAPH_MT_editor_menus,
)

amp_dope_classes = (
    # DOPESHEET_MT_editor_menus,
    DOPESHEET_HT_header,
)


bl_dope_classes = (
    # bl_ui.space_dopesheet.DOPESHEET_MT_editor_menus,
    bl_ui.space_dopesheet.DOPESHEET_HT_header,
)


# def register_blender_dope_top_right_bar():


def toggle_amp_graph_top_right_bar(self, context):
    prefs = bpy.context.preferences.addons[base_package].preferences
    if prefs.toggle_amp_graph_top_right_bar_active:
        try:
            for cls in bl_graph_classes:
                bpy.utils.unregister_class(cls)
            for cls in amp_graph_classes:
                bpy.utils.register_class(cls)
        except (RuntimeError, AttributeError) as e:
            print(f"AniMatePro: Failed to register custom Graph header: {e}")
            for cls in bl_graph_classes:
                try: bpy.utils.register_class(cls)
                except: pass
    else:
        try:
            for cls in amp_graph_classes:
                bpy.utils.unregister_class(cls)
        except (RuntimeError, AttributeError): pass
        for cls in bl_graph_classes:
            try: bpy.utils.register_class(cls)
            except: pass


def toggle_blender_dope_top_right_bar(self, context):
    prefs = bpy.context.preferences.addons[base_package].preferences
    if prefs.toggle_blender_dope_top_right_bar_active:
        try:
            for cls in bl_dope_classes:
                bpy.utils.unregister_class(cls)
            for cls in amp_dope_classes:
                bpy.utils.register_class(cls)
        except (RuntimeError, AttributeError) as e:
            print(f"AniMatePro: Failed to register custom Dopesheet header: {e}")
            for cls in bl_dope_classes:
                try: bpy.utils.register_class(cls)
                except: pass
    else:
        try:
            for cls in amp_dope_classes:
                bpy.utils.unregister_class(cls)
        except (RuntimeError, AttributeError): pass
        for cls in bl_dope_classes:
            try: bpy.utils.register_class(cls)
            except: pass


def register():
    toggle_amp_graph_top_right_bar(None, bpy.context)
    toggle_blender_dope_top_right_bar(None, bpy.context)
    pass


def unregister():
    pass
