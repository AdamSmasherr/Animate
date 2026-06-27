import bpy
import json
import os
import mathutils
from bpy_extras.io_utils import ExportHelper, ImportHelper
from bpy.types import AddonPreferences
from bpy.props import (
    EnumProperty,
    StringProperty,
    BoolProperty,
    FloatProperty,
    IntProperty,
    FloatVectorProperty,
)
from .ui.ui import (
    amp_spacebaraction_interface,
    amp_scrubbing_interface,
    amp_limits_interface,
    amp_text_interface,
)

from .utils import (
    reboot_theme_colors,
    evaluate_amp_triggers,
)
from .utils.customIcons import get_icon, reboot_icons, refresh_icons
from .utils.insert_keyframes import (
    get_3d_view_items,
    get_graph_editor_items,
    get_timeline_dopesheet_items,
)

from .autoKeying.ui import (
    amp_AutoKeying_header_interface,
    amp_AutoKeying_frame_interface,
    amp_AutoKeying_offset_interface,
    amp_AutoKeying_text_interface,
    amp_AutoKeying_theme_colors,
)
from .ui.top_sections import refresh_top_sections
from .ui.blender_ui import toggle_amp_graph_top_right_bar, toggle_blender_dope_top_right_bar
from .ui.top_sections import draw_ui_sections_lists_side_panel
from .anim_poser.anim_silhouette import register_silohuette_button

# from .ui.side_panles_ui import register_action_picker

from . import __package__ as base_package
from . import anim_experimental
from . import register_keymaps
from . import changelog


def toggle_experimental(self, context):
    prefs = bpy.context.preferences.addons[base_package].preferences
    if prefs.experimental:
        anim_experimental.register()
    else:
        anim_experimental.unregister()


def refresh_ui(self, context):
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()


def normalize_auto_save_path(path):
    # Ensure the path ends with .json (normalized at point of use)
    if path and not path.lower().endswith(".json"):
        path += ".json"
    return path


class ButtonItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()
    enable_graph: bpy.props.BoolProperty(
        default=True,
        name="Enable in Graph Editor",
        description="Enable this button in the Graph Editor",
        update=refresh_top_sections,
    )
    enable_dope: bpy.props.BoolProperty(
        default=True,
        name="Enable in Dope Sheet",
        description="Enable this button in the Dope Sheet",
        update=refresh_top_sections,
    )
    visible_graph: bpy.props.BoolProperty(default=True)
    visible_dope: bpy.props.BoolProperty(default=True)

    def to_dict(self):
        return {
            "name": self.name,
            "enable_graph": self.enable_graph,
            "enable_dope": self.enable_dope,
            "visible_graph": self.visible_graph,
            "visible_dope": self.visible_dope,
        }

    def from_dict(self, item_dict):
        for key, value in item_dict.items():
            if hasattr(self, key):
                setattr(self, key, value)


class SectionItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()
    enable_graph: bpy.props.BoolProperty(
        default=True,
        name="Enable in Graph Editor",
        description="Enable this section in the Graph Editor",
        update=refresh_top_sections,
    )
    enable_dope: bpy.props.BoolProperty(
        default=True,
        name="Enable in Dope Sheet",
        description="Enable this section in the Dope Sheet",
        update=refresh_top_sections,
    )
    visible_graph: bpy.props.BoolProperty(default=True)
    visible_dope: bpy.props.BoolProperty(default=True)
    active_button_index: bpy.props.IntProperty(default=0)
    buttons: bpy.props.CollectionProperty(type=ButtonItem)

    def to_dict(self):
        return {
            "name": self.name,
            "enable_graph": self.enable_graph,
            "enable_dope": self.enable_dope,
            "visible_graph": self.visible_graph,
            "visible_dope": self.visible_dope,
            "active_button_index": self.active_button_index,
            "buttons": [button.to_dict() for button in self.buttons],
        }

    def from_dict(self, item_dict):
        for key, value in item_dict.items():
            if key == "buttons":
                self.buttons.clear()
                for button_dict in value:
                    button = self.buttons.add()
                    button.from_dict(button_dict)
            elif hasattr(self, key):
                setattr(self, key, value)


# Transient / runtime-only preference properties that must NOT be serialized on
# export and must be ignored on import (operator state, captured originals, etc.).
_NON_SERIALIZED_PREFS = {
    "auto_save_path",
    "capturing_key",
    "is_scrubbing",
    "jump_already_made",
    "animation_was_playing",
    "initial_mouse_x",
    "initial_frame",
    "has_dragged",
    "is_sensitivity_mode",
    "current_mode",
    "scrubbing_error",
    "preview_range_set_scrub",
    "preview_start_frame",
    "is_mopaths_active",
    "icons_loaded",
    "refreshing_icons",
    "cycle_fcurves_index",
    "deselect_state_index",
    "last_transform_type",
    "solo_fcurve",
    "frame_last_action",
}


def _is_serializable_pref(identifier):
    if identifier.startswith("__") or identifier == "rna_type":
        return False  # Skip internal Blender properties
    if identifier.startswith("original_"):
        return False  # Skip captured-original / transient theme state
    if identifier in _NON_SERIALIZED_PREFS:
        return False  # Skip operator / runtime flags
    return True


