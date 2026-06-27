import sys
import os
import traceback
import bpy

def main():
    print("\n--- STARTING SMOKE TEST ---")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_root = os.path.dirname(script_dir)
    
    if workspace_root not in sys.path:
        sys.path.append(workspace_root)
    
    try:
        import addon_utils
        print("Importing AMP_AniMatePro...")
        import AMP_AniMatePro
        print("Import successful.")
        
        print("Registering AMP_AniMatePro...")
        addon_utils.enable("AMP_AniMatePro", default_set=True)
        print("Register successful.")
        
        print("Unregistering AMP_AniMatePro...")
        addon_utils.disable("AMP_AniMatePro")
        print("Unregister successful.")
        
        print("\n--- SMOKE TEST PASSED ---")
        sys.exit(0)
    except Exception as e:
        print("\n--- SMOKE TEST FAILED ---")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
