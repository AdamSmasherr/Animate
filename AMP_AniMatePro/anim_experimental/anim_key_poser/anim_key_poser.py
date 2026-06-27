import bpy
from ... import utils
from bpy.props import IntProperty, BoolProperty, EnumProperty
from .anim_key_poser_baker import draw_keyposer_baker
from .anim_key_poser_time_warper import AnimTimeWarperButton


def start_keyposer(obj):
    scene = bpy.context.scene

    # Ensure the object uses NLA and has tracks
    anim_data = obj.animation_data
    if not anim_data or not anim_data.use_nla:
        anim_data.use_nla = True

    # Ensure no duplicate NLA track names
    track_names = [track.name for track in anim_data.nla_tracks]
    unique_track_names = set()
    for i, name in enumerate(track_names):
        if name in unique_track_names:
            new_name = name + "_unique"
            anim_data.nla_tracks[i].name = new_name
            unique_track_names.add(new_name)
        else:
            unique_track_names.add(name)

    # Update the list of tracks in the UI
    update_keyposer_ui_list(obj, anim_data.nla_tracks)


def update_keyposer_ui_list(obj, nla_tracks):
    props = bpy.context.scene.amp_keyposer_properties
    props.nla_tracks.clear()

    for track in reversed(obj.animation_data.nla_tracks):
        for strip in track.strips:
            if strip.action:
                utils.dprint(f"Action Updated: {strip.action.name}")
                item = props.nla_tracks.add()
                item.name = f"{strip.action.name}"
                item.action_path = f"bpy.data.actions['{strip.action.name}']"
                item.action_ref = f"action:{strip.action.name}"
                item.track_name = track.name
                item.strip_name = strip.name


def update_active_track_index(self, context):
    obj = context.active_object
    if obj and obj.animation_data and obj.animation_data.nla_tracks:
        # Convert UI index to internal index
        internal_index = len(obj.animation_data.nla_tracks) - 1 - self.active_track_index

        # Make sure the index is valid
        if internal_index >= 0 and internal_index < len(obj.animation_data.nla_tracks):
            if context.scene.is_nla_tweakmode:
                tweak_mode_nla_strip(context, obj, enter=False)

            track = obj.animation_data.nla_tracks[internal_index]

            # Deselect all tracks and strips
            deselect_all_tracks(obj)
            deselect_all_strips(obj)

            # Select the track and its strips
            track.select = True
            for strip in track.strips:
                strip.select = True  # Assuming you want to select all strips in the track

            # Set as active track for NLA editor context
            obj.animation_data.nla_tracks.active = track

            # Ensure obj is the active object
            context.view_layer.objects.active = obj

            # Enter tweak mode if not already in it
            if not context.scene.is_nla_tweakmode:
                tweak_mode_nla_strip(context, obj, enter=True)

            # Call function to refresh the UI list to reflect any changes
            update_keyposer_ui_list(context.active_object, context.active_object.animation_data.nla_tracks)


def update_strip_and_action_name(self, context):
    # `self.name` holds the new name and `self.action_path` holds the old action name for reference
    if "['" in self.action_path and "']" in self.action_path:
        old_action_name = self.action_path.split("['")[1].split("']")[0]
        new_name = self.name

        # if context.scene.is_nla_tweakmode:
        #     tweak_mode_nla_strip(context, obj, enter=False)

        # Find the action and rename it
        action = bpy.data.actions.get(old_action_name)
        if action:
            action.name = new_name
            # After renaming, the actual new name might differ if Blender added a suffix
            actual_new_name = action.name

            # Now, find the corresponding strip in all NLA tracks and update the name
            for obj in bpy.data.objects:
                # if obj.animation_data and obj.animation_data.nla_tracks:
                if obj.animation_data and obj.animation_data.nla_tracks and len(obj.animation_data.nla_tracks) > 0:
                    for track in obj.animation_data.nla_tracks:
                        for strip in track.strips:
                            if strip.action == action:
                                strip.name = actual_new_name  # Update strip name to match the action's actual new name
                                # Update 'action_path' and 'name' properties to reflect the actual new name
                                self.action_path = f"bpy.data.actions['{actual_new_name}']"
                                self.name = actual_new_name
                                break