class AMP_Preferences(AddonPreferences):
    bl_idname = __package__
    # prefs = bpy.context.preferences.addons[base_package].preferences

    # * ----------------------------- Import / Export -------------------------- * #

    def to_dict(self):
        pref_dict = {}
        for prop in self.bl_rna.properties:
            if not _is_serializable_pref(prop.identifier):
                continue  # Skip internal / transient / runtime properties

            value = getattr(self, prop.identifier)
            # print(
            #     f"Processing property: {prop.identifier}, type: {prop.type}, subtype: {prop.subtype}, value type: {type(value)}"
            # )
            try:
                if prop.type == "COLLECTION":
                    # Serialize each item in the collection
                    pref_dict[prop.identifier] = [item.to_dict() for item in value]
                elif prop.type == "ENUM":
                    pref_dict[prop.identifier] = value
                elif prop.type in {"FLOAT_VECTOR", "INT_VECTOR"}:
                    # Convert to list to make it JSON serializable
                    pref_dict[prop.identifier] = list(value)
                elif prop.type == "FLOAT" and prop.subtype in {"COLOR", "COLOR_GAMMA"}:
                    # Handle color properties
                    pref_dict[prop.identifier] = list(value)
                elif isinstance(value, mathutils.Vector):
                    # Catch any remaining mathutils.Vector instances
                    pref_dict[prop.identifier] = list(value)
                else:
                    # Attempt to serialize value directly
                    json.dumps(value)  # This will raise TypeError if not serializable
                    pref_dict[prop.identifier] = value
            except TypeError as e:
                print(f"Skipping non-serializable property '{prop.identifier}': {e}")
        return pref_dict

    def from_dict(self, pref_dict):
        for prop in self.bl_rna.properties:
            if not _is_serializable_pref(prop.identifier):
                continue  # Skip internal / transient / runtime properties

            if prop.identifier not in pref_dict:
                continue  # Skip missing properties

            value = pref_dict[prop.identifier]

            try:
                if prop.type == "COLLECTION":
                    collection = getattr(self, prop.identifier)
                    collection.clear()
                    for item_dict in value:
                        item = collection.add()
                        item.from_dict(item_dict)
                elif prop.type == "ENUM":
                    # Validate the Enum value before setting
                    if value in [item.identifier for item in prop.enum_items]:
                        setattr(self, prop.identifier, value)
                    else:
                        print(f"Warning: '{value}' is not a valid option for '{prop.identifier}'. Using default.")
                        setattr(self, prop.identifier, prop.default)
                elif prop.type in {"FLOAT_VECTOR", "INT_VECTOR"} or (
                    prop.type == "FLOAT" and prop.subtype in {"COLOR", "COLOR_GAMMA"}
                ):
                    # Assign the list directly
                    setattr(self, prop.identifier, value)
                elif isinstance(getattr(self, prop.identifier), mathutils.Vector):
                    # Assign the list to the vector
                    getattr(self, prop.identifier)[:] = value
                else:
                    setattr(self, prop.identifier, value)
            except Exception as e:
                print(f"Error setting property '{prop.identifier}': {e}")

    auto_save_path: StringProperty(
        name="Auto Save Path",
        description="Path for auto-saving preferences",
        subtype="FILE_PATH",
        default="",
    )

    # * ---------------------------------- * #
    # * AniMate Pro Addon Preferences UI * #
    # * ---------------------------------- * #

    experimental: bpy.props.BoolProperty(
        name="Experimenta Modules and Features",
        description="Enable Experimental Modules and Features",
        default=False,
        update=toggle_experimental,
    )

    debug: bpy.props.BoolProperty(
        default=False,
        name="Debug",
        description="Enable Debugging",
    )

    sections: bpy.props.CollectionProperty(type=SectionItem)
    active_section_index: bpy.props.IntProperty(default=0)

    config_top_panel: bpy.props.BoolProperty(
        name="Configure Top Panel",
        description="Configure the top panel sections and buttons",
        default=True,
    )

    show_category_buttons: bpy.props.BoolProperty(
        name="Show Category Buttons in Top Bar",
        description="Display toggle buttons for each category/section directly in the Top Bar header. "
                    "When enabled, each section (e.g. View, Select, Keyframes, Tools) appears as a "
                    "toggle button. Only sections with active toggles show their tools",
        default=False,
        update=refresh_top_sections,
    )

    jump_to_first_selected_keyframe: BoolProperty(
        name="Jump to First Selected Keyframe",
        description="Jump to the first selected keyframe in the Graph Editor",
        default=True,
    )

    jump_already_made: BoolProperty(
        name="Jump Already Made",
        description="True if the jump to the first selected keyframe was already made",
        default=True,
        update=evaluate_amp_triggers,
    )

    capturing_key: bpy.props.StringProperty()

    playback_loop_only_if_cyclical: BoolProperty(
        name="Loop Only if Cyclical",
        description="Loop the playback only if the current action is cyclical",
        default=True,
    )

    # * ---------------- Scrub ------------------ * #

    scrubbing_key: StringProperty(
        name="Scrubbing Key",
        description="Key for scrubbing the timeline",
        default="SPACE",
    )

    is_scrubbing: BoolProperty(
        name="Is Scrubbing",
        description="True if the timeline is being scrubbed",
        default=False,
    )

    use_lmb_for_scrubbing: BoolProperty(
        name="Use LMB for Scrubbing",
        description="""Scrubbing will not start until LMB is down during the scrubbing operation,
but all the other operations are available""",
        default=False,
    )

    toggle_for_scrubbing: BoolProperty(
        name="Toggle for Scrubbing",
        description="""Toggle the scrubbing instead of holding the key:
        
        - When enabled, the scrubbing will be active when the key is
        pressed and deactivated on ESC, RMB.
        
        - When disabled, the scrubbing will be active when the key is
        pressed and deactivated when the key is released""",
        default=False,
    )

    use_mwheel_to_sensitivity: BoolProperty(
        name="Use Mouse Wheel for Sensitivity",
        description="Use the mouse wheel to change the scrubbing sensitivity",
        default=True,
    )

    add_marker_key: StringProperty(
        name="Add Marker Key",
        description="Key to add a marker",
        default="M",
    )

    remove_marker_keyframe_key: StringProperty(
        name="Remove Marker/Keyframe Key",
        description="Key to remove a Marker or Meyframe in the corresponding mode",
        default="X",
    )

    play_animation_key: StringProperty(
        name="Play",
        description="Key to play or reverse the animation",
        default="Z",
    )

    play_reverse_animation_key: StringProperty(
        name="Play-Reverse",
        description="Key to play or reverse the animation",
        default="SHIFT+Z",
    )

    next_keyframe_key: StringProperty(
        name="Next Keyframe Key",
        description="Key for jumping to the next keyframe",
        default="D",
    )

    prev_keyframe_key: StringProperty(
        name="Previous Keyframe Key",
        description="Key for jumping to the previous keyframe",
        default="A",
    )

    next_frame_key: StringProperty(
        name="Next Frame Key",
        description="Key for moving to the next frame",
        default="E",
    )

    prev_frame_key: StringProperty(
        name="Previous Frame Key",
        description="Key for moving to the previous frame",
        default="Q",
    )

    scrub_nudge_key_L: StringProperty(
        name="Nudge Left",
        description="Key for Anin Nudger Left",
        default="SHIFT+Q",
    )

    scrub_nudge_key_R: StringProperty(
        name="Nudge Right",
        description="Key for Anin Nudger Right",
        default="SHIFT+E",
    )

    insert_keyframe_key: StringProperty(
        name="Insert Keyframe Key",
        description="Key for inserting a keyframe",
        default="F",
    )

    first_frame_key: StringProperty(
        name="First Frame Key",
        description="Key for jumping to the first frame of the animation",
        default="S",
    )

    last_frame_key: StringProperty(
        name="Last Frame Key",
        description="Key for jumping to the last frame of the animation",
        default="W",
    )

    gui_help_key: StringProperty(
        name="GUI Help Key",
        description="Key for opening the GUI Help",
        default="H",
    )

    limit_to_range_key: StringProperty(
        name="Limit to Range Key",
        description="Key for limiting the timeline to the range of the selected action",
        default="L",
    )

    breakdown_pose_key: StringProperty(
        name="Breakdown Pose Key",
        description="Key for creating a breakdown pose",
        default="ONE",
    )

    blend_to_neighbor_key: StringProperty(
        name="Blend to Neighbor Key",
        description="Key for blending to the neighboring keyframe",
        default="TWO",
    )

    relax_to_breakdown_key: StringProperty(
        name="Relax to Breakdown Key",
        description="Key for relaxing the pose to the breakdown pose",
        default="THREE",
    )

    set_preview_range_key: StringProperty(
        name="Set Preview Range Key",
        description="Key for setting the preview range to the selected action",
        default="R",
    )

    quick_anim_offset_key: StringProperty(
        name="Set Quick AnimOffset Key",
        description="Key for toggling the Quick AnimOffset",
        default="G",
    )

    quick_anim_offset_blend_key: StringProperty(
        name="Quick AnimOffset Blend Key",
        description="Key for modifying the mask blend range while AnimOffset mask is active",
        default="B",
    )

    quick_anim_offset_mask_key: StringProperty(
        name="Quick AnimOffset Mask Key",
        description="Key for modifying the mask range while AnimOffset mask is active",
        default="M",
    )

    copy_pose_key: StringProperty(
        name="Set Copy Pose Key",
        description="Key to copy the current pose for selected bones",
        default="C",
    )

    paste_pose_key: StringProperty(
        name="Set Paste Pose Key",
        description="Key to paste the copied pose",
        default="V",
    )

    animation_was_playing: BoolProperty(
        name="Animation Was Playing",
        description="True if the animation was playing when the scrubbing started",
        default=False,
    )

    # ** ----------------- Keymaps ----------------- ** #

    # graph_editor_lock_transforms_kmi_active: BoolProperty(
    #     name="Toggle Lock Transforms",
    #     description="Lock the transforms for the Graph Editor Keyframe Translation",
    #     default=True,
    #     update=graph_editor_lock_transforms_kmi_active_toggle,
    # )

    graph_editor_jump_to_keyframe_kmi_active: BoolProperty(
        name="Jump to Keyframe",
        description="Jump to the keyframe when selecting it in the Graph Editor",
        default=False,
        update=register_keymaps.graph_editor_jump_to_keyframe_kmi_active_toggle,
    )

    graph_editor_jump_to_keyframe_ctrl_g_kmi_active: BoolProperty(
        name="Box select to first selected Keyframe",
        description="CTRL+G Jump to first selected Keyframe after box select",
        default=False,
        update=register_keymaps.graph_editor_jump_to_keyframe_ctrl_g_kmi_toggle,
    )

    scrub_timeline_keymap_kmi_active: BoolProperty(
        name="Anim Scrub - Timeline",
        description="Timeline scrubbing functionality (Space)",
        default=True,
        update=register_keymaps.scrub_timeline_kmi_active_toggle,
    )

    graph_dope_select_fcurves_kmi_active: BoolProperty(
        name="Select/Transform Fcurves Keymaps (Graph Editor: G,R,S,1,2,3,4)",
        description="Select Fcurves in the Graph Editor and Dope Sheet",
        default=False,
        update=register_keymaps.key_graph_dope_select_fcurves_toggle,
    )

    all_insert_keyframes_kmi_active: BoolProperty(
        name="Insert Keyframes (I)",
        description="Insert Keyframes in the 3D View, Graph Editor and Dope Sheet",
        default=False,
        update=register_keymaps.key_all_insert_keyframes_toggle,
    )

    all_world_transforms_kmi_active: BoolProperty(
        name="Copy World Transforms (ALT C, ALT V - Needs Transformator)",
        description="World Transforms of the selected objct or bone",
        default=False,
        update=register_keymaps.key_all_world_transforms_toggle,
    )

    graph_anim_tools_kmi_active: BoolProperty(
        name="Graph Anim Tools (Graph Editor, Y, shift-Y, ctrl-Y)",
        description="Graph Editor Animation Tools (Sculpt, Lattice, TimeWarper)",
        default=True,
        update=register_keymaps.key_graph_anim_tools_toggle,
    )

    all_autokeying_kmi_active: BoolProperty(
        name="Toggle AutoKeying (General: D)",
        description="AutoKeying in the Graph Editor and Dope Sheet",
        default=True,
        update=register_keymaps.key_all_autokeying_toggle,
    )

    graph_editor_isolate_curves_kmi_active: BoolProperty(
        name="Toggle Isolate Curves (Graph Editor: W)",
        description="Isolate Curves in the Graph Editor",
        default=True,
        update=register_keymaps.key_graph_editor_isolate_curves_toggle,
    )

    graph_editor_zoom_curves_kmi_active: BoolProperty(
        name="Toggle Zoom Curves (Graph Editor: Z, shift-Z)",
        description="Zoom Curves in the Graph Editor",
        default=True,
        update=register_keymaps.key_graph_editor_zoom_curves_toggle,
    )

    # ** ----------------- Preferences menus ----------------- ** #

    # Define the enum property for modes
    preferences_sections: EnumProperty(
        name="Mode",
        description="Select the mode to display",
        items=[
            (
                "CONFIGURATION",
                "Configuration",
                "Show configuration options",
                "SETTINGS",
                0,
            ),
            (
                "KEYMAPS",
                "Keymaps",
                "Show keymaps",
                "EVENT_SPACEKEY",
                1,
            ),
            (
                "CHANGELOG",
                "Changelog",
                "Show changelog",
                "INFO",
                2,
            ),
            (
                "SUPPORT",
                "Support",
                "Show support information",
                "QUESTION",
                3,
            ),
        ],
        default="CONFIGURATION",
    )

    config_sections: EnumProperty(
        name="Config Sections",
        description="Select the section to configure",
        items=[
            (
                "THEME",
                "General Theme",
                "Show the AniMatePro Theme options",
                "",
                0,
            ),
            (
                "TOP BAR",
                "Top Bar Buttons",
                "Show the top bar buttons",
                "",
                1,
            ),
            (
                "TIMELINE SCRUBBING",
                "Timeline Scrubbing",
                "Show the timeline scrubbing options",
                "",
                2,
            ),
            (
                "AUTOKEYING",
                "AutoKeying",
                "Show the AutoKeying options",
                "",
                3,
            ),
            (
                "TIMEWARP",
                "Anim TimeWarper",
                "Show the TimeWarper options",
                "",
                4,
            ),
            (
                "SCULPT",
                "Anim Sculpt",
                "Show the Anim Sculpt options",
                "",
                5,
            ),
            (
                "LATTICE",
                "Anim Lattice",
                "Show the Anim Lattice options",
                "",
                6,
            ),
            (
                "OFFSET",
                "Anim Offset",
                "Show the Anim Offset options",
                "",
                7,
            ),
            (
                "PIE",
                "Anim Pie",
                "Show the Anim Pie options",
                "",
                8,
            ),
            (
                "EXPETIMENTAL",
                "Experimental",
                "Show the Experimental options",
                "",
                9,
            ),
            (
                "EXPORT/IMPORT",
                "Export / Import",
                "Show the Export / Import options",
                "",
                10,
            ),
        ],
        default="THEME",
    )

    config_keymaps: EnumProperty(
        name="Config Keymaps",
        description="Select the keymap to configure",
        items=[
            (
                "RECOMMENDED",
                "Recommended",
                "Show the recommended keymaps",
                "",
                0,
            ),
            (
                "ALL",
                "All",
                "Show all the keymaps",
                "",
                1,
            ),
            (
                "SCRUBBING",
                "Scrubbing",
                "Show the scrubbing keymaps",
                "",
                2,
            ),
            (
                "AUTOKEYING",
                "AutoKeying",
                "Show the AutoKeying keymaps",
                "",
                3,
            ),
            (
                "TIMEWARP",
                "Anim TimeWarp",
                "Show the TimeWarp keymaps",
                "",
                4,
            ),
            (
                "SCULPT",
                "Anim Sculpt",
                "Show the Anim Sculpt keymaps",
                "",
                5,
            ),
            (
                "LATTICE",
                "Anim Lattice",
                "Show the Anim Lattice keymaps",
                "",
                6,
            ),
        ],
        default="RECOMMENDED",
    )

    default_3d_view_insert_keyframe: EnumProperty(
        name="3D View Default Method",
        description="Default method for inserting keyframes in 3D View",
        items=get_3d_view_items,
    )

    default_graph_editor_insert_keyframe: EnumProperty(
        name="Graph Editor Default Method",
        description="Default method for inserting keyframes in Graph Editor",
        items=get_graph_editor_items,
    )

    default_timeline_dopesheet_insert_keyframe: EnumProperty(
        name="Timeline/Dopesheet Default Method",
        description="Default method for inserting keyframes in Timeline/Dopesheet",
        items=get_timeline_dopesheet_items,
    )

    ao_fast_offset: BoolProperty(
        name="Fast calculation",
        description="Do not redraw the curves while tweaking the aciton while AnimOffset is active",
        default=False,
    )

    # * --------------------------------------- * #
    # * Autokeying Addon Preferences Properties * #
    # * --------------------------------------- * #

    show_settings: bpy.props.BoolProperty(default=False)

    text_position: bpy.props.EnumProperty(
        name="Text Position",
        description="Position of the text on the screen",
        items=[
            ("B", "Bottom", "", 0),
            ("BR", "Bottom-Right", "", 1),
            ("R", "Right", "", 2),
            ("TR", "Top-Right", "", 3),
            ("T", "Top", "", 4),
            ("TL", "Top-Left", "", 5),
            ("L", "Left", "", 6),
            ("BL", "Bottom-Left", "", 7),
        ],
        default="B",
    )

    include_n_panel_width: bpy.props.BoolProperty(default=False, name="Include N-panel Width")

    tool_settings_height: bpy.props.IntProperty(
        default=26,
        max=100,
        min=0,
        name="Frame top extra offset if the tool settings is visible in the viewport",
    )

    n_panel_bar: bpy.props.IntProperty(
        default=21,
        max=100,
        min=0,
        name="Frame right extra offset if the n-panel is uncollapsed",
    )

    viewport_text: bpy.props.BoolProperty(default=False)

    text_content: bpy.props.StringProperty(default="● REC")

    text_size: bpy.props.IntProperty(
        min=5,
        max=100,
        default=15,
        name="Text Size",
        description="Text Size in units",
    )

    corners_length: bpy.props.FloatProperty(min=0.02, max=0.1, default=0.02)

    viewport_frame: bpy.props.BoolProperty(default=True)

    frame_offset: bpy.props.IntProperty(
        min=0,
        max=50,
        default=4,
        name="Frame Offset",
        description="Frame Offset in pixels",
    )

    text_offset: bpy.props.IntProperty(
        min=0,
        max=100,
        default=10,
        name="Text Offset",
        description="Text Offset in pixels",
    )

    rec_text_color: bpy.props.FloatVectorProperty(subtype="COLOR", default=(0.6, 0, 0, 1), size=4, min=0.0, max=1.0)

    # * ----------------------------- Frame Viewport -------------------------- * #

    frame_color: bpy.props.FloatVectorProperty(subtype="COLOR", default=(0.6, 0, 0, 1), size=4, min=0.0, max=1.0)

    frame_inner: bpy.props.BoolProperty(default=True)

    frame_width: bpy.props.IntProperty(
        min=1,
        max=100,
        default=2,
        name="Frame Width",
        description="Frame Width in pixels",
    )

    frame_outter: bpy.props.BoolProperty(default=False)

    frame_outter_color: bpy.props.FloatVectorProperty(
        subtype="COLOR", default=(0.2, 0.15, 0.15, 0.4), size=4, min=0.0, max=1.0
    )

    # * ----------------------------- Frame Editors -------------------------- * #

    frame_dopesheet: bpy.props.BoolProperty(
        default=False,
        description="Draw frame in Dope Sheet",
    )

    frame_grapheditor: bpy.props.BoolProperty(
        default=False,
        description="Draw frame in Graph Editor",
    )

    frame_nla: bpy.props.BoolProperty(
        default=False,
        description="Draw frame in Nonlinear Animator",
    )

    frame_width_editors: bpy.props.IntProperty(
        min=1,
        max=50,
        default=2,
        name="Frame Width Editors",
        description="Frame Width Editors in pixels",
    )

    frame_offset_editors: bpy.props.IntProperty(
        min=1,
        max=50,
        default=4,
        name="Frame Offset Editors",
        description="Frame Offset Editors in pixels",
    )

    frame_top_offset_editors: bpy.props.IntProperty(
        min=0,
        max=100,
        default=26,
        name="Frame Top Offset Editors",
        description="Frame Top Offset Editors in pixels",
    )

    # * ----------------------------- AutoKeying Viewport -------------------------- * #

    autoKeying_viewport_text_options_expand: bpy.props.BoolProperty(
        name="Frame Options",
        description="expand / collapse options",
        default=False,
    )

    autoKeying_viewport_frame_options_expand: bpy.props.BoolProperty(
        name="Text Options",
        description="expand / collapse options",
        default=False,
    )

    autoKeying_viewport_offsets_options_expand: bpy.props.BoolProperty(
        name="Offsets Options",
        description="expand / collapse options",
        default=False,
    )

    autokeying_viewport_theme_options_expand: bpy.props.BoolProperty(
        name="Theme Options",
        description="expand / collapse options",
        default=False,
    )

    # * ----------------------------- Selection Colors -------------------------- * #

    autokeying_selection_color_use: BoolProperty(
        name="Change Selection Color",
        description="Change the outline color of the selected object when AutoKeying is active",
        default=False,
        update=reboot_theme_colors,
    )

    autokeying_selection_color_on: FloatVectorProperty(
        name="Highlight Selectiactive",
        description="The color of the Selection when AutoKeying is active",
        subtype="COLOR_GAMMA",
        size=3,
        default=(0.6, 0, 0),
        min=0.0,
        max=1.0,
    )

    # * ----------------------------- Pose Bone Colors -------------------------- * #

    autokeying_posebone_color_use: BoolProperty(
        name="Highlight Pose Bone",
        description="Change the color of the selected Pose Bones when AutoKeying is active",
        default=False,
        update=reboot_theme_colors,
    )

    autokeying_posebone_color_on: FloatVectorProperty(
        name="Highlight Pose Bone Color",
        description="The color of the selected Pose Bones when AutoKeying is active",
        subtype="COLOR_GAMMA",
        size=3,
        default=(0.6, 0, 0),
        min=0.0,
        max=1.0,
    )

    # * ----------------------------- Playhead Colors -------------------------- * #

    autokeying_playhead_color_use: BoolProperty(
        name="Highlight Playhead",
        description="Change the color of the playhead when AutoKeying is active",
        default=False,
        update=reboot_theme_colors,
    )

    autokeying_playhead_color_on: FloatVectorProperty(
        name="Highlight Playhead Selection Color",
        description="The color of the Playhead when AutoKeying is active",
        subtype="COLOR_GAMMA",
        size=3,
        default=(0.6, 0, 0),
        min=0.0,
        max=1.0,
    )

    # * ----------------------------- Header Colors -------------------------- * #

    autokeying_header_color_use: BoolProperty(
        name="Highlight Header",
        description="Change the color of the header when AutoKeying is active",
        default=False,
        update=reboot_theme_colors,
    )

    autokeying_header_color_on: FloatVectorProperty(
        name="Highlight Header Color",
        description="The color of the Viewport Header when AutoKeying is active",
        subtype="COLOR_GAMMA",
        size=4,
        default=(0.3, 0.1, 0.1, 0.9),
        min=0.0,
        max=1.0,
    )

    autokeying_header_3dview_color_use: BoolProperty(
        name="Highlight 3D View Header",
        description="Change the color of the 3D View Header when AutoKeying is active",
        default=True,
        update=reboot_theme_colors,
    )

    autokeying_header_dopesheet_color_use: BoolProperty(
        name="Highlight Dopesheet Header",
        description="Change the color of the Dopesheet Header when AutoKeying is active",
        default=True,
        update=reboot_theme_colors,
    )

    autokeying_header_graph_color_use: BoolProperty(
        name="Highlight Graph Editor Header",
        description="Change the color of the Graph Editor Header when AutoKeying is active",
        default=True,
        update=reboot_theme_colors,
    )

    autokeying_header_nla_color_use: BoolProperty(
        name="Highlight NLA Editor Header",
        description="Change the color of the NLA Editor Header when AutoKeying is active",
        default=True,
        update=reboot_theme_colors,
    )

    # * ----------------------------- FCurves options -------------------------- * #

    zoom_to_visible_curve: BoolProperty(
        name="Zoom to Visible FCurves",
        description="""Zoom to the visible curves in the Graph Editor
Recommended when working with sorter cyclical animations
to keep a general view of all the fcurves of the whole 
action and frame the visible curves""",
        default=False,
    )

    smart_zoom: BoolProperty(
        name="Smart Zoom",
        description="""Zoom to the keyframes around the current frame
Recommended when working with longer non cyclical animations
to zoom in onto a reasonable portion of the action and frame
all the values for the visible curves""",
        default=False,
    )

    frame_range_smart_zoom: IntProperty(
        name="Frame Range to Zoom to",
        description="Frame range to zoom to in the Editors",
        default=15,
        min=2,
    )

    isolate_fcurves: BoolProperty(
        name="Isolate Fcurves",
        description="Isolate the selected Fcurves",
        default=True,
    )

    cycle_fcurves: BoolProperty(
        name="Cycle Fcurves",
        description="Cycle through the selected Fcurves",
        default=False,
    )

    cycle_fcurves_index: IntProperty(
        name="Cycle Index", default=-1, description="Current index in the F-Curve component cycle"
    )

    deselect_state_index: bpy.props.IntProperty(
        name="Select Index", default=-1, description="Index to track cycling through F-Curves"
    )

    last_transform_type: bpy.props.StringProperty(
        name="Last Transform Type", default="", description="Last selected transform type"
    )

    expand_curve_groups: BoolProperty(
        name="Collapse / Expand",
        description="Collapse / Expand all the curve groups in the Graph Editor",
        default=True,
    )

    icons_set: EnumProperty(
        name="Icons Set",
        description="Select the set of icons to use",
        items=[
            ("icons_grey", "Grey", "Use monochromatic icons", "COLORSET_13_VEC", 0),
            ("icons_tint", "Tint", "Use tinted icons", "SEQUENCE_COLOR_02", 1),
            ("icons_highlight", "Highlight", "Use highlighted icons", "KEYTYPE_MOVING_HOLD_VEC", 2),
            ("icons_black", "Black", "Use Black on White icons", "COLORSET_10_VEC", 3),
        ],
        default="icons_grey",
        update=reboot_icons,
    )

    refreshing_icons: BoolProperty(
        name="Refresh Icons",
        description="Refresh the icons",
        default=False,
        update=refresh_icons,
    )

    original_theme_captured: BoolProperty(default=False)
    original_dopesheet_header: bpy.props.StringProperty(default="")
    original_graph_header: bpy.props.StringProperty(default="")
    original_nla_header: bpy.props.StringProperty(default="")
    original_object_active: bpy.props.StringProperty(default="")
    original_bone_pose_active: bpy.props.StringProperty(default="")
    original_header: bpy.props.StringProperty(default="")
    original_frame_current: bpy.props.StringProperty(default="")
    original_dopesheet_frame_current: bpy.props.StringProperty(default="")
    original_graph_frame_current: bpy.props.StringProperty(default="")
    original_nla_frame_current: bpy.props.StringProperty(default="")

    # * ----------------------------- Scrubbing properties -------------------------- * #

    drag_threshold: IntProperty(
        name="Drag Threshold",
        description="Minimum mouse movement in pixels to initiate a drag",
        default=5,
        min=1,
        max=100,
    )

    timeline_sensitivity: FloatProperty(
        name="Timeline Sensitivity",
        description="Sensitivity of timeline scrubbing",
        default=0.5,
        min=0.01,
        max=2,
    )

    limit_to_active_range: BoolProperty(
        name="Limit to Active Range",
        description="Limit scrubbing to the active frame range",
        default=True,
    )

    timeline_gui_toggle: BoolProperty(
        name="Toggle GUI",
        description="Toggle the display of the GUI help",
        default=False,
    )

    timeline_gui_offset: FloatProperty(
        name="Timeline GUI Offset",
        description="Offset for the timeline GUI in pixels",
        default=0.0,
    )

    timeline_gui_color: FloatVectorProperty(
        name="GUI Color", default=(1.0, 1.0, 1.0), subtype="COLOR", min=0.0, max=1.0
    )

    timeline_gui_text_size: IntProperty(
        name="GUI Text Size",
        description="Text size for the timeline GUI",
        default=10,  # Default size
        min=1,
        max=50,
    )
    initial_mouse_x: FloatProperty(name="Initial Mouse X")

    initial_frame: IntProperty(name="Initial Frame")

    has_dragged: BoolProperty(name="Has Dragged", default=False)

    is_sensitivity_mode: BoolProperty(name="Is Sensitivity Mode", default=False)

    show_frame_number: BoolProperty(name="Show Frame Number at cursor", default=True)

    current_mode: StringProperty(name="Current Mode", default="SCRUBBING")

    scrubbing_error: StringProperty(name="Scrubbing errors", default="")

    text_color: FloatVectorProperty(
        name="Text Color",
        subtype="COLOR",
        size=4,
        default=(1.0, 1.0, 1.0, 1.0),
        min=0.0,
        max=1.0,
        description="Color for the text",
    )

    accent_color: FloatVectorProperty(
        name="Accent Color",
        subtype="COLOR",
        size=4,
        default=(1.0, 0.5, 0.0, 1.0),
        min=0.0,
        max=1.0,
        description="Accent color for the GUI",
    )
    text_size: IntProperty(
        name="Text Size",
        description="Size of the text in the GUI",
        default=12,
        min=1,
        max=100,
    )

    mode_options = [
        ("PLAY", "Play", "Play Animation", "PLAY", 0),
        ("TOOLBAR", "Toolbar", "Show Toolbar", "TOOL_SETTINGS", 1),
        ("SEARCH", "Search", "Search Menu", "VIEWZOOM", 2),
        ("NONE", "None", "No Action", "X", 3),
    ]

    mode: EnumProperty(
        name="Spacebar Action",
        description="Select the Spacebar action",
        items=mode_options,
        default="PLAY",
    )

    lock_text_in_place: BoolProperty(
        name="Lock Text While Scrubbing",
        description="Whether to move frames text while dragging the mouse",
        default=True,
    )

    lock_vertical_movement: BoolProperty(
        name="Allow Vertical Movement",
        description="Allow the drawn text to follow the mouse's vertical movement",
        default=True,
    )

    allow_horizontal_movement: BoolProperty(
        name="Allow Horizontal Movement",
        description="Allow the drawn text to follow the mouse's horizontal movement",
        default=True,
    )

    preview_range_set_scrub: BoolProperty(
        name="Operation Started",
        description="Flag to indicate if the preview range setting operation has started",
        default=False,
    )

    preview_start_frame: IntProperty(
        name="Preview Start Frame",
        description="Frame number where the preview range starts",
        default=1,
    )

    frame_last_action: BoolProperty(
        name="Frame Last Action",
        description="Zooming last action on the Editors",
        default=False,
    )

    solo_fcurve: bpy.props.BoolProperty(default=False, name="Solo Fcurve for select curves operator")
    set_keyframe_value: bpy.props.FloatProperty(
        default=1.0, name="Set Value", description="Set the value of all selected keframes"
    )

    select_keyframes_on_current_frame: bpy.props.BoolProperty(
        name="Scrubbing: Select Keyframes on Frame",
        description="Select all the keyframes on the current frame at the end of scrubbing",
        default=False,
    )

    icons_loaded: bpy.props.BoolProperty(default=False, name="Icons Loaded")

    # * ----------------------------- Motion Path settings -------------------------- * #

    realtime_mopaths_timer_interval: bpy.props.FloatProperty(
        name="Timer Interval",
        description="""Time interval in seconds between motion path updates
Use with caution: lower values will slow down Blender""",
        default=0.1,
        min=0.01,
        max=2.0,
    )

    realtime_mograph: bpy.props.BoolProperty(
        name="Realtime Mograph",
        description="Update motion paths in real-time as keyframes or selected element move",
        default=True,
    )

    clear_previous: bpy.props.BoolProperty(
        name="Clear Previous Paths",
        description="Clear previous motion paths before updating",
        default=False,
    )

    display_options: bpy.props.BoolProperty(
        name="Display Options",
        description="Display options for motion paths",
        default=False,
    )

    is_mopaths_active: bpy.props.BoolProperty(
        name="Is Operator Running",
        description="Flag to check if the motion paths operator is active",
        default=False,
        update=refresh_ui,
    )
    # * ----------------------------- Time Warper -------------------------- * #

    tw_realtime_time_warp_updates: bpy.props.BoolProperty(
        name="Realtime Time Warp Updates",
        description="Update the keyframes in real-time during drag",
        default=True,
    )

    tw_snap_to_frame: bpy.props.BoolProperty(
        name="Snap to Frame",
        description="Snap the time warper to the nearest frame",
        default=True,
    )

    tw_topbar_color: bpy.props.FloatVectorProperty(
        name="Top Bar Color",
        subtype="COLOR",
        size=4,
        default=(1.0, 0.25, 0.0, 0.3),
        min=0.0,
        max=1.0,
        description="Color for the time warper pin",
    )

    tw_pin_color: bpy.props.FloatVectorProperty(
        name="Pin Color",
        subtype="COLOR",
        size=4,
        default=(1.0, 0.5, 0.0, 1.0),
        min=0.0,
        max=1.0,
        description="Color for the time warper pin",
    )

    tw_bar_color: bpy.props.FloatVectorProperty(
        name="Bar Color",
        subtype="COLOR",
        size=4,
        default=(0.8, 0.25, 0.0, 0.5),
        min=0.0,
        max=1.0,
        description="Color for the time warper bar",
    )

    tw_easing_color: bpy.props.FloatVectorProperty(
        name="Easing Color",
        subtype="COLOR",
        size=4,
        default=(0.6, 0.125, 0.0, 0.5),
        min=0.0,
        max=1.0,
        description="Color for the time warper easing",
    )

    # * ----------------------------- Anim_Poser -------------------------- * #
    poser_foreground_color: bpy.props.FloatVectorProperty(
        name="Foreground Color",
        subtype="COLOR",
        size=3,
        default=(0.0, 0.0, 0.0),
        min=0.0,
        max=1.0,
        description="Silouette foreground color",
    )

    poser_background_color: bpy.props.FloatVectorProperty(
        name="Background Color",
        subtype="COLOR",
        size=3,
        default=(0.8, 0.8, 0.8),
        min=0.0,
        max=1.0,
        description="Silouette background color",
    )

    poser_silohuette_button: bpy.props.BoolProperty(
        name="Silouette Button",
        description="Show the Poser Silouette button in the header",
        default=True,
        update=register_silohuette_button,
    )

    isoalte_char_include_armature: bpy.props.BoolProperty(
        name="include Armature",
        description="Include objects with the armature modifier to the current armature",
        default=True,
    )

    isoalte_char_include_modifiers: bpy.props.BoolProperty(
        name="include Modifiers",
        description="Include objects with other modifier to the current armature",
        default=True,
    )

    isoalte_char_include_constraints: bpy.props.BoolProperty(
        name="include Constraints",
        description="Include objects with constraints to the current armature",
        default=True,
    )

    isoalte_char_limit_to_selectable: bpy.props.BoolProperty(
        name="Limit to Visible",
        description="Limit the isolation to the visible and selectable objects",
        default=True,
    )

    isolate_char_include_children: bpy.props.BoolProperty(
        name="Include Children",
        description="Include the children of objects visible, with modifiers or constraints",
        default=True,
    )

    # * ----------------------------- Appending UI Buttons -------------------------- * #

    toggle_blender_dope_top_right_bar_active: bpy.props.BoolProperty(
        name="Better DopeSheet default Top Buttons",
        description="Better version of the Dope Sheet Top Right Bar",
        default=False,
        update=toggle_blender_dope_top_right_bar,
    )
    toggle_amp_graph_top_right_bar_active: bpy.props.BoolProperty(
        name="Better Graph Editor default Top Buttons",
        description="Better version of the Graph Editor Top Right Bar",
        default=True,
        update=toggle_amp_graph_top_right_bar,
    )
    # # * ----------------------------- Appending UI Buttons -------------------------- * #

    # action_picker_dopesheet: bpy.props.BoolProperty(
    #     name="Action Picker Dopesheet",
    #     description="Action Picker in the Dopesheet",
    #     default=True,
    #     update=register_action_picker,
    # )

    # action_picker_graph: bpy.props.BoolProperty(
    #     name="Action Picker Graph",
    #     description="Action Picker in the Graph Editor",
    #     default=True,
    #     update=register_action_picker,
    # )

    # * ---------------------------- Draw Section ------------------------- * #

    def draw(self, context):
        draw_preferences(self, context)


