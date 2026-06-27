import bpy
from mathutils import Matrix, Vector, Quaternion
from .. import utils


def add_item_to_list(collection_property, item_type):
    """Generic function to add an item to a Blender collection property."""
    item = collection_property.add()
    # Initialize any necessary properties of the item here, if needed
    return item


def remove_item_from_list(collection_property, index):
    """Generic function to remove an item from a Blender collection property."""
    if index >= 0 and index < len(collection_property):
        collection_property.remove(index)


def move_item_in_list(collection_property, index, direction):
    """Generic function to move an item up or down in a Blender collection property."""
    target_index = index + (-1 if direction == "UP" else 1)
    if 0 <= index < len(collection_property) and 0 <= target_index < len(collection_property):
        collection_property.move(index, target_index)


def delete_action(action):
    """
    Delete an action by name.
    """
    if action:
        action.use_fake_user = False
        while action.users > 0:
            action.user_clear()
        bpy.data.actions.remove(action)
        print(f"Action '{action}' removed.")
    else:
        print(f"Action '{action}' not found.")


def duplicate_action(obj, action_suffix="_baked_to_scene_camera"):
    """
    If the baked action exists, remove it, then duplicate the original action.
    """
    original_action = obj.animation_data.action
    if not original_action:
        print(f"No original action found for {obj.name}.")
        return None

    new_action_name = (
        f"{original_action.name}{action_suffix}"
        if not original_action.name.endswith(action_suffix)
        else original_action.name
    )
    baked_action = bpy.data.actions.get(new_action_name)

    if baked_action:
        delete_action(baked_action)

    # After ensuring the baked action does not exist, duplicate the original action
    new_action = original_action.copy()
    new_action.name = new_action_name
    new_action.use_fake_user = True  # Optional based on your use case
    print(f"Duplicated action: '{original_action.name}' to '{new_action_name}' for object {obj.name}.")

    return new_action


# def copy_relative_matrix(obj, camera):
#     """
#     Copy the object's matrix relative to the camera.
#     """
#     relative_matrix = camera.matrix_world.inverted() @ obj.matrix_world
#     loc, rot, sca = relative_matrix.decompose()
#     return (loc, rot, sca)


# def paste_relative_matrix(obj, camera, loc, rot, sca, frame):
#     """
#     Paste a relative transformation to an object at a given frame.
#     """
#     relative_matrix = Matrix.LocRotScale(loc, rot, sca)
#     new_matrix = camera.matrix_world @ relative_matrix
#     obj.matrix_world = new_matrix
#     bpy.context.scene.frame_set(frame)

#     # Decompose the new matrix to its components and keyframe them
#     location, rotation_quat, scale = new_matrix.decompose()

#     # Apply the decomposed transformations to the object
#     obj.location = location
#     obj.rotation_mode = "QUATERNION"
#     obj.rotation_quaternion = rotation_quat
#     obj.scale = scale


def copy_relative_matrix(obj, camera):
    """
    Copy the object's matrix relative to the camera.
    """
    # Compute the relative matrix from the object to the camera
    relative_matrix = camera.matrix_world.inverted() @ obj.matrix_world
    return relative_matrix


def paste_relative_matrix(obj, camera, relative_matrix, frame):
    """
    Paste a relative transformation to an object at a given frame.
    """
    # Calculate the new world matrix for the object based on the camera's transformation
    new_matrix_world = camera.matrix_world @ relative_matrix

    # Set the new world matrix to the object
    obj.matrix_world = new_matrix_world


def copy_relative_matrix_bone(armature, bone_name, camera):
    """
    Get the bone's head position and orientation relative to the camera.
    """
    bone = armature.pose.bones.get(bone_name)
    if bone:
        bone_matrix_world = armature.matrix_world @ bone.matrix
        relative_matrix = camera.matrix_world.inverted() @ bone_matrix_world
        return relative_matrix
    return None


def paste_relative_matrix_bone(armature, bone_name, relative_matrix, camera, frame):
    """
    Apply the relative transformation matrix to a bone at a given frame, considering all transforms.
    """

    bone = armature.pose.bones.get(bone_name)
    if not bone:
        return

    # Calculate the new world matrix for the bone based on the camera's current transformation
    new_matrix_world = camera.matrix_world @ relative_matrix
    bone.matrix = armature.matrix_world.inverted() @ new_matrix_world