def update_nla_strip_properties(self, context):
    # Split the action path to get the action name
    action_name = self.action_path.split("['")[1].split("']")[0]

    if context.active_object.animation_data and len(context.active_object.animation_data.nla_tracks) > 0:
        # Locate the corresponding NLA strip
        for track in context.active_object.animation_data.nla_tracks:
            for strip in track.strips:
                if strip.action and strip.action.name == action_name:
                    # Update strip properties
                    strip.blend_type = self.blend_type
                    strip.extrapolation = self.extrapolation
                    strip.influence = self.influence
                    # update_keyposer_ui_list(context.active_object, context.active_object.animation_data.nla_tracks)
                    break


def anim_data_type(obj):
    """Get the animation data of an object."""
    return getattr(obj, "animation_data", None)


def tweak_mode_nla_strip(context, obj, enter=True):
    """Toggle tweak mode for NLA strip."""
    anim_data = anim_data_type(obj)
    if not anim_data:
        utils.dprint(f"No animation data for {obj.name}")
        return

    window = context.window
    screen = window.screen
    old_area_type = screen.areas[0].type
    screen.areas[0].type = "NLA_EDITOR"
    area = screen.areas[0]
    scene = context.scene

    with context.temp_override(window=window, area=area):
        if scene.is_nla_tweakmode:
            bpy.ops.nla.tweakmode_exit()
            utils.dprint(f"Exiting tweak mode for {obj.name}")

        anim_data.action = None  # Ensure no active action outside the NLA

        if enter:
            try:
                bpy.ops.nla.tweakmode_enter(use_upper_stack_evaluation=True)
                utils.dprint(f"Entering tweak mode for {obj.name}")
            except RuntimeError as e:
                utils.dprint(f"Error entering tweak mode for {obj.name}: {e}")

    screen.areas[0].type = old_area_type


def deselect_all_tracks(obj):
    """
    Deselect all NLA tracks for the given object.

    :param obj: The object whose NLA tracks are to be deselected.
    """
    for track in obj.animation_data.nla_tracks:
        track.select = False


def deselect_all_strips(obj):
    """
    Deselect all NLA strips for the given object.

    :param obj: The object whose NLA strips are to be deselected.
    """
    # Iterate through all tracks of the object
    for track in obj.animation_data.nla_tracks:
        # Iterate through all strips within the current track
        for strip in track.strips:
            # Deselect the strip
            strip.select = False


def find_track_with_action(obj, action_name):
    """
    Find the NLA track that contains the specified action.

    :param obj: The object to search the NLA tracks on.
    :param action_name: The name of the action to search for.
    :return: The NLA track containing the action, or None if not found.
    """
    if obj.animation_data and obj.animation_data.nla_tracks:
        for track in obj.animation_data.nla_tracks:
            for strip in track.strips:
                if strip.action and strip.action.name == action_name:
                    return track
    return None


def confirm_clear_nla_tracks(context):
    # This is a placeholder for the confirmation functionality
    # Ideally, use a modal operator to confirm with the user
    return True  # Placeholder for confirmation


