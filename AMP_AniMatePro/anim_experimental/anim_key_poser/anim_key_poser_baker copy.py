import bpy
from ... import utils
from bpy.props import BoolProperty, IntProperty


def selected_bones_filter(obj, fcu_data_path):
    # Assuming you want to filter out F-Curves not related to currently selected bones
    if obj.type != "ARMATURE":
        return False
    if obj.mode != "POSE":
        return False

    if "pose.bones" not in fcu_data_path:
        return False  # Not a pose bone F-Curve

    bone_name = fcu_data_path.split('"')[1]
    bone = obj.pose.bones.get(bone_name)

    return bone is not None and not bone.select


class smartkeyframe:
    def __init__(self, key=None):
        if key is None:
            self.frame = 0.0
            self.value = 0.0
            self.handle_left = None
            self.handle_right = None
            self.interpolation = "BEZIER"
            self.handle_left_type = "AUTO"
            self.handle_right_type = "AUTO"
            self.easing = "AUTO"
            self.inbetween = False
        else:
            self.frame = round(float(key.co[0]), 2)
            self.value = key.co[1]
            self.handle_left = key.handle_left
            self.handle_right = key.handle_right
            self.interpolation = key.interpolation
            self.handle_left_type = key.handle_left_type
            self.handle_right_type = key.handle_right_type
            self.easing = key.easing
            self.inbetween = False

    def __lt__(self, other):
        return self.frame < other.frame

    def __eq__(self, other):
        return self.frame == other.frame and self.value == other.value

    def __hash__(self):
        return hash((self.frame, self.value))


def smart_keyposer_baker_setup(context):
    obj = context.active_object
    frame_start, frame_end = context.scene.frame_start, context.scene.frame_end
    fcu_smartkeys = {}

    # Process each NLA track
    for track in obj.animation_data.nla_tracks:
        if track.mute or len(track.strips) != 1 or track.strips[0].action is None:
            continue

        strip = track.strips[0]
        process_fcurves_from_strip(strip, fcu_smartkeys, obj, frame_start, frame_end)

    # Add inbetweens for smoothing transitions
    for fcu, smartkeys in fcu_smartkeys.items():
        smartkeys = add_inbetween(smartkeys)
        fcu_smartkeys[fcu] = smartkeys

    return fcu_smartkeys


def add_inbetween(smartkeys):
    new_smartkeys = []
    for i in range(len(smartkeys) - 1):
        current_key = smartkeys[i]
        next_key = smartkeys[i + 1]

        # Insert existing key
        new_smartkeys.append(current_key)

        # Calculate and insert an in-between key
        if not current_key.inbetween and not next_key.inbetween:
            mid_frame = (current_key.frame + next_key.frame) / 2
            mid_value = (current_key.value + next_key.value) / 2

            inbetween_key = smartkeyframe()
            inbetween_key.frame = mid_frame
            inbetween_key.value = mid_value
            inbetween_key.inbetween = True

            new_smartkeys.append(inbetween_key)

    # Make sure to add the last keyframe
    if smartkeys:
        new_smartkeys.append(smartkeys[-1])

    return new_smartkeys


def process_fcurves_from_strip(strip, fcu_smartkeys, obj, frame_start, frame_end):
    for fcu in strip.action.fcurves:
        if not fcu.is_valid or fcu.mute or selected_bones_filter(obj, fcu.data_path):
            continue
        smartkeys = []

        for key in fcu.keyframe_points:
            keyframe = smartkeyframe(key)
            # Adjust frame according to strip and layer speeds and offsets
            keyframe.frame = adjust_frame_by_strip(keyframe.frame, strip)
            if keyframe not in smartkeys:
                smartkeys.append(keyframe)

        smartkeys.sort()
        if (fcu.data_path, fcu.array_index) in fcu_smartkeys:
            smartkeys += fcu_smartkeys[(fcu.data_path, fcu.array_index)]

        fcu_smartkeys[(fcu.data_path, fcu.array_index)] = list(set(smartkeys))


def adjust_frame_by_strip(frame, strip):
    # Adjust frame based on strip's action start and action end, considering the playback speed
    # This example assumes simple proportional mapping
    action_duration = strip.action_frame_end - strip.action_frame_start
    strip_duration = strip.frame_end - strip.frame_start
    if action_duration == 0 or strip_duration == 0:
        return frame
    frame_offset = (frame - strip.frame_start) / strip_duration * action_duration
    return strip.action_frame_start + frame_offset


def smart_keyposer_bake(obj, nla_tracks, fcu_keys, extrapolations):
    # Identify target strip for baking
    target_strip = nla_tracks[obj.als.layer_index].strips[0]
    target_action = target_strip.action if target_strip else bpy.data.actions.new(name="BakedAction")

    # Process each F-Curve in the smartkeys
    for fcu_key, smartkeys in fcu_keys.items():
        process_fcurve_smartkeys(fcu_key, smartkeys, target_action, obj, extrapolations)


def process_fcurve_smartkeys(fcu_key, smartkeys, target_action, obj, extrapolations):
    # Create or find target F-Curve in the baked action
    target_fcu = target_action.fcurves.find(fcu_key[0], index=fcu_key[1])
    if not target_fcu:
        target_fcu = target_action.fcurves.new(fcu_key[0], index=fcu_key[1])

    # Apply smartkeys to the target F-Curve
    for smartkey in smartkeys:
        target_fcu.keyframe_points.insert(smartkey.frame, smartkey.value, options={"FAST"})

    # Set extrapolation if needed
    if (fcu_key[0], fcu_key[1]) in extrapolations:
        target_fcu.extrapolation = "LINEAR"


class AMP_OT_smart_bake(bpy.types.Operator):
    """Smart Bake Key Pose Layers"""

    bl_idname = "anim.amp_smart_bake"
    bl_label = "Smart Bake"
    bl_options = {"REGISTER", "UNDO"}

    bake_step: bpy.props.IntProperty(name="Bake Step", description="Frame step for baking", default=1, min=1)

    use_smart_baking: bpy.props.BoolProperty(
        name="Use Smart Baking", description="Apply smart baking optimizations", default=True
    )

    def execute(self, context):
        if self.use_smart_baking:
            fcu_smartkeys = smart_keyposer_baker_setup(context)
            smart_keyposer_bake(
                context.active_object, context.active_object.animation_data.nla_tracks, fcu_smartkeys, []
            )
        else:
            # Alternative or direct baking logic can be implemented here
            pass

        self.report({"INFO"}, "Smart Baking Completed")
        return {"FINISHED"}


def draw_keyposer_baker(layout, context):
    # layout.use_smart_baking = True
    # layout.prop(layout, "bake_step")
    layout.operator("anim.amp_smart_bake")


classes = [
    AMP_OT_smart_bake,
    smartkeyframe,
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
