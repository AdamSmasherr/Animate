import os
import bpy

# Documentation on icons:
# https://developer.blender.org/docs/features/interface/icons/
# Source Tools icons file: https://projects.blender.org/blender/blender-assets/src/branch/main/icons/toolbar.blend


def load_icons():
    # Get the directory where icon files are stored
    icons_dir = bpy.utils.system_resource("DATAFILES", path="icons")
    icon_files = [f for f in os.listdir(icons_dir) if f.endswith(".dat")]
    icons = {}
    for icon_file in icon_files:
        icon_name = icon_file[:-4]  # Remove the .dat extension
        icon_path = os.path.join(icons_dir, icon_file)
        try:
            icon_value = bpy.app.icons.new_triangles_from_file(icon_path)
            icons[icon_name] = icon_value
        except Exception as e:
            print(f"Failed to load icon {icon_name}: {e}")
    return icons


icons = load_icons()


class ICONS_PT_customPanel(bpy.types.Panel):
    bl_label = "Dat File Icons"
    bl_idname = "ICONS_PT_customPanel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tools"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        for icon_name, icon_value in icons.items():
            row = col.row()
            row.label(text="", icon_value=icon_value)
            col.separator(factor=2)


def register():
    bpy.utils.register_class(ICONS_PT_customPanel)
    

def unregister():
    bpy.utils.unregister_class(ICONS_PT_customPanel)
    bpy.app.icons.release(icon_value for icon_value in icons.values())


if __name__ == "__main__":
    register()