def add_and_select_keypose_layer(obj, context):
    if not obj.animation_data:
        obj.animation_data_create()

    scene = bpy.context.scene

    # Generate unique track name
    base_track_name = obj.name + "_keyposer_track"
    track_names = {track.name for track in obj.animation_data.nla_tracks}
    track_name = next(
        (f"{base_track_name}_{i}" for i in range(1, 1000) if f"{base_track_name}_{i}" not in track_names), None
    )

    # Generate unique action name
    base_action_name = obj.name + "_keyposer_layer"
    action_names = {action.name for action in bpy.data.actions}
    action_name = next(
        (f"{base_action_name}_{i}" for i in range(1, 1000) if f"{base_action_name}_{i}" not in action_names), None
    )

    start_frame = scene.frame_start
    end_frame = scene.frame_end

    # Create a new action
    action = bpy.data.actions.new(name=action_name)
    action.frame_range = (start_frame, end_frame)

    # Add a new NLA track and strip
    new_track = obj.animation_data.nla_tracks.new()
    new_track.name = track_name
    new_strip = new_track.strips.new(action_name, start_frame, action)
    new_strip.action_frame_start = start_frame
    new_strip.action_frame_end = end_frame
    new_strip.extrapolation = "NOTHING"
    new_strip.blend_type = "COMBINE"
    new_strip.influence = 1.0
    new_strip.use_animated_influence = True

    # Select the new track and strip
    for track in obj.animation_data.nla_tracks:
        track.select = False  # Deselect others
        if track == new_track:
            track.select = True
            obj.animation_data.nla_tracks.active = track
            for strip in track.strips:
                strip.select = False  # Deselect others
                if strip == new_strip:
                    strip.select = True

    tweak_mode_nla_strip(context, obj, enter=True)
    frame_range = [start_frame, end_frame]
    key_start_and_end_frames(obj, frame_range)

    # Update UI list to reflect changes
    update_keyposer_ui_list(obj, obj.animation_data.nla_tracks)


def key_start_and_end_frames(obj, frame_range):

    for frame in frame_range:
        bpy.context.scene.frame_current = frame
        # Keyframe all pose bones using the specific keyframe type, within the proper context
        if obj.type == "ARMATURE" and obj.mode == "POSE":
            bpy.context.view_layer.objects.active = obj  # Ensure the armature is the active object
            bpy.ops.object.mode_set(mode="POSE")

            for bone in obj.pose.bones:
                bone.select = True  # Correct way to select the bone for keyframing

            bpy.ops.anim.keyframe_insert_menu(type="LocRotScale")
            bpy.ops.object.mode_set(mode="OBJECT")  # Optionally switch back to object mode
        else:
            # Handle non-armature objects
            if obj.animation_data:
                bpy.context.view_layer.objects.active = obj
                bpy.ops.anim.keyframe_insert_menu(type="LocRotScale")

    bpy.context.scene.frame_current = frame_range[0]  # Reset the frame to the start frame


def cleanup_after_deactivation(obj):
    # Check if the object has animation data and NLA tracks
    if obj.animation_data and obj.animation_data.nla_tracks:
        # Loop through the NLA tracks in reverse to avoid index errors during deletion
        for track in reversed(obj.animation_data.nla_tracks):
            obj.animation_data.nla_tracks.remove(track)
        print("All NLA tracks for the object have been deleted.")


def insert_keyposer_keyframes(self, obj, context, key_types):
    frame_start = context.scene.frame_start
    frame_end = context.scene.frame_end
    frames = [frame_start, frame_end]

    print(frames)

    def insert_keyframe_for_bone(bone, frame, key_types):
        if key_types.get("loc", False):
            bone.keyframe_insert(data_path="location", frame=frame)
        if key_types.get("rot", False):
            # Determine the correct rotation data path based on the bone's rotation mode
            rotation_data_path = "rotation_euler"
            if bone.rotation_mode == "QUATERNION":
                rotation_data_path = "rotation_quaternion"
            elif bone.rotation_mode == "AXIS_ANGLE":
                rotation_data_path = "rotation_axis_angle"
            bone.keyframe_insert(data_path=rotation_data_path, frame=frame)
        if key_types.get("scale", False):
            bone.keyframe_insert(data_path="scale", frame=frame)

    if obj.type == "ARMATURE" and obj.animation_data and obj.animation_data.action:
        for bone in obj.pose.bones:
            if not bone.bone.hide:  # Check if the bone is not hidden
                for frame in frames:
                    insert_keyframe_for_bone(bone, frame, key_types)
    else:
        # Handle non-armature objects
        for frame in frames:
            if key_types.get("loc", False):
                obj.keyframe_insert(data_path="location", frame=frame)
            if key_types.get("rot", False):
                obj.keyframe_insert(data_path="rotation_euler", frame=frame)  # Adjust based on obj.rotation_mode
            if key_types.get("scale", False):
                obj.keyframe_insert(data_path="scale", frame=frame)

    print("Keyframes inserted for frames:", frames)