def draw_preferences(self, context):
    layout = self.layout

    # Draw the mode selector
    top_row = layout.row()
    top_row.scale_y = 1.5
    top_row.prop(self, "preferences_sections", expand=True)

    # Conditionally display content based on selected mode
    if self.preferences_sections == "CONFIGURATION":

        layout.separator()

        config_split = layout.split(factor=0.25)
        col1 = config_split.column()
        col1.scale_y = 1.5
        col1.prop(self, "config_sections", expand=True)

        col2 = config_split.column()

        if self.config_sections == "THEME":
            header = draw_section_header(col2, context, "Theme:")
            header.label(text="AniMatePro Theme WIP")
            draw_theme_header(self, header, context)

        elif self.config_sections == "TOP BAR":
            header = draw_section_header(col2, context, "Top Bar:")
            draw_top_bar_preferences(self, header, context)

        elif self.config_sections == "TIMELINE SCRUBBING":
            header = draw_section_header(col2, context, "Timeline Scrubbing:", draw_scrubbing_keymap)
            draw_timeline_tools_preferences(header, context)

        elif self.config_sections == "AUTOKEYING":
            header = draw_section_header(col2, context, "AutoKeying:", draw_autokeying_keymap)
            draw_autokeying_preferences(header, context)

        elif self.config_sections == "TIMEWARP":
            header = draw_section_header(col2, context, "Time Warper:", draw_timewarp_keymap)
            draw_timewarper_preferences(header, context)

        elif self.config_sections == "SCULPT":
            header = draw_section_header(col2, context, "Anim Sculpt:", draw_sculpt_keymap)
            header.label(text="Anim Sculpt options WIP")

        elif self.config_sections == "LATTICE":
            header = draw_section_header(col2, context, "Anim Lattice:", draw_lattice_keymap)
            header.label(text="Anim Lattice options WIP")

        elif self.config_sections == "OFFSET":
            header = draw_section_header(col2, context, "Anim Offset:")
            draw_anim_offset_preferences(header, context)

        elif self.config_sections == "PIE":
            header = draw_section_header(col2, context, "Anim Pie:")
            header.label(text="Anim Pie options WIP")

        elif self.config_sections == "EXPETIMENTAL":
            header = draw_section_header(col2, context, "Experimental:")
            header.label(text="For advanced testing and development purposes only")
            header.prop(self, "experimental")
            header.prop(self, "debug")

        elif self.config_sections == "EXPORT/IMPORT":
            prefs = self
            header = draw_section_header(col2, context, "Export / Import:")
            draw_import_export_preferences(prefs, header, context)

    elif self.preferences_sections == "KEYMAPS":

        layout.separator()

        # config_keymaps
        config_split = layout.split(factor=0.25)
        col1 = config_split.column()
        col1.scale_y = 1.5
        col1.prop(self, "config_keymaps", expand=True)

        all_keymaps = self.config_keymaps == "ALL"

        col2 = config_split.column()
        if self.config_keymaps == "RECOMMENDED":
            header = draw_section_header(col2, context, "Recommended Keymaps:")
            draw_recommend_keymaps(self, header, context)
        if self.config_keymaps == "SCRUBBING" or all_keymaps:
            draw_scrubbing_keymap(col2, context)
        if self.config_keymaps == "AUTOKEYING" or all_keymaps:
            draw_autokeying_keymap(col2, context)
        if self.config_keymaps == "TIMEWARP" or all_keymaps:
            draw_timewarp_keymap(col2, context)
        if self.config_keymaps == "SCULPT" or all_keymaps:
            draw_sculpt_keymap(col2, context)
        if self.config_keymaps == "LATTICE" or all_keymaps:
            draw_lattice_keymap(col2, context)

    elif self.preferences_sections == "CHANGELOG":

        layout.separator()
        changelog.draw_changelog(layout, context)

    elif self.preferences_sections == "SUPPORT":

        layout.separator()
        draw_support_section(layout)


