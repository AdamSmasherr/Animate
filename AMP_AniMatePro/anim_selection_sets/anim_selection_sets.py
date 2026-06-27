import bpy
import gpu
import blf
import re
import uuid
import json
from gpu_extras.batch import batch_for_shader
from bpy.types import Operator, Panel, PropertyGroup, UIList
from bpy.props import (
    BoolProperty,
    FloatVectorProperty,
    StringProperty,
    CollectionProperty,
    IntProperty,
    EnumProperty,
    PointerProperty,
)
from mathutils import Vector
from ..utils.customIcons import get_icon
from ..utils import refresh_ui

icon_map = {
    "BONE": "BONE_DATA",
    "LIGHT": "LIGHT_DATA",
    "CAMERA": "CAMERA_DATA",
    "OBJECT": "OBJECT_DATA",
}


def get_unique_set_name(coll, new_name, exclude_set=None):
    base_name = re.sub(r"\.\d{3}$", "", new_name)
    existing_indices = set()
    for s in coll:
        if s is exclude_set:
            continue
        if s.name == base_name:
            existing_indices.add(0)
        else:
            m = re.match(re.escape(base_name) + r"\.(\d{3})$", s.name)
            if m:
                existing_indices.add(int(m.group(1)))
    i = 1
    while i in existing_indices:
        i += 1
    return base_name if 0 not in existing_indices else f"{base_name}.{i:03d}"


class AMP_PG_AnimSetElement(PropertyGroup):
    object_ref: PointerProperty(type=bpy.types.Object)
    bone_name: StringProperty()


class AMP_PG_AnimSet(PropertyGroup):
    name: StringProperty(default="AMP_Set")
    color: FloatVectorProperty(subtype="COLOR", size=3, default=(1, 0.2, 0.2), min=0.0, max=1.0)
    pinned: BoolProperty(default=True)
    elements: CollectionProperty(type=AMP_PG_AnimSetElement)
    set_type: EnumProperty(
        name="Set Type",
        items=[
            ("BONE", "Bones", ""),
            ("LIGHT", "Lights", ""),
            ("CAMERA", "Cameras", ""),
            ("OBJECT", "Objects", ""),
        ],
        default="OBJECT",
    )
    row: IntProperty(name="Row", default=1, description="Row in the pinned UI")
    priority: IntProperty(name="Priority", default=1, description="Ordering priority within each row")
    uid: StringProperty(default="", description="Unique ID for this Anim Set")

    def get_set_icon(self):
        if not self.elements:
            return "SELECT_SET"
        return icon_map.get(self.set_type, "QUESTION")


class AMP_PG_AnimSetPreset(PropertyGroup):
    name: StringProperty(default="AnimSet_Preset")
    # Each preset now contains its own sets list.
    sets: CollectionProperty(type=AMP_PG_AnimSet)
    pinned: BoolProperty(default=True)


class AMP_PG_SceneAnimSets(PropertyGroup):
    display_settings: BoolProperty(name="Display Settings", default=False)
    display_colors: BoolProperty(name="Display Colors", default=True)
    display_icons: BoolProperty(name="Display Icons", default=True)
    simple_order: BoolProperty(name="Simple Order", default=True)
    display_presets: BoolProperty(name="Display Presets", default=False)
    display_gui: BoolProperty(name="Display GUI", default=False, update=lambda s, c: update_display_gui(s, c))
    # Removed the scene-level "sets" collection.
    # Instead, each preset (in presets) holds its own sets.
    presets: CollectionProperty(type=AMP_PG_AnimSetPreset)
    active_preset_index: IntProperty(default=-1, update=lambda s, c: None)
    # Store the active set index for the active preset.
    active_set_index: IntProperty(default=-1)
    # For move-with-keys, we still keep an active_move_set_index.
    active_move_set_index: IntProperty(default=-1)


def ensure_unique_set_names(coll):
    name_count = {}
    for anim_set in sorted(coll, key=lambda s: s.name.lower()):
        base_name = re.sub(r"\.\d{3}$", "", anim_set.name)
        if base_name not in name_count:
            name_count[base_name] = 0
            anim_set.name = base_name
        else:
            name_count[base_name] += 1
            new_name = f"{base_name}.{name_count[base_name]:03d}"
            while new_name in [s.name for s in coll]:
                name_count[base_name] += 1
                new_name = f"{base_name}.{name_count[base_name]:03d}"
            anim_set.name = new_name


def update_display_gui(self, context):
    gui_state["show_pinned_gui"] = self.display_gui
    if self.display_gui:
        if pinned_sets_draw_callback not in draw_callbacks:
            draw_callbacks.append(pinned_sets_draw_callback)
        if pinned_sets_event_handler not in event_handlers:
            event_handlers.append(pinned_sets_event_handler)
    else:
        if pinned_sets_draw_callback in draw_callbacks:
            draw_callbacks.remove(pinned_sets_draw_callback)
        if pinned_sets_event_handler in event_handlers:
            event_handlers.remove(pinned_sets_event_handler)


def detect_element_types_in_selection(context):
    st = set()
    mode = context.mode
    obj = context.active_object

    if mode == "POSE" and obj and obj.type == "ARMATURE":
        if context.selected_pose_bones:
            st.add("BONE")
    elif mode == "OBJECT":
        for o in context.selected_objects:
            if o.type == "ARMATURE":
                st.add("BONE")
            elif o.type == "CAMERA":
                st.add("CAMERA")
            elif o.type == "LIGHT":
                st.add("LIGHT")
            else:
                st.add("OBJECT")
    return st


def deselect_bones(arm_obj):
    if arm_obj and arm_obj.type == "ARMATURE":
        if arm_obj.data.bones and hasattr(arm_obj.data.bones[0], "select"):
            for b in arm_obj.data.bones:
                b.select = False
        else:
            for pb in arm_obj.pose.bones:
                pb.select = False