def select_corresponding_nla_track(self, context, obj):
    action_name = obj.animation_data.action.name
    for track in obj.animation_data.nla_tracks:
        for strip in track.strips:
            if strip.action and strip.action.name == action_name:
                # Ensure the track is selected and set as active
                track.select = True
                obj.animation_data.nla_tracks.active = track
                return


class AMP_OT_StartAnimKeyPoser(bpy.types.Operator):
    """Toggle the state of Anim KeyPoser, creating a special key poses track in the NLA Editor"""

    bl_idname = "anim.amp_start_animkeyposer"
    bl_label = "Start Anim Key Poser"
    bl_options = {"REGISTER", "UNDO"}

    # Define input properties
    key_loc: BoolProperty(name="Location", default=True)
    key_rot: BoolProperty(name="Rotation", default=True)
    key_scale: BoolProperty(name="Scale", default=True)
    slice_on_markers: BoolProperty(name="Slice on Markers", default=True)

    def execute(self, context):
        props = context.scene.amp_keyposer_properties
        obj = bpy.context.active_object

        if not anim_data_type(obj):
            self.report({"WARNING"}, "Active object must have animation data.")
            return {"CANCELLED"}

        if not props.is_keyposer_active:
            # Activate KeyPoser
            self.activate_keyposer(context, obj)
        else:
            # Deactivate KeyPoser
            self.deactivate_keyposer(context, obj)

        # Update the UI list to reflect the changes
        update_keyposer_ui_list(obj, obj.animation_data.nla_tracks)

        return {"FINISHED"}

    def activate_keyposer(self, context, obj):
        props = context.scene.amp_keyposer_properties

        # Step 1: Require an active action on the active object
        if not obj or not obj.animation_data or not obj.animation_data.action:
            self.report({"WARNING"}, "Active object must have an active action.")
            return {"CANCELLED"}

        props.is_keyposer_active = True

        # Ensure NLA is enabled for the object
        obj.animation_data.use_nla = True

        # Optionally clear existing tracks after confirmation
        if obj.animation_data.nla_tracks and not confirm_clear_nla_tracks(context):
            return {"CANCELLED"}

        # # setup NLA editor override
        # dope_editor_area = next((area for area in bpy.context.screen.areas if area.type == "DOPESHEET_EDITOR"), None)
        # region = dope_editor_area.regions[0]
        # if dope_editor_area:
        #     dope_editor_area.spaces.active.mode = "ACTION"
        # with bpy.context.temp_override(area=dope_editor_area, region=region, active_object=obj):
        #     bpy.ops.action.push_down()

        # Directly push the action to an NLA track without needing a Dopesheet Editor
        action = obj.animation_data.action
        track = obj.animation_data.nla_tracks.new()  # Create a new NLA track
        track.name = action.name + "_NLA"  # Set the name after creating the track
        # Convert frame_range start to integer
        start_frame = int(action.frame_range[0])
        strip = track.strips.new(action.name, start_frame, action)
        strip.action_frame_start = start_frame
        strip.action_frame_end = int(action.frame_range[1])

        # Clear the active action to prevent conflicts
        obj.animation_data.action = None

        # Step 4: Add a new key pose layer and select it in the list
        add_and_select_keypose_layer(obj, context)

        # Step 5: Add keyframe on first and last frame:
        # key_types = {"loc": self.key_loc, "rot": self.key_rot, "scale": self.key_scale}
        # insert_keyposer_keyframes(self, obj, context, key_types)

    def deactivate_keyposer(self, context, obj):
        props = context.scene.amp_keyposer_properties
        props.is_keyposer_active = False

        # go out of tweak mode or the action is read only
        if context.scene.is_nla_tweakmode:
            tweak_mode_nla_strip(context, obj, enter=False)

        # Ensure there's at least one NLA track from which to take the bottom action
        if obj.animation_data.nla_tracks:
            bottom_track = obj.animation_data.nla_tracks[0]
            if bottom_track.strips:
                bottom_action = bottom_track.strips[0].action
                obj.animation_data.action = bottom_action  # Set as the main action
                print(f"Bottom Action: {bottom_action.name}")
        cleanup_after_deactivation(obj)

        self.report({"INFO"}, "Anim KeyPoser Deactivated and cleanup performed.")


