import bpy
from .. import utils


class AnimStepperProperties(bpy.types.PropertyGroup):

    anim_step: bpy.props.IntProperty(
        name="Step",
        default=2,
        min=1,
        description="Number of frames to skip",
    )

    anim_offset: bpy.props.FloatProperty(
        name="Offset",
        default=0,
        min=0,
        description="Offset to apply to the animation step",
    )

    update_all: bpy.props.BoolProperty(
        name="Affect All in Scene",
        default=False,
        description="Affect all objects in the scene",
    )


class AMP_OT_AddSteppedModifier(bpy.types.Operator):
    """Add or update stepped modifier to selected objects or bones"""

    bl_idname = "anim.amp_anim_stepper"
    bl_label = "Add Stepped Modifier"
    bl_options = {"REGISTER", "UNDO"}

    anim_step: bpy.props.IntProperty(
        name="Step",
        default=2,
        min=1,
        description="Number of frames to skip",
    )

    anim_offset: bpy.props.FloatProperty(
        name="Offset",
        default=0,
        min=0,
        description="Offset to apply to the animation step",
    )

    update_all: bpy.props.BoolProperty(
        name="Update All",
        default=False,
        description="Update all objects in the scene",
    )

    @classmethod
    def poll(cls, context):
        return context.selected_objects

    def invoke(self, context, event):
        scene = context.scene
        self.anim_step = scene.anim_stepper_props_old.anim_step
        self.anim_offset = scene.anim_stepper_props_old.anim_offset
        self.update_all = scene.anim_stepper_props_old.update_all
        return self.execute(context)

    def execute(self, context):
        scene = context.scene

        if self.update_all:
            Anim_Step_targets = context.scene.objects
            # scene.anim_stepper_props_old.update_all = self.update_all
        else:
            Anim_Step_targets = context.selected_objects

        for obj in Anim_Step_targets:
            self.process_object(obj, scene)

        return {"FINISHED"}

    def process_object(self, obj, scene):
        # Process object or armature bones for fcurves
        action = obj.animation_data.action if obj.animation_data else None
        fcurves =utils.curve.all_fcurves(action)
        if action and fcurves:
            for fcurve in fcurves:
                self.add_stepped_modifier_to_fcurve(fcurve, scene)

        if obj.type == "ARMATURE":
            for bone in obj.pose.bones:
                for fcurve in fcurves:
                    if fcurve.data_path.startswith(f'pose.bones["{bone.name}"]'):
                        self.add_stepped_modifier_to_fcurve(fcurve, scene)

    def add_stepped_modifier_to_fcurve(self, fcurve, scene):
        # Find an existing Stepped modifier or create a new one
        mod = None
        for modifier in fcurve.modifiers:
            if modifier.type == "STEPPED" and modifier.name == "AnimStep":
                mod = modifier
                mod.frame_step = self.anim_step
                mod.frame_offset = self.anim_offset
                scene.anim_stepper_props_old.anim_step = self.anim_step
                scene.anim_stepper_props_old.anim_offset = self.anim_offset
            else:
                pass

        if mod is None:  # and not self.update_all:
            mod = fcurve.modifiers.new(type="STEPPED")
            mod.use_frame_start = False
            mod.use_frame_end = False
            mod.frame_step = self.anim_step
            mod.frame_offset = self.anim_offset
            scene.anim_stepper_props_old.anim_step = self.anim_step
            scene.anim_stepper_props_old.anim_offset = self.anim_offset
            mod.name = "AnimStep"

    def draw(self, context):
        layout = self.layout
        draw_anim_stepper_options(self, layout, context)


