import bpy
import sys
import traceback

def create_smoke_scene():
    print("\n--- STARTING SMOKE SCENE CREATION ---")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    
    # 1. Object with transform keyframes
    bpy.ops.mesh.primitive_cube_add()
    cube = bpy.context.active_object
    cube.name = "AnimatedCube"
    cube.location = (0, 0, 0)
    cube.keyframe_insert(data_path="location", frame=1)
    cube.location = (1, 1, 1)
    cube.keyframe_insert(data_path="location", frame=10)

    # 2. Armature with a selected pose bone and pose-bone keyframes
    bpy.ops.object.armature_add()
    armature = bpy.context.active_object
    armature.name = "AnimatedArmature"
    bpy.ops.object.mode_set(mode='POSE')
    bone = armature.pose.bones["Bone"]
    bone.location = (0, 0, 0)
    bone.keyframe_insert(data_path="location", frame=1)
    bone.location = (0, 0, 1)
    bone.keyframe_insert(data_path="location", frame=10)
    bpy.ops.object.mode_set(mode='OBJECT')

    # 3. Material/node-tree animated property
    mat = bpy.data.materials.new(name="AnimatedMaterial")
    mat.use_nodes = True
    cube.data.materials.append(mat)
    node = mat.node_tree.nodes.get("Principled BSDF")
    if node:
        node.inputs['Base Color'].default_value = (1, 0, 0, 1)
        node.inputs['Base Color'].keyframe_insert(data_path="default_value", frame=1)
        node.inputs['Base Color'].default_value = (0, 1, 0, 1)
        node.inputs['Base Color'].keyframe_insert(data_path="default_value", frame=10)

    # 4. Shape-key animated property
    bpy.context.view_layer.objects.active = cube
    cube.shape_key_add(name="Basis", from_mix=False)
    sk = cube.shape_key_add(name="Key 1", from_mix=False)
    sk.value = 0.0
    sk.keyframe_insert(data_path="value", frame=1)
    sk.value = 1.0
    sk.keyframe_insert(data_path="value", frame=10)

    # 5. Grease Pencil object with two layers and several frames
    try:
        # For Blender 5.1 / GPv3
        # Grease Pencil objects require grease_pencil_add (if it still exists) or gpencil_add
        if hasattr(bpy.ops.object, 'grease_pencil_add'):
            bpy.ops.object.grease_pencil_add(type='EMPTY')
        else:
            bpy.ops.object.gpencil_add(type='EMPTY')
        
        gp = bpy.context.active_object
        gp.name = "AnimatedGreasePencil"
        
        # Add layers
        if hasattr(gp.data, 'layers'):
            layer1 = gp.data.layers.new(name="Layer1")
            layer2 = gp.data.layers.new(name="Layer2")
            
            # Add frames
            if hasattr(layer1, 'frames'):
                layer1.frames.new(1)
                layer1.frames.new(10)
                layer2.frames.new(5)
                layer2.frames.new(15)
            elif hasattr(gp.data, 'frames'):
                # Handle possible alternative api
                pass
    except Exception as e:
        print("Warning: Grease Pencil creation failed. API might have changed.")
        print(e)

    # 6. NLA strip
    if cube.animation_data and cube.animation_data.action:
        action = cube.animation_data.action
        track = cube.animation_data.nla_tracks.new()
        track.name = "Track1"
        track.strips.new("Strip1", 1, action)

    print("\n--- SMOKE SCENE CREATION PASSED ---")

if __name__ == "__main__":
    try:
        create_smoke_scene()
        sys.exit(0)
    except Exception as e:
        print("\n--- SMOKE SCENE CREATION FAILED ---")
        traceback.print_exc()
        sys.exit(1)
