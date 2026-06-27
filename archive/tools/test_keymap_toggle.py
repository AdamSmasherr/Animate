import sys, os
sys.path.append(os.path.abspath('.'))
import bpy
import sys

def run():
    print("Enabling addon...")
    bpy.ops.preferences.addon_enable(module="AMP_AniMatePro")
    
    prefs = bpy.context.preferences.addons["AMP_AniMatePro"].preferences
    
    print("Toggling keymap preferences off...")
    prefs.scrub_timeline_keymap_kmi_active = False
    prefs.graph_editor_jump_to_keyframe_kmi_active = False
    prefs.graph_editor_jump_to_keyframe_ctrl_g_kmi_active = False
    prefs.graph_dope_select_fcurves_kmi_active = False
    prefs.all_insert_keyframes_kmi_active = False
    prefs.all_world_transforms_kmi_active = False
    prefs.graph_anim_tools_kmi_active = False
    prefs.all_autokeying_kmi_active = False
    prefs.graph_editor_isolate_curves_kmi_active = False
    prefs.graph_editor_zoom_curves_kmi_active = False
    
    print("Toggling keymap preferences on...")
    prefs.scrub_timeline_keymap_kmi_active = True
    prefs.graph_editor_jump_to_keyframe_kmi_active = True
    prefs.graph_editor_jump_to_keyframe_ctrl_g_kmi_active = True
    prefs.graph_dope_select_fcurves_kmi_active = True
    prefs.all_insert_keyframes_kmi_active = True
    prefs.all_world_transforms_kmi_active = True
    prefs.graph_anim_tools_kmi_active = True
    prefs.all_autokeying_kmi_active = True
    prefs.graph_editor_isolate_curves_kmi_active = True
    prefs.graph_editor_zoom_curves_kmi_active = True
    
    print("Toggling keymap preferences off again...")
    prefs.scrub_timeline_keymap_kmi_active = False
    prefs.graph_editor_jump_to_keyframe_kmi_active = False
    prefs.graph_editor_jump_to_keyframe_ctrl_g_kmi_active = False
    prefs.graph_dope_select_fcurves_kmi_active = False
    prefs.all_insert_keyframes_kmi_active = False
    prefs.all_world_transforms_kmi_active = False
    prefs.graph_anim_tools_kmi_active = False
    prefs.all_autokeying_kmi_active = False
    prefs.graph_editor_isolate_curves_kmi_active = False
    prefs.graph_editor_zoom_curves_kmi_active = False
    
    print("Disabling addon...")
    bpy.ops.preferences.addon_disable(module="AMP_AniMatePro")
    
    print("Keymap tests passed successfully without crash.")

if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print("Error during test:", e)
        sys.exit(1)
