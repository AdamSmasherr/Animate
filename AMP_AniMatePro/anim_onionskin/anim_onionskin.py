"""
Onion Skin (Tools category)

GPU onion skinning in the 3D viewport for armatures and any animated object.

Design notes
------------
Geometry is produced by *frame stepping*: to bake a frame the scene playhead is
moved to that frame, the dependency graph is evaluated and every related mesh is
read as world space triangles. This is universal (it works for armatures,
meshes, and anything that deforms or moves through animation, modifiers,
constraints or drivers) and is the pragmatic alternative to the NLA strip
duplication approach. Baked geometry is held in a module level cache keyed by a
stable per target id, never in ID properties (raw geometry cannot live there).

Baking moves the playhead, which is illegal inside a draw callback and would
recurse inside a frame_change handler, so all baking is deferred to a one shot
``bpy.app.timers`` callback guarded by a global ``_baking`` flag. The persistent
POST_VIEW draw handler only ever *reads* the cache.

Implemented: four modes (Snapshots, Frame Step, On Keyframes, Before/After),
Before/After colour coding with a distance based alpha gradient, X-Ray / Solid
render modes, Mesh In Front, per target independent settings, multi target
support, global visibility toggle, frame range limiting, manual refresh and
depsgraph driven auto refresh.

Documented as future work in FEATURES.md: screen door dithering shaders,
per element configuration lists with vertex group filtering, NLA strip based
Before/After, and on disk presets.
"""

import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from bpy.app.handlers import persistent
from bpy.types import PropertyGroup, Operator, Panel, UIList
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.utils import register_class, unregister_class

from ..utils import blender_compat


# ----------------------------------------------------------------------------
# Module state
# ----------------------------------------------------------------------------

_geo_cache = {}            # target uid -> { frame:int -> [(x, y, z), ...] tri verts }
_draw_handle = None
_uniform_shader = None
_baking = False
_timer_pending = False
_in_front_original = {}    # mesh object name -> original show_in_front bool

MAX_BAKED_FRAMES = 64      # hard cap on baked frames per target


def _get_uniform_shader():
    global _uniform_shader
    if _uniform_shader is None:
        _uniform_shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    return _uniform_shader


def get_osk(scene):
    return getattr(scene, "amp_onion_skin", None)


# ----------------------------------------------------------------------------
# Frame selection (single source of truth for both bake and draw)
# ----------------------------------------------------------------------------

def _scene_range(scene):
    if scene.use_preview_range:
        return int(scene.frame_preview_start), int(scene.frame_preview_end)
    return int(scene.frame_start), int(scene.frame_end)


def _keyframe_frames(obj):
    """All keyframe frames for obj, filtered to the active pose bone for
    armatures when one is active. Includes the active action (slot aware) and
    stashed / pushed down NLA actions."""
    frames = set()
    ad = getattr(obj, "animation_data", None)
    if ad is None:
        return []

    path_prefix = None
    if obj.type == "ARMATURE":
        bone = obj.data.bones.active if obj.data else None
        if bone is not None:
            path_prefix = 'pose.bones["{}"]'.format(bone.name)

    def scan(action, slot):
        for fc in blender_compat.iter_action_fcurves(action, slot=slot):
            if path_prefix and not fc.data_path.startswith(path_prefix):
                continue
            for kp in fc.keyframe_points:
                frames.add(int(round(kp.co[0])))

    if ad.action is not None:
        scan(ad.action, blender_compat.get_action_slot(obj))

    for track in ad.nla_tracks:
        for strip in track.strips:
            if strip.action is not None:
                scan(strip.action, getattr(strip, "action_slot", None))

    return sorted(frames)


