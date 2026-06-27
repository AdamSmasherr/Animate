import bpy
from ... import utils
from bpy.props import BoolProperty, IntProperty


def smart_keyposer_baker_setup(context, only_selected_bones):
    obj = context.active_object
    keyframe_frames = set()

    for track in obj.animation_data.nla_tracks:
        if track.mute:
            continue
        for strip in track.strips:
            if strip.action:
                for fcu in utils.curve.all_fcurves(strip.action):
                    if only_selected_bones and not is_selected_bone_fcurve(obj, fcu):
                        continue
                    for keyframe in fcu.keyframe_points:
                        keyframe_frames.add(keyframe.co[0])

    return sorted(list(keyframe_frames))


def is_selected_bone_fcurve(obj, fcu):
    if "pose.bones[" in fcu.data_path:
        bone_name = fcu.data_path.split('"')[1]
        return obj.pose.bones[bone_name].select
    return False


def smart_keyposer_bake(obj, keyframe_frames, only_selected_bones, clean_curves, overwrite, visual_keying):
    if not keyframe_frames:
        return  # Skip if no keyframes to bake

    # Convert frame_start and frame_end to integers
    frame_start = int(min(keyframe_frames))
    frame_end = int(max(keyframe_frames))

    # Adjust the baking function call with correct parameters
    bpy.ops.nla.bake(
        frame_start=frame_start,
        frame_end=frame_end,
        step=1,
        only_selected=only_selected_bones,
        visual_keying=visual_keying,
        clear_constraints=False,
        clear_parents=False,
        use_current_action=overwrite,
        bake_types={"POSE"},
    )

    if clean_curves:
        # Remove unnecessary keyframes
        clean_animation_curves(obj, keyframe_frames)


def clean_animation_curves(obj, keyframe_frames):
    """Remove keyframes not in the keyframe_frames list passed in."""
    action = obj.animation_data.action
    for fcu in utils.curve.all_fcurves(action):
        keyframe_indices = range(len(fcu.keyframe_points))
        for index in reversed(keyframe_indices):
            keyframe = fcu.keyframe_points[index]
            if keyframe.co[0] not in keyframe_frames:
                fcu.keyframe_points.remove(keyframe)


class AMP_OT_smart_bake(bpy.types.Operator):
    """Smart Bake Key Pose Layers"""

    bl_idname = "anim.amp_smart_bake"
    bl_label = "Smart Bake"
    bl_options = {"REGISTER", "UNDO"}

    bake_step: bpy.props.IntProperty(
        name="Bake Step",
        description="Frame step for baking",
        default=1,
        min=1,
    )
    only_selected_bones: bpy.props.BoolProperty(
        name="Only Selected Bones",
        description="Bake only selected bones",
        default=False,
    )
    clean_curves: bpy.props.BoolProperty(
        name="Clean Curves",
        description="Clean up the animation curves after baking",
        default=True,
    )
    overwrite_current_action: bpy.props.BoolProperty(
        name="Overwrite Current Action",
        description="Overwrite the current action instead of creating a new one",
        default=False,
    )
    visual_keying: bpy.props.BoolProperty(
        name="Visual Keying",
        description="Use visual keying for baking",
        default=False,
    )

    def execute(self, context):
        keyframe_frames = smart_keyposer_baker_setup(context, self.only_selected_bones)
        smart_keyposer_bake(
            context.active_object,
            keyframe_frames,
            self.only_selected_bones,
            self.clean_curves,
            self.overwrite_current_action,
            self.visual_keying,
        )

        self.report({"INFO"}, "Smart Baking Completed")
        return {"FINISHED"}


def draw_keyposer_baker(layout, context):

    layout.operator("anim.amp_smart_bake", icon="ANIM_DATA")


classes = [
    AMP_OT_smart_bake,
]


def register():
    try:
        for cls in classes:
            bpy.utils.register_class(cls)
    except:
        utils.dutils.dprint(f"{cls} already registered, skipping...")


def unregister():

    try:
        for cls in reversed(classes):
            bpy.utils.unregister_class(cls)
    except:
        utils.dutils.dprint(f"{cls} not found, skipping...")


if __name__ == "__main__":
    register()
