import bpy
import addon_utils
import sys
import traceback

sys.path.append(r"D:\Code\AMP_AniMatePro\AMP_AniMatePro_v0.25.10318")

def run_tests():
    # 1. Enable addon
    addon_name = "AMP_AniMatePro"
    try:
        addon_utils.enable(addon_name, default_set=True)
        print(f"Successfully enabled {addon_name}")
    except Exception as e:
        print(f"Failed to enable addon: {e}")
        sys.exit(1)

    try:
        # Clear existing elements/objects to start fresh
        props = bpy.context.scene.mp_props
        props.elements.clear()
        
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)

        # 2. Add primitive object
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        cube = bpy.context.active_object
        cube.name = "MyUniqueCube"
        cube.select_set(True)

        # 3. Add object to Flex MoPaths list
        bpy.ops.anim.amp_fmp_add_element()
        
        # Verify element is added
        assert len(props.elements) == 1, "Failed to add element"
        elem = props.elements[0]
        assert elem.name == "MyUniqueCube", f"Expected element name to be MyUniqueCube, got {elem.name}"
        assert elem.object_ref == cube, "Object ref not set correctly"
        assert elem.empty_ref is not None, "Empty ref not created"
        
        empty = elem.empty_ref
        collection_name = elem.collection_name
        print(f"Added element successfully: name={elem.name}, empty={empty.name}, collection={collection_name}")

        # 4. Rename the object
        cube.name = "RenamedCube"
        print("Renamed object to 'RenamedCube'")

        # 5. Trigger deferred update
        from AMP_AniMatePro.anim_mopaths.anim_flex_mopaths import deferred_flex_mopaths_update
        deferred_flex_mopaths_update()

        # 6. Verify name synchronization of element, empty, and collection
        assert elem.name == "RenamedCube", f"Element name was not synchronized, got: {elem.name}"
        assert empty.name == "AMP_FMP_CustomOrigin_RenamedCube", f"Empty was not renamed, got: {empty.name}"
        assert elem.collection_name == "AMP_FMP_CustomOrigin_RenamedCube_Collection", f"Collection name property was not renamed, got: {elem.collection_name}"
        assert "AMP_FMP_CustomOrigin_RenamedCube_Collection" in bpy.data.collections, "Collection was not renamed in bpy.data.collections"
        print("Rename synchronization verification PASSED!")

        # 7. Test UIList drawing and panel drawing
        from AMP_AniMatePro.anim_mopaths.anim_flex_mopaths import AMP_FMP_UL_Elements, AMP_FMP_PT_FlexMoPathsPanel

        class MockLayout:
            enabled = True
            def row(self, *args, **kwargs):
                return self
            def box(self, *args, **kwargs):
                return self
            def separator(self, *args, **kwargs):
                pass
            def column(self, *args, **kwargs):
                return self
            def prop(self, *args, **kwargs):
                pass
            def label(self, *args, **kwargs):
                pass
            def template_list(self, *args, **kwargs):
                pass
            def operator(self, *args, **kwargs):
                return MockOperator()

        class MockOperator:
            index = 0

        class DummyUIList:
            layout_type = 'DEFAULT'

        layout = MockLayout()
        # Draw the item using class method and dummy self
        AMP_FMP_UL_Elements.draw_item(DummyUIList(), bpy.context, layout, props, elem, 0, props, "active_index", 0)
        print("UI List draw test PASSED!")

        # Test Panel Drawing
        class DummyPanel:
            layout = MockLayout()

        AMP_FMP_PT_FlexMoPathsPanel.draw(DummyPanel(), bpy.context)
        print("Panel draw test PASSED!")

        # 8. Test deleting the tracked object
        bpy.data.objects.remove(cube, do_unlink=True)
        print("Deleted the tracked object from scene")

        # Run update visibility and deferred update checks to ensure they don't crash
        deferred_flex_mopaths_update()
        from AMP_AniMatePro.anim_mopaths.anim_flex_mopaths import update_visibility
        update_visibility(bpy.context)
        print("Post-deletion visibility update and deferred update tests PASSED without crash!")

        # Draw item again post-deletion
        AMP_FMP_UL_Elements.draw_item(DummyUIList(), bpy.context, layout, props, elem, 0, props, "active_index", 0)
        print("UI List draw test post-deletion PASSED without crash!")
        # 9. Stress-test: Deleting empty tracking objects, then renaming target objects
        print("--- Testing Deletion of Empty Tracking Objects followed by Rename ---")
        bpy.ops.mesh.primitive_cube_add(location=(1, 1, 1))
        cube2 = bpy.context.active_object
        cube2.name = "Cube2"
        cube2.select_set(True)
        bpy.ops.anim.amp_fmp_add_element()
        
        # Verify added
        assert len(props.elements) == 2, "Failed to add second element"
        elem2 = props.elements[1]
        empty2 = elem2.empty_ref
        assert empty2 is not None, "Empty ref not created for second element"
        
        # Manually delete the empty tracking object
        bpy.data.objects.remove(empty2, do_unlink=True)
        print("Deleted empty tracking object for Cube2")
        
        # Rename target object
        cube2.name = "RenamedCube2"
        print("Renamed Cube2 to RenamedCube2")
        
        # Run deferred update
        deferred_flex_mopaths_update()
        
        # Verify name sync completes for the element name itself
        assert elem2.name == "RenamedCube2", f"Element name was not synchronized, got: {elem2.name}"
        print("Name synchronization with deleted empty tracking object PASSED!")

        # 10. Stress-test: Clicking select buttons on deleted elements/empties (verifying no Python traceback)
        print("--- Testing selection operators on deleted elements/empties ---")
        
        # Element 0 (MyUniqueCube) has its target cube deleted already.
        # Let's call select element on index 0
        res1 = bpy.ops.anim.amp_fmp_select_element(index=0)
        assert res1 == {'CANCELLED'}, f"Expected CANCELLED, got {res1}"
        
        # Delete the empty for element 0 if not deleted, and call select empty
        empty_obj_0 = props.elements[0].empty_ref
        if empty_obj_0:
            try:
                bpy.data.objects.remove(empty_obj_0, do_unlink=True)
            except ReferenceError:
                pass
        
        res2 = bpy.ops.anim.amp_fmp_select_empty(index=0)
        assert res2 == {'CANCELLED'}, f"Expected CANCELLED, got {res2}"
        print("Selection operator guards for deleted elements/empties PASSED!")

        # 11. Stress-test: Executing remove active/index operators on empty/missing collections
        print("--- Testing remove operators with missing collections/out of range indexes ---")
        
        # Let's delete the sub-collection of elem2 manually
        if elem2.collection_name in bpy.data.collections:
            coll2 = bpy.data.collections[elem2.collection_name]
            bpy.data.collections.remove(coll2, do_unlink=True)
            print("Manually deleted the sub-collection for elem2")
        
        # Now remove index operator on elem2 (which is at index 1)
        res_remove = bpy.ops.anim.amp_fmp_remove_index_element(index=1)
        assert res_remove == {'FINISHED'}, f"Expected FINISHED, got {res_remove}"
        
        # Test out-of-range index on remove_index_element
        res_out_of_range = bpy.ops.anim.amp_fmp_remove_index_element(index=99)
        assert res_out_of_range == {'CANCELLED'}, f"Expected CANCELLED, got {res_out_of_range}"
        
        # Test remove active when active is None
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = None
        res_remove_active = bpy.ops.anim.amp_fmp_remove_active_element()
        assert res_remove_active == {'CANCELLED'}, f"Expected CANCELLED for remove active, got {res_remove_active}"
        
        print("Remove operator tests with missing collections/invalid indexes PASSED!")

        # 12. Stress-test: Active Object Guard in Realtime Updates (anim_mopaths.py)
        print("--- Testing active object guard in anim_mopaths.py ---")
        from AMP_AniMatePro.anim_mopaths.anim_mopaths import update_motion_paths
        # When active_object is None
        bpy.context.view_layer.objects.active = None
        try:
            update_motion_paths(bpy.context)
            print("update_motion_paths with active_object=None PASSED without AttributeError!")
        except AttributeError as ae:
            print(f"update_motion_paths failed with AttributeError: {ae}")
            raise

        print("\n--- ALL FLEX MOPATHS CRASH FIX TESTS PASSED ---")

    except Exception as e:
        print(f"Test FAILED: {e}")
        traceback.print_exc()
        sys.exit(1)

    finally:
        try:
            addon_utils.disable(addon_name)
            print(f"Successfully disabled {addon_name}")
        except Exception as e:
            print(f"Failed to disable addon during cleanup: {e}")

if __name__ == "__main__":
    run_tests()
