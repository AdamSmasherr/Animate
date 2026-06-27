import bpy
import addon_utils
import sys

sys.path.append(r"D:\Code\AMP_AniMatePro\AMP_AniMatePro_v0.25.10318")

def test_leak():
    addon_name = "AMP_AniMatePro"
    addon_utils.enable(addon_name, default_set=True)
    
    props = bpy.context.scene.mp_props
    props.elements.clear()
    
    # 1. Clean up collections and objects
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for col in list(bpy.data.collections):
        if col.name.startswith("AMP_FMP"):
            bpy.data.collections.remove(col)
            
    # 2. Pre-create a collection to cause a rename collision
    collision_coll_name = "AMP_FMP_CustomOrigin_TargetCube_Collection"
    bpy.data.collections.new(collision_coll_name)
    
    # 3. Create active object and add to list
    bpy.ops.mesh.primitive_cube_add(location=(0,0,0))
    cube = bpy.context.active_object
    cube.name = "SourceCube"
    cube.select_set(True)
    bpy.ops.anim.amp_fmp_add_element()
    
    elem = props.elements[0]
    print(f"Initial collection name stored: {elem.collection_name}")
    
    # 4. Rename cube to 'TargetCube' (this causes the collision on rename)
    cube.name = "TargetCube"
    
    from AMP_AniMatePro.anim_mopaths.anim_flex_mopaths import deferred_flex_mopaths_update
    deferred_flex_mopaths_update()
    
    print(f"After rename, stored collection name: {elem.collection_name}")
    print(f"Collections in blend file: {[col.name for col in bpy.data.collections]}")
    
    # Check if the stored name is in bpy.data.collections
    found = elem.collection_name in bpy.data.collections
    print(f"Is stored collection name valid? {found}")
    
    # 5. Remove element and see if collection is leaked
    bpy.ops.anim.amp_fmp_remove_index_element(index=0)
    print(f"Collections remaining after element removal: {[col.name for col in bpy.data.collections]}")
    
    addon_utils.disable(addon_name)

if __name__ == "__main__":
    test_leak()
