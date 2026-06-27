import bpy
from .. import __package__ as base_package
from .customIcons import load_icons, unload_icons


@bpy.app.handlers.persistent
def amp_on_file_load(dummy):
    # Instead of reloading icons immediately, schedule it with a minimal delay.
    bpy.app.timers.register(delayed_icon_reload, first_interval=0.1)


def delayed_icon_reload():
    addon = bpy.context.preferences.addons.get(base_package)
    if addon is None:
        return None
    prefs = addon.preferences
    try:
        unload_icons()
        load_icons(["icons", prefs.icons_set])
        print("Icons reloaded")
        # Optionally, force UI redraw:
        for screen in bpy.data.screens:
            for area in screen.areas:
                area.tag_redraw()
    except Exception as e:
        print(f"Icon reload failed: {e}")
    return None


def _stop_playback_timer():
    """Stop playback safely from a timer. Calling screen.animation_play() with a
    bare timer context crashes Blender, so run it inside a temp_override that
    supplies a full window / screen / area / region context."""
    wm = bpy.context.window_manager
    if wm is None:
        return None
    for win in wm.windows:
        screen = win.screen
        if screen is None or not screen.is_animation_playing:
            continue
        area = next((a for a in screen.areas if a.type == "VIEW_3D"), None)
        if area is None:
            area = screen.areas[0] if screen.areas else None
        region = None
        if area is not None:
            region = next((r for r in area.regions if r.type == "WINDOW"), None)
        try:
            with bpy.context.temp_override(window=win, screen=screen, area=area, region=region):
                bpy.ops.screen.animation_play()
        except Exception:
            pass
        return None
    return None


@bpy.app.handlers.persistent
def amp_on_frame_change_post(dummy):
    screen = bpy.context.screen
    addon = bpy.context.preferences.addons.get(base_package)
    if addon is None:
        return
    prefs = addon.preferences
    scene = bpy.context.scene

    # if scene.is_nla_tweakmode:
    #     return

    if not screen or not screen.is_animation_playing or scene.frame_current != scene.frame_end:
        return

    active_obj = bpy.context.active_object
    if active_obj and (not active_obj.animation_data or not active_obj.animation_data.action):
        return

    if active_obj and active_obj.animation_data:
        action = active_obj.animation_data.action
        if action and getattr(action, "use_cyclic", False):
            return

    if prefs.playback_loop_only_if_cyclical:
        if not bpy.app.timers.is_registered(_stop_playback_timer):
            bpy.app.timers.register(_stop_playback_timer)


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
