import bpy
import addon_utils
import sys
sys.path.append(r"D:\Code\AMP_AniMatePro\AMP_AniMatePro_v0.25.10318")
import traceback

def create_test_scene():
    bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
    cube = bpy.context.active_object
    cube.name = "TestCube"
    
    cube.keyframe_insert(data_path="location", frame=1)
    cube.location = (1, 1, 1)
    cube.keyframe_insert(data_path="location", frame=10)
    cube.location = (2, 2, 2)
    cube.keyframe_insert(data_path="location", frame=20)
    
    # Ensure action exists
    assert cube.animation_data and cube.animation_data.action
    action = cube.animation_data.action
    
    import AMP_AniMatePro.utils.blender_compat as compat
    # Select fcurves and keyframes
    for fcu in compat.iter_action_fcurves(action):
        fcu.select = True
        for kp in fcu.keyframe_points:
            kp.select_control_point = True

    return cube

def test_operators():
    cube = create_test_scene()
    
    # Build context override for graph editor
    area = None
    region = None
    for a in bpy.context.screen.areas:
        if a.type == 'GRAPH_EDITOR':
            area = a
            for r in a.regions:
                if r.type == 'WINDOW':
                    region = r
                    break
            break
            
    if not area:
        # Create a graph editor area
        area = bpy.context.screen.areas[0]
        area.type = 'GRAPH_EDITOR'
        for r in area.regions:
            if r.type == 'WINDOW':
                region = r
                break
                
    with bpy.context.temp_override(area=area, region=region):
        ops_to_test = [
            ("anim.amp_select_or_transform_keyframes", bpy.ops.anim.amp_select_or_transform_keyframes),
            ("anim.timeline_anim_nudger", bpy.ops.anim.timeline_anim_nudger),
            ("anim.anim_pusher", bpy.ops.anim.anim_pusher),
            ("anim.amp_anim_retimer", bpy.ops.anim.amp_anim_retimer),
            ("anim.amp_anim_shifter", bpy.ops.anim.amp_anim_shifter),
            ("anim.amp_anim_slicer", bpy.ops.anim.amp_anim_slicer),
            ("anim.amp_anim_sculpt", bpy.ops.anim.amp_anim_sculpt),
            ("anim.amp_anim_lattice", bpy.ops.anim.amp_anim_lattice),
            ("anim.amp_anim_timewarper", bpy.ops.anim.amp_anim_timewarper),
            ("anim.amp_anim_loop", bpy.ops.anim.amp_anim_loop),
            ("anim.amp_anim_stepper", bpy.ops.anim.amp_anim_stepper),
            ("anim.amp_match_selected_keyframe_values", bpy.ops.anim.amp_match_selected_keyframe_values),
            ("anim.amp_propagate_pose_to_range", bpy.ops.anim.amp_propagate_pose_to_range)
        ]
        
        passed = 0
        failed = 0
        
        print("\n--- Testing Operator Polls ---")
        for op_name, op_func in ops_to_test:
            try:
                # We just verify poll() doesn't crash on compatibility layer logic
                res = op_func.poll()
                print(f"[{op_name}] Poll OK: {res}")
                passed += 1
            except Exception as e:
                print(f"[{op_name}] Poll FAILED: {e}")
                traceback.print_exc()
                failed += 1
                
        # Execute test for nudger
        print("\n--- Testing Operator Execution ---")
        try:
            res = bpy.ops.anim.timeline_anim_nudger(direction="RIGHT")
            print(f"[anim.timeline_anim_nudger] Executed: {res}")
        except Exception as e:
            print(f"[anim.timeline_anim_nudger] FAILED: {e}")
            traceback.print_exc()
            failed += 1
            
        return failed == 0

def main():
    print("\\n--- STARTING STAGE 9 FUNCTIONAL TESTS ---")
    
    addon_name = "AMP_AniMatePro"
    try:
        addon_utils.enable(addon_name, default_set=True)
        print(f"Successfully enabled {addon_name}")
    except Exception as e:
        print(f"Failed to enable addon: {e}")
        sys.exit(1)
        
    try:
        success = test_operators()
        if not success:
            print("\\n--- SOME TESTS FAILED ---")
            sys.exit(1)
    except Exception as e:
        print(f"Test suite crashed: {e}")
        traceback.print_exc()
        sys.exit(1)
        
    try:
        addon_utils.disable(addon_name)
        print(f"Successfully disabled {addon_name}")
    except Exception as e:
        print(f"Failed to disable addon: {e}")
        sys.exit(1)
        
    print("\\n--- STAGE 9 FUNCTIONAL TESTS PASSED ---")

if __name__ == "__main__":
    main()
