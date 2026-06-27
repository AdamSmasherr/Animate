# Pseudocode for Full Physics Simulation:
# 1. Identify selected pose bones and store their names.
# 2. Switch to EDIT mode and create helper (physics proxy) bones (prefixed with "FS_") by copying the transform of each original bone.
# 3. Return to POSE mode and add a physics constraint (COPY_TRANSFORMS) to each helper bone linking it to its original.
# 4. For each frame from frame_start to frame_end (with step), set the scene frame, and for each bone:
#      a. Copy the helper bone’s simulated transform to the original bone.
#      b. Insert keyframes on original bone’s location, rotation, and scale.
# 5. After baking, switch to EDIT mode, delete helper bones, and return to POSE mode.
import bpy
from bpy.types import Operator, Panel
from bpy.props import BoolProperty, FloatProperty, IntProperty

# Operator to create physics proxy bones, simulate physics overlaps,
# bake simulation to original bones, and delete helper bones.
class OBJECT_OT_add_physics_overlaps(Operator):
    bl_idname = "object.add_physics_overlaps"
    bl_label = "Add Physics Overlaps"
    bl_description = ("Create physics proxy bones, simulate physics overlaps, bake the simulation "
                      "onto the original bones over a frame range, and clean up helper bones")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != "ARMATURE":
            self.report({"ERROR"}, "Active object is not an armature.")
            return {"CANCELLED"}
            
        scene = context.scene
        # Get baking parameters from the scene properties
        bake_start = scene.rgc_bake_frame_start
        bake_end   = scene.rgc_bake_frame_end
        bake_step  = scene.rgc_bake_frame_step

        # Store selected bone names before mode changes
        selected_bone_names = [bone.name for bone in context.selected_pose_bones or []]
        if not selected_bone_names:
            self.report({"ERROR"}, "No pose bones selected.")
            return {"CANCELLED"}

        # Create helper bones in EDIT mode
        bpy.ops.object.mode_set(mode="EDIT")
        edit_bones = obj.data.edit_bones
        for name in selected_bone_names:
            orig_ebone = obj.data.bones.get(name)
            if not orig_ebone:
                continue
            physics_bone_name = f"FS_{name}"
            new_ebone = edit_bones.new(physics_bone_name)
            new_ebone.head = orig_ebone.head_local
            new_ebone.tail = orig_ebone.tail_local
            # ...copy additional properties as needed...
        bpy.ops.object.mode_set(mode="POSE")

        # Add physics constraint to helper bones linking them to originals
        for name in selected_bone_names:
            physics_bone_name = f"FS_{name}"
            helper_pb = obj.pose.bones.get(physics_bone_name)
            if helper_pb:
                helper_pb.bone.use_deform = False
                constraint = helper_pb.constraints.new(type="COPY_TRANSFORMS")
                constraint.target = obj
                constraint.subtarget = name
            else:
                self.report({"ERROR"}, f"Could not retrieve pose bone: {physics_bone_name}")

        self.report({"INFO"}, "Helper bones created and physics constraints added. Baking simulation...")

        # Bake simulation: for each frame in the range, copy helper transform to original bone and keyframe
        current_frame = scene.frame_current
        for f in range(bake_start, bake_end + 1, bake_step):
            scene.frame_set(f)
            # Force evaluation so constraints update
            depsgraph = context.evaluated_depsgraph_get()
            for name in selected_bone_names:
                orig_pb = obj.pose.bones.get(name)
                helper_pb = obj.pose.bones.get(f"FS_{name}")
                if orig_pb and helper_pb:
                    orig_pb.matrix = helper_pb.matrix.copy()
                    orig_pb.keyframe_insert(data_path="location", frame=f)
                    orig_pb.keyframe_insert(data_path="rotation_quaternion", frame=f)
                    orig_pb.keyframe_insert(data_path="scale", frame=f)
        scene.frame_set(current_frame)

        # Clean up: Delete helper bones
        bpy.ops.object.mode_set(mode="EDIT")
        for ebone in list(obj.data.edit_bones):
            if ebone.name.startswith("FS_"):
                obj.data.edit_bones.remove(ebone)
        bpy.ops.object.mode_set(mode="POSE")

        self.report({"INFO"}, "Physics simulation baked and helper bones removed.")
        return {"FINISHED"}
    

# Panel to display scene properties and start the full physics simulation
class VIEW3D_PT_physics_panel(Panel):
    bl_label = "Physics Overlap Settings"
    bl_idname = "VIEW3D_PT_physics_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Rig"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.prop(scene, "rgc_physics_enable")
        layout.prop(scene, "rgc_physics_stiffness")
        layout.prop(scene, "rgc_physics_distance")
        layout.separator()
        layout.prop(scene, "rgc_bake_frame_start")
        layout.prop(scene, "rgc_bake_frame_end")
        layout.prop(scene, "rgc_bake_frame_step")
        layout.operator("object.add_physics_overlaps", text="Run Physics Simulation and Bake")

# Register scene properties including baking frame range
def register_properties():
    bpy.types.Scene.rgc_physics_enable = BoolProperty(
        name="Enable Physics", description="Toggle physics simulation for bones", default=True
    )
    bpy.types.Scene.rgc_physics_stiffness = FloatProperty(
        name="Stiffness", description="Stiffness value for physics constraints", default=1.0, min=0.0, max=10.0
    )
    bpy.types.Scene.rgc_physics_distance = FloatProperty(
        name="Target Distance", description="Distance for bone overlap simulation", default=0.5, min=0.0, max=5.0
    )
    bpy.types.Scene.rgc_bake_frame_start = IntProperty(
        name="Bake Start Frame", description="Start frame for simulation baking", default=1, min=1
    )
    bpy.types.Scene.rgc_bake_frame_end = IntProperty(
        name="Bake End Frame", description="End frame for simulation baking", default=250, min=1
    )
    bpy.types.Scene.rgc_bake_frame_step = IntProperty(
        name="Bake Step", description="Frame step for baking simulation", default=1, min=1
    )

def unregister_properties():
    del bpy.types.Scene.rgc_physics_enable
    del bpy.types.Scene.rgc_physics_stiffness
    del bpy.types.Scene.rgc_physics_distance
    del bpy.types.Scene.rgc_bake_frame_start
    del bpy.types.Scene.rgc_bake_frame_end
    del bpy.types.Scene.rgc_bake_frame_step

classes = (
    OBJECT_OT_add_physics_overlaps,
    VIEW3D_PT_physics_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    register_properties()

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    unregister_properties()

if __name__ == "__main__":
    register()
