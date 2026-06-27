import bpy

def test():
    bpy.ops.object.empty_add(type='PLAIN_AXES', align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
    empty = bpy.context.active_object
    
    try:
        bpy.ops.object.paths_update()
        print("paths_update SUCCESS!")
    except Exception as e:
        print(f"paths_update FAILED: {e}")

test()