def _selected_frames(scene, osk, target, cur):
    obj = bpy.data.objects.get(target.object_name)
    mode = target.mode
    out = []

    if mode == "SNAPSHOTS":
        out = [int(s.frame) for s in target.snapshots if s.enabled]

    elif mode == "FRAME_STEP":
        # Grid is anchored at the range start so steps stay consistent
        # regardless of the playhead position.
        anchor, _ = _scene_range(scene)
        step = max(1, target.step_size)
        k0 = (cur - anchor) // step
        base = anchor + k0 * step          # largest grid frame <= cur
        before = base if base < cur else base - step
        for i in range(target.step_before):
            out.append(before - i * step)
        after = base + step                 # smallest grid frame > cur
        for i in range(target.step_after):
            out.append(after + i * step)

    elif mode == "KEYFRAMES":
        if obj is not None:
            kfs = _keyframe_frames(obj)
            before = [f for f in kfs if f < cur]
            after = [f for f in kfs if f > cur]
            out = before[-target.key_before:] + after[: target.key_after]

    elif mode == "BEFORE_AFTER":
        out = [cur + int(it.offset) for it in target.ba_items if it.enabled]

    # Range limiting.
    if osk.limit_to_range:
        lo, hi = _scene_range(scene)
        out = [f for f in out if lo <= f <= hi]

    out = sorted({int(f) for f in out})
    if len(out) > MAX_BAKED_FRAMES:
        out = out[:MAX_BAKED_FRAMES]
    return out


# ----------------------------------------------------------------------------
# Related mesh discovery + baking
# ----------------------------------------------------------------------------

def get_related_meshes(obj):
    meshes = []
    if obj is None:
        return meshes
    if obj.type == "MESH":
        meshes.append(obj)
    for o in bpy.data.objects:
        if o.type != "MESH" or o is obj or o in meshes:
            continue
        related = o.parent is obj
        if not related:
            for m in o.modifiers:
                if getattr(m, "object", None) is obj:
                    related = True
                    break
        if not related:
            for c in o.constraints:
                if getattr(c, "target", None) is obj:
                    related = True
                    break
        if related:
            meshes.append(o)
    return meshes


def _bake_current(meshes, depsgraph):
    """Read evaluated world space triangle verts for meshes at the current
    (already set) frame."""
    tris = []
    for m in meshes:
        eval_obj = m.evaluated_get(depsgraph)
        me = None
        try:
            me = eval_obj.to_mesh()
        except Exception:
            me = None
        if me is None:
            continue
        try:
            me.calc_loop_triangles()
            mw = eval_obj.matrix_world
            verts = me.vertices
            for lt in me.loop_triangles:
                for vi in lt.vertices:
                    co = mw @ verts[vi].co
                    tris.append((co.x, co.y, co.z))
        except Exception:
            pass
        finally:
            try:
                eval_obj.to_mesh_clear()
            except Exception:
                pass
    return tris


def _deferred_rebake():
    """One shot timer: bake all needed frames for every target, then redraw."""
    global _baking, _timer_pending
    _timer_pending = False

    context = bpy.context
    scene = context.scene
    osk = get_osk(scene)
    if osk is None or not osk.targets:
        return None

    cur = scene.frame_current
    plan = {}        # uid -> (target, meshes, needed_frames)
    for target in osk.targets:
        obj = bpy.data.objects.get(target.object_name)
        if obj is None:
            continue
        needed = _selected_frames(scene, osk, target, cur)
        if not needed:
            _geo_cache.pop(target.uid, None)
            continue
        meshes = get_related_meshes(obj)
        if not meshes:
            continue
        plan[target.uid] = (target, meshes, needed)

    # Which frames actually need baking across all targets?
    work = {uid: [f for f in needed if f not in _geo_cache.get(uid, {})]
            for uid, (_t, _m, needed) in plan.items()}
    any_work = any(work.values())

    if any_work:
        original_frame = scene.frame_current
        _baking = True
        try:
            # Bake frame by frame, sharing each playhead position across targets.
            all_frames = sorted({f for fs in work.values() for f in fs})
            for f in all_frames:
                scene.frame_set(f)
                depsgraph = context.evaluated_depsgraph_get()
                for uid, frames in work.items():
                    if f in frames:
                        target, meshes, _needed = plan[uid]
                        _geo_cache.setdefault(uid, {})[f] = _bake_current(meshes, depsgraph)
            scene.frame_set(original_frame)
        finally:
            _baking = False

    # Evict frames no longer needed.
    for uid, (_t, _m, needed) in plan.items():
        cache = _geo_cache.get(uid)
        if cache:
            keep = set(needed)
            for f in list(cache.keys()):
                if f not in keep:
                    del cache[f]
    # Drop caches for targets that vanished.
    valid = {t.uid for t in osk.targets}
    for uid in list(_geo_cache.keys()):
        if uid not in valid:
            del _geo_cache[uid]

    _tag_redraw_view3d()
    return None


