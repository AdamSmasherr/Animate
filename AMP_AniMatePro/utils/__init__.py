from .general import *
from .api import *
from . import key, curve, insert_keyframes
from . import operators, handlers, blender_compat

# import general, insert_keyframes, key, curve

modules = (operators, handlers)


def register():
    for module in modules:
        try:
            module.register()
        except:
            pass


def unregister():
    for module in reversed(modules):
        try:
            module.unregister()
        except:
            pass


if __name__ == "__main__":
    register()