def draw_theme_header(self, layout, context):
    layout.label(text="AniMatePro General Theme Properties (WIP)")


def draw_section_header(layout, context, text, draw_keymap=None):
    box = layout.box()
    row = box.row()
    row.scale_y = 1.5

    title_row = row.row()
    title_row.scale_y = 1
    title_row.alignment = "LEFT"
    row.label(text=text, **get_icon("AniMateProContact"))

    if draw_keymap:
        keymap_row = row.row()
        keymap_row.alignment = "RIGHT"
        keymap_icon = "DOWNARROW_HLT" if changelog.panels_visibility.get(str(draw_keymap), False) else "EVENT_RETURN"
        keymap_prop = keymap_row.operator(
            "ui.amp_toggle_panels_visibility",
            text="",
            icon=keymap_icon,
        )
        keymap_prop.version = str(draw_keymap)
        if changelog.panels_visibility.get(str(draw_keymap), False):
            draw_keymap(layout, context)

    layout.separator(factor=2)

    body_row = layout.row()
    empty_col = body_row.column()
    empty_col.scale_x = 0.5
    empty_col.label(text="", icon="BLANK1")
    body_col = body_row.column()

    layout.separator(factor=2)

    return body_col


def draw_import_export_preferences(self, layout, context):
    prefs = self

    layout.label(text="Choose Folder:")
    row = layout.row()
    row.operator("amp.export_preferences", text="Export AniMate Pro Preferences", **get_icon("EXPORT"))
    row.operator("amp.import_preferences", text="Import AniMate Pro Preferences", **get_icon("IMPORT"))

    layout.separator()

    layout.label(text="Default path:")
    row = layout.row()
    row.operator("amp.auto_save_preferences", text="Quick Export", icon="FOLDER_REDIRECT")
    row.prop(prefs, "auto_save_path", text="")