def _request_rebake():
    global _timer_pending
    if _timer_pending or _baking:
        return
    _timer_pending = True
    if not bpy.app.timers.is_registered(_deferred_rebake):
        bpy.app.timers.register(_deferred_rebake, first_interval=0.0)


def _invalidate_all():
    _geo_cache.clear()


def _invalidate_target(target):
    _geo_cache.pop(target.uid, None)


# ----------------------------------------------------------------------------
# Drawing
# ----------------------------------------------------------------------------

def _alpha_for(rank, count, a_start, a_end):
    if count <= 1:
        return a_start
    t = rank / (count - 1)
    return a_start + (a_end - a_start) * t


def _setup_gpu_state(render_mode):
    gpu.state.blend_set("ALPHA")
    if render_mode in ("SOLID", "SOLID_DITHER"):
        gpu.state.depth_test_set("LESS_EQUAL")
        gpu.state.depth_mask_set(True)
        gpu.state.face_culling_set("BACK")
    else:
        gpu.state.depth_test_set("NONE")
        gpu.state.depth_mask_set(False)
        gpu.state.face_culling_set("NONE")


def _reset_gpu_state():
    gpu.state.depth_mask_set(False)
    gpu.state.depth_test_set("NONE")
    gpu.state.face_culling_set("NONE")
    gpu.state.blend_set("NONE")


def _draw_onion():
    context = bpy.context
    scene = context.scene
    osk = get_osk(scene)
    if osk is None or not osk.global_visible or not osk.targets:
        return

    cur = scene.frame_current
    shader = _get_uniform_shader()

    for target in osk.targets:
        if not target.visible:
            continue
        cache = _geo_cache.get(target.uid)
        if not cache:
            continue

        frames = _selected_frames(scene, osk, target, cur)
        before = sorted([f for f in frames if f < cur], key=lambda f: cur - f)
        after = sorted([f for f in frames if f > cur], key=lambda f: f - cur)

        _setup_gpu_state(target.render_mode)
        for side_frames, color, enabled in (
            (before, target.before_color, target.before_enabled),
            (after, target.after_color, target.after_enabled),
        ):
            if not enabled:
                continue
            n = len(side_frames)
            for rank, f in enumerate(side_frames):
                geo = cache.get(f)
                if not geo:
                    continue
                a = _alpha_for(rank, n, target.alpha_start, target.alpha_end)
                if a < 0.01:
                    continue
                batch = batch_for_shader(shader, "TRIS", {"pos": geo})
                shader.bind()
                shader.uniform_float("color", (color[0], color[1], color[2], a))
                batch.draw(shader)
        _reset_gpu_state()

    _reset_gpu_state()


def _tag_redraw_view3d():
    wm = bpy.context.window_manager
    if wm is None:
        return
    for window in wm.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


# ----------------------------------------------------------------------------
# Mesh In Front
# ----------------------------------------------------------------------------

def _apply_mesh_in_front(target, enable):
    obj = bpy.data.objects.get(target.object_name)
    for m in get_related_meshes(obj):
        if enable:
            if m.name not in _in_front_original:
                _in_front_original[m.name] = m.show_in_front
            m.show_in_front = True
        else:
            if m.name in _in_front_original:
                m.show_in_front = _in_front_original.pop(m.name)


# ----------------------------------------------------------------------------
# Property update callbacks
# ----------------------------------------------------------------------------

def _u_redraw(self, context):
    _tag_redraw_view3d()


def _u_rebake_all(self, context):
    _invalidate_all()
    _request_rebake()
    _tag_redraw_view3d()


def _u_rebake_soft(self, context):
    # Frame counts changed: no new bake needed, only the displayed selection.
    _request_rebake()
    _tag_redraw_view3d()


def _u_mesh_in_front(self, context):
    _apply_mesh_in_front(self, self.mesh_in_front)
    _tag_redraw_view3d()


# ----------------------------------------------------------------------------
# Property groups
# ----------------------------------------------------------------------------

