import bpy
from bpy_extras import anim_utils

print("BLENDER VERSION:", bpy.app.version)
print("ANIM UTILS DIR:", dir(anim_utils))

action = bpy.data.actions.new("test_layered")
print("ACTION DIR:", [x for x in dir(action) if not x.startswith('_')])

obj = bpy.data.objects.new("test_obj", None)
bpy.context.scene.collection.objects.link(obj)
obj.animation_data_create()
obj.animation_data.action = action

print("ANIM_DATA DIR:", [x for x in dir(obj.animation_data) if not x.startswith('_')])
try:
    print("ACTION_SLOT:", getattr(obj.animation_data, 'action_slot', None))
except Exception as e:
    pass

try:
    bag = anim_utils.action_ensure_channelbag_for_slot(action, obj.animation_data.action_slot)
    print("BAG:", bag)
    print("BAG fcurves:", getattr(bag, 'fcurves', None))
except Exception as e:
    print("BAG ERROR:", e)