def move_track(self, obj, track_index, direction):
    """
    Move the selected NLA track up or down based on the provided index and direction.
    """
    scene = bpy.context.scene

    # Convert the UI index to the internal index considering the reversed order
    internal_track_index = len(obj.animation_data.nla_tracks) - 1 - track_index

    # Find the NLA_EDITOR area and its first region to use for overriding context
    nla_editor_area = next((area for area in bpy.context.screen.areas if area.type == "NLA_EDITOR"), None)

    if nla_editor_area is None:
        self.report({"ERROR"}, "NLA Editor not found. Cannot move track.")
        return

    region = nla_editor_area.regions[0]

    # Ensure the specific track is selected
    obj.animation_data.nla_tracks[internal_track_index].select = True
    bpy.context.view_layer.objects.active = obj  # Ensure the object is active

    # Use temp_override to correctly set the context for the operation
    with bpy.context.temp_override(area=nla_editor_area, region=region, active_object=obj):

        # Exit tweak mode if necessary
        if scene.is_nla_tweakmode:

            bpy.ops.nla.tweakmode_exit()

        # Move the track in the specified direction
        bpy.ops.anim.channels_move(direction=direction)

    # Store the updated UI index
    bpy.context.scene.amp_keyposer_properties.active_track_index = track_index


class AMP_OT_move_track_nla(bpy.types.Operator):
    """Move an NLA Track up or down."""

    bl_idname = "anim.amp_move_track_nla"
    bl_label = "Move NLA Track"
    direction: bpy.props.EnumProperty(
        name="Direction",
        items=[("UP", "Up", ""), ("DOWN", "Down", "")],
        default="UP",
    )

    def execute(self, context):
        obj = context.active_object
        track_index = context.scene.amp_keyposer_properties.active_track_index

        # if trying to move the highest index of the list stop:
        if track_index == len(obj.animation_data.nla_tracks) - 1 and self.direction == "UP":
            self.report({"WARNING"}, "Cannot move the source animation layer.")
            return {"CANCELLED"}

        # if trying to move the highest index of the list stop:
        if track_index == len(obj.animation_data.nla_tracks) - 2 and self.direction == "DOWN":
            self.report({"WARNING"}, "Cannot move below the source animation layer.")
            return {"CANCELLED"}

        if 0 <= track_index < len(obj.animation_data.nla_tracks) - 1:
            move_track(self, obj, track_index, self.direction)

            # # # Update the active track index based on the move direction
            if self.direction == "UP" and track_index > 0:
                context.scene.amp_keyposer_properties.active_track_index -= 1
            elif self.direction == "DOWN" and track_index < len(obj.animation_data.nla_tracks) - 1:
                context.scene.amp_keyposer_properties.active_track_index += 1

            # Refresh the UI list to include the new track
            # update_keyposer_ui_list(obj, obj.animation_data.nla_tracks)

            self.report({"INFO"}, f"Animation Layer moved {self.direction.lower()}.")
            return {"FINISHED"}
        else:
            self.report({"WARNING"}, "Cannot move the Animation layer further.")
            return {"CANCELLED"}


class AMP_OT_add_nla_track(bpy.types.Operator):
    """Add an NLA Track"""

    bl_idname = "anim.amp_add_nla_track"
    bl_label = "Add NLA Track"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.active_object

        add_and_select_keypose_layer(obj, context)

        # Select the list element corresponding to the new track
        context.scene.amp_keyposer_properties.active_track_index = 0

        self.report({"INFO"}, f"New layer added and correctly selected in the UI list.")
        return {"FINISHED"}