def draw_recommend_keymaps(self, layout, context):
    prefs = self

    layout.label(text="AniMatePro Modules:")
    layout.prop(prefs, "graph_anim_tools_kmi_active")
    layout.prop(prefs, "all_autokeying_kmi_active")

    layout.separator()
    layout.prop(prefs, "scrub_timeline_keymap_kmi_active")

    layout.separator()
    layout.label(text="Graph Editor Zoom:")
    layout.prop(prefs, "graph_editor_isolate_curves_kmi_active")
    layout.prop(prefs, "graph_editor_zoom_curves_kmi_active")

    layout.separator(factor=2)
    layout.label(text="The below will persist through remaping", icon="ERROR")
    layout.label(text="leave them off if you want other keybinds")

    layout.separator()

    layout.label(text="Graph Editor Frames:")
    layout.prop(prefs, "graph_editor_jump_to_keyframe_kmi_active")

    layout.separator()
    layout.label(text="General:")
    layout.prop(prefs, "all_insert_keyframes_kmi_active")
    layout.prop(prefs, "all_world_transforms_kmi_active")

    layout.separator()
    layout.label(text="Graph Editor Keyremaps:")
    layout.prop(prefs, "graph_editor_jump_to_keyframe_ctrl_g_kmi_active")
    layout.prop(prefs, "graph_dope_select_fcurves_kmi_active")