def stick_object_poses_to_camera(obj, context, original_action, baked_action, frames):
    """
    Adjust the object's animation to maintain its relative matrix to the camera.
    Captures and applies a dynamic relative matrix for each frame, ensuring
    the object maintains its screen space position relative to the camera.
    """
    # Ensure modifications are applied to the baked action.
    obj.animation_data.action = baked_action
    original_fcurves = utils.curve.all_fcurves(original_action)
    # Gather all keyframes from the original action.
    keyframes = sorted({int(kp.co.x) for fc in original_fcurves for kp in fc.keyframe_points})

    for i, start_frame in enumerate(keyframes[:-1]):
        if frames and start_frame not in frames:
            continue

        end_frame = keyframes[i + 1]
        camera = context.scene.camera
        # At the start of each interval, capture the object's relative matrix to the camera
        bpy.context.scene.frame_set(start_frame)
        relative_matrix_start = copy_relative_matrix(obj, camera)

        # Paste this matrix at the start frame (to set initial keyframe)
        paste_relative_matrix(obj, camera, relative_matrix_start, start_frame)
        # bpy.ops.anim.keyframe_insert_menu(type="LocRotScale")
        obj.keyframe_insert(data_path="location", frame=start_frame)
        obj.keyframe_insert(
            data_path="rotation_euler",
            frame=start_frame,
            options={"INSERTKEY_AVAILABLE"},
        )
        obj.keyframe_insert(
            data_path="rotation_quaternion",
            frame=start_frame,
            options={"INSERTKEY_AVAILABLE"},
        )
        obj.keyframe_insert(
            data_path="scale",
            frame=start_frame,
            options={"INSERTKEY_AVAILABLE"},
        )

        for frame in range(start_frame + 1, end_frame):
            if frame not in frames:
                continue
            segment_relative_matrix = copy_relative_matrix(obj, camera)
            bpy.context.scene.frame_set(frame)
            paste_relative_matrix(obj, camera, segment_relative_matrix, frame)
            # bpy.ops.anim.keyframe_insert_menu(type="LocRotScale")
            obj.keyframe_insert(data_path="location", frame=frame)
            obj.keyframe_insert(
                data_path="rotation_euler",
                frame=frame,
                options={"INSERTKEY_AVAILABLE"},
            )
            obj.keyframe_insert(
                data_path="rotation_quaternion",
                frame=frame,
                options={"INSERTKEY_AVAILABLE"},
            )
            obj.keyframe_insert(
                data_path="scale",
                frame=frame,
                options={"INSERTKEY_AVAILABLE"},
            )

    print(f"Finished processing '{baked_action.name}' for {obj.name}.")


def stick_bone_poses_to_camera(armature, context, original_action, baked_action, selected_bones, frames):
    """
    Adjust selected bones' animation in the armature to maintain relative transformation
    to the camera. This method captures and applies a dynamic relative matrix for each
    frame in the interval, based on the camera's movement, ensuring the bone maintains
    its screen space transformation relative to the camera throughout the animation.
    """
    # Ensure modifications are applied to the baked action.
    armature.animation_data.action = baked_action
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="POSE")

    # Gather all keyframes from the original action
    original_action_fcurves = utils.curve.all_fcurves(original_action)
    keyframes = sorted({int(kp.co.x) for fc in original_action_fcurves for kp in fc.keyframe_points})

    for bone_name in selected_bones:
        for i, start_frame in enumerate(keyframes[:-1]):

            end_frame = keyframes[i + 1]
            camera = context.scene.camera
            # Set the scene to the start frame and capture the initial relative matrix
            bpy.context.scene.frame_set(start_frame)
            initial_relative_matrix = copy_relative_matrix_bone(armature, bone_name, camera)

            # Apply this matrix at the start of the interval and insert a keyframe
            # paste_relative_matrix_bone(armature, bone_name, initial_relative_matrix, camera, start_frame)
            # bpy.ops.anim.keyframe_insert_menu(type="LocRotScale")

            # Apply this matrix at the start of the interval and insert a keyframe
            paste_relative_matrix_bone(armature, bone_name, initial_relative_matrix, camera, start_frame)
            bone = armature.pose.bones[bone_name]
            bone.keyframe_insert(data_path="location", frame=start_frame, group=bone_name)
            bone.keyframe_insert(
                data_path="rotation_euler",
                frame=start_frame,
                group=bone_name,
                options={"INSERTKEY_AVAILABLE"},
            )
            bone.keyframe_insert(
                data_path="rotation_quaternion",
                frame=start_frame,
                group=bone_name,
                options={"INSERTKEY_AVAILABLE"},
            )
            bone.keyframe_insert(
                data_path="scale",
                frame=start_frame,
                group=bone_name,
                options={"INSERTKEY_AVAILABLE"},
            )

            # Iterate through each frame in the interval, re-applying the initial relative matrix
            for frame in range(start_frame + 1, end_frame):
                if frame not in frames:
                    continue
                segment_relative_matrix = copy_relative_matrix_bone(armature, bone_name, camera)
                bpy.context.scene.frame_set(frame)
                # paste_relative_matrix_bone(armature, bone_name, segment_relative_matrix, camera, frame)
                # bpy.ops.anim.keyframe_insert_menu(type="LocRotScale")
                paste_relative_matrix_bone(armature, bone_name, segment_relative_matrix, camera, frame)
                bone.keyframe_insert(data_path="location", frame=frame, group=bone_name)
                bone.keyframe_insert(
                    data_path="rotation_euler",
                    frame=frame,
                    group=bone_name,
                    options={"INSERTKEY_AVAILABLE"},
                )
                bone.keyframe_insert(
                    data_path="rotation_quaternion",
                    frame=frame,
                    group=bone_name,
                    options={"INSERTKEY_AVAILABLE"},
                )
                bone.keyframe_insert(
                    data_path="scale",
                    frame=frame,
                    group=bone_name,
                    options={"INSERTKEY_AVAILABLE"},
                )

    bpy.ops.object.mode_set(mode="OBJECT")
    print(f"Finished processing '{baked_action.name}' for {armature.name}.")