class AMP_OT_remove_nla_track(bpy.types.Operator):
    """Remove the NLA track corresponding to the active index in the reversed UI list."""

    bl_idname = "anim.amp_remove_nla_track"
    bl_label = "Remove NLA Track"
    bl_options = {"REGISTER", "UNDO"}

    minimum_elements: bpy.props.IntProperty(default=2)

    def execute(self, context):
        props = context.scene.amp_keyposer_properties
        active_index = props.active_track_index
        obj = context.active_object

        if +len(obj.animation_data.nla_tracks) == self.minimum_elements:
            self.report({"WARNING"}, "A Minimum of two layers is needed.")
            return {"CANCELLED"}

        # if trying to delete the highest index of the list stop:
        if active_index == len(obj.animation_data.nla_tracks) - 1:
            self.report({"WARNING"}, "Cannot remove the source animation.")
            return {"CANCELLED"}

        # Calculate the correct internal index based on the UI's reversed order
        internal_index = len(obj.animation_data.nla_tracks) - 1 - active_index

        if context.scene.is_nla_tweakmode:
            tweak_mode_nla_strip(context, obj, enter=False)

        if 0 <= internal_index < len(obj.animation_data.nla_tracks):
            track_to_remove = obj.animation_data.nla_tracks[internal_index]
            obj.animation_data.nla_tracks.remove(track_to_remove)

            # Refresh and correctly adjust the UI list after removal
            update_keyposer_ui_list(obj, obj.animation_data.nla_tracks)

            # Adjust the active index if necessary
            props.active_track_index = max(0, min(active_index, len(props.nla_tracks) - 2))

            self.report({"INFO"}, "Track removed and list correctly updated.")
        else:
            self.report({"WARNING"}, "Invalid track index. Unable to remove.")

        return {"FINISHED"}


class AMP_OT_refresh_nla_tracks(bpy.types.Operator):
    """Refresh NLA Tracks List"""

    bl_idname = "anim.amp_refresh_nla_tracks"
    bl_label = "Refresh NLA Tracks"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.active_object
        if obj and obj.animation_data:
            update_keyposer_ui_list(obj, obj.animation_data.nla_tracks)
        return {"FINISHED"}


class AMP_PG_ActiveNLATrackItem(bpy.types.PropertyGroup):
    """Property group to hold the name of an NLA track."""

    # name: bpy.props.StringProperty(name="Name", update=update_strip_and_action_name)
    action_path: bpy.props.StringProperty(name="Action Path")
    track_name: bpy.props.StringProperty(name="Track Name")
    strip_name: bpy.props.StringProperty(name="Strip Name")


class AMP_PG_AMPKeyPoserProperties(bpy.types.PropertyGroup):
    is_keyposer_active: bpy.props.BoolProperty(
        name="Is KeyPoser Active", description="True if the Anim KeyPoser is active", default=False
    )
    is_time_warper_active: bpy.props.BoolProperty(
        name="Is Time Warper Active", description="True if the Time Warper is active", default=False
    )

    object_name: bpy.props.StringProperty(name="Object Name", description="Name of the object being manipulated")

    source_animation_name: bpy.props.StringProperty(
        name="Source Animation Name", description="Name of the source animation"
    )

    nla_tracks: bpy.props.CollectionProperty(type=AMP_PG_ActiveNLATrackItem)
    active_track_index: bpy.props.IntProperty(update=update_active_track_index)
    ui_collapse_properties: bpy.props.BoolProperty(name="Expand Properties", default=True)
    keypose_marker_radius: bpy.props.FloatProperty(name="Marker Radius", default=10, min=1.0, max=20.0)
    keypose_marker_text_size: bpy.props.FloatProperty(name="Text Size", default=10, min=1.0, max=20.0)
    keypose_marker_top_offset: bpy.props.FloatProperty(name="Top Offset", default=40, min=1.0, max=100.0)