def evaluate_set_type(anim_set):
    has_cam, has_light, has_other = False, False, False
    for e in anim_set.elements:
        if e.bone_name:
            anim_set.set_type = "BONE"
            return
        if e.object_ref and e.object_ref.type == "CAMERA":
            has_cam = True
        elif e.object_ref and e.object_ref.type == "LIGHT":
            has_light = True
        else:
            has_other = True

    if not anim_set.elements:
        if anim_set.set_type == "BONE":
            anim_set.set_type = "BONE"
        else:
            anim_set.set_type = "OBJECT"
        return

    if has_cam and not has_light and not has_other:
        anim_set.set_type = "CAMERA"
    elif has_light and not has_cam and not has_other:
        anim_set.set_type = "LIGHT"
    else:
        anim_set.set_type = "OBJECT"


class AMP_OT_AnimSetSelect(Operator):
    bl_idname = "anim.amp_anim_set_select"
    bl_label = "Select Anim Set"
    bl_description = (
        "Select all objects/bones in this set.\n"
        "SHIFT: Add selection\n"
        "CTRL: Toggle selection\n"
        "If SHIFT/CTRL are pressed, swapping Pose/Object modes is restricted."
    )

    set_index: IntProperty()
    selection_mode: EnumProperty(
        items=[("REPLACE", "Replace", ""), ("ADD", "Add", ""), ("TOGGLE", "Toggle", "")],
        default="REPLACE",
    )

    def invoke(self, context, event):
        scene_props = context.scene.amp_anim_set
        if scene_props.active_preset_index < 0 or scene_props.active_preset_index >= len(scene_props.presets):
            self.report({"WARNING"}, "No active preset.")
            return {"CANCELLED"}
        preset = scene_props.presets[scene_props.active_preset_index]
        sets = preset.sets

        if 0 <= self.set_index < len(sets):
            anim_set = sets[self.set_index]
            if context.mode == "OBJECT" and anim_set.set_type == "BONE":
                if event.shift or event.ctrl:
                    self.report({"WARNING"}, "Cannot add/toggle bone selection in OBJECT mode.")
                    return {"CANCELLED"}
            if context.mode == "POSE" and anim_set.set_type != "BONE":
                if event.shift or event.ctrl:
                    self.report({"WARNING"}, "Cannot add/toggle object selection in POSE mode.")
                    return {"CANCELLED"}

        if event.shift and not event.ctrl:
            self.selection_mode = "ADD"
        elif event.ctrl and not event.shift:
            self.selection_mode = "TOGGLE"
        else:
            self.selection_mode = "REPLACE"
        return self.execute(context)

    def execute(self, context):
        scene_props = context.scene.amp_anim_set
        if scene_props.active_preset_index < 0 or scene_props.active_preset_index >= len(scene_props.presets):
            return {"CANCELLED"}
        preset = scene_props.presets[scene_props.active_preset_index]
        sets = preset.sets
        if not (0 <= self.set_index < len(sets)):
            return {"CANCELLED"}
        anim_set = sets[self.set_index]

        if not context.active_object:
            if context.scene.objects:
                context.view_layer.objects.active = context.scene.objects[0]
            else:
                self.report({"WARNING"}, "No objects in scene.")
                return {"CANCELLED"}

        if anim_set.set_type == "BONE":
            arm = None

            # Remove unreachable references
            for i in reversed(range(len(anim_set.elements))):
                e_item = anim_set.elements[i]
                if (
                    not e_item.object_ref
                    or e_item.object_ref.name not in bpy.data.objects
                    or e_item.object_ref.name not in [obj.name for obj in context.view_layer.objects]
                ):
                    self.report({"WARNING"}, f"Element not found. Removed from set.")
                    anim_set.elements.remove(i)

            if self.selection_mode == "REPLACE":
                bpy.ops.object.mode_set(mode="OBJECT")
                bpy.ops.object.select_all(action="DESELECT")

            for e in anim_set.elements:
                if e.object_ref and e.object_ref.type == "ARMATURE":
                    arm = e.object_ref
                    arm.select_set(True)
                    context.view_layer.objects.active = arm

            if arm:
                bpy.ops.object.mode_set(mode="POSE")

                for i in reversed(range(len(anim_set.elements))):
                    e_item = anim_set.elements[i]
                    if not arm or not arm.data.bones.get(e_item.bone_name):
                        self.report({"WARNING"}, f"Bone {e_item.bone_name} not found. Removed from set.")
                        anim_set.elements.remove(i)

                evaluate_set_type(anim_set)

                for i in reversed(range(len(anim_set.elements))):
                    e_item = anim_set.elements[i]
                    if not arm.data.bones.get(e_item.bone_name):
                        self.report({"WARNING"}, f"Bone {e_item.bone_name} not found. Removed from set.")
                        anim_set.elements.remove(i)

                if self.selection_mode == "REPLACE":
                    deselect_bones(arm)
                if self.selection_mode == "TOGGLE":
                    any_selected = False
                    for e in anim_set.elements:
                        bone = arm.pose.bones.get(e.bone_name)
                        if bone and bone.select:
                            any_selected = True
                            break
                    for e in anim_set.elements:
                        bone = arm.pose.bones.get(e.bone_name)
                        if bone:
                            bone.select = not any_selected
                else:
                    for e in anim_set.elements:
                        bone = arm.pose.bones.get(e.bone_name)
                        if bone:
                            bone.select = True

        else:
            # Remove unreachable references
            for i in reversed(range(len(anim_set.elements))):
                e_item = anim_set.elements[i]
                if (
                    not e_item.object_ref
                    or e_item.object_ref.name not in bpy.data.objects
                    or e_item.object_ref.name not in [obj.name for obj in context.view_layer.objects]
                ):
                    self.report({"WARNING"}, f"Element not found. Removed from set.")
                    anim_set.elements.remove(i)

            bpy.ops.object.mode_set(mode="OBJECT")
            if self.selection_mode == "REPLACE":
                bpy.ops.object.select_all(action="DESELECT")
            if self.selection_mode == "TOGGLE":
                any_selected = False
                for e in anim_set.elements:
                    obj = e.object_ref
                    if obj and obj.select_get():
                        any_selected = True
                        break
                for e in anim_set.elements:
                    obj = e.object_ref
                    if obj:
                        obj.select_set(not any_selected)
                        if not any_selected:
                            context.view_layer.objects.active = obj
            else:
                for e in anim_set.elements:
                    obj = e.object_ref
                    if obj:
                        obj.select_set(True)
                        context.view_layer.objects.active = obj

        return {"FINISHED"}


