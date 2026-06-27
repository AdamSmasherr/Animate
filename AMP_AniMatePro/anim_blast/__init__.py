from . import anim_blast

modules = (anim_blast,)


def register():
    for module in modules:
        module.register()


def unregister():
    for module in reversed(modules):
        module.unregister()
