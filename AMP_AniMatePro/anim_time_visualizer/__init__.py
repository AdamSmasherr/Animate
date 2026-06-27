import bpy
from . import anim_time_visualizer

modules = (anim_time_visualizer,)


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
