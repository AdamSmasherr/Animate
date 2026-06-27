import bpy
import addon_utils
import sys
import time
import traceback

# Add addon directory to path
sys.path.append(r"D:\Code\AMP_AniMatePro\AMP_AniMatePro_v0.25.10318")

def run_stress_tests():
    addon_name = "AMP_AniMatePro"
    
    # 1. Enable addon
    try:
        addon_utils.enable(addon_name, default_set=True)
        print("Addon enabled successfully.")
    except Exception as e:
        print(f"Failed to enable addon: {e}")
        sys.exit(1)

    try:
        props = bpy.context.scene.mp_props
        props.elements.clear()
        
        # Clean up scene
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        
        from AMP_AniMatePro.anim_mopaths.anim_flex_mopaths import (
            deferred_flex_mopaths_update,
            update_visibility,
            AMP_FMP_UL_Elements,
            AMP_FMP_PT_FlexMoPathsPanel,
        )
        
        # Helper mock structures for drawing tests
        class MockLayout:
            enabled = True
            def row(self, *args, **kwargs): return self
            def box(self, *args, **kwargs): return self
            def separator(self, *args, **kwargs): pass
            def column(self, *args, **kwargs): return self
            def prop(self, *args, **kwargs): pass
            def label(self, *args, **kwargs): pass
            def template_list(self, *args, **kwargs): pass
            def operator(self, *args, **kwargs): return MockOperator()
        
        class MockOperator:
            index = 0
            
        class DummyUIList:
            layout_type = 'DEFAULT'
            
        class DummyPanel:
            layout = MockLayout()
            
        layout = MockLayout()
        uilist = DummyUIList()
        panel = DummyPanel()
        
        # ----------------------------------------------------
        # TEST 1: Rapid Object Renaming
        # ----------------------------------------------------
        print("\n--- Test 1: Rapid Object Renaming ---")
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        cube = bpy.context.active_object
        cube.name = "TestCube"
        cube.select_set(True)
        
        props.show_motion_paths = True
        bpy.ops.anim.amp_fmp_add_element()
        
        assert len(props.elements) == 1
        elem = props.elements[0]
        
        # Rapidly rename 200 times
        print("Renaming object 200 times rapidly...")
        for i in range(200):
            cube.name = f"TestCube_Rename_{i}"
            # Periodically trigger updates to simulate fast frame rates/depsgraph events
            if i % 10 == 0:
                deferred_flex_mopaths_update()
                update_visibility(bpy.context)
        
        # Final update
        deferred_flex_mopaths_update()
        update_visibility(bpy.context)
        
        print(f"Final name of cube: {cube.name}")
        print(f"Name of element: {elem.name}")
        assert elem.name == cube.name, f"Name mismatch: {elem.name} != {cube.name}"
        assert elem.empty_ref.name == f"AMP_FMP_CustomOrigin_{cube.name}", f"Empty name mismatch: {elem.empty_ref.name}"
        print("Test 1: Rapid Object Renaming PASSED.")
        
        # ----------------------------------------------------
        # TEST 2: Renaming collisions (Naming Collisions)
        # ----------------------------------------------------
        print("\n--- Test 2: Naming Collisions ---")
        # Create second object
        bpy.ops.mesh.primitive_cylinder_add(location=(2, 0, 0))
        cylinder = bpy.context.active_object
        cylinder.name = "CollisionTarget"
        cylinder.select_set(True)
        bpy.ops.anim.amp_fmp_add_element()
        
        assert len(props.elements) == 2
        elem_cyl = props.elements[1]
        
        # Attempt to rename cube to "CollisionTarget" (the existing name)
        # Blender should auto-rename cube to "CollisionTarget.001"
        print("Renaming TestCube to 'CollisionTarget' (collision)...")
        cube.name = "CollisionTarget"
        deferred_flex_mopaths_update()
        
        print(f"Resulting cube name: {cube.name}")
        print(f"Element 0 name: {props.elements[0].name}")
        print(f"Element 1 name: {props.elements[1].name}")
        print(f"Element 0 empty name: {props.elements[0].empty_ref.name}")
        print(f"Element 1 empty name: {props.elements[1].empty_ref.name}")
        print(f"Element 0 collection: {props.elements[0].collection_name}")
        print(f"Element 1 collection: {props.elements[1].collection_name}")
        
        # Verify no crash occurred and references remain intact
        assert props.elements[0].object_ref == cube
        assert props.elements[1].object_ref == cylinder
        
        c0_name = props.elements[0].collection_name
        c1_name = props.elements[1].collection_name
        assert c0_name in bpy.data.collections, f"Collection {c0_name} not found in bpy.data.collections"
        assert c1_name in bpy.data.collections, f"Collection {c1_name} not found in bpy.data.collections"
        
        # Clean up second element for subsequent tests
        bpy.ops.anim.amp_fmp_remove_index_element(index=1)
        assert len(props.elements) == 1
        print("Test 2: Naming Collisions PASSED.")
        
        # ----------------------------------------------------
        # TEST 3: Deleting objects while they are being tracked
        # ----------------------------------------------------
        print("\n--- Test 3: Deleting Tracked Objects & Components ---")
        # 3a. Delete tracking empty directly
        print("Scenario A: Deleting the tracking empty directly...")
        empty_ref = props.elements[0].empty_ref
        bpy.data.objects.remove(empty_ref, do_unlink=True)
        
        # Trigger updates and drawing
        deferred_flex_mopaths_update()
        update_visibility(bpy.context)
        AMP_FMP_UL_Elements.draw_item(uilist, bpy.context, layout, props, props.elements[0], 0, props, "active_index", 0)
        AMP_FMP_PT_FlexMoPathsPanel.draw(panel, bpy.context)
        print("Successfully handled tracking empty deletion without crash.")
        
        # Recreate elements to test other deletion scenarios
        props.elements.clear()
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        
        # Create object
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        cube = bpy.context.active_object
        cube.name = "DeleteTestCube"
        cube.select_set(True)
        bpy.ops.anim.amp_fmp_add_element()
        elem = props.elements[0]
        
        # 3b. Delete sub-collection directly
        print("Scenario B: Deleting the sub-collection directly...")
        coll_name = elem.collection_name
        sub_coll = bpy.data.collections.get(coll_name)
        assert sub_coll is not None
        bpy.data.collections.remove(sub_coll, do_unlink=True)
        
        deferred_flex_mopaths_update()
        update_visibility(bpy.context)
        AMP_FMP_UL_Elements.draw_item(uilist, bpy.context, layout, props, elem, 0, props, "active_index", 0)
        print("Successfully handled sub-collection deletion without crash.")
        
        # Re-add elements
        props.elements.clear()
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        cube = bpy.context.active_object
        cube.name = "DeleteTestCube2"
        cube.select_set(True)
        bpy.ops.anim.amp_fmp_add_element()
        elem = props.elements[0]
        
        # 3c. Delete the main object
        print("Scenario C: Deleting the main tracked object...")
        bpy.data.objects.remove(cube, do_unlink=True)
        deferred_flex_mopaths_update()
        update_visibility(bpy.context)
        AMP_FMP_UL_Elements.draw_item(uilist, bpy.context, layout, props, elem, 0, props, "active_index", 0)
        AMP_FMP_PT_FlexMoPathsPanel.draw(panel, bpy.context)
        print("Successfully handled main tracked object deletion without crash.")
        
        # Verify selecting the deleted element raises ReferenceError but doesn't crash Blender
        print("Invoking Select Element operator on a deleted object...")
        try:
            bpy.ops.anim.amp_fmp_select_element(index=0)
            print("Select Element operator executed (no crash).")
        except ReferenceError as re:
            print(f"Select Element operator raised ReferenceError as expected: {re}")
        except Exception as e:
            print(f"Select Element operator raised unexpected exception: {e}")

        print("Invoking Select Empty operator on a deleted empty...")
        try:
            bpy.ops.anim.amp_fmp_select_empty(index=0)
            print("Select Empty operator executed (no crash).")
        except ReferenceError as re:
            print(f"Select Empty operator raised ReferenceError as expected: {re}")
        except Exception as e:
            print(f"Select Empty operator raised unexpected exception: {e}")

        # 3d. Delete armature/bone tracking target
        print("Scenario D: Deleting armature/bone tracking target...")
        props.elements.clear()
        # Create armature with a bone
        bpy.ops.object.armature_add(radius=1.0, enter_editmode=True, align='WORLD', location=(0, 0, 0))
        armature = bpy.context.active_object
        armature.name = "TestArmature"
        bpy.ops.object.mode_set(mode='POSE')
        bone = armature.pose.bones[0]
        bone.name = "TestBone"
        
        # Add bone element to list
        bone.select = True
        bpy.ops.anim.amp_fmp_add_element()
        assert len(props.elements) == 1
        elem_bone = props.elements[0]
        assert elem_bone.item_type == "BONE"
        assert elem_bone.bone_name == "TestBone"
        assert elem_bone.armature_ref == armature
        
        # Switch mode to object and delete armature
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.data.objects.remove(armature, do_unlink=True)
        
        deferred_flex_mopaths_update()
        update_visibility(bpy.context)
        AMP_FMP_UL_Elements.draw_item(uilist, bpy.context, layout, props, elem_bone, 0, props, "active_index", 0)
        AMP_FMP_PT_FlexMoPathsPanel.draw(panel, bpy.context)
        
        print("Invoking Select Element operator on a deleted armature/bone...")
        try:
            bpy.ops.anim.amp_fmp_select_element(index=0)
            print("Select Element operator executed on deleted armature/bone.")
        except ReferenceError as re:
            print(f"Select Element operator raised ReferenceError as expected: {re}")
            
        print("Successfully handled armature/bone deletion without crash.")
        
        print("Test 3: Deleting Tracked Components PASSED.")
        
        # ----------------------------------------------------
        # TEST 4: Toggling visibility and drawing of elements list under different contexts
        # ----------------------------------------------------
        print("\n--- Test 4: Toggling Visibility & Drawing ---")
        props.elements.clear()
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        
        # Create a few objects
        objs = []
        for i in range(5):
            bpy.ops.mesh.primitive_cube_add(location=(i*2, 0, 0))
            obj = bpy.context.active_object
            obj.name = f"ToggleCube_{i}"
            obj.select_set(True)
            bpy.ops.anim.amp_fmp_add_element()
            objs.append(obj)
            
        # Draw under different modes: OBJECT
        bpy.ops.object.mode_set(mode='OBJECT')
        print("Drawing list in OBJECT mode...")
        AMP_FMP_PT_FlexMoPathsPanel.draw(panel, bpy.context)
        
        # Draw under different modes: EDIT
        bpy.ops.object.mode_set(mode='EDIT')
        print("Drawing list in EDIT mode...")
        AMP_FMP_PT_FlexMoPathsPanel.draw(panel, bpy.context)
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Toggle show_motion_paths rapidly
        print("Toggling show_motion_paths and show_list...")
        for val in [True, False, True, False]:
            props.show_motion_paths = val
            props.show_list = val
            update_visibility(bpy.context)
            AMP_FMP_PT_FlexMoPathsPanel.draw(panel, bpy.context)
            
        print("Test 4: Toggling Visibility & Drawing PASSED.")
        
        print("\n--- ALL ADVANCED STRESS TESTS PASSED SUCCESSFULLY ---")
        
    except Exception as e:
        print(f"\n!!! STRESS TEST FAILED !!!")
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Disable addon
        try:
            addon_utils.disable(addon_name)
            print("Addon disabled.")
        except Exception as e:
            print(f"Failed to disable addon during cleanup: {e}")

if __name__ == "__main__":
    run_stress_tests()