MODE_ITEMS = (
    ("SNAPSHOTS", "Snapshots", "Manually placed snapshot frames", "PINNED", 0),
    ("FRAME_STEP", "Frame Step", "Regular interval around the playhead", "SNAP_INCREMENT", 1),
    ("KEYFRAMES", "On Keyframes", "On the keyframes of the active bone or object", "KEYFRAME", 2),
    ("BEFORE_AFTER", "Before / After", "Explicit per item frame offsets", "TRACKING", 3),
)

RENDER_ITEMS = (
    ("XRAY", "X-Ray", "Semi transparent, see through"),
    ("XRAY_DITHER", "X-Ray Dither", "X-Ray (dither approximated as X-Ray in this build)"),
    ("SOLID", "Solid", "Opaque with depth testing"),
    ("SOLID_DITHER", "Solid Dither", "Solid with back face culling (dither approximated)"),
)


class AMP_PG_OnionSnapshot(PropertyGroup):
    frame: IntProperty(name="Frame", default=1, update=_u_rebake_all)
    enabled: BoolProperty(name="Enabled", default=True, update=_u_redraw)
    name: StringProperty(name="Name", default="Snapshot")


class AMP_PG_OnionBAItem(PropertyGroup):
    offset: IntProperty(name="Offset", default=-3, update=_u_rebake_soft)
    enabled: BoolProperty(name="Enabled", default=True, update=_u_redraw)


class AMP_PG_OnionTarget(PropertyGroup):
    object_name: StringProperty(name="Object")
    uid: IntProperty(name="UID", default=0)
    visible: BoolProperty(name="Visible", default=True, update=_u_redraw)
    show_config: BoolProperty(name="Drawing Settings", default=False)

    mode: EnumProperty(name="Mode", items=MODE_ITEMS, default="SNAPSHOTS", update=_u_rebake_all)

    snapshots: CollectionProperty(type=AMP_PG_OnionSnapshot)
    active_snapshot_index: IntProperty(default=0)

    ba_items: CollectionProperty(type=AMP_PG_OnionBAItem)
    active_ba_index: IntProperty(default=0)

    step_size: IntProperty(name="Step Size", default=5, min=1, soft_max=120, update=_u_rebake_all)
    step_before: IntProperty(name="Before", default=2, min=0, soft_max=32, update=_u_rebake_soft)
    step_after: IntProperty(name="After", default=2, min=0, soft_max=32, update=_u_rebake_soft)
    key_before: IntProperty(name="Before", default=2, min=0, soft_max=32, update=_u_rebake_soft)
    key_after: IntProperty(name="After", default=2, min=0, soft_max=32, update=_u_rebake_soft)

    before_color: FloatVectorProperty(
        name="Before", subtype="COLOR", size=3, min=0.0, max=1.0,
        default=(0.9, 0.2, 0.2), update=_u_redraw,
    )
    after_color: FloatVectorProperty(
        name="After", subtype="COLOR", size=3, min=0.0, max=1.0,
        default=(0.2, 0.45, 0.9), update=_u_redraw,
    )
    before_enabled: BoolProperty(name="Show Before", default=True, update=_u_redraw)
    after_enabled: BoolProperty(name="Show After", default=True, update=_u_redraw)

    alpha_start: FloatProperty(name="Alpha Start", default=0.5, min=0.0, max=1.0, subtype="FACTOR", update=_u_redraw)
    alpha_end: FloatProperty(name="Alpha End", default=0.1, min=0.0, max=1.0, subtype="FACTOR", update=_u_redraw)

    render_mode: EnumProperty(name="Render", items=RENDER_ITEMS, default="XRAY", update=_u_redraw)
    mesh_in_front: BoolProperty(name="Mesh In Front", default=False, update=_u_mesh_in_front)


class AMP_PG_OnionSkin(PropertyGroup):
    targets: CollectionProperty(type=AMP_PG_OnionTarget)
    active_index: IntProperty(default=0, update=_u_redraw)
    global_visible: BoolProperty(name="Global Visibility", default=True, update=_u_redraw)
    limit_to_range: BoolProperty(
        name="Limit to Range",
        description="Constrain onion skins to the preview / scene frame range",
        default=True, update=_u_rebake_all,
    )
    uid_counter: IntProperty(default=0)


# ----------------------------------------------------------------------------
# Operators
# ----------------------------------------------------------------------------