class AMP_OT_RemoveSteppedModifier(bpy.types.Operator):
    """Remove stepped modifier from selected objects or bones"""

    bl_idname = "anim.amp_remove_anim_stepper"
    bl_label = "Remove Stepped Modifier"
    bl_options = {"REGISTER", "UNDO"}

    update_all: bpy.props.BoolProperty(
        name="Update All",
        default=False,
        description="Remove from all objects in the scene",
    )

    @classmethod
    def poll(cls, context):
        return context.selected_objects or context.scene.objects

    def execute(self, context):
        if self.update_all:
            targets = context.scene.objects
        else:
            targets = context.selected_objects

        for obj in targets:
            self.remove_stepped_modifier(obj)

        if context.area:
            context.area.tag_redraw()

        return {"FINISHED"}

    def remove_stepped_modifier(self, obj):
        action = obj.animation_data.action if obj.animation_data else None
        fcurves = utils.curve.all_fcurves(action)
        if action:
            for fcurve in fcurves:
                self.remove_stepped_from_fcurve(fcurve)

        if obj.type == "ARMATURE":
            for bone in obj.pose.bones:
                action = obj.animation_data.action if obj.animation_data else None
                if action:
                    for fcurve in fcurves:
                        if fcurve.data_path.startswith(f'pose.bones["{bone.name}"]'):
                            self.remove_stepped_from_fcurve(fcurve)

    def remove_stepped_from_fcurve(self, fcurve):
        modifiers_to_remove = [mod for mod in fcurve.modifiers if mod.type == "STEPPED" and mod.name == "AnimStep"]
        for mod in modifiers_to_remove:
            fcurve.modifiers.remove(mod)
            fcurve.update()


class AMP_PT_AnimStepper(bpy.types.Panel):
    bl_label = ""
    bl_idname = "AMP_PT_AnimStepper"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_context = ""
    bl_ui_units_x = 15

    def draw(self, context):
        layout = self.layout
        props = context.scene.anim_stepper_props_old
        ui_column = layout.column()

        ui_column.separator(factor=2)

        slice_anim = ui_column.row()
        slice_anim.scale_y = 1.5
        AnimStepperButton(slice_anim, context, "Add Anim Stepper", utils.customIcons.get_icon_id("AMP_anim_step"))

        slice_anim.operator("anim.amp_remove_anim_stepper", text="Remove from selected", icon="CANCEL")

        ui_column.separator(factor=1)
        slice_anim = ui_column.row()
        slice_anim.scale_y = 1.5
        AnimStepperButton_All(slice_anim, context, "Update Scene", utils.customIcons.get_icon_id("AMP_anim_step"))
        slice_anim.operator("anim.amp_remove_anim_stepper", text="Remove from All", icon="CANCEL").update_all = True
        ui_column.separator(factor=2)

        draw_anim_stepper_options(props, ui_column, context)


def draw_anim_stepper_options(self, layout, context):

    container = layout.box()
    slicer_column = container.column(align=True)
    slicer_column.label(text="Scene Step Settings:")

    slicer_column.separator(factor=1)
    slicer_column.prop(self, "anim_step")
    slicer_column.separator(factor=0.5)
    slicer_column.prop(self, "anim_offset")
    slicer_column.separator(factor=0.5)
    slicer_column.prop(self, "update_all")


def AnimStepperButton(layout, context, text, icon_value):
    row = layout.row(align=True)
    row.operator(
        "anim.amp_anim_stepper",
        text=text,
        icon_value=icon_value,
    ).update_all = False


def AnimStepperButton_All(layout, context, text, icon_value):
    row = layout.row(align=True)
    row.operator(
        "anim.amp_anim_stepper",
        text=text,
        icon_value=icon_value,
    ).update_all = True


classes = (
    AnimStepperProperties,
    AMP_OT_AddSteppedModifier,
    AMP_PT_AnimStepper,
    AMP_OT_RemoveSteppedModifier,
)


def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            utils.dprint(f"{cls} already registered, skipping... ({e})")

    bpy.types.Scene.anim_stepper_props_old = bpy.props.PointerProperty(type=AnimStepperProperties)


def unregister():
    del bpy.types.Scene.anim_stepper_props_old

    try:
        for cls in reversed(classes):
            bpy.utils.unregister_class(cls)
    except:
        utils.dprint(f"{cls} not found, skipping...")


if __name__ == "__main__":
    register()