class AMP_OT_AnimSetAdd(Operator):
    bl_idname = "anim.amp_anim_set_add"
    bl_label = "Add Anim Set"
    bl_description = "Create a new Anim Set with the currently selected elements"

    def execute(self, context):
        distinct = detect_element_types_in_selection(context)
        if len(distinct) == 0:
            self.report({"WARNING"}, "No elements selected. Canceled.")
            return {"CANCELLED"}

        scene_props = context.scene.amp_anim_set
        if not scene_props.presets:
            new_preset = scene_props.presets.add()
            new_preset.name = "AnimSet_Preset.001"
            scene_props.active_preset_index = 0
        preset = scene_props.presets[scene_props.active_preset_index]

        new_set = preset.sets.add()
        new_set.uid = str(uuid.uuid4())
        # update the active set index to the new one
        scene_props.active_set_index = len(preset.sets) - 1

        if context.mode == "POSE":
            arm = context.active_object
            if arm and arm.type == "ARMATURE":
                for b in context.selected_pose_bones:
                    e = new_set.elements.add()
                    e.bone_name = b.name
                    e.object_ref = arm
        else:
            bpy.ops.anim.amp_anim_set_add_members(set_index=len(preset.sets) - 1)

        base_name = "object_set"
        if len(distinct) == 1:
            st = list(distinct)[0].lower()
            base_name = f"{st}_set"
            new_set.set_type = st.upper() if st != "armature" else "BONE"
        else:
            new_set.set_type = "OBJECT"

        new_set.name = base_name
        ensure_unique_set_names(preset.sets)

        if new_set.set_type == "BONE":
            new_set.color = (0.2, 1.0, 0.2)
        elif new_set.set_type == "CAMERA":
            new_set.color = (0.2, 0.2, 1.0)
        elif new_set.set_type == "LIGHT":
            new_set.color = (0.5, 0.5, 0.0)
        else:
            new_set.color = (1.0, 0.2, 0.2)

        # For ordering in the pinned UI
        if preset.sets:
            max_row = max(s.row for s in preset.sets) if preset.sets else 0
            new_set.row = max_row + 1
            new_set.priority = 1

        return {"FINISHED"}


class AMP_OT_AnimSetRemove(Operator):
    bl_idname = "anim.amp_anim_set_remove"
    bl_label = "Remove Anim Set"
    bl_description = "Delete this set from the list"

    def execute(self, context):
        scene_props = context.scene.amp_anim_set
        if scene_props.active_preset_index < 0 or scene_props.active_preset_index >= len(scene_props.presets):
            return {"CANCELLED"}
        preset = scene_props.presets[scene_props.active_preset_index]
        idx = scene_props.active_set_index
        if 0 <= idx < len(preset.sets):
            preset.sets.remove(idx)
            scene_props.active_set_index = min(idx, len(preset.sets) - 1)
            ensure_unique_set_names(preset.sets)
        return {"FINISHED"}


class AMP_OT_AnimSetMove(Operator):
    bl_idname = "anim.amp_anim_set_move"
    bl_label = "Move Anim Set"
    bl_description = "Move set up/down in the UI list"

    direction: StringProperty()

    def execute(self, context):
        scene_props = context.scene.amp_anim_set
        if scene_props.active_preset_index < 0 or scene_props.active_preset_index >= len(scene_props.presets):
            return {"CANCELLED"}
        preset = scene_props.presets[scene_props.active_preset_index]
        idx = scene_props.active_set_index
        if self.direction == "UP" and idx > 0:
            preset.sets.move(idx, idx - 1)
            scene_props.active_set_index -= 1
        elif self.direction == "DOWN" and idx < len(preset.sets) - 1:
            preset.sets.move(idx, idx + 1)
            scene_props.active_set_index += 1
        return {"FINISHED"}


class AMP_OT_AnimSetAddMembers(Operator):
    bl_idname = "anim.amp_anim_set_add_members"
    bl_label = "Add Members"
    bl_description = "Add selected elements to this set.\nIf the set ends up mixed, it becomes MULTI."

    set_index: IntProperty()

    def execute(self, context):
        scene_props = context.scene.amp_anim_set
        if scene_props.active_preset_index < 0 or scene_props.active_preset_index >= len(scene_props.presets):
            return {"CANCELLED"}
        preset = scene_props.presets[scene_props.active_preset_index]
        sets = preset.sets
        if not (0 <= self.set_index < len(sets)):
            return {"CANCELLED"}

        anim_set = sets[self.set_index]
        distinct = detect_element_types_in_selection(context)

        if not distinct:
            self.report({"WARNING"}, "No valid elements selected.")
            return {"CANCELLED"}

        if "BONE" in distinct and anim_set.set_type != "BONE":
            self.report({"WARNING"}, "Can't add bones to a non-bone set.")
            return {"CANCELLED"}

        if context.mode == "POSE":
            arm = context.active_object
            if arm and arm.type == "ARMATURE":
                for b in context.selected_pose_bones:
                    if anim_set.set_type in {"OBJECT", ""}:
                        anim_set.set_type = "BONE"
                    if anim_set.set_type != "BONE":
                        return {"CANCELLED"}
                    if not any(e.bone_name == b.name and e.object_ref == arm for e in anim_set.elements):
                        ne = anim_set.elements.add()
                        ne.bone_name = b.name
                        ne.object_ref = arm
        else:
            for o in context.selected_objects:
                if not any(e.object_ref == o for e in anim_set.elements):
                    ne = anim_set.elements.add()
                    ne.object_ref = o

        evaluate_set_type(anim_set)
        return {"FINISHED"}


