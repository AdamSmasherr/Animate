import bpy
from . import anim_key_poser_time_warper, anim_key_poser, anim_key_poser_baker

modules = (
    anim_key_poser,
    anim_key_poser_baker,
    anim_key_poser_time_warper,
)


# Register classes and properties
def register():
    for module in modules:
        try:
            module.register()
        except:
            pass


# Unregister classes and properties
def unregister():
    for module in reversed(modules):
        try:
            module.unregister()
        except:
            pass
