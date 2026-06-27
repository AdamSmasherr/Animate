# ------------------------------------------------------------------------ #
# Start of Rig_UI_customIcons.py
# This module contains the code for adding custom icons

import bpy
import os
import time
from bpy.utils import previews

from .. import __package__ as base_package

custom_icons = None


def get_addon_path():
    return os.path.normpath(os.path.join(os.path.dirname(__file__), os.pardir))


def load_icons(icons_folders=["icons"]):
    global custom_icons

    custom_icons = previews.new()
    addon_dir = get_addon_path()

    for folder in icons_folders:
        folder_path = os.path.join(addon_dir, "assets", folder)
        if os.path.exists(folder_path):
            for icon_file in os.listdir(folder_path):
                if icon_file.endswith(".png"):
                    icon_path = os.path.join(folder_path, icon_file)
                    icon_name = os.path.splitext(icon_file)[0]
                    custom_icons.load(icon_name, icon_path, "IMAGE")


def reboot_icons(self, context):
    reload_icons()


def refresh_icons(self, context):
    global custom_icons
    prefs = bpy.context.preferences.addons[base_package].preferences

    unload_icons()

    load_icons(["icons", prefs.icons_set])

    if prefs.refreshing_icons:
        prefs.refreshing_icons = False
        return


def reload_icons():
    unload_icons()

    global custom_icons
    prefs = bpy.context.preferences.addons[base_package].preferences

    load_icons(["icons", prefs.icons_set])


def unload_icons():
    global custom_icons

    if custom_icons is not None:
        bpy.utils.previews.remove(custom_icons)
        custom_icons = None


# def get_custom_icons():
#     global custom_icons
#     return custom_icons if custom_icons is not None else None


def get_icon_id(icon_name):

    if icon_name in bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items.keys():
        return bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items[icon_name].value
    elif custom_icons is not None and icon_name in custom_icons:
        return custom_icons[icon_name].icon_id
    else:
        return bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items["ERROR"].value


def get_icon(icon_name):
    """Get the appropriate icon parameters for a UI element."""
    if isinstance(icon_name, int):
        return {"icon_value": icon_name}

    if isinstance(icon_name, str) and custom_icons is not None and icon_name in custom_icons:
        return {"icon_value": custom_icons[icon_name].icon_id}

    if (
        isinstance(icon_name, str)
        and icon_name in bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items
    ):
        return {"icon": icon_name}

    return {"icon": "BLANK1"}


# ------------------------------Registration------------------------------ #

# classes = ()


def register():
    # for cls in classes:
    #     bpy.utils.register_class(cls)
    prefs = bpy.context.preferences.addons[base_package].preferences
    unload_icons()
    load_icons(["icons", prefs.icons_set])

def unregister():
    # for cls in reversed(classes):
    #     bpy.utils.unregister_class(cls)
    unload_icons()

if __name__ == "__main__":
    register()

# End of Rig_UI_customIcons.py
# ------------------------------------------------------------------------ #