def draw_scrubbing_keymap(layout, context):
    register_keymaps.draw_keymap(
        layout,
        context,
        keymap_name="Scrubbing (Global):",
        editor_name="Window",
        operator_name="anim.amp_timeline_scrub",
        extra_func=draw_timeline_tools_keymaps,
    )


def draw_autokeying_keymap(layout, context):
    register_keymaps.draw_keymap(
        layout,
        context,
        keymap_name="AutoKeying (Global):",
        editor_name="Window",
        operator_name="anim.amp_autokeying_toggle",
    )


def draw_timewarp_keymap(layout, context):
    register_keymaps.draw_keymap(
        layout,
        context,
        keymap_name="TimeWarper (Graph Editor):",
        editor_name="Graph Editor",
        operator_name="anim.amp_anim_timewarper",
    )


def draw_sculpt_keymap(layout, context):
    register_keymaps.draw_keymap(
        layout,
        context,
        keymap_name="AnimSculpt (Graph Editor):",
        editor_name="Graph Editor",
        operator_name="anim.amp_anim_sculpt",
    )


def draw_lattice_keymap(layout, context):
    register_keymaps.draw_keymap(
        layout,
        context,
        keymap_name="AnimLattice (Graph Editor):",
        editor_name="Graph Editor",
        operator_name="anim.amp_anim_lattice",
    )