class AMP_OT_AnimSetRemoveMembers(Operator):
    bl_idname = "anim.amp_anim_set_remove_members"
    bl_label = "Remove Members"
    bl_description = (
        "Remove selected elements from this set.\n"
        "If all remaining elements are a single type, set switches to that type."
    )

    set_index: IntProperty()

    def execute(self, context):
        scene_props = context.scene.amp_anim_set
        if scene_props.active_preset_index < 0 or scene_props.active_preset_index >= len(scene_props.presets):
            return {"CANCELLED"}
        preset = scene_props.presets[scene_props.active_preset_index]
        sets = preset.sets
        if not (0 <= self.set_index < len(sets)):
            return {"CANCELLED"}
        anim_set = sets[self.set_index]

        if anim_set.set_type == "BONE" and context.mode == "POSE":
            arm = context.active_object
            if arm and arm.type == "ARMATURE":
                for b in context.selected_pose_bones:
                    for i in reversed(range(len(anim_set.elements))):
                        e = anim_set.elements[i]
                        if e.bone_name == b.name and e.object_ref == arm:
                            anim_set.elements.remove(i)
        elif anim_set.set_type in {"LIGHT", "CAMERA", "OBJECT"} and context.mode == "OBJECT":
            for o in context.selected_objects:
                for i in reversed(range(len(anim_set.elements))):
                    e = anim_set.elements[i]
                    if e.object_ref == o:
                        anim_set.elements.remove(i)

        evaluate_set_type(anim_set)
        return {"FINISHED"}


class AMP_OT_AnimSetPresetAdd(Operator):
    bl_idname = "anim.amp_anim_set_preset_add"
    bl_label = "New Preset"
    bl_description = "Create a new blank preset"

    def execute(self, context):
        scene_props = context.scene.amp_anim_set
        if len(scene_props.presets) >= 9:
            self.report({"WARNING"}, "Max 9 presets reached.")
            return {"CANCELLED"}

        new_preset = scene_props.presets.add()
        new_preset.name = f"AnimSet_Preset.{len(scene_props.presets):03d}"
        scene_props.active_preset_index = len(scene_props.presets) - 1
        # Reset the active set index when switching presets.
        scene_props.active_set_index = 0
        return {"FINISHED"}


class AMP_OT_AnimSetPresetRemove(Operator):
    bl_idname = "anim.amp_anim_set_preset_remove"
    bl_label = "Remove Preset"

    def execute(self, context):
        scene_props = context.scene.amp_anim_set
        idx = scene_props.active_preset_index
        if 0 <= idx < len(scene_props.presets):
            scene_props.presets.remove(idx)
            scene_props.active_preset_index = min(idx, len(scene_props.presets) - 1)
            # Reset active set index if no presets remain.
            if len(scene_props.presets) == 0:
                scene_props.active_set_index = -1
            else:
                scene_props.active_set_index = 0
        return {"FINISHED"}


class AMP_OT_AnimSetPresetMove(Operator):
    bl_idname = "anim.amp_anim_set_preset_move"
    bl_label = "Move Preset"
    direction: StringProperty()

    def execute(self, context):
        scene_props = context.scene.amp_anim_set
        idx = scene_props.active_preset_index
        if self.direction == "UP" and idx > 0:
            scene_props.presets.move(idx, idx - 1)
            scene_props.active_preset_index = idx - 1
        elif self.direction == "DOWN" and idx < len(scene_props.presets) - 1:
            scene_props.presets.move(idx, idx + 1)
            scene_props.active_preset_index = idx + 1
        return {"FINISHED"}


class AMP_OT_AnimSetPresetCopy(Operator):
    bl_idname = "anim.amp_anim_set_preset_copy"
    bl_label = "Copy Preset"

    def execute(self, context):
        scene_props = context.scene.amp_anim_set
        idx = scene_props.active_preset_index
        if 0 <= idx < len(scene_props.presets):
            preset = scene_props.presets[idx]
            preset_data = {"name": preset.name, "sets": []}
            for s in preset.sets:
                preset_data["sets"].append(
                    {
                        "name": s.name,
                        "color": list(s.color),
                        "pinned": s.pinned,
                        "set_type": s.set_type,
                        "row": s.row,
                        "priority": s.priority,
                        "uid": s.uid,
                        "elements": [
                            {"bone_name": e.bone_name, "object_ref": e.object_ref.name if e.object_ref else ""}
                            for e in s.elements
                        ],
                    }
                )
            bpy.context.window_manager.clipboard = json.dumps(preset_data)
        return {"FINISHED"}


class AMP_OT_AnimSetPresetPaste(Operator):
    bl_idname = "anim.amp_anim_set_preset_paste"
    bl_label = "Paste Preset"

    def execute(self, context):
        scene_props = context.scene.amp_anim_set
        idx = scene_props.active_preset_index
        if 0 <= idx < len(scene_props.presets):
            preset = scene_props.presets[idx]
            try:
                preset_data = json.loads(bpy.context.window_manager.clipboard)
                preset.sets.clear()
                for s_dict in preset_data.get("sets", []):
                    new_s = preset.sets.add()
                    new_s.name = s_dict["name"]
                    new_s.color = s_dict["color"]
                    new_s.pinned = s_dict["pinned"]
                    new_s.set_type = s_dict["set_type"]
                    new_s.row = s_dict["row"]
                    new_s.priority = s_dict["priority"]
                    new_s.uid = s_dict["uid"]
                    for e_dict in s_dict["elements"]:
                        ne = new_s.elements.add()
                        ne.bone_name = e_dict["bone_name"]
                        if e_dict["object_ref"]:
                            obj = bpy.data.objects.get(e_dict["object_ref"])
                            ne.object_ref = obj
            except Exception:
                self.report({"WARNING"}, "Invalid data in clipboard.")
        return {"FINISHED"}