class TIMELINE_UL_ActiveNLATracks(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index, flt_flag):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            reversed_index = len(context.active_object.animation_data.nla_tracks) - 1 - index
            track = self.find_nla_track_by_index(context, reversed_index)
            if track:
                row = layout.row(align=True)
                # Display the first strip's action name if available
                if track.strips:
                    action = track.strips[0].action if track.strips[0].action else "No Action"
                    row.prop(action, "name", text="", emboss=False, icon="ACTION")
                else:
                    row.label(text="No Strips", icon="ACTION")
                # row.prop(item, "name", text="", emboss=False, icon="ACTION")
                row.prop(track, "mute", text="", emboss=False, icon="HIDE_ON" if track.mute else "HIDE_OFF")
                row.prop(track, "lock", text="", emboss=False, icon="LOCKED" if track.lock else "UNLOCKED")
                row.prop(track, "is_solo", text="", emboss=False, icon="SOLO_ON" if track.is_solo else "SOLO_OFF")
            else:
                layout.prop(item, "name", text="", emboss=False, icon="ACTION")
        elif self.layout_type == "GRID":
            layout.alignment = "CENTER"
            layout.label(text="", icon="ACTION")

    @staticmethod
    def find_nla_track_by_index(context, index):
        obj = context.active_object
        if obj and obj.animation_data and obj.animation_data.nla_tracks:
            # Safely access the track by index if it exists
            tracks = list(obj.animation_data.nla_tracks)
            if 0 <= index < len(tracks):
                return tracks[index]
        return None


def draw_anim_keyposer_panel(self, context):
    layout = self.layout
    props = context.scene.amp_keyposer_properties

    ####### TOP UI PANEL #######

    if props.is_keyposer_active:
        layout.operator("anim.amp_start_animkeyposer", text="Deactivate Anim KeyPoser", icon="CANCEL")
    else:
        layout.operator("anim.amp_start_animkeyposer", text="Activate Anim KeyPoser", icon="PLAY")

    if props.is_keyposer_active:

        ######## BAKE AND TIMEWARP KEYPOSES ########

        layout.separator()

        row = layout.row()
        row.scale_y = 1.5

        AnimTimeWarperButton(row, context, text="Activate Time Warper", icon="MOD_WARP")
        draw_keyposer_baker(row, context)

        ####### LAYERS LIST #######

        layout.label(text="Animation Layers:")
        row = layout.row()
        row.template_list(
            "TIMELINE_UL_ActiveNLATracks", "", props, "nla_tracks", props, "active_track_index", rows=5, maxrows=5
        )

        col = row.column(align=True)
        col.operator("anim.amp_add_nla_track", icon="ADD", text="")
        col.operator("anim.amp_remove_nla_track", icon="REMOVE", text="")
        col.separator()
        col.operator("anim.amp_move_track_nla", icon="TRIA_UP", text="").direction = "UP"
        col.operator("anim.amp_move_track_nla", icon="TRIA_DOWN", text="").direction = "DOWN"
        col.separator()
        col.operator("anim.amp_refresh_nla_tracks", icon="FILE_REFRESH", text="")

        ####### LAYER PROPERTIES #######

        # Display properties for the selected track
        if props.ui_collapse_properties:
            box = layout.box()
            box.scale_y = 0.5
            row = box.row(align=True)
            row.alignment = "LEFT"
            row.prop(props, "ui_collapse_properties", icon="RIGHTARROW_THIN", text="", emboss=False)
            row.prop(props, "ui_collapse_properties", text="Layer Properties", emboss=False)

        elif props.nla_tracks and 0 <= props.active_track_index < len(props.nla_tracks):
            box = layout.box()
            selected_track_item = props.nla_tracks[props.active_track_index]

            # Title row
            row = box.row(align=True)
            row.alignment = "LEFT"
            row.scale_y = 0.5
            row.prop(props, "ui_collapse_properties", icon="DOWNARROW_HLT", text="", emboss=False)
            row.prop(props, "ui_collapse_properties", text="Layer Properties", emboss=False)

            # Properties
            col = box.column()
            col.use_property_split = True
            col.use_property_decorate = False
            draw_anim_layer_properties(col, context)


def draw_anim_layer_properties(layout, context):
    props = context.scene.amp_keyposer_properties

    if props.nla_tracks and 0 <= props.active_track_index < len(props.nla_tracks):
        # Calculate the corresponding track index in the actual Blender data structure
        obj = context.active_object

        if obj and obj.animation_data and obj.animation_data.nla_tracks:
            total_tracks = len(obj.animation_data.nla_tracks)
            # Calculate the reverse index since the UI list might be showing the tracks in reversed order
            track_index = total_tracks - 1 - props.active_track_index

            if 0 <= track_index < total_tracks:
                track = list(obj.animation_data.nla_tracks)[track_index]
                if track:
                    # Assuming the first strip is what you want to manipulate for simplicity
                    strip = track.strips[0] if track.strips else None

                    if strip:
                        # Directly manipulate the selected NLA strip properties
                        layout.prop(strip, "name", text="Name")
                        layout.prop(strip, "extrapolation", text="Extrapolation")
                        layout.prop(strip, "blend_type", text="Blend Type")

                        layout.prop(strip, "use_animated_influence", text="Animate Influence")

                        if strip.use_animated_influence:
                            row = layout.row(align=True)
                            row.active = strip.use_animated_influence
                            row.prop(strip, "influence", text="Influence")
    else:
        layout.label(text="No NLA strip selected.")


