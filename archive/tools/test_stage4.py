import bpy
import sys
import os

# Ensure the addon is in the path
addon_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if addon_dir not in sys.path:
    sys.path.append(addon_dir)

import addon_utils
addon_utils.enable("AMP_AniMatePro", default_set=True)

def test_stage4():
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.grease_pencil_add(type='EMPTY', location=(0, 0, 0))
    gp_obj = bpy.context.active_object
    
    # In Blender 5.1, grease pencil v3 might have different data structure
    if hasattr(gp_obj.data, "layers"):
        layer1 = gp_obj.data.layers.new(name="Layer 1")
        layer2 = gp_obj.data.layers.new(name="Layer 2")
        
        # Add frames at 1, 10, 20
        for layer in (layer1, layer2):
            if hasattr(layer.frames, "new"):
                layer.frames.new(1)
                layer.frames.new(10)
                layer.frames.new(20)
    
    # Run Anim Shifter
    bpy.context.scene.frame_set(10)
    
    # positive shift
    try:
        bpy.ops.anim.amp_anim_shifter(scope='SCENE', shift_amount=5)
        print("Shift +5 succeeded")
    except Exception as e:
        print("Shift +5 failed:", e)

test_stage4()
addon_utils.disable("AMP_AniMatePro")