class AMP_OT_AnimSetPresetActivate(Operator):
    bl_idname = "anim.amp_anim_set_preset_activate"
    bl_label = "Activate Preset"

    index: IntProperty()

    def execute(self, context):
        scene_props = context.scene.amp_anim_set
        if 0 <= self.index < len(scene_props.presets):
            scene_props.active_preset_index = self.index
            scene_props.active_set_index = 0
        return {"FINISHED"}


def can_add(context, anim_set):
    if anim_set.set_type == "BONE":
        if context.mode not in {"POSE", "OBJECT"}:
            return False
    elif anim_set.set_type in {"LIGHT", "CAMERA", "OBJECT"}:
        if context.mode != "OBJECT":
            return False
    selected_types = detect_element_types_in_selection(context)
    if anim_set.set_type == "BONE":
        if any(t != "BONE" for t in selected_types):
            return False
        if context.mode not in {"POSE", "OBJECT"}:
            return False
    else:
        if context.mode != "OBJECT":
            return False
        if "BONE" in selected_types:
            return False
    if not context.selected_objects and context.mode != "POSE":
        return False
    all_in_set = True
    if context.mode == "POSE":
        arm = context.active_object
        if arm and arm.type == "ARMATURE":
            for b in context.selected_pose_bones:
                if not any(e.bone_name == b.name for e in anim_set.elements):
                    all_in_set = False
                    break
    else:
        for o in context.selected_objects:
            if not any(e.object_ref == o for e in anim_set.elements):
                all_in_set = False
                break
    return not all_in_set


def can_remove(context, anim_set):
    if anim_set.set_type == "BONE":
        arm = context.active_object
        if arm and arm.type == "ARMATURE":
            for b in context.selected_pose_bones:
                if any(e.bone_name == b.name and e.object_ref == arm for e in anim_set.elements):
                    return True
    else:
        for o in context.selected_objects:
            if any(e.object_ref == o for e in anim_set.elements):
                return True
    return False


