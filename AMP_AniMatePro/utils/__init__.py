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
        except Exception as e:
            print(f"AMP utils: failed to register {module.__name__}: {e}")


def unregister():
    for module in reversed(modules):
        try:
            module.unregister()
        except Exception as e:
            print(f"AMP utils: failed to unregister {module.__name__}: {e}")


if __name__ == "__main__":
    register()
