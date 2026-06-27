import bpy
from bpy_extras import anim_utils

action = bpy.data.actions.new("test_action")
obj = bpy.data.objects.new("test_obj", None)
obj.animation_data_create()
obj.animation_data.action = action

print("SLOTS:", action.slots)
try:
    slot = action.slots.new("test_slot")
    print("NEW SLOT:", slot)
    obj.animation_data.action_slot = slot
    print("ASSIGNED SLOT:", obj.animation_data.action_slot)
    bag = anim_utils.action_ensure_channelbag_for_slot(action, slot)
    fcu = bag.fcurves.new(data_path="location", index=0)
    print("FCU:", fcu)
except Exception as e:
    print("ERROR:", e)