def _active_target(scene):
    osk = get_osk(scene)
    if osk and 0 <= osk.active_index < len(osk.targets):
        return osk.targets[osk.active_index]
    return None


class AMP_OT_OnionAddTarget(Operator):
    """Add the active object as an onion skin target"""
    bl_idname = "anim.amp_onionskin_add_target"
    bl_label = "Add Onion Target"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        osk = get_osk(context.scene)
        obj = context.active_object
        if osk is None or obj is None:
            self.report({"WARNING"}, "Select an object first")
            return {"CANCELLED"}
        if any(t.object_name == obj.name for t in osk.targets):
            self.report({"INFO"}, "Object already a target")
            return {"CANCELLED"}
        target = osk.targets.add()
        target.object_name = obj.name
        osk.uid_counter += 1
        target.uid = osk.uid_counter
        # Default Before/After pair at -3 / +3.
        for off in (-3, 3):
            it = target.ba_items.add()
            it.offset = off
        osk.active_index = len(osk.targets) - 1
        _request_rebake()
        _tag_redraw_view3d()
        return {"FINISHED"}


class AMP_OT_OnionRemoveTarget(Operator):
    """Remove the active onion skin target and clean up its data"""
    bl_idname = "anim.amp_onionskin_remove_target"
    bl_label = "Remove Onion Target"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        osk = get_osk(context.scene)
        if osk is None or not (0 <= osk.active_index < len(osk.targets)):
            return {"CANCELLED"}
        target = osk.targets[osk.active_index]
        _apply_mesh_in_front(target, False)
        _geo_cache.pop(target.uid, None)
        osk.targets.remove(osk.active_index)
        osk.active_index = min(osk.active_index, len(osk.targets) - 1)
        _request_rebake()
        _tag_redraw_view3d()
        return {"FINISHED"}


class AMP_OT_OnionMoveTarget(Operator):
    """Move the active target up or down"""
    bl_idname = "anim.amp_onionskin_move_target"
    bl_label = "Move Onion Target"
    bl_options = {"REGISTER", "UNDO"}
    direction: StringProperty(default="UP")

    def execute(self, context):
        osk = get_osk(context.scene)
        if osk is None:
            return {"CANCELLED"}
        i = osk.active_index
        j = i + (-1 if self.direction == "UP" else 1)
        if 0 <= j < len(osk.targets):
            osk.targets.move(i, j)
            osk.active_index = j
            _tag_redraw_view3d()
        return {"FINISHED"}


class AMP_OT_OnionAddSnapshot(Operator):
    """Capture the current frame as a snapshot"""
    bl_idname = "anim.amp_onionskin_add_snapshot"
    bl_label = "Add Snapshot"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        target = _active_target(context.scene)
        if target is None:
            return {"CANCELLED"}
        frame = context.scene.frame_current
        if any(int(s.frame) == frame for s in target.snapshots):
            self.report({"INFO"}, "Snapshot already exists at this frame")
            return {"CANCELLED"}
        s = target.snapshots.add()
        s.frame = frame
        s.name = "Frame {}".format(frame)
        target.active_snapshot_index = len(target.snapshots) - 1
        _invalidate_target(target)
        _request_rebake()
        _tag_redraw_view3d()
        return {"FINISHED"}


class AMP_OT_OnionRemoveSnapshot(Operator):
    """Remove a snapshot"""
    bl_idname = "anim.amp_onionskin_remove_snapshot"
    bl_label = "Remove Snapshot"
    bl_options = {"REGISTER", "UNDO"}
    index: IntProperty(default=-1)

    def execute(self, context):
        target = _active_target(context.scene)
        if target is None:
            return {"CANCELLED"}
        idx = self.index if self.index >= 0 else target.active_snapshot_index
        if 0 <= idx < len(target.snapshots):
            target.snapshots.remove(idx)
            target.active_snapshot_index = min(idx, len(target.snapshots) - 1)
            _invalidate_target(target)
            _request_rebake()
            _tag_redraw_view3d()
        return {"FINISHED"}


class AMP_OT_OnionClearSnapshots(Operator):
    """Remove every snapshot"""
    bl_idname = "anim.amp_onionskin_clear_snapshots"
    bl_label = "Remove All Snapshots"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        target = _active_target(context.scene)
        if target is None:
            return {"CANCELLED"}
        target.snapshots.clear()
        _invalidate_target(target)
        _request_rebake()
        _tag_redraw_view3d()
        return {"FINISHED"}