def bake_and_mark_actions(self, context, objects_to_bake, action_suffix="_baked_to_scene_camera"):
    # Check if the scene has an active camera set
    if not context.scene.camera:
        self.report({"ERROR"}, "No active camera set in the scene.")
        return {"CANCELLED"}

    for obj in objects_to_bake:

        if obj.animation_data is None:
            self.report({"WARNING"}, f"No animation data found for {obj.name}.")
            return {"CANCELLED"}

        # Check for already baked action
        current_action = obj.animation_data.action
        if current_action and current_action.name.endswith(action_suffix):
            original_action_name = current_action.name[: -len(action_suffix)]
            original_action = bpy.data.actions.get(original_action_name, None)
            if not original_action:
                self.report(
                    {"ERROR"},
                    f"Baked action '{current_action.name}' exists but original action '{original_action_name}' does not.",
                )
                return {"CANCELLED"}

        # Initialize frames set
        frames = set()

        # Attempt to retrieve frame ranges from TIMELINE_object_list
        for timeline_obj in getattr(context.scene, "TIMELINE_object_list", []):
            if timeline_obj.object_reference == obj:
                found_frames = True
                for frame_range in timeline_obj.frame_ranges:
                    start_range = frame_range.start_range
                    end_range = frame_range.end_range
                    frames.update(range(max(1, start_range), min(context.scene.frame_end + 1, end_range + 1)))
            else:
                found_frames = False

        # If no specific frames were found, use the entire scene frame range
        if not found_frames:
            frames.update(range(context.scene.frame_start, context.scene.frame_end + 1))

        frames = sorted(list(frames))  # Sort and remove duplicates

        print(frames)

        # Always use the scene's active camera
        original_action = obj.animation_data.action

        if original_action is None:
            continue  # Skip objects without animation data

        if obj.type == "ARMATURE":
            selected_bones = [bone.name for bone in context.scene.TIMELINE_bone_list]
            # print(selected_bones)
            baked_action = duplicate_action(obj, action_suffix)
            stick_bone_poses_to_camera(obj, context, original_action, baked_action, selected_bones, frames)
        else:
            baked_action = duplicate_action(obj, action_suffix)
            stick_object_poses_to_camera(obj, context, original_action, baked_action, frames)

    return {"FINISHED"}


class AMP_OT_Enable(bpy.types.Operator):
    """Enable Camera Stepper on selected objects"""

    bl_idname = "anim.amp_enable"
    bl_label = "Enable Camera Stepper"

    def execute(self, context):
        # Get a set of all objects currently in the TIMELINE list
        list_objects = {item.object_reference for item in context.scene.TIMELINE_object_list}

        # Extend the check to include objects that are armatures
        # or have the amp_camera_stepper_properties attribute.
        selected_objs_not_in_list = [
            obj
            for obj in context.selected_objects
            if obj not in list_objects and (obj.type == "ARMATURE" or hasattr(obj, "amp_camera_stepper_properties"))
        ]

        for obj in selected_objs_not_in_list:
            # Check and enable TIMELINE properties if the object has them
            if hasattr(obj, "amp_camera_stepper_properties"):
                obj.amp_camera_stepper_properties.enabled = True

            # Add the object or armature to the TIMELINE list
            new_item = context.scene.TIMELINE_object_list.add()
            new_item.object_reference = obj

            # If the object is an armature and doesn't have the custom properties,
            # You may want to initialize or set them here if necessary
            # This step depends on your implementation and needs

        self.report({"INFO"}, f"Enabled TIMELINE for {len(selected_objs_not_in_list)} objects.")

        return {"FINISHED"}