def draw_top_bar_preferences(self, layout, context):
    prefs = bpy.context.preferences.addons[base_package].preferences

    # NEW: Category buttons toggle
    layout.label(text="Category Display Mode:")
    box = layout.box()
    box.prop(prefs, "show_category_buttons")
    box.label(text="Show category toggle buttons in the Top Bar header.")
    box.label(text="Each section becomes a clickable button to show/hide its tools.")

    layout.separator()

    draw_ui_sections_lists_side_panel(self, layout, context)

    layout.separator()

    layout.label(text="Top Bar replacements:")
    box = layout.box()
    box.prop(prefs, "toggle_blender_dope_top_right_bar_active")
    box.label(text="Recommended off for now")
    box.separator()
    box.prop(prefs, "toggle_amp_graph_top_right_bar_active")
    box.label(text="Recommended on. Removes the Normalize button and")
    box.label(text="makes it avalable as a normal button in the to row.")

    layout.separator()

    layout.label(text="Silhouette button:")
    box = layout.box()
    box.use_property_split = True
    box.use_property_decorate = False
    box.prop(self, "poser_foreground_color")
    box.prop(self, "poser_background_color")
    box.prop(self, "poser_silohuette_button")


def draw_autokeying_preferences(layout, context):
    layout.label(text="AutoKeying Configuration:")
    box = layout.box()

    amp_AutoKeying_header_interface(box)
    amp_AutoKeying_frame_interface(box)
    amp_AutoKeying_text_interface(box)
    amp_AutoKeying_offset_interface(box)
    amp_AutoKeying_theme_colors(box, context)


def draw_timewarper_preferences(layout, context):

    layout.use_property_split = True
    layout.use_property_decorate = False

    box = layout.box()

    prefs = bpy.context.preferences.addons[base_package].preferences

    box.prop(prefs, "tw_realtime_time_warp_updates")
    box.prop(prefs, "tw_snap_to_frame")
    box.prop(prefs, "tw_topbar_color")
    box.prop(prefs, "tw_pin_color")
    box.prop(prefs, "tw_bar_color")
    box.prop(prefs, "tw_easing_color")


def draw_timeline_tools_keymaps(layout, context):
    prefs = bpy.context.preferences.addons[base_package].preferences

    row = layout.row(align=False)
    scrub_icon = "DOWNARROW_HLT" if changelog.panels_visibility.get("ScrubModalKeymaps", False) else "SETTINGS"
    scrub_modal_keymaps = row.operator(
        "ui.amp_toggle_panels_visibility",
        text="Scrubbing Keymaps",
        icon=scrub_icon,
    )
    scrub_modal_keymaps.version = "ScrubModalKeymaps"

    options_row = row.row(align=True)
    options_row.prop(
        prefs,
        "toggle_for_scrubbing",
        text="",
        icon="PINNED",
    )
    options_row.prop(
        prefs,
        "use_lmb_for_scrubbing",
        text="",
        icon="MOUSE_LMB",
    )

    if changelog.panels_visibility.get("ScrubModalKeymaps", False):

        actions = [
            ("", "Keymap during Scrubbing:", False),
            ("gui_help_key", "Toggle GUI Help (H)", True),
            ("quick_anim_offset_key", "Quick AnimOffset (G)", False),
            ("quick_anim_offset_mask_key", "Quick AnimOffset Blend (B)", False),
            ("quick_anim_offset_blend_key", "Quick AnimOffset Mask (M)", False),
            ("limit_to_range_key", "Limit to Action Range (L)", True),
            ("", "Navigation:", False),
            ("next_frame_key", "Next Frame (E)", True),
            ("prev_frame_key", "Previous Frame (Q)", True),
            ("next_keyframe_key", "Next Keyframe (D)", True),
            ("prev_keyframe_key", "Previous Keyframe (A)", True),
            ("scrub_nudge_key_R", "Nudge Right (SHIFT+E)", True),
            ("scrub_nudge_key_L", "Nudge Left (SHIFT+Q)", True),
            ("last_frame_key", "Last Frame (W)", True),
            ("first_frame_key", "First Frame (S)", True),
            ("", "Play/Reverse:", False),
            ("play_animation_key", "Play Animation (Z)", True),
            ("play_reverse_animation_key", "Play Animation in Reverse (SHIFT+Z)", True),
            ("", "Markers/Keyframes:", False),
            ("add_marker_key", "Add Marker (M)", False),
            ("insert_keyframe_key", "Insert Keyframe (F)", True),
            ("remove_marker_keyframe_key", "Remove Marker/Keyframe (X)", False),
            ("", "Preview Range:", False),
            ("set_preview_range_key", "Set Preview Range (R)", True),
            ("", "Pose Tools:", False),
            ("breakdown_pose_key", "Create Breakdown Pose (1)", True),
            ("blend_to_neighbor_key", "Blend to Neighbor (2)", True),
            ("relax_to_breakdown_key", "Relax to Breakdown (3)", True),
            ("copy_pose_key", "Copy Pose (C)", False),
            ("paste_pose_key", "Paste Pose (V)", False),
        ]

        layout.separator()

        toggle_row = layout.row()

        toggle_row.prop(
            prefs,
            "toggle_for_scrubbing",
            text="Toggle for Scrubbing",
            **get_icon("PINNED"),
        )

        hold_row = layout.row()
        hold_row.prop(
            prefs,
            "use_lmb_for_scrubbing",
            text="Use LMB for Scrubbing",
            **get_icon("MOUSE_LMB"),
        )

        mwheel_row = layout.row()
        mwheel_row.prop(
            prefs,
            "use_mwheel_to_sensitivity",
            text="Use Mouse Wheel for Sensitivity",
            **get_icon("MOUSE_MMB_SCROLL"),
        )

        for action_id, action_name, action_modifiers in actions:
            if action_id == "":
                layout.separator()
                layout.label(text=action_name)
            else:
                box = layout.box()
                row = box.row()
                split = row.split(factor=0.4)

                # Determine the label and pressed state for the button
                is_capturing_this_action = prefs.capturing_key == action_id
                current_key = getattr(prefs, action_id, "Not Set")
                capture_label = "Press a Key" if is_capturing_this_action else current_key

                # Create the button for key capture
                op = split.operator(
                    "anim.amp_capture_key_input",
                    text=capture_label,
                    depress=is_capturing_this_action,
                )
                op.action_id = action_id
                op.action_modifiers = action_modifiers

                # Display the action name
                split.label(text=action_name)