class AMP_OT_OnionSnapshotNav(Operator):
    """Jump the playhead to the previous / next snapshot frame"""
    bl_idname = "anim.amp_onionskin_snapshot_nav"
    bl_label = "Navigate Snapshots"
    bl_options = {"REGISTER", "UNDO"}
    direction: StringProperty(default="NEXT")

    def execute(self, context):
        target = _active_target(context.scene)
        if target is None or not target.snapshots:
            return {"CANCELLED"}
        cur = context.scene.frame_current
        frames = sorted(int(s.frame) for s in target.snapshots)
        if self.direction == "NEXT":
            nxt = next((f for f in frames if f > cur), None)
        else:
            nxt = next((f for f in reversed(frames) if f < cur), None)
        if nxt is not None:
            context.scene.frame_current = nxt
        return {"FINISHED"}


class AMP_OT_OnionBAAdd(Operator):
    """Add a Before/After offset item"""
    bl_idname = "anim.amp_onionskin_ba_add"
    bl_label = "Add Before/After Item"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        target = _active_target(context.scene)
        if target is None:
            return {"CANCELLED"}
        it = target.ba_items.add()
        it.offset = -3 if len(target.ba_items) % 2 else 3
        target.active_ba_index = len(target.ba_items) - 1
        _u_rebake_soft(self, context)
        return {"FINISHED"}


class AMP_OT_OnionBARemove(Operator):
    """Remove a Before/After item"""
    bl_idname = "anim.amp_onionskin_ba_remove"
    bl_label = "Remove Before/After Item"
    bl_options = {"REGISTER", "UNDO"}
    index: IntProperty(default=-1)

    def execute(self, context):
        target = _active_target(context.scene)
        if target is None:
            return {"CANCELLED"}
        idx = self.index if self.index >= 0 else target.active_ba_index
        if 0 <= idx < len(target.ba_items):
            target.ba_items.remove(idx)
            target.active_ba_index = min(idx, len(target.ba_items) - 1)
            _u_rebake_soft(self, context)
        return {"FINISHED"}


class AMP_OT_OnionBAReset(Operator):
    """Reset Before/After items to the default -3 / +3 pair"""
    bl_idname = "anim.amp_onionskin_ba_reset"
    bl_label = "Reset Before/After"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        target = _active_target(context.scene)
        if target is None:
            return {"CANCELLED"}
        target.ba_items.clear()
        for off in (-3, 3):
            it = target.ba_items.add()
            it.offset = off
        _u_rebake_soft(self, context)
        return {"FINISHED"}


class AMP_OT_OnionRefresh(Operator):
    """Force a full re-bake of the active target's onion frames"""
    bl_idname = "anim.amp_onionskin_refresh"
    bl_label = "Refresh Onion Skin"
    bl_options = {"REGISTER"}
    all_targets: BoolProperty(default=False)

    def execute(self, context):
        if self.all_targets:
            _invalidate_all()
        else:
            target = _active_target(context.scene)
            if target is not None:
                _invalidate_target(target)
        _request_rebake()
        _tag_redraw_view3d()
        return {"FINISHED"}


class AMP_OT_OnionToggle(Operator):
    """Toggle all onion skins on or off"""
    bl_idname = "anim.amp_onionskin_toggle"
    bl_label = "Toggle Onion Skins"
    bl_options = {"REGISTER"}

    def execute(self, context):
        osk = get_osk(context.scene)
        if osk is None:
            return {"CANCELLED"}
        osk.global_visible = not osk.global_visible
        _tag_redraw_view3d()
        return {"FINISHED"}


# ----------------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------------