class AMP_OT_BakeSelected(bpy.types.Operator):
    """Bake TIMELINE for the selected object only."""

    bl_idname = "anim.amp_bake_selected_object"
    bl_label = "Bake Selected Object"

    def execute(self, context):
        # Get the actively selected list item
        index = context.scene.TIMELINE_object_list_index
        item = context.scene.TIMELINE_object_list[index] if index < len(context.scene.TIMELINE_object_list) else None

        if not item or not item.object_reference or not item.object_reference.amp_camera_stepper_properties.enabled:
            self.report({"WARNING"}, "No valid or enabled object selected in the TIMELINE list.")
            return {"CANCELLED"}

        obj = item.object_reference

        # Temporarily disable use_baked_action if it was enabled
        original_use_baked_action = item.use_baked_action
        if original_use_baked_action:
            item.use_baked_action = False
            item.update_action_use(context)

        # Bake the selected object
        bake_and_mark_actions(self, context, [obj])

        # Restore the use_baked_action flag after baking
        item.use_baked_action = original_use_baked_action
        if original_use_baked_action:
            item.update_action_use(context)

        item.use_baked_action = True

        self.report({"INFO"}, f"Baked action for '{obj.name}' successfully.")
        return {"FINISHED"}


class AMP_OT_Disable(bpy.types.Operator):
    """Disable TIMELINE mechanism for the selected list item and remove it from the list."""

    bl_idname = "anim.amp_disable"
    bl_label = "Disable TIMELINE"

    @classmethod
    def poll(cls, context):
        # Ensure there's a valid item selected in the list.
        items = context.scene.TIMELINE_object_list
        index = context.scene.TIMELINE_object_list_index
        return len(items) > 0 and 0 <= index < len(items)

    def execute(self, context):
        scene = context.scene
        index = scene.TIMELINE_object_list_index
        if 0 <= index < len(scene.TIMELINE_object_list):
            item = scene.TIMELINE_object_list[index]
            obj = item.object_reference
            item.use_baked_action = False
            if obj and "amp_camera_stepper_properties" in obj:
                # Disable the TIMELINE mechanism
                obj.amp_camera_stepper_properties.enabled = False

                # Identify the baked action to delete
                action_suffix = "_baked_to_scene_camera"
                if obj.animation_data and obj.animation_data.action is not None:
                    baked_action = bpy.data.actions.get(obj.animation_data.action.name + action_suffix)
                    delete_action(baked_action)

                # Optionally switch back to original action here if needed
                # This step depends on how delete_action is implemented and if it resets the action for the object

            # Remove the item from the list regardless of object existence
            scene.TIMELINE_object_list.remove(index)
            # Update the list index to avoid out-of-range errors
            scene.TIMELINE_object_list_index = min(max(0, index - 1), len(scene.TIMELINE_object_list) - 1)

        return {"FINISHED"}


class AMP_OT_ToggleAll(bpy.types.Operator):
    """Toggle 'Use Baked Action' for all items in the TIMELINE list."""

    bl_idname = "anim.amp_toggle_all"
    bl_label = "Toggle All Use Baked Action"

    def execute(self, context):
        scene = context.scene
        # Toggle the use_baked_action for each item in the list
        for item in scene.TIMELINE_object_list:
            item.use_baked_action = not item.use_baked_action
            # Optionally, trigger the update method of each item to apply the change
            item.update_action_use(context)
        return {"FINISHED"}


class AMP_OT_MoveItem(bpy.types.Operator):
    """Move an item in the list"""

    bl_idname = "anim.amp_move_item"
    bl_label = "Move Item"

    direction: bpy.props.EnumProperty(items=(("UP", "Up", ""), ("DOWN", "Down", "")))

    def execute(self, context):
        scene = context.scene
        index = scene.TIMELINE_object_list_index

        if self.direction == "UP" and index > 0:
            scene.TIMELINE_object_list.move(index, index - 1)
            scene.TIMELINE_object_list_index -= 1
        elif self.direction == "DOWN" and index < len(scene.TIMELINE_object_list) - 1:
            scene.TIMELINE_object_list.move(index, index + 1)
            scene.TIMELINE_object_list_index += 1
        return {"FINISHED"}