class AMP_PT_AnimKeyPoserPop(bpy.types.Panel):
    bl_label = "Anim KeyPoser"
    bl_idname = "AMP_PT_AnimKeyPoserPop"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_context = ""
    bl_options = {"DEFAULT_CLOSED"}
    bl_ui_units_x = 15

    def draw(self, context):
        layout = self.layout
        draw_anim_keyposer_panel(self, context)


class AMP_PT_AnimKeyPoserGraph(bpy.types.Panel):
    bl_label = "Anim KeyPoser"
    bl_idname = "AMP_PT_AnimKeyPoserGraph"
    bl_space_type = "GRAPH_EDITOR"
    bl_region_type = "UI"
    bl_category = "Animation"
    bl_parent_id = "AMP_PT_ExperimentalGraph"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        layout = self.layout
        layout.label(text="", icon="ARMATURE_DATA")

    def draw(self, context):
        layout = self.layout
        draw_anim_keyposer_panel(self, context)


class AMP_PT_AnimKeyPoserDope(bpy.types.Panel):
    bl_label = "Anim KeyPoser"
    bl_idname = "AMP_PT_AnimKeyPoserDope"
    bl_space_type = "DOPESHEET_EDITOR"
    bl_region_type = "UI"
    bl_category = "Animation"
    bl_parent_id = "AMP_PT_ExperimentalDope"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        layout = self.layout
        layout.label(text="", icon="ARMATURE_DATA")

    def draw(self, context):
        layout = self.layout
        draw_anim_keyposer_panel(self, context)


# class AMP_PT_AnimKeyPoserNLA(bpy.types.Panel):
#     bl_label = "Anim KeyPoser"
#     bl_idname = "AMP_PT_AnimKeyPoserNLA"
#     bl_space_type = "NLA_EDITOR"
#     bl_region_type = "UI"
#     bl_category = "Animation"
#     bl_parent_id = "AMP_PT_TimelineToolsNLA"
#     bl_options = {"DEFAULT_CLOSED"}

#     def draw_header(self, context):
#         layout = self.layout
#         layout.label(text="", icon="ARMATURE_DATA")

#     def draw(self, context):
#         layout = self.layout
#         draw_anim_keyposer_panel(self, context)


classes = (
    AMP_OT_add_nla_track,
    AMP_OT_remove_nla_track,
    AMP_OT_refresh_nla_tracks,
    AMP_OT_move_track_nla,
    # AMP_OT_select_nla_strip,
    AMP_OT_StartAnimKeyPoser,
    TIMELINE_UL_ActiveNLATracks,
    AMP_PT_AnimKeyPoserGraph,
    AMP_PT_AnimKeyPoserDope,
    # AMP_PT_AnimKeyPoserNLA,
    AMP_PT_AnimKeyPoserPop,
)


def register_properties():
    bpy.utils.register_class(AMP_PG_ActiveNLATrackItem)
    bpy.utils.register_class(AMP_PG_AMPKeyPoserProperties)
    bpy.types.Scene.amp_keyposer_properties = bpy.props.PointerProperty(type=AMP_PG_AMPKeyPoserProperties)


def unregister_properties():
    del bpy.types.Scene.amp_keyposer_properties
    bpy.utils.unregister_class(AMP_PG_AMPKeyPoserProperties)
    bpy.utils.unregister_class(AMP_PG_ActiveNLATrackItem)


def register():
    register_properties()
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
    unregister_properties()


if __name__ == "__main__":
    register()