class AMP_UL_OnionTargets(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        obj = bpy.data.objects.get(item.object_name)
        ico = "ARMATURE_DATA" if (obj and obj.type == "ARMATURE") else "OBJECT_DATA"
        row = layout.row(align=True)
        row.label(text=item.object_name or "<missing>", icon=ico)
        row.prop(item, "visible", text="", icon="HIDE_OFF" if item.visible else "HIDE_ON", emboss=False)
        row.prop(item, "show_config", text="", icon="SETTINGS", emboss=False)


def _draw_drawing_settings(layout, target):
    box = layout.box()
    box.label(text="Drawing Settings", icon="SETTINGS")
    row = box.row(align=True)
    row.prop(target, "before_enabled", text="", icon="HIDE_OFF" if target.before_enabled else "HIDE_ON")
    row.prop(target, "before_color", text="Before")
    row = box.row(align=True)
    row.prop(target, "after_enabled", text="", icon="HIDE_OFF" if target.after_enabled else "HIDE_ON")
    row.prop(target, "after_color", text="After")
    col = box.column(align=True)
    col.prop(target, "alpha_start")
    col.prop(target, "alpha_end")
    box.prop(target, "render_mode", text="")
    box.prop(target, "mesh_in_front")


def draw_onion_ui(layout, context):
    scene = context.scene
    osk = get_osk(scene)
    if osk is None:
        layout.label(text="Unavailable", icon="ERROR")
        return

    header = layout.row(align=True)
    header.prop(osk, "global_visible", text="",
                icon="HIDE_OFF" if osk.global_visible else "HIDE_ON")
    header.label(text="Onion Skins")
    header.prop(osk, "limit_to_range", text="", icon="ARROW_LEFTRIGHT")

    row = layout.row()
    row.template_list("AMP_UL_OnionTargets", "", osk, "targets", osk, "active_index", rows=3)
    col = row.column(align=True)
    col.operator("anim.amp_onionskin_add_target", text="", icon="ADD")
    col.operator("anim.amp_onionskin_remove_target", text="", icon="REMOVE")
    col.separator()
    col.operator("anim.amp_onionskin_move_target", text="", icon="TRIA_UP").direction = "UP"
    col.operator("anim.amp_onionskin_move_target", text="", icon="TRIA_DOWN").direction = "DOWN"

    target = _active_target(scene)
    if target is None:
        return

    mode_row = layout.row(align=True)
    mode_row.prop(target, "mode", text="")
    mode_row.operator("anim.amp_onionskin_refresh", text="", icon="FILE_REFRESH")

    if target.mode == "SNAPSHOTS":
        r = layout.row(align=True)
        r.operator("anim.amp_onionskin_add_snapshot", text="Add", icon="ADD")
        r.operator("anim.amp_onionskin_snapshot_nav", text="", icon="TRIA_LEFT").direction = "PREV"
        r.operator("anim.amp_onionskin_snapshot_nav", text="", icon="TRIA_RIGHT").direction = "NEXT"
        r.operator("anim.amp_onionskin_clear_snapshots", text="", icon="TRASH")
        box = layout.box()
        if not target.snapshots:
            box.label(text="No snapshots", icon="INFO")
        for i, s in enumerate(target.snapshots):
            sr = box.row(align=True)
            sr.prop(s, "enabled", text="", icon="HIDE_OFF" if s.enabled else "HIDE_ON")
            sr.prop(s, "frame", text="")
            sr.operator("anim.amp_onionskin_remove_snapshot", text="", icon="X").index = i

    elif target.mode == "FRAME_STEP":
        col = layout.column(align=True)
        col.prop(target, "step_size")
        col.prop(target, "step_before")
        col.prop(target, "step_after")

    elif target.mode == "KEYFRAMES":
        col = layout.column(align=True)
        col.prop(target, "key_before")
        col.prop(target, "key_after")
        layout.label(text="Uses active bone / object keys", icon="KEYFRAME")

    elif target.mode == "BEFORE_AFTER":
        r = layout.row(align=True)
        r.operator("anim.amp_onionskin_ba_add", text="Add", icon="ADD")
        r.operator("anim.amp_onionskin_ba_reset", text="", icon="LOOP_BACK")
        box = layout.box()
        for i, it in enumerate(target.ba_items):
            br = box.row(align=True)
            br.prop(it, "enabled", text="", icon="HIDE_OFF" if it.enabled else "HIDE_ON")
            br.prop(it, "offset", text="Offset")
            br.operator("anim.amp_onionskin_ba_remove", text="", icon="X").index = i

    if target.show_config:
        _draw_drawing_settings(layout, target)


class AMP_PT_OnionSkin(Panel):
    bl_idname = "AMP_PT_OnionSkin"
    bl_label = "Onion Skins"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Animation"

    def draw(self, context):
        draw_onion_ui(self.layout, context)


class AMP_PT_OnionSkinPopover(Panel):
    bl_idname = "AMP_PT_OnionSkinPopover"
    bl_label = "Onion Skins"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_ui_units_x = 17

    def draw(self, context):
        draw_onion_ui(self.layout, context)


def OnionSkinButton(layout, context):
    """Header button for the Tools section: global toggle + settings popover."""
    osk = get_osk(context.scene)
    enabled = bool(osk and osk.global_visible and osk.targets)
    row = layout.row(align=True)
    row.operator("anim.amp_onionskin_toggle", text="", icon="GHOST_ENABLED", depress=enabled)
    row.popover("AMP_PT_OnionSkinPopover", text="")


# ----------------------------------------------------------------------------
# Handlers
# ----------------------------------------------------------------------------

@persistent
def _on_frame_change(scene, depsgraph=None):
    if _baking:
        return
    osk = get_osk(scene)
    if osk is None or not osk.targets or not osk.global_visible:
        return
    # Relative modes depend on the playhead; snapshots are absolute.
    if any(t.mode in {"FRAME_STEP", "KEYFRAMES", "BEFORE_AFTER"} for t in osk.targets):
        _request_rebake()


@persistent
def _on_depsgraph_update(scene, depsgraph=None):
    if _baking:
        return
    screen = bpy.context.screen
    if screen is not None and screen.is_animation_playing:
        return
    osk = get_osk(scene)
    if osk is None or not osk.targets:
        return
    if depsgraph is None:
        return
    dirty = False
    target_objs = {t.object_name for t in osk.targets}
    for upd in depsgraph.updates:
        idd = upd.id
        name = getattr(idd, "name", None)
        if name in target_objs and (upd.is_updated_geometry or upd.is_updated_transform):
            for t in osk.targets:
                if t.object_name == name:
                    _invalidate_target(t)
                    dirty = True
    if dirty:
        _request_rebake()


@persistent
def _on_load(_dummy):
    _invalidate_all()


# ----------------------------------------------------------------------------
# Register
# ----------------------------------------------------------------------------

classes = (
    AMP_PG_OnionSnapshot,
    AMP_PG_OnionBAItem,
    AMP_PG_OnionTarget,
    AMP_PG_OnionSkin,
    AMP_OT_OnionAddTarget,
    AMP_OT_OnionRemoveTarget,
    AMP_OT_OnionMoveTarget,
    AMP_OT_OnionAddSnapshot,
    AMP_OT_OnionRemoveSnapshot,
    AMP_OT_OnionClearSnapshots,
    AMP_OT_OnionSnapshotNav,
    AMP_OT_OnionBAAdd,
    AMP_OT_OnionBARemove,
    AMP_OT_OnionBAReset,
    AMP_OT_OnionRefresh,
    AMP_OT_OnionToggle,
    AMP_UL_OnionTargets,
    AMP_PT_OnionSkin,
    AMP_PT_OnionSkinPopover,
)


def register():
    global _draw_handle
    for cls in classes:
        register_class(cls)
    bpy.types.Scene.amp_onion_skin = PointerProperty(type=AMP_PG_OnionSkin)

    if _draw_handle is None:
        _draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            _draw_onion, (), "WINDOW", "POST_VIEW"
        )
    if _on_frame_change not in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.append(_on_frame_change)
    if _on_depsgraph_update not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_on_depsgraph_update)
    if _on_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_on_load)


def unregister():
    global _draw_handle, _uniform_shader

    for handler_list, fn in (
        (bpy.app.handlers.frame_change_post, _on_frame_change),
        (bpy.app.handlers.depsgraph_update_post, _on_depsgraph_update),
        (bpy.app.handlers.load_post, _on_load),
    ):
        if fn in handler_list:
            handler_list.remove(fn)

    if _draw_handle is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, "WINDOW")
        except (ValueError, ReferenceError):
            pass
        _draw_handle = None

    _invalidate_all()
    _in_front_original.clear()
    _uniform_shader = None

    if hasattr(bpy.types.Scene, "amp_onion_skin"):
        del bpy.types.Scene.amp_onion_skin

    for cls in reversed(classes):
        try:
            unregister_class(cls)
        except RuntimeError:
            pass
