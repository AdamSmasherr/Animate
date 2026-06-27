import sys
sys.path.append('D:/Code/AMP_AniMatePro/AMP_AniMatePro_v0.25.10318')

import bpy

def test():
    # Create an armature
    bpy.ops.object.armature_add(enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
    arm = bpy.context.active_object
    
    bpy.ops.object.mode_set(mode='POSE')
    
    # Calculate initial path
    bpy.ops.pose.paths_calculate(display_type='RANGE', range='SCENE')
    
    # Now try to update it in generic background context
    try:
        bpy.ops.object.paths_update_visible()
        print("paths_update_visible succeeded!")
    except Exception as e:
        print(f"paths_update_visible FAILED: {e}")

test()
