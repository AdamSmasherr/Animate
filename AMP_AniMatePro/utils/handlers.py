import bpy
from .. import __package__ as base_package
from .customIcons import load_icons, unload_icons


@bpy.app.handlers.persistent
def amp_on_file_load(dummy):
    # Instead of reloading icons immediately, schedule it with a minimal delay.
    bpy.app.timers.register(delayed_icon_reload, first_interval=0.1)


def delayed_icon_reload():
    prefs = bpy.context.preferences.addons[base_package].preferences
    unload_icons()
    load_icons(["icons", prefs.icons_set])
    print("Icons reloaded")
    # Optionally, force UI redraw:
    for screen in bpy.data.screens:
        for area in screen.areas:
            area.tag_redraw()
    return None


@bpy.app.handlers.persistent
def amp_on_frame_change_post(dummy):
    screen = bpy.context.screen
    prefs = bpy.context.preferences.addons[base_package].preferences
    scene = bpy.context.scene

    # if scene.is_nla_tweakmode:
    #     return

    if not screen or not screen.is_animation_playing or scene.frame_current != scene.frame_end:
        return

    active_obj = bpy.context.active_object
    if active_obj and not active_obj.animation_data.action:
        return

    if active_obj and active_obj.animation_data:
        action = active_obj.animation_data.action
        if action and getattr(action, "use_cyclic", False):
            return

    if prefs.playback_loop_only_if_cyclical:
        def stop_playback():
            if bpy.context.screen and bpy.context.screen.is_animation_playing:
                bpy.ops.screen.animation_play()
            return None
        bpy.app.timers.register(stop_playback)
        print("End of playback")


def register() -> None:
    try:
        bpy.app.handlers.frame_change_post.remove(amp_on_frame_change_post)
        bpy.app.handlers.load_post.remove(amp_on_file_load)
    except ValueError:
        pass

    try:
        bpy.app.handlers.frame_change_post.append(amp_on_frame_change_post)
        bpy.app.handlers.load_post.append(amp_on_file_load)
    except ValueError:
        pass


def unregister() -> None:
    try:
        bpy.app.handlers.frame_change_post.remove(amp_on_frame_change_post)
        bpy.app.handlers.load_post.remove(amp_on_file_load)
    except ValueError:
        pass
