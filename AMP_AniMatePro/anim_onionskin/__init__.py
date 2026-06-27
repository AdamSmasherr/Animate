import bpy
from . import anim_onionskin

modules = (anim_onionskin,)


def register():
    for module in modules:
        module.register()


def unregister():
    for module in reversed(modules):
        try:
            module.unregister()
        except:
            pass


if __name__ == "__main__":
    register()
