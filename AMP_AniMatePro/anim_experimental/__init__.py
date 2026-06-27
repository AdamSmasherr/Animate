import bpy
from . import anim_experimental, anim_key_poser

modules = (anim_experimental, anim_key_poser)


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
