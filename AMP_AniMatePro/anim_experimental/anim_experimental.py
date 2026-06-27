import bpy


class AMP_PT_ExperimentalGraph(bpy.types.Panel):
    bl_label = "Experimental"
    bl_idname = "AMP_PT_ExperimentalGraph"
    bl_space_type = "GRAPH_EDITOR"
    bl_region_type = "UI"
    bl_context = ""
    bl_parent_id = "AMP_PT_TimelineToolsGraph"
    bl_options = {"DEFAULT_CLOSED"}
    bl_category = "Animation"

    # def draw_header(self, context):
    #     layout = self.layout
    #     layout.label(text="", icon="CAMERA_DATA")

    def draw(self, context):
        layout = self.layout


class AMP_PT_ExperimentalDope(bpy.types.Panel):
    bl_label = "Experimental"
    bl_idname = "AMP_PT_ExperimentalDope"
    bl_space_type = "DOPESHEET_EDITOR"
    bl_region_type = "UI"
    bl_context = ""
    bl_parent_id = "AMP_PT_TimelineToolsDope"
    bl_options = {"DEFAULT_CLOSED"}
    bl_category = "Animation"

    # def draw_header(self, context):
    #     layout = self.layout
    #     layout.label(text="", icon="CAMERA_DATA")

    def draw(self, context):
        layout = self.layout


classes = (AMP_PT_ExperimentalGraph, AMP_PT_ExperimentalDope)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