class AMP_OT_AddBone(bpy.types.Operator):
    """Add selected bone to the list"""

    bl_idname = "anim.amp_add_bone"
    bl_label = "Add Bone"

    # def execute(self, context):
    #     armature = context.active_object
    #     if armature and armature.type == "ARMATURE" and context.mode == "POSE":
    #         selected_bones = armature.data.bones
    #         for bone in context.selected_pose_bones:
    #             if bone.name not in [item.name for item in context.scene.TIMELINE_bone_list]:
    #                 new_bone_item = context.scene.TIMELINE_bone_list.add()
    #                 new_bone_item.name = bone.name
    #         return {"FINISHED"}
    #     else:
    #         self.report({"WARNING"}, "No armature selected or not in Pose mode.")
    #         return {"CANCELLED"}
    def execute(self, context):
        # Fetch the selected TIMELINE_ObjectItem
        obj_list = context.scene.TIMELINE_object_list
        obj_index = context.scene.TIMELINE_object_list_index
        if not (0 <= obj_index < len(obj_list)):
            return {"CANCELLED"}
        obj_item = obj_list[obj_index]

        armature = context.active_object
        if armature and armature.type == "ARMATURE" and context.mode == "POSE":
            for bone in context.selected_pose_bones:
                # Check if the bone is already in the list
                if not any(b.name == bone.name for b in obj_item.bone_list):
                    new_bone_item = obj_item.bone_list.add()
                    new_bone_item.name = bone.name
            return {"FINISHED"}
        else:
            self.report({"WARNING"}, "No armature selected or not in Pose mode.")
            return {"CANCELLED"}


class AMP_OT_MoveBone(bpy.types.Operator):
    """Move a bone in the list up or down"""

    bl_idname = "anim.amp_move_bone"
    bl_label = "Move Bone"

    direction: bpy.props.EnumProperty(items=[("UP", "Up", ""), ("DOWN", "Down", "")])

    def execute(self, context):
        obj_list = context.scene.TIMELINE_object_list
        obj_index = context.scene.TIMELINE_object_list_index
        if not (0 <= obj_index < len(obj_list)):
            return {"CANCELLED"}
        obj_item = obj_list[obj_index]
        bone_list = obj_item.bone_list
        index = obj_item.bone_list_index
        # bone_list = context.scene.TIMELINE_bone_list
        # index = context.scene.TIMELINE_bone_list_index

        # Move up
        if self.direction == "UP" and index > 0:
            bone_list.move(index, index - 1)
            obj_item.bone_list_index -= 1

        # Move down
        elif self.direction == "DOWN" and index < len(bone_list) - 1:
            bone_list.move(index, index + 1)
            obj_item.bone_list_index += 1

        return {"FINISHED"}


class AMP_OT_RemoveBone(bpy.types.Operator):
    """Remove selected bone from the list"""

    bl_idname = "anim.amp_remove_bone"
    bl_label = "Remove Bone"

    def execute(self, context):
        obj_list = context.scene.TIMELINE_object_list
        obj_index = context.scene.TIMELINE_object_list_index
        if not (0 <= obj_index < len(obj_list)):
            return {"CANCELLED"}
        obj_item = obj_list[obj_index]
        bone_list = obj_item.bone_list
        index = obj_item.bone_list_index
        # bone_list = context.scene.TIMELINE_bone_list
        # index = context.scene.TIMELINE_bone_list_index

        if 0 <= index < len(bone_list):
            bone_list.remove(index)
            obj_item.bone_list_index = min(max(0, index - 1), len(bone_list) - 1)

        return {"FINISHED"}


class AMP_OT_AddFrameRange(bpy.types.Operator):
    """Add a new frame range to the selected object."""

    bl_idname = "anim.amp_add_frame_range"
    bl_label = "Add Frame Range"

    @classmethod
    def poll(cls, context):
        index = context.scene.TIMELINE_object_list_index
        return 0 <= index < len(context.scene.TIMELINE_object_list)

    def execute(self, context):
        obj_list = context.scene.TIMELINE_object_list
        index = context.scene.TIMELINE_object_list_index
        if not (0 <= index < len(obj_list)):
            return {"CANCELLED"}
        obj_item = obj_list[index]
        add_item_to_list(obj_item.frame_ranges, TIMELINE_FrameRangesItem)
        return {"FINISHED"}


class AMP_OT_RemoveFrameRange(bpy.types.Operator):
    """Remove the selected frame range from the selected object."""

    bl_idname = "anim.amp_remove_frame_range"
    bl_label = "Remove Frame Range"

    @classmethod
    def poll(cls, context):
        index = context.scene.TIMELINE_object_list_index
        if not (0 <= index < len(context.scene.TIMELINE_object_list)):
            return False
        obj_item = context.scene.TIMELINE_object_list[index]
        return obj_item.frame_ranges_index >= 0

    def execute(self, context):
        obj_list = context.scene.TIMELINE_object_list
        index = context.scene.TIMELINE_object_list_index
        if not (0 <= index < len(obj_list)):
            return {"CANCELLED"}
        obj_item = obj_list[index]
        remove_item_from_list(obj_item.frame_ranges, obj_item.frame_ranges_index)
        return {"FINISHED"}


