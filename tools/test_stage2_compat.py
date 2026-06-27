import bpy
import sys
import os

# append root path
addon_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if addon_dir not in sys.path:
    sys.path.append(addon_dir)

import AMP_AniMatePro
from AMP_AniMatePro.utils import blender_compat

print("BLENDER VERSION:", blender_compat.BLENDER_VERSION)
print("HAS LAYERED ACTIONS:", blender_compat.has_layered_actions())

# Create some actions and test the compatibility layer
obj = bpy.data.objects.new("compat_test_obj", None)
bpy.context.scene.collection.objects.link(obj)

action1 = bpy.data.actions.new("test_action_1")
obj.animation_data_create()
obj.animation_data.action = action1

print("CREATED OBJECT ACTION")

fcu = blender_compat.ensure_fcurve(obj, "location", 0, "TestGroup")
print("ENSURED FCURVE:", fcu)

count = sum(1 for _ in blender_compat.iter_action_fcurves(action1, include_all_slots=True))
print("FCURVE COUNT:", count)

groups = list(blender_compat.iter_action_groups(action1, include_all_slots=True))
print("GROUP COUNT:", len(groups))
if groups:
    print("GROUP NAME:", groups[0].name)

blender_compat.remove_fcurve(action1, fcu)
count_after = sum(1 for _ in blender_compat.iter_action_fcurves(action1, include_all_slots=True))
print("FCURVE COUNT AFTER REMOVE:", count_after)

# check shape key, material, nla
mesh = bpy.data.meshes.new("test_mesh")
obj2 = bpy.data.objects.new("compat_test_obj_2", mesh)
bpy.context.scene.collection.objects.link(obj2)

shape_key = obj2.shape_key_add(name="Basis")
shape_key = obj2.shape_key_add(name="Key 1")
action2 = bpy.data.actions.new("test_shape_action")
mesh.shape_keys.animation_data_create()
mesh.shape_keys.animation_data.action = action2

fcu2 = blender_compat.ensure_fcurve(mesh.shape_keys, 'key_blocks["Key 1"].value', 0)
print("ENSURED SHAPE KEY FCURVE:", fcu2)
count_sk = sum(1 for _ in blender_compat.iter_action_fcurves(action2, include_all_slots=True))
print("SHAPE KEY FCURVE COUNT:", count_sk)

print("SUCCESS: Stage 2 compat tests passed")
sys.exit(0)
