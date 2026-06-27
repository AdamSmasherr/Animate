import bpy
from . import anim_stepper, camera_stepper

modules = (
    anim_stepper,
    camera_stepper,
)


# Register classes and properties
def register():
    for module in modules:

        module.register()


# Unregister classes and properties
def unregister():
    for module in reversed(modules):
        try:
            module.unregister()
        except:
            pass