class AMP_PT_CameraStepperGraph(bpy.types.Panel):
    bl_label = "Camera Stepper"
    bl_idname = "AMP_PT_CameraStepperGraph"
    bl_space_type = "GRAPH_EDITOR"
    bl_region_type = "UI"
    bl_parent_id = "AMP_PT_AniMateProGraph"
    bl_options = {"DEFAULT_CLOSED"}
    bl_category = "Animation"

    def draw_header(self, context):
        layout = self.layout
        layout.label(text="", icon="CAMERA_DATA")

    def draw(self, context):
        draw_camera_stepper_panel(self, context)


class AMP_PT_CameraStepperDope(bpy.types.Panel):
    bl_label = "Camera Stepper"
    bl_idname = "AMP_PT_CameraStepperDope"
    bl_space_type = "DOPESHEET_EDITOR"
    bl_region_type = "UI"
    bl_parent_id = "AMP_PT_AniMateProDope"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        layout = self.layout
        layout.label(text="", icon="CAMERA_DATA")

    def draw(self, context):
        draw_camera_stepper_panel(self, context)


class AMP_PT_CameraStepperViewport(bpy.types.Panel):
    bl_label = "Camera Stepper"
    bl_idname = "AMP_PT_CameraStepperViewport"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    # bl_category = "Animation"
    bl_parent_id = "AMP_PT_AniMateProView"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        layout = self.layout
        layout.label(text="", icon="CAMERA_DATA")

    def draw(self, context):
        draw_camera_stepper_panel(self, context)


class AMP_PT_CameraStepperPop(bpy.types.Panel):
    bl_label = "Camera Stepper"
    bl_idname = "AMP_PT_CameraStepperPop"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"

    def draw(self, context):
        draw_camera_stepper_panel(self, context)


def draw_camera_stepper_panel(self, context):
    layout = self.layout
    scene = context.scene

    row = layout.row(align=True)
    row.template_list(
        "TIMELINE_UL_objects",
        "The_List",
        scene,
        "TIMELINE_object_list",
        scene,
        "TIMELINE_object_list_index",
    )

    col = row.column(align=True)
    col.operator("anim.amp_enable", icon="ADD", text="")
    col.operator("anim.amp_disable", icon="REMOVE", text="")
    col.operator("anim.amp_toggle_all", icon="KEYFRAME", text="")
    col.operator("anim.amp_bake_selected_object", icon="FILE_REFRESH", text="")
    col.separator()

    col.operator("anim.amp_move_item", icon="TRIA_UP", text="").direction = "UP"
    col.operator("anim.amp_move_item", icon="TRIA_DOWN", text="").direction = "DOWN"

    # Display bone management UI for selected armature
    index = scene.TIMELINE_object_list_index
    if index >= 0 and index < len(scene.TIMELINE_object_list):
        item = scene.TIMELINE_object_list[index]

        ############# FRAME RANGES #############

        layout.label(text="Frame Ranges:")
        row = layout.row()
        row.template_list("TIMELINE_UL_frame_ranges", "", item, "frame_ranges", item, "frame_ranges_index", rows=3)

        # Buttons for managing frame ranges
        col = row.column(align=True)
        col.operator("anim.amp_add_frame_range", icon="ADD", text="")
        col.operator("anim.amp_remove_frame_range", icon="REMOVE", text="")

        # col.operator("anim.amp_move_frame_range", icon="TRIA_UP", text="").direction = "UP"
        # col.operator("anim.amp_move_frame_range", icon="TRIA_DOWN", text="").direction = "DOWN"
        ############# BONES #############

        if item.object_reference and item.object_reference.type == "ARMATURE":
            layout.label(text="Armature Bones:")

            # Display bone list for the selected item
            row = layout.row()
            row.template_list("TIMELINE_UL_bones", "", item, "bone_list", item, "bone_list_index", rows=3)

            # Button column for managing the bone list within the selected object item
            col = row.column(align=True)
            col.operator("anim.amp_add_bone", icon="PLUS", text="")
            col.operator("anim.amp_remove_bone", icon="REMOVE", text="")
            # # Bone List
            # row = layout.row()
            # row.template_list(
            #     "TIMELINE_UL_bones", "", scene, "TIMELINE_bone_list", scene, "TIMELINE_bone_list_index", rows=3
            # )

            # # Column for list management buttons (remove, move up, move down)
            # col = row.column(align=True)
            # col.operator("anim.amp_add_bone", icon="PLUS", text="")
            # col.operator("anim.amp_remove_bone", icon="REMOVE", text="")
            col.operator("anim.amp_move_bone", icon="TRIA_UP", text="").direction = "UP"
            col.operator("anim.amp_move_bone", icon="TRIA_DOWN", text="").direction = "DOWN"

    else:
        layout.label(text="Select an item from the list.")