class AMP_UL_AnimSets(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        sel_op = row.operator("anim.amp_anim_set_select", text="", icon=item.get_set_icon())
        sel_op.set_index = index
        sel_op.selection_mode = "REPLACE"
        row.separator(factor=0.5)
        row.prop(item, "name", text="", emboss=False)
        row.separator(factor=0.5)
        clr = row.row(align=True)
        clr.active = False
        clr.prop(item, "color", text="", icon="BLANK1")
        row2 = row.row(align=True)
        sub21 = row2.row()
        sub21.enabled = can_add(context, item)
        add_op = sub21.operator("anim.amp_anim_set_add_members", text="", icon="ADD")
        add_op.set_index = index
        sub22 = row2.row()
        sub22.enabled = can_remove(context, item)
        rem_op = sub22.operator("anim.amp_anim_set_remove_members", text="", icon="REMOVE")
        rem_op.set_index = index
        row3 = row.row(align=True)
        row3.prop(item, "pinned", text="", icon="PINNED" if item.pinned else "UNPINNED", emboss=False)


class AMP_UL_AnimSetPresets(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        icon_str = f"AMP_COLORS_0{index+1}" if index < 9 else "NONE"
        op = row.operator(
            "anim.amp_anim_set_preset_activate",
            text="",
            **get_icon(icon_str),
            emboss=False,
        )
        op.index = index
        row.prop(item, "name", text="", emboss=False)
        row.prop(item, "pinned", text="", icon="PINNED" if item.pinned else "UNPINNED", emboss=False)


def draw_toggles_row(self, context):
    layout = self.layout
    row = layout.row(align=True)
    box = row.box()
    box.scale_y = 0.65
    box.label(text="Selection Sets")
    if context.scene.amp_anim_set.display_settings:
        row.separator(factor=0.25)
        row.prop(context.scene.amp_anim_set, "display_colors", text="", **get_icon("COLOR"))
        row.separator(factor=0.25)
        row.prop(context.scene.amp_anim_set, "display_icons", text="", **get_icon("OBJECT_DATA"))
        row.separator(factor=0.25)
        row.prop(context.scene.amp_anim_set, "simple_order", text="", **get_icon("PRESET"))
        row.separator(factor=0.25)
        row.prop(context.scene.amp_anim_set, "display_presets", text="", **get_icon("OPTIONS"))
        row.separator(factor=0.25)
    row.prop(context.scene.amp_anim_set, "display_settings", text="", icon="SETTINGS")


def draw_preset_list(self, context):
    layout = self.layout
    scene_props = context.scene.amp_anim_set
    box = layout.box()
    box.label(text="Presets")
    row = box.row()
    row.template_list("AMP_UL_AnimSetPresets", "", scene_props, "presets", scene_props, "active_preset_index")
    col = row.column(align=True)
    col.operator("anim.amp_anim_set_preset_add", icon="ADD", text="")
    col.operator("anim.amp_anim_set_preset_remove", icon="REMOVE", text="")
    col.separator()
    up_op = col.operator("anim.amp_anim_set_preset_move", icon="TRIA_UP", text="")
    up_op.direction = "UP"
    down_op = col.operator("anim.amp_anim_set_preset_move", icon="TRIA_DOWN", text="")
    down_op.direction = "DOWN"
    col.separator()
    col.operator("anim.amp_anim_set_preset_copy", icon="COPYDOWN", text="")
    col.operator("anim.amp_anim_set_preset_paste", icon="PASTEDOWN", text="")


def draw_config_panel(self, context):
    layout = self.layout
    scene_props = context.scene.amp_anim_set
    if scene_props.display_settings:
        row = layout.row()
        # Use the active preset's sets for the UIList.
        if scene_props.active_preset_index >= 0 and scene_props.active_preset_index < len(scene_props.presets):
            preset = scene_props.presets[scene_props.active_preset_index]
            row.template_list("AMP_UL_AnimSets", "", preset, "sets", scene_props, "active_set_index", rows=4)
        else:
            row.label(text="No preset active.")
        col = row.column(align=True)
        col.operator("anim.amp_anim_set_add", icon="ADD", text="")
        col.operator("anim.amp_anim_set_remove", icon="REMOVE", text="")
        col.separator()
        move_up = col.operator("anim.amp_anim_set_move", icon="TRIA_UP", text="")
        move_up.direction = "UP"
        move_down = col.operator("anim.amp_anim_set_move", icon="TRIA_DOWN", text="")
        move_down.direction = "DOWN"
        if scene_props.display_presets:
            draw_preset_list(self, context)


def draw_main_panel(self, context):
    layout = self.layout
    col = layout.column(align=True)
    scene_props = context.scene.amp_anim_set

    if scene_props.display_presets:
        presets_row = col.row(align=True)
        box = presets_row.box()
        box.scale_y = 0.65
        if scene_props.active_preset_index >= 0 and scene_props.active_preset_index < len(scene_props.presets):
            preset_name = scene_props.presets[scene_props.active_preset_index].name
        else:
            preset_name = "Presets"
        box.label(text=preset_name)
        col.separator(factor=0.2)
        pinned_presets = [(idx, p) for idx, p in enumerate(scene_props.presets) if p.pinned][:9]
        presets_row.separator(factor=0.2)
        for idx, preset in pinned_presets:
            btn = presets_row.operator(
                "anim.amp_anim_set_preset_activate",
                text="",
                **get_icon(f"AMP_COLORS_0{idx+1}"),
                depress=preset == scene_props.presets[scene_props.active_preset_index],
            )
            btn.index = idx
            presets_row.separator(factor=0.2)
        col.separator()

    if scene_props.active_preset_index < 0 or scene_props.active_preset_index >= len(scene_props.presets):
        col.label(text="No sets created yet.")
        return

    preset = scene_props.presets[scene_props.active_preset_index]
    if scene_props.simple_order:
        for i, s in enumerate(preset.sets):
            if s.pinned:
                draw_set_button(col, context, i, s, True)
            col.separator(factor=0.2)
    else:
        pinned_sets = [s for s in preset.sets if s.pinned]
        sets_by_row = {}
        for s in pinned_sets:
            sets_by_row.setdefault(s.row, []).append((s, s.priority))
        for row_number in sorted(sets_by_row.keys()):
            row_layout = col.row(align=True)
            for the_set, prio in sorted(sets_by_row[row_number], key=lambda x: x[1]):
                i = preset.sets.find(the_set.name)
                draw_set_button(row_layout, context, i, the_set, False)
                if prio != max(p[1] for p in sets_by_row[row_number]):
                    row_layout.separator(factor=0.2)
            col.separator(factor=0.2)


def draw_set_button(layout, context, i, s, simple_order=True):
    row = layout.row(align=True)
    if context.scene.amp_anim_set.active_move_set_index == i:
        row.alert = True
    else:
        row.alert = False
    if context.scene.amp_anim_set.display_settings and not simple_order:
        move_op = row.operator("anim.amp_anim_set_move_element", text="", icon="EMPTY_ARROWS", emboss=False)
        move_op.set_index = i
        row.separator(factor=0.25)
    if context.scene.amp_anim_set.display_colors:
        sub = row.row(align=True)
        sub.scale_x = 0.7
        sub.enabled = False
        sub.prop(s, "color", text="", icon="BLANK1")
    icon = s.get_set_icon() if context.scene.amp_anim_set.display_icons else "BLANK1"
    select_op = row.operator("anim.amp_anim_set_select", text=s.name, icon=icon)
    select_op.set_index = i


class AMP_PT_AnimSetsPanelBase(Panel):
    bl_label = "Selection Sets"
    bl_category = "AniMatePro"
    bl_region_type = "UI"

    def draw_header(self, context):
        layout = self.layout
        layout.label(text="", **get_icon("AMP_select_sets"))

    def draw(self, context):
        draw_toggles_row(self, context)
        draw_config_panel(self, context)
        draw_main_panel(self, context)


class AMP_PT_AnimSetsPanelView(AMP_PT_AnimSetsPanelBase):
    bl_idname = "AMP_PT_AnimSetsPanelView"
    bl_space_type = "VIEW_3D"
    bl_parent_id = "AMP_PT_AniMateProView"
    bl_options = {"DEFAULT_CLOSED"}


class AMP_PT_AnimSetsPanelDope(AMP_PT_AnimSetsPanelBase):
    bl_idname = "AMP_PT_AnimSetsPanelDope"
    bl_space_type = "DOPESHEET_EDITOR"
    bl_parent_id = "AMP_PT_AniMateProDope"
    bl_options = {"DEFAULT_CLOSED"}


class AMP_PT_AnimSetsPanelGraph(AMP_PT_AnimSetsPanelBase):
    bl_idname = "AMP_PT_AnimSetsPanelGraph"
    bl_space_type = "GRAPH_EDITOR"
    bl_parent_id = "AMP_PT_AniMateProGraph"
    bl_options = {"DEFAULT_CLOSED"}


class AMP_PT_AnimSetsPanelPop(Panel):
    bl_label = "Selection Sets"
    bl_idname = "AMP_PT_AnimSetsPanelPop"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_ui_units_x = 20

    def draw(self, context):
        draw_main_panel(self, context)


class AMP_OT_AnimSetMoveElement(Operator):
    bl_idname = "anim.amp_anim_set_move_element"
    bl_label = "Move Set with Arrow Keys"

    set_index: IntProperty()
    set_uid: StringProperty()

    def invoke(self, context, event):
        scene_props = context.scene.amp_anim_set
        if scene_props.active_preset_index < 0 or scene_props.active_preset_index >= len(scene_props.presets):
            return {"CANCELLED"}
        preset = scene_props.presets[scene_props.active_preset_index]
        target = preset.sets[self.set_index]
        self.set_uid = target.uid
        scene_props.active_move_set_index = self.set_index
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        scene_props = context.scene.amp_anim_set
        if scene_props.active_preset_index < 0 or scene_props.active_preset_index >= len(scene_props.presets):
            scene_props.active_move_set_index = -1
            refresh_ui(context)
            return {"CANCELLED"}
        preset = scene_props.presets[scene_props.active_preset_index]
        sets = preset.sets
        this_set = next((s for s in sets if s.uid == self.set_uid), None)
        if not this_set:
            scene_props.active_move_set_index = -1
            refresh_ui(context)
            return {"CANCELLED"}

        if event.type in {"ESC", "RIGHTMOUSE", "LEFTMOUSE", "RET"}:
            scene_props.active_move_set_index = -1
            refresh_ui(context)
            return {"CANCELLED"}

        if event.value == "PRESS":
            if event.type in {"UP_ARROW", "W"}:
                handle_vertical_movement(this_set, "up", sets)
            elif event.type in {"DOWN_ARROW", "S"}:
                handle_vertical_movement(this_set, "down", sets)
            elif event.type in {"LEFT_ARROW", "A"}:
                handle_horizontal_movement(this_set, "left", sets)
            elif event.type in {"RIGHT_ARROW", "D"}:
                handle_horizontal_movement(this_set, "right", sets)
            context.area.tag_redraw()

        refresh_ui(context)
        return {"RUNNING_MODAL"}


def handle_vertical_movement(anim_set, direction, all_sets):
    row = anim_set.row
    same_row = [s for s in all_sets if s.row == row]
    is_only_in_row = len(same_row) == 1
    if direction == "up" and row > 0:
        if not is_only_in_row:
            for s in all_sets:
                if s.row < row:
                    s.row -= 2
            anim_set.row -= 1
            anim_set.priority = -1
        else:
            anim_set.row -= 1
            anim_set.priority = -1
            for s in all_sets:
                if s.row < anim_set.row:
                    s.row -= 1
    elif direction == "down":
        max_row = max(s.row for s in all_sets) if all_sets else 0
        if not (row == max_row and is_only_in_row):
            if not is_only_in_row:
                for s in all_sets:
                    if s.row > row:
                        s.row += 2
                anim_set.row += 1
                anim_set.priority = -1
            else:
                anim_set.row += 1
                anim_set.priority = -1
                for s in all_sets:
                    if s.row > anim_set.row:
                        s.row += 1
    reorganize_sets(all_sets)


def handle_horizontal_movement(anim_set, direction, all_sets):
    same_row = [s for s in all_sets if s.row == anim_set.row]
    if not same_row:
        return
    max_priority = max(s.priority for s in same_row)
    if direction == "left" and anim_set.priority > 1:
        for s in same_row:
            s.priority *= 3
        anim_set.priority -= 4
    elif direction == "right" and anim_set.priority < max_priority:
        for s in same_row:
            s.priority *= 3
        anim_set.priority += 4
    reorganize_sets(all_sets)


def reorganize_sets(all_sets):
    if not all_sets:
        return
    unique_rows = sorted({s.row for s in all_sets})
    row_map = {old: new for new, old in enumerate(unique_rows, start=1)}
    for s in all_sets:
        s.row = row_map[s.row]
    for row_val in set(s.row for s in all_sets):
        row_items = [st for st in all_sets if st.row == row_val]
        row_items.sort(key=lambda x: x.priority)
        for i, st in enumerate(row_items, start=1):
            st.priority = i


gui_state = {
    "show_pinned_gui": False,
    "dragging_background": False,
    "dragging_frame": False,
    "drag_offset": (0, 0),
    "bg_pos": (50, 300),
    "bg_width": 200,
    "bg_height": 0,
    "pinned_item_height": 30,
    "pinned_item_width": 150,
    "items_offset": 5,
    "frame_pos": (50, 300),
    "frame_size": (200, 400),
    "is_frame_hovered": False,
    "hovered_set_index": None,
}


def region_to_gui(context, mouse_x, mouse_y):
    return mouse_x - gui_state["frame_pos"][0], mouse_y - gui_state["frame_pos"][1]


def pinned_sets_draw_callback():
    if not gui_state["show_pinned_gui"]:
        return
    scene = bpy.context.scene
    scene_props = scene.amp_anim_set
    if scene_props.active_preset_index < 0 or scene_props.active_preset_index >= len(scene_props.presets):
        return
    preset = scene_props.presets[scene_props.active_preset_index]
    pinned = [s for s in preset.sets if s.pinned]
    if not pinned:
        return
    x, y = gui_state["frame_pos"]
    fw, fh = gui_state["frame_size"]
    item_w = gui_state["pinned_item_width"]
    item_h = gui_state["pinned_item_height"]
    margin = gui_state["items_offset"]
    gap = 5
    frame_c = (0.2, 0.2, 0.2, 0.9 if gui_state["is_frame_hovered"] else 0.7)
    frame_coords = [(x, y), (x + fw, y), (x + fw, y - fh), (x, y - fh)]
    shader.bind()
    shader.uniform_float("color", frame_c)
    batch = batch_for_shader(shader, "TRI_FAN", {"pos": frame_coords})
    gpu.state.blend_set("ALPHA")
    batch.draw(shader)
    gpu.state.blend_set("NONE")
    cur_y = y - margin
    for i, s in enumerate(pinned):
        top = cur_y
        bot = top - item_h
        if gui_state["hovered_set_index"] == i:
            display_c = s.color
        else:
            display_c = tuple(max(c - 0.2, 0) for c in s.color)
        coords = [(x + margin, top), (x + margin + item_w, top), (x + margin + item_w, bot), (x + margin, bot)]
        shader.bind()
        shader.uniform_float("color", display_c)
        batch2 = batch_for_shader(shader, "TRI_FAN", {"pos": coords})
        gpu.state.blend_set("ALPHA")
        batch2.draw(shader)
        gpu.state.blend_set("NONE")
        blf.position(0, x + margin + 5, bot + 5, 0)
        blf.draw(0, s.name)
        cur_y -= item_h + gap


def pinned_sets_event_handler(context, event):
    if not gui_state["show_pinned_gui"]:
        return
    scene = bpy.context.scene
    scene_props = scene.amp_anim_set
    if scene_props.active_preset_index < 0 or scene_props.active_preset_index >= len(scene_props.presets):
        return
    preset = scene_props.presets[scene_props.active_preset_index]
    pinned = [s for s in preset.sets if s.pinned]
    if not pinned:
        return
    mx, my = event.mouse_x, event.mouse_y
    gm_x, gm_y = region_to_gui(context, mx, my)
    fx, fy = gui_state["frame_pos"]
    fw, fh = gui_state["frame_size"]
    margin = gui_state["items_offset"]
    item_w = gui_state["pinned_item_width"]
    item_h = gui_state["pinned_item_height"]
    gap = 5
    left, top = fx, fy
    right, bot = fx + fw, fy - fh
    if event.type == "LEFTMOUSE":
        if event.value == "PRESS":
            if left <= gm_x <= right and bot <= gm_y <= top:
                cur_y = fy - margin
                hovered = None
                for i, s in enumerate(pinned):
                    box_top = cur_y
                    box_bot = box_top - item_h
                    box_left = fx + margin
                    box_right = box_left + item_w
                    if (box_left <= gm_x <= box_right) and (box_bot <= gm_y <= box_top):
                        hovered = i
                        idx = list(preset.sets).index(s)
                        bpy.ops.anim.amp_anim_set_select(set_index=idx, selection_mode="REPLACE")
                        break
                    cur_y -= item_h + gap
                if hovered is None:
                    gui_state["dragging_frame"] = True
                    gui_state["drag_offset"] = (gm_x - fx, gm_y - fy)
        elif event.value == "RELEASE":
            gui_state["dragging_frame"] = False
    elif event.type == "MOUSEMOVE":
        if gui_state["dragging_frame"]:
            gui_state["frame_pos"] = (
                gm_x - gui_state["drag_offset"][0],
                gm_y - gui_state["drag_offset"][1],
            )
        else:
            hovered_set_index = None
            is_hovered = False
            if left <= gm_x <= right and bot <= gm_y <= top:
                cur_y = fy - margin
                for i, s in enumerate(pinned):
                    box_top = cur_y
                    box_bot = box_top - item_h
                    box_left = fx + margin
                    box_right = box_left + item_w
                    if (box_left <= gm_x <= box_right) and (box_bot <= gm_y <= box_top):
                        hovered_set_index = i
                        is_hovered = True
                        break
                    cur_y -= item_h + gap
                if not is_hovered:
                    border_thresh = 10
                    if (
                        (left - border_thresh <= gm_x <= left + border_thresh)
                        or (right - border_thresh <= gm_x <= right + border_thresh)
                        or (top - border_thresh <= gm_y <= top + border_thresh)
                        or (bot - border_thresh <= gm_y <= bot + border_thresh)
                    ):
                        is_hovered = True
                gui_state["is_frame_hovered"] = is_hovered
                gui_state["hovered_set_index"] = hovered_set_index
                bpy.context.window.cursor_set("HAND" if is_hovered else "DEFAULT")
            else:
                gui_state["is_frame_hovered"] = False
                gui_state["hovered_set_index"] = None
                bpy.context.window.cursor_set("DEFAULT")


draw_callbacks = []
event_handlers = []
try:
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
except SystemError:
    shader = None


class AMP_OT_ModalEventHandler(Operator):
    bl_idname = "anim.amp_modal_event_handler"
    bl_label = "Modal Event Handler"

    def execute(self, context):
        return {"FINISHED"}

    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type in {"ESC"}:
            return {"CANCELLED"}
        for fn in event_handlers:
            fn(context, event)
        return {"PASS_THROUGH"}


def view3d_draw_handler(dummy, context):
    for fn in draw_callbacks:
        fn()


def view3d_event_handler(context, event):
    for fn in event_handlers:
        fn(context, event)


classes = (
    AMP_PG_AnimSetElement,
    AMP_PG_AnimSet,
    AMP_PG_AnimSetPreset,
    AMP_PG_SceneAnimSets,
    AMP_OT_AnimSetSelect,
    AMP_OT_AnimSetAdd,
    AMP_OT_AnimSetRemove,
    AMP_OT_AnimSetMove,
    AMP_OT_AnimSetAddMembers,
    AMP_OT_AnimSetRemoveMembers,
    AMP_UL_AnimSets,
    AMP_OT_AnimSetMoveElement,
    AMP_OT_ModalEventHandler,
    AMP_OT_AnimSetPresetAdd,
    AMP_OT_AnimSetPresetRemove,
    AMP_OT_AnimSetPresetMove,
    AMP_OT_AnimSetPresetCopy,
    AMP_OT_AnimSetPresetPaste,
    AMP_OT_AnimSetPresetActivate,
    AMP_UL_AnimSetPresets,
    AMP_PT_AnimSetsPanelView,
    AMP_PT_AnimSetsPanelDope,
    AMP_PT_AnimSetsPanelGraph,
    AMP_PT_AnimSetsPanelPop,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.amp_anim_set = PointerProperty(type=AMP_PG_SceneAnimSets)
    bpy.types.SpaceView3D.draw_handler_add(view3d_draw_handler, (None, None), "WINDOW", "POST_PIXEL")
    bpy.ops.anim.amp_modal_event_handler("INVOKE_DEFAULT")
    bpy.context.scene.amp_anim_set.display_gui = False


def unregister():
    if gui_state["show_pinned_gui"]:
        gui_state["show_pinned_gui"] = False
    del bpy.types.Scene.amp_anim_set
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    bpy.types.SpaceView3D.draw_handler_remove(view3d_draw_handler, "WINDOW")
    bpy.ops.anim.amp_modal_event_handler("CANCELLED")


if __name__ == "__main__":
    register()