def draw_timeline_tools_preferences(layout, context):
    prefs = bpy.context.preferences.addons[base_package].preferences

    layout.label(text="Timeline Tools Configuration:")
    box = layout.box()
    config_col = box.column()

    amp_spacebaraction_interface(
        config_col,
    )

    amp_scrubbing_interface(
        config_col,
    )

    amp_limits_interface(
        config_col,
    )

    amp_text_interface(
        config_col,
    )

    config_col.separator()

    config_col.prop(
        prefs,
        "select_keyframes_on_current_frame",
    )

    config_col.prop(
        prefs,
        "playback_loop_only_if_cyclical",
    )

    config_col.separator()


def draw_anim_offset_preferences(layout, context):
    prefs = bpy.context.preferences.addons[base_package].preferences
    anim_offset_box = layout.box()
    anim_offset_box.prop(prefs, "ao_fast_offset", text="Fast calculation", toggle=False)


def draw_support_section(layout):

    row = layout.row()

    column_left = row.column()
    column_left.label(text="Commuity & Support:")
    left_container = column_left.box()
    left_container.operator("wm.url_open", text="Twitter", **get_icon("Twitter")).url = (
        "https://www.twitter.com/notthatnda"
    )
    left_container.operator("wm.url_open", text="Discord", **get_icon("Discord")).url = "https://discord.gg/JWzJxTKx48"
    left_container.operator("wm.url_open", text="Patreon", **get_icon("Patreon")).url = (
        "https://www.patreon.com/AniMatePro/"
    )

    column_right = row.column()
    column_right.label(text="Download:")
    right_container = column_right.box()
    right_container.operator(
        "wm.url_open",
        text="Blender Market",
        **get_icon("BlenderMarket"),
    ).url = "https://blendermarket.com/products/animatepro"
    right_container.operator(
        "wm.url_open",
        text="Gumroad",
        **get_icon("Gumroad"),
    ).url = "https://nda.gumroad.com/l/animatepro"

    layout.separator(factor=2)


class AMP_OT_ToggleVisibility(bpy.types.Operator):

    bl_idname = "ui.amp_toggle_panels_visibility"
    bl_label = "Toggle"
    bl_description = "Expand or collapse the panel"
    bl_options = {"INTERNAL"}

    version: bpy.props.StringProperty()

    def execute(self, context):
        # Toggle the visibility state
        if self.version in changelog.panels_visibility:
            changelog.panels_visibility[self.version] = not changelog.panels_visibility[self.version]
        else:
            changelog.panels_visibility[self.version] = True
        return {"FINISHED"}


class AMP_OT_ExportPreferences(bpy.types.Operator, ExportHelper):
    bl_idname = "amp.export_preferences"
    bl_label = "Export Preferences"
    bl_description = "Export add-on preferences to a JSON file"

    filename_ext = ".json"
    filter_glob: StringProperty(
        default="*.json",
        options={"HIDDEN"},
        maxlen=255,
    )

    def invoke(self, context, event):
        if not self.filepath:
            user_home_dir = os.path.expanduser("~")
            os.makedirs(user_home_dir, exist_ok=True)
            default_filepath = os.path.join(user_home_dir, "AMP_preferences.json")
            self.filepath = default_filepath
        return ExportHelper.invoke(self, context, event)

    def execute(self, context):
        prefs = context.preferences.addons[base_package].preferences
        return self.save_preferences(self.filepath, prefs)

    def save_preferences(self, filepath, prefs):
        try:
            pref_dict = prefs.to_dict()
            json_str = json.dumps(pref_dict, indent=4)
            with open(filepath, "w") as f:
                f.write(json_str)
            self.report({"INFO"}, f"Preferences successfully saved to {filepath}")
            return {"FINISHED"}
        except TypeError as e:
            print(f"Serialization failed: {e}")
            self.report({"ERROR"}, f"Failed to serialize preferences: {e}")
            return {"CANCELLED"}
        except Exception as e:
            print(f"Failed to save preferences: {e}")
            self.report({"ERROR"}, f"Failed to save preferences: {e}")
            return {"CANCELLED"}


class AMP_OT_ImportPreferences(bpy.types.Operator, ImportHelper):
    bl_idname = "amp.import_preferences"
    bl_label = "Import Preferences"

    filename_ext = ".json"

    filter_glob: StringProperty(
        default="*.json",
        options={"HIDDEN"},
        maxlen=255,
    )

    def execute(self, context):
        prefs = context.preferences.addons[base_package].preferences
        return self.load_preferences(self.filepath, prefs)

    def load_preferences(self, filepath, prefs):
        try:
            with open(filepath, "r") as f:
                pref_dict = json.load(f)
            prefs.from_dict(pref_dict)
            # Force UI refresh
            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    area.tag_redraw()
            self.report({"INFO"}, f"Preferences loaded from {filepath}")
            return {"FINISHED"}
        except Exception as e:
            self.report({"ERROR"}, f"Failed to load preferences: {e}")
            return {"CANCELLED"}


class AMP_OT_AutoSavePreferences(bpy.types.Operator):
    bl_idname = "amp.auto_save_preferences"
    bl_label = "Auto Save Preferences"

    def execute(self, context):
        prefs = context.preferences.addons[base_package].preferences

        auto_save_path = prefs.auto_save_path
        if not auto_save_path:
            # Define default auto-save path, e.g., in the add-on directory
            addon_dir = os.path.dirname(os.path.abspath(__file__))
            auto_save_path = os.path.join(addon_dir, "preferences_auto_save.json")

        auto_save_path = normalize_auto_save_path(auto_save_path)

        return self.save_preferences(auto_save_path, prefs)

    def save_preferences(self, filepath, prefs):
        try:
            with open(filepath, "w") as f:
                json.dump(prefs.to_dict(), f, indent=4)
            self.report({"INFO"}, f"Preferences auto-saved to {filepath}")
            return {"FINISHED"}
        except Exception as e:
            self.report({"ERROR"}, f"Failed to auto-save preferences: {e}")
            return {"CANCELLED"}


classes = [
    ButtonItem,
    SectionItem,
    AMP_Preferences,
    AMP_OT_ToggleVisibility,
    AMP_OT_ExportPreferences,
    AMP_OT_ImportPreferences,
    AMP_OT_AutoSavePreferences,
]


def register():

    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError as e:
            print(f"AMP_AniMatePro: could not register {cls.__name__}: {e}")

    try:
        addon = bpy.context.preferences.addons.get(base_package)
        if addon is not None:
            prefs = addon.preferences
            if not prefs.auto_save_path:
                addon_dir = os.path.dirname(os.path.abspath(__file__))
                default_auto_save_path = os.path.join(addon_dir, "AMP_preferences.json")
                prefs.auto_save_path = default_auto_save_path
    except Exception as e:
        print(f"AMP_AniMatePro: could not set default auto_save_path during register: {e}")


def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except ValueError:
            pass


if __name__ == "__main__":
    register()