class TIMELINE_UL_objects(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        obj_item = item.object_reference
        if not obj_item:
            layout.label(text="Missing Object", icon="ERROR")
            return

        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row(align=True)

            icon = "RESTRICT_SELECT_OFF" if obj_item.select_get() else "RESTRICT_SELECT_ON"
            row.operator("anim.amp_select_object", text="", icon=icon, emboss=False).object_name = obj_item.name
            row.operator("anim.amp_select_object", text=obj_item.name, emboss=False).object_name = obj_item.name

            row.prop(
                item,
                "use_baked_action",
                text="",
                icon="KEYTYPE_MOVING_HOLD_VEC" if item.use_baked_action else "HANDLETYPE_FREE_VEC",
            )


class TIMELINE_UL_bones(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        # This method draws each item in the list
        if item.name:
            layout.label(text=item.name, icon="BONE_DATA")


def update_frame_ranges(self, context):
    # Assuming this gets the correct list of frame ranges. Adjust as needed.
    frame_ranges = [item for item in self.id_data.frame_ranges]
    frame_ranges.sort(key=lambda item: item.start_range)  # Ensure ranges are sorted

    for i, frame_range in enumerate(frame_ranges):
        # Ensure the start is always smaller and within the scene's range,
        # and the end is always higher than the start and within the scene's range.
        if i > 0:
            # Ensure no overlap with the previous range
            frame_range.start_range = max(frame_range.start_range, frame_ranges[i - 1].end_range + 1)
        if i < len(frame_ranges) - 1:
            # Ensure no overlap with the next range
            frame_range.end_range = min(frame_range.end_range, frame_ranges[i + 1].start_range - 1)

        # Ensure start and end are within the scene's timeline
        frame_range.start_range = max(1, min(frame_range.start_range, bpy.context.scene.frame_end))
        frame_range.end_range = max(
            frame_range.start_range + 1, min(frame_range.end_range, bpy.context.scene.frame_end)
        )


def start_range_update(self, context):
    """Called when start_range is changed."""
    # Ensure the start is at least 1 and not greater than end_range - 1
    self.start_range = max(1, min(self.start_range, self.end_range - 1))
    update_frame_ranges(self, context)


def end_range_update(self, context):
    """Called when end_range is changed."""
    # Ensure the end is at least start_range + 1 and within the scene range
    self.end_range = max(self.start_range + 1, min(self.end_range, bpy.context.scene.frame_end))
    update_frame_ranges(self, context)


class TIMELINE_FrameRangesItem(bpy.types.PropertyGroup):
    start_range: bpy.props.IntProperty(name="Start Frame", default=1, update=utils.curve.update_frame_range_end_frame)
    end_range: bpy.props.IntProperty(name="End Frame", default=250, update=utils.curve.update_frame_range_start_frame)


class TIMELINE_UL_frame_ranges(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        active_index = getattr(active_data, active_propname)
        icon = "RESTRICT_SELECT_OFF" if index == active_index else "RESTRICT_SELECT_ON"
        row.label(text="", icon=icon)
        row.prop(item, "start_range", text="Start")
        row.prop(item, "end_range", text="End")


class TIMELINE_BoneItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Bone Name")


class TIMELINE_ObjectItem(bpy.types.PropertyGroup):
    object_reference: bpy.props.PointerProperty(name="Object", type=bpy.types.Object)
    use_baked_action: bpy.props.BoolProperty(
        name="Use Baked Action",
        default=False,
        update=lambda self, context: self.update_action_use(context),
        description="Use baked action instead of original action",
    )
    original_action_name: bpy.props.StringProperty(name="Original Action Name")  # Store the original action name

    frame_ranges: bpy.props.CollectionProperty(type=TIMELINE_FrameRangesItem)
    frame_ranges_index: bpy.props.IntProperty(name="Frame Ranges Index", default=0)

    bone_list: bpy.props.CollectionProperty(type=TIMELINE_BoneItem)
    bone_list_index: bpy.props.IntProperty(name="Bone List Index", default=0)

    def add_frame_range(self, start, end):
        frame_range_item = self.frame_ranges.add()
        frame_range_item.start_range = start
        frame_range_item.end_range = end

    def update_action_use(self, context):
        obj = self.object_reference
        if not obj or not obj.animation_data or not obj.animation_data.action:
            return

        # Extract the base action name without the suffix
        original_action_name = obj.animation_data.action.name.replace("_baked_to_scene_camera", "")
        baked_action_name = original_action_name + "_baked_to_scene_camera"

        if self.use_baked_action:
            # Switch to the baked action
            baked_action = bpy.data.actions.get(baked_action_name)
            if baked_action:
                obj.animation_data.action = baked_action
        else:
            # Switch back to the original action
            original_action = bpy.data.actions.get(original_action_name)
            if original_action:
                obj.animation_data.action = original_action


class AMP_OT_SelectElement(bpy.types.Operator):
    """Select Object in 3D View"""

    bl_idname = "anim.amp_select_object"
    bl_label = "Select Object"
    bl_options = {"REGISTER", "UNDO"}

    object_name: bpy.props.StringProperty()

    def execute(self, context):
        # Ensure we are in Object mode
        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        # Deselect all objects
        bpy.ops.object.select_all(action="DESELECT")

        # Select the specified object
        obj = bpy.data.objects.get(self.object_name)

        if obj and obj.name in context.view_layer.objects:
            context.view_layer.objects.active = obj
            obj.select_set(True)

            for i, item in enumerate(context.scene.TIMELINE_object_list):
                if item.object_reference == obj:
                    context.scene.TIMELINE_object_list_index = i
                    break

        return {"FINISHED"}


class TIMELINE_BakeToCameraProperties(bpy.types.PropertyGroup):
    enabled: bpy.props.BoolProperty(
        name="Enable TIMELINE", description="Enable or disable the bake to camera for this object", default=False
    )

    camera: bpy.props.PointerProperty(
        name="TIMELINE Camera",
        description="Camera to use for bake to camera calculations",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == "CAMERA",
    )

    frame_range: bpy.props.IntVectorProperty(
        name="Frame Range", description="The frame range for the bake to camera mechanism", size=2, default=(1, 250)
    )


classes = (
    TIMELINE_BakeToCameraProperties,
    TIMELINE_FrameRangesItem,
    TIMELINE_BoneItem,
    TIMELINE_ObjectItem,
    TIMELINE_UL_frame_ranges,
    TIMELINE_UL_bones,
    TIMELINE_UL_objects,
    AMP_OT_Enable,
    AMP_OT_Disable,
    AMP_OT_MoveItem,
    # AMP_OT_FrameRange,
    AMP_OT_ToggleAll,
    AMP_OT_AddBone,
    AMP_OT_MoveBone,
    AMP_OT_RemoveBone,
    AMP_OT_AddFrameRange,
    AMP_OT_BakeSelected,
    AMP_OT_RemoveFrameRange,
    AMP_OT_SelectElement,
    # AMP_PT_CameraStepperGraph,
    # AMP_PT_CameraStepperDope,
    # AMP_PT_CameraStepperViewport,
    AMP_PT_CameraStepperPop,
)


def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            pass

    bpy.types.Scene.TIMELINE_object_list = bpy.props.CollectionProperty(type=TIMELINE_ObjectItem)
    bpy.types.Scene.TIMELINE_object_list_index = bpy.props.IntProperty(name="Active Object Index", default=0)

    bpy.types.Scene.TIMELINE_bone_list = bpy.props.CollectionProperty(type=TIMELINE_BoneItem)
    bpy.types.Scene.TIMELINE_bone_list_index = bpy.props.IntProperty(name="Bone List Index", default=0)

    bpy.types.Scene.TIMELINE_range_list = bpy.props.CollectionProperty(type=TIMELINE_FrameRangesItem)
    bpy.types.Scene.TIMELINE_range_list_index = bpy.props.IntProperty(name="Frame Ranges List Index", default=0)

    bpy.types.Object.amp_camera_stepper_properties = bpy.props.PointerProperty(type=TIMELINE_BakeToCameraProperties)
    bpy.types.Armature.amp_camera_stepper_properties = bpy.props.PointerProperty(type=TIMELINE_BakeToCameraProperties)

    bpy.types.Scene.frame_ranges = bpy.props.CollectionProperty(type=TIMELINE_FrameRangesItem)


def unregister():
    del bpy.types.Scene.TIMELINE_object_list
    del bpy.types.Scene.TIMELINE_object_list_index

    del bpy.types.Scene.TIMELINE_bone_list
    del bpy.types.Scene.TIMELINE_bone_list_index

    del bpy.types.Scene.TIMELINE_range_list
    del bpy.types.Scene.TIMELINE_range_list_index

    del bpy.types.Object.amp_camera_stepper_properties
    del bpy.types.Armature.amp_camera_stepper_properties

    del bpy.types.Scene.frame_ranges

    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except ValueError:
            pass


if __name__ == "__main__":
    register()
