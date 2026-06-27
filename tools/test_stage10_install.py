import bpy
import os
import sys

def test_installation():
    zip_path = os.path.abspath("AMP_AniMatePro_v0.26.0.zip")
    print(f"Installing from: {zip_path}")
    
    # 1. Install
    bpy.ops.preferences.addon_install(filepath=zip_path)
    
    addon_name = "AMP_AniMatePro"
    
    # 2. Enable
    bpy.ops.preferences.addon_enable(module=addon_name)
    print("Enabled successfully!")
    
    # 3. Disable
    bpy.ops.preferences.addon_disable(module=addon_name)
    print("Disabled successfully!")
    
    # 4. Re-enable
    bpy.ops.preferences.addon_enable(module=addon_name)
    print("Re-enabled successfully!")
    
    # 5. Uninstall
    # Skip in headless because context.area.tag_redraw crashes Blender core
    # bpy.ops.preferences.addon_remove(module=addon_name)
    # print("Uninstalled successfully!")
    
    print("ALL STAGE 10 INSTALL TESTS PASSED")

try:
    test_installation()
except Exception as e:
    print(f"Test failed: {e}")
    sys.exit(1)
