import bpy
from bpy.types import Operator

class AMP_OT_pan_zoom(Operator):
    bl_idname = "amp.pan_zoom"
    bl_label = "AMP Pan & Zoom"
    bl_options = {'GRAB_CURSOR', 'UNDO'}

    def invoke(self, context, event):
        if context.area.type not in {'DOPESHEET_EDITOR', 'GRAPH_EDITOR'}:
            return {'CANCELLED'}
        
        region = context.region
        if not region or not hasattr(region, 'view2d'):
            return {'CANCELLED'}
        
        self.view2d = region.view2d
        self.init_mouse_x = event.mouse_x
        self.init_mouse_y = event.mouse_y

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if (event.type == 'MIDDLEMOUSE' and event.alt and event.value == 'RELEASE') or event.type == 'ESC':
            return {'FINISHED'}

        if event.type == 'MOUSEMOVE':
            dx = event.mouse_x - self.init_mouse_x
            dy = event.mouse_y - self.init_mouse_y

            # Sensitivity factors
            pan_sensitivity = 0.000001    # Adjust for pan responsiveness
            zoom_sensitivity = 0.000001 # Adjust for zoom responsiveness

            # Apply horizontal pan
            if dx != 0:
                pan_deltax = int(-dx * pan_sensitivity)  # Cast to int to match operator requirements
                bpy.ops.view2d.pan(deltax=pan_deltax, deltay=0)

            # Apply vertical zoom
            if dy != 0:
                # Calculate zoom factor based on vertical movement
                zoom_delta = dy * zoom_sensitivity
                zoom_delta = max(min(zoom_delta, 5.0), -5.0)  # Clamp to prevent excessive zooming

                if zoom_delta < 0:
                    # Zoom in
                    bpy.ops.view2d.zoom_in(zoomfacx=abs(zoom_delta), zoomfacy=abs(zoom_delta))
                elif zoom_delta > 0:
                    # Zoom out
                    bpy.ops.view2d.zoom_out(zoomfacx=zoom_delta, zoomfacy=zoom_delta)

        return {'RUNNING_MODAL'}

def register_keymap():
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if not kc:
        kc = wm.keyconfigs.new(name='AniMatePro')

    keymap_entries = [
        ('Dopesheet', 'DOPESHEET_EDITOR'),
        ('Graph Editor', 'GRAPH_EDITOR')
    ]

    for km_name, space_type in keymap_entries:
        km = kc.keymaps.get(km_name)
        if not km:
            km = kc.keymaps.new(name=km_name, space_type=space_type)

        # Remove existing Alt+MMB bindings to avoid conflicts
        to_remove = []
        for kmi in km.keymap_items:
            if kmi.type == 'MIDDLEMOUSE' and kmi.alt and kmi.value in {'PRESS', 'CLICK'}:
                to_remove.append(kmi)
        for kmi in to_remove:
            km.keymap_items.remove(kmi)

        # Add the AMP_OT_pan_zoom operator to Alt+MMB
        km.keymap_items.new("amp.pan_zoom", 'MIDDLEMOUSE', 'PRESS', alt=True)

def unregister_keymap():
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if not kc:
        return

    keymap_names = ['Dopesheet', 'Graph Editor']
    for km_name in keymap_names:
        km = kc.keymaps.get(km_name)
        if km:
            to_remove = []
            for kmi in km.keymap_items:
                if kmi.idname == "amp.pan_zoom" and kmi.alt:
                    to_remove.append(kmi)
            for kmi in to_remove:
                km.keymap_items.remove(kmi)

classes = (AMP_OT_pan_zoom,)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    register_keymap()

def unregister():
    unregister_keymap()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
