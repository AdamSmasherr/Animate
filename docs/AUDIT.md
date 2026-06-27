# AMP_AniMatePro — Stage 1 Audit Report

**Target:** Blender 5.1.2  •  **Add-on:** AMP_AniMatePro  •  **Date:** 2026-06-27

## Executive Summary

This Stage 1 audit reviewed the AMP_AniMatePro add-on for Blender 5.1.2 compatibility,
register/unregister correctness, runtime crash paths, layered-action (4.4+/5.1) regressions,
GPU-backend (Vulkan/Metal) issues, destructive scene/preference mutations, and dead code.
After deduplicating near-identical findings, **204 issues** remain. The most urgent are a
**layered-action regression** that silently breaks AnimOffset masking, several
**generator-vs-`len()`/subscript** crashes introduced by the 4.4+ layered-action refactor,
multiple **draw-handler / depsgraph-handler leaks** where `unregister()` never removes what
`register()` (or a toggle) added, a few **hardcoded `bpy.data.scenes["Scene"]`** lookups that
KeyError in panel draw, and **operators invoked from property-update callbacks** that corrupt
undo/context. A large tail of Low-severity items is dead/duplicated code and missing `None`
guards. Many of the highest-count problems are mechanically safe one-line fixes; the riskier
items involve modal lifecycle, undo, native-UI reimplementation, and destructive batch operations.

### Counts by severity (after dedup)

| Severity | Count |
|----------|-------|
| Critical | 1     |
| High     | 23    |
| Medium   | 107   |
| Low      | 73    |
| **Total**| **204** |

---

## Safe fixes to apply now (checklist)

These are verified, low-risk, behavior-preserving fixes. (See the severity sections for full detail.)

- [ ] `properties.py:165-173` — delete stray `del Scene.timeline_scrub_settings` in `unregister()`.
- [ ] `dope_header_51.py` / `graph_header_51.py` — delete unused, never-imported stock header snapshots.
- [ ] `__init__.py:101,140` — drop `anim_overlap` import + duplicate `persistent` + unused imports.
- [ ] `__init__.py:163-185` — gate `anim_experimental.unregister()` on the same `experimental` flag as register.
- [ ] `register_keymaps.py:300-321` — make `unregister()` mirror `register()` (per-flag toggle).
- [ ] `operators.py:107…` — add `poll()` requiring `context.area` and guard `header_text_set`.
- [ ] `preferences.py:152-220` — allow-list user-config props in `to_dict/from_dict`; exclude transient/`original_*`/`auto_save_path`.
- [ ] `preferences.py:2079-2090` — guard prefs access during register; stop swallowing `ValueError`.
- [ ] `preferences.py:67-70` — normalize `.json` at point of use, not inside the update callback.
- [ ] `utils/general.py:1141,1153-1177` — fix `capture_original_theme_colors()` arity and `global _was_save_preferences_true`.
- [ ] `utils/general.py:1138,1214` — remove the `original_theme_captured = False` line that defeats capture-once.
- [ ] `utils/general.py:803-810` — filter `None` from `[context.active_object]`.
- [ ] `utils/general.py:1402-1408` — replace `TRI_FAN` with `TRIS`/`TRI_STRIP`.
- [ ] `utils/general.py:1062-1063,1078-1083` — guard `context.area`/`space_data.dopesheet`.
- [ ] `utils/general.py:97-98` — use `.get()` with `None` checks in `find_user_keyconfig`.
- [ ] `utils/curve.py:205` — `fcurves = list(all_fcurves(action))` before `len()`.
- [ ] `utils/curve.py:299-336` — materialize generators / remove dead clone functions.
- [ ] `utils/curve.py:713-725` — collect targets then remove in reverse; call `fcurve.update()`.
- [ ] `utils/curve.py:124-127` — `create_path` should test/eval the `z` dict, not `x`.
- [ ] `utils/curve.py:629,656,1150` — replace `('A' or 'B')` with membership set tests.
- [ ] `utils/curve.py:584-587,648-657,664,1382,350-362` — add `None` guards (active_object/area/space_data).
- [ ] `utils/handlers.py:36-37` — guard `active_obj.animation_data` before `.action`.
- [ ] `utils/operators.py:163-168` — per-class try/except, catch `(RuntimeError, AttributeError)`.
- [ ] `utils/key.py:206` — use `if key_i is not None:`.
- [ ] `utils/customIcons.py:89` — guard `custom_icons is not None`.
- [ ] `utils/__init__.py:11-24` — catch `Exception` and log instead of bare `except: pass`.
- [ ] `utils/blender_compat.py:189-197` — collapse the duplicate GP-layer branches.
- [ ] `utils/handlers.py:13-15,27,45-51` — guard `addons.get(base_package)`; dedupe timer registration.
- [ ] `ui/ui.py:98-141` — replace `bpy.data.scenes["Scene"]` with `context.scene`.
- [ ] `ui/blender_ui.py:321-322` — implement `unregister()` to restore native headers / remove custom ones.
- [ ] `ui/top_sections.py:616-617` — wrap menu `.remove()` in try/except.
- [ ] `ui/ui.py:840-947`, `ui/side_panles_ui.py:13-24`, `ui/blender_ui.py:231-241` — remove dead classes / unused imports / add `None` guards.
- [ ] `anim_curves/anim_curves.py:771-810,671-690,212-220,324-326,1196-1219,1997-2132,193-210,585-605` — init `fcurves`, add `None` guards/poll, fix generator `.remove`.
- [ ] `anim_timewarper/anim_timewarper.py:1805-1817,777-779,1811-1814,1259-1266,228-245` — del Scene prop on unregister, `None` guards, dead-code removal, GPU blend.
- [ ] `anim_selection_sets/anim_selection_sets.py:1275-1287,948-957,30-45` — store/remove draw handle, drop invalid `bpy.ops("CANCELLED")`, defer modal, bounds-check, remove dead helpers.
- [ ] `anim_lattice/anim_lattice.py:217-219,1215-1250,9` — `None` guard poll, delete duplicate panel, remove dead import.
- [ ] `anim_flex_mopaths.py:1129-1130,478-487,547-552` — guard scene read at register; cancel timers; re-arm handler on load_post.
- [ ] `anim_mopaths.py:218-241,367-368,247-313` — cancel timers on unregister; dedupe imports; wrap deferred handler.
- [ ] `anim_sculpt.py:602-604,430-432,23-104,366-408,954-956` — poll `None` guard, O(n²) fix, dead-code removal, space_data guard.
- [ ] `anim_stepper/anim_stepper.py:245-262` — per-class try/except in register/unregister.
- [ ] `anim_scrub/anim_scrub.py:240-242,139-148,146` — annotate props, guard `context.area`, `getattr(action,'use_cyclic',False)`.
- [ ] `anim_stepper/camera_stepper.py:459,529-619,998-1004,68-93` — `animation_data` guard, bounds checks, remove duplicate unregister/dead code.
- [ ] `anim_offset/support.py:145,222,243` — read mask curve via `all_fcurves`/`include_all_slots=True`.
- [ ] `anim_offset/support.py:174-199,378-389` — use passed `obj` not `active_object`; fix poll selection check.
- [ ] `anim_offset/ops.py:117,162,41-86` — guard `context.area`/`screen`; delete dead modal-test.
- [ ] `anim_offset/ui.py:281-286` — init `mask_in_use = False`.
- [ ] `autoKeying/utils.py:377-403,428-462,38-155,27` — stop sharing `'SpaceView3D'` dict key; remove dead `draw_frame`; safe UI-region lookup.
- [ ] `autoKeying/ui.py:675-679` — simplify tautological `poll`.
- [ ] `anim_poser/anim_poser.py:567-576,86-88,107-225,503` — remove handler/timer on unregister; init `props=None`; delete dead funcs; guard `context.area`.
- [ ] `anim_poser/anim_silhouette.py:408-412` — remove/register dead panel.
- [ ] `anim_euler/anim_euler.py:479` — use in-addon euler filter / try-except instead of `bpy.ops.graph.euler_filter()`.
- [ ] `anim_retimer/anim_retimer.py:66-72,97,126-142,86` — dedupe action datablocks; per-fcurve original-first-frame; restore frame.
- [ ] `anim_shifter/anim_shifter.py:235-254,80-116` — `fcurve.update()` on all modified curves; remove dead helpers.
- [ ] `anim_baker/anim_baker.py:147-153,371-379,353,165` — add poll/`None` guard; snapshot iterate; `frame_range[0]`; remove debug print.
- [ ] `anim_looper/realtime_looper.py:190-198,6` — remove handler on unregister; clear `_last_copied_values`.
- [ ] `anim_looper/anim_looper.py:337-338`, `anim_keyframer/anim_keyframer.py:230-231` — `utils.dprint` not `utils.dutils.dprint`.
- [ ] `anim_nudger/anim_nudger.py:46-47,361-396` — guard `context.area`; remove dead panel.
- [ ] `anim_experimental/anim_key_poser/anim_key_poser.py:40-42,872-888,8-13,83-128,563` — delete `item.action_ref`; fix `utils.dprint`; remove dead funcs.
- [ ] `anim_experimental/anim_key_poser/anim_key_poser_baker.py:127-142` — fix `utils.dprint`.
- [ ] `anim_experimental/anim_key_poser/anim_key_poser_time_warper.py:243,255-309,5` — `None` guards; remove dead min/max; drop unused import.
- [ ] `markers_tools/markers.py:246-258,153-163` — `context.scene` not `bpy.data.scenes["Scene"]`; guard active_object.
- [ ] `changelog.py:82,111,489` — fix duplicate dict key; remove unused import.
- [ ] `keymaps/keymaps.py` — delete unused incompatible-schema dead config.
- [ ] `keymaps/key_graph_editor_zoom_curves.py:54-83` — use `"name": "Dopesheet"` for DOPESHEET entries.

---

## Critical

- **interpolation_update cannot find the blend curve on layered actions** — `anim_offset/props.py:32` (safe)
  Why: `interpolation_update` calls `iter_action_fcurves(blends_action)` with no slot / `include_all_slots`, so on 4.4+/5.1 layered `amp_action` it yields nothing; `blends_curves` is empty and changing easing/interp EnumProperties silently does nothing (mask interpolation never applied). Same root cause as the `support.py` reads.
  Fix: Use `utils.curve.all_fcurves(blends_action)` or pass `include_all_slots=True` to `iter_action_fcurves`.

---

## High

- **Mask blend F-Curve unreachable on layered actions** — `anim_offset/support.py:145,222,243` (safe)
  Why: `magnet()`, `remove_mask()`, `set_blend_values()` read the layered `amp_action` via `iter_action_fcurves` with no slot, so `blends_curves` is always empty; the soft blend falloff degrades to a hard cutoff and `set_blend_values` no-ops. AnimOffset masking is broken on 5.1.2.
  Fix: At all three sites read via `list(utils.curve.all_fcurves(blends_action))` (i.e. `include_all_slots=True`), matching `add_blends`.

- **`len()` on `all_fcurves()` generator breaks duplicate()/add_clone()** — `utils/curve.py:205` (safe)
  Why: `all_fcurves()` is now a generator; `index = len(all_fcurves(action))` raises `TypeError`. Reached via `add_clone()` → `duplicate()`, so clone creation crashes on first use.
  Fix: `fcurves = list(all_fcurves(action)); index = len(fcurves)`.

- **get_all_fcurves uses action.fcurves directly and dereferences shape_keys/animation_data unguarded** — `utils/curve.py:154-171` (risky)
  Why: Uses `trans_action.fcurves` and `obj.data.shape_keys.animation_data.action` directly; `.fcurves` is empty for layered actions, and `shape_keys`/`animation_data` can be `None` → AttributeError for non-armature objects.
  Fix: Use `blender_compat.iter_action_fcurves(...)` for both actions and `getattr`-chain guard `shape_keys`→`animation_data`→`action`.

- **amp_on_frame_change_post dereferences animation_data without None guard** — `utils/handlers.py:36-37` (safe)
  Why: `if active_obj and not active_obj.animation_data.action:` — `animation_data` is `None` for non-animated objects; fires on every playback-end loop with such an object active, spamming tracebacks.
  Fix: `if active_obj and (not active_obj.animation_data or not active_obj.animation_data.action): return`.

- **Hardcoded `bpy.data.scenes["Scene"]` in panel draw** — `ui/ui.py:98-141` (safe)
  Why: `amp_limits_interface()` reads/writes the literally-named scene at lines 98,104,113,120,135,141; renamed/absent scene → KeyError in `Panel.draw`, breaking the Timeline Scrub panel and targeting the wrong scene with multiple scenes.
  Fix: Replace every `bpy.data.scenes["Scene"]` with `bpy.context.scene`.

- **`unregister()` is a no-op; native headers not restored, custom header classes leak** — `ui/blender_ui.py:321-322` (safe)
  Why: `register()` swaps native GRAPH/DOPESHEET headers for custom ones; `unregister()` does `pass`, leaking the custom classes and leaving native headers removed until restart, with errors on re-enable.
  Fix: Implement `unregister()` to unregister the custom header classes and re-register the captured native `bl_graph_classes`/`bl_dope_classes`, each guarded with try/except.

- **select_or_transform_keyframes: UnboundLocalError on `fcurves` and unguarded active_object** — `anim_curves/anim_curves.py:771-810` (safe)
  Why: `fcurves` only assigned inside the animation_data check but iterated unconditionally at 796; with no animation and nothing selected → UnboundLocalError. `obj = context.active_object` dereferenced with no `None` guard and no `poll()`.
  Fix: Initialize `fcurves = []` before the check; add `if obj is None: return {'CANCELLED'}` and a `poll()` requiring an active object.

- **cleanup_flat_fcurves calls `.remove()` on a generator and never deletes from the action** — `anim_curves/anim_curves.py:212-220` (safe)
  Why: `get_active_fcurves_obj(obj)` is a generator; `fcurves.remove(fcurve)` raises AttributeError. The POSE/SELECTED path passes a throwaway list, so the F-Curve is never removed from the action ("Delete Unnecessary Keyframes" silently no-ops, not layered-action safe).
  Fix: At cleanup_action level materialize `fcurves = list(...)`, thread the owning `action` into `cleanup_flat_fcurves`, and delete via `utils.curve.remove_fcurve_from_action(action, fcurve)`.

- **Draw handler added without storing handle; remove() passes the function** — `anim_selection_sets/anim_selection_sets.py:1275,1286` (safe)
  Why: `register()` discards the handle from `draw_handler_add`; `unregister()` passes the *function* to `draw_handler_remove`, which raises and never removes the callback → disable errors and a permanently-firing leaked handler.
  Fix: Store `_draw_handle` at register; pass it (guarded by `None`) to `draw_handler_remove` at unregister.

- **unregister calls bpy.ops with invalid exec-context and after the class was unregistered** — `anim_selection_sets/anim_selection_sets.py:1283-1287` (safe)
  Why: `bpy.ops.anim.amp_modal_event_handler("CANCELLED")` passes an invalid execution-context enum, and the operator was already unregistered in the loop above → raises on disable (also unreachable behind the 1286 handle bug).
  Fix: Delete the invalid call; signal the modal to stop via a flag and remove the draw handler (stored handle) before the unregister_class loop.

- **Modal operator launched and scene property written during register()** — `anim_selection_sets/anim_selection_sets.py:1271-1277` (safe)
  Why: `register()` runs `bpy.ops.anim.amp_modal_event_handler('INVOKE_DEFAULT')` and writes `bpy.context.scene.amp_anim_set.display_gui`; during persistent enable at startup / `--background` the context is restricted and `scene` is `None`, aborting registration.
  Fix: Remove both from register; defer modal start via a guarded one-shot `bpy.app.timers` (skip when `bpy.app.background`); set `display_gui` via the property default.

- **Re-invoking the lattice leaks the SpaceGraphEditor draw handler and disables normalization** — `anim_lattice/anim_lattice.py:555-557,742-780` (safe)
  Why: `_is_running` is a class attribute; a second invoke's `cancel()` only removes its own (`None`) handle, so the original modal's handler leaks and `initial_use_normalization` is never restored (Blender does not call `cancel()` on a `{'CANCELLED'}` return).
  Fix: In `modal()` return `self.cancel(context)` instead of a bare `{'CANCELLED'}`; store the active instance at class level and cancel it directly from the toggle branch.

- **register() reads bpy.context.scene.mp_props at registration time** — `anim_flex_mopaths.py:1129-1130` (safe)
  Why: `if bpy.context.scene.mp_props.show_motion_paths:` — `scene` can be `None` at startup/background, raising AttributeError and aborting enable after classes are already registered.
  Fix: Guard `scene = getattr(bpy.context,'scene',None)` and the chain; add a `load_post` handler to sync the depsgraph handler when scenes actually load.

- **Property update callbacks run bpy.ops (mode_set/select_all/paths_calculate) and mutate selection+mode** — `anim_flex_mopaths.py:314-356` (safe)
  Why: `ensure_motion_paths` / `refresh_all_motion_paths` (wired to many props incl. color/thickness) run operators from `update=` callbacks; dragging a slider silently changes active object/selection/mode and can raise "context is incorrect" or corrupt undo.
  Fix: Have callbacks set a "needs refresh" flag and schedule one debounced `bpy.app.timers` job (mirroring the existing depsgraph pattern) that performs the work at a safe time.

- **Modal mixes REGISTER|UNDO with manual undo_push and live undo()/redo()** — `anim_sculpt.py:534,913,936-942` (risky)
  Why: Declares `{'REGISTER','UNDO'}`, pushes its own undo step per LMB, and runs `bpy.ops.ed.undo()/redo()` inside the modal while holding live keyframe/fcurve references → invalidated references / crash and a corrupted undo stack.
  Fix: Drop `UNDO` (push one step on finish) and remove the in-modal undo/redo calls, or re-fetch all references after they run.

- **draw_handler key 'SpaceView3D' collides between frame and text handlers, leaking handlers** — `autoKeying/utils.py:377-403,428-462` (safe)
  Why: The frame handler is stored in `draw_handler_dict['SpaceView3D']` and the text handler in `draw_handler_text`, but the OFF branch does `del draw_handler_dict['SpaceView3D']`, destroying the frame handler's bookkeeping; `unregister()` then can't remove it and it fires against an unregistered add-on.
  Fix: Manage the text handler solely via `draw_handler_text`; delete the `del draw_handler_dict['SpaceView3D']` lines so frame-handler bookkeeping is untouched.

- **get_delta uses context.active_object.animation_data unconditionally** — `anim_offset/support.py:174-199` (safe)
  Why: Called per selected object from `magnet()`, but computes NLA timing from `context.active_object` — `None`/no-animation_data → AttributeError in the depsgraph timer, and it uses the wrong object's NLA mapping for multi-select (wrong deltas / silent value corruption).
  Fix: Use the passed `obj`; `anim = getattr(obj,'animation_data',None)`; compute `nla_dif = 0` when `anim is None`.

- **isolate_character depsgraph handler and deferred timer never removed on unregister** — `anim_poser/anim_poser.py:567-576` (safe)
  Why: The `@persistent` `isolate_character_handler` is appended on enable but `unregister()` never removes it (nor the timer); disabling while isolate is on leaves an orphaned handler firing against a deleted Scene prop → error spam, recoverable only by restart.
  Fix: In `unregister()` remove the handler (membership-guarded), unregister the timer if registered, and reset the module guard flags.

- **Retimer re-scales shared/linked actions multiple times** — `anim_retimer/anim_retimer.py:66-72` (safe)
  Why: `execute()` iterates `selected_objects` and retimes each `obj.animation_data.action` with no dedupe; objects sharing one Action datablock get scaled `scale_factor^N`, silently corrupting timing.
  Fix: Collect unique Action datablocks into a `set()` and retime each once.

- **depsgraph_update_post handler and timer not removed on unregister** — `anim_looper/realtime_looper.py:190-198` (safe)
  Why: The persistent `anim_looper_update_handler` is appended when the toggle is on but `unregister()` only deletes the Scene prop and the class; disabling while active leaves the handler firing and silently mutating keyframes.
  Fix: Remove the handler in `unregister()` (membership-guarded), reset module globals, and guard the Scene-prop delete with `hasattr`.

- **update_keyposer_ui_list assigns undefined property item.action_ref** — `anim_experimental/anim_key_poser/anim_key_poser.py:40-42` (safe)
  Why: `AMP_PG_ActiveNLATrackItem` does not register `action_ref`; assigning it on a PropertyGroup instance raises AttributeError. This refresh routine is core to activating/refreshing the KeyPoser, so the first action-strip crashes it.
  Fix: Delete line 42 (`action_ref` is never read).

- **active_track_index update callback runs bpy.ops and mutates context (mode/area/active object)** — `anim_experimental/anim_key_poser/anim_key_poser.py:47-80,633` (risky)
  Why: A UIList row click fires the `update=` callback, which switches `areas[0].type`, runs `nla.tweakmode_enter/exit`, sets active object, and rebuilds the UIList's backing collection — an unsupported pattern prone to undo corruption / reentrancy / context errors.
  Fix: Have the callback only set the index; trigger tweak-mode + selection from an explicit operator or a deferred `bpy.app.timers` job; don't rebuild the collection inside the selection callback.

- **draw_markers_lock hardcodes bpy.data.scenes["Scene"]** — `markers_tools/markers.py:246-258` (safe)
  Why: References `bpy.data.scenes["Scene"].tool_settings` (lines 249,254-255) during panel/button draw (reachable via MarkersToolsButton at 336); renamed/absent scene → KeyError every redraw, breaking the UI.
  Fix: Use `context.scene.tool_settings`; also fix the arg order of the line-234 call to `draw_markers_lock(operations_row, context)`.

---

## Medium

- **Panels reuse private USERPREF_PT_animation_* classes; call draw_centered with foreign self** — `operators.py:240-241, 268-269, 295-296` (risky) — Wrap lookups in `getattr/hasattr` and fall back gracefully; verify the class names/signature still exist in 5.1.2.
- **deactivate_other_keymaps disables user keymaps with no confirmation/restore** — `operators.py:13-72` (risky) — Require confirmation, record deactivated `(km,kmi)` pairs for restore, scope the match narrowly, and report what was disabled.
- **to_dict/from_dict serialize ALL properties incl. transient runtime state** — `preferences.py:152-220` (safe) — Replace the blanket `bl_rna` iteration with an explicit allow-list; exclude `original_*`, operator/runtime flags, and `auto_save_path`.
- **from_dict triggers a cascade of heavy update callbacks during import** — `preferences.py:196-218` (risky) — Set a module-level "loading" guard the callbacks early-return on; run refreshes once after import.
- **Property `text_size` declared twice with different definitions** — `preferences.py:801-807 and 1191-1197` (risky) — Rename one (e.g. `rec_text_size`) and update references so each feature sizes independently.
- **Auto-save falls back to writing into the add-on install directory** — `preferences.py:2050-2051` (risky) — Default the fallback to `bpy.utils.user_resource('CONFIG')` (read-only extensions dir / wiped on update).
- **Forcing original_theme_captured=False before capture re-captures modified theme as 'original'** — `utils/general.py:1138,1214` (safe) — Remove the `original_theme_captured = False` line at 1214 (and 1138) so the capture-once guard preserves true originals.
- **save_userpref() from theme-reset path persists temporary theme edits to disk** — `utils/general.py:1175-1177` (risky) — Only save after the genuine original theme is restored and guard behind a verified-restore condition; avoid saving from draw/handler-adjacent contexts.
- **insert_keyframe uses [context.active_object] with no None guard** — `utils/general.py:803-810` (safe) — Filter `None` from the objects list and report a warning when empty.
- **draw_callback uses 'TRI_FAN' batch primitive** — `utils/general.py:1402-1408` (safe) — Use `TRIS` with explicit indices or `TRI_STRIP` (unsupported on Metal/Vulkan).
- **poll()/get_items() dereference context.area / space_data.dopesheet without guards** — `utils/general.py:1062-1063, 1078-1083` (safe) — `getattr(context.area,'type',None)` and check `space_data` + `hasattr(...,'dopesheet')`.
- **find_user_keyconfig raises KeyError when key/keymap name absent** — `utils/general.py:97-98` (safe) — Use `addon_keymaps.get(key)` and `keyconfigs.user.keymaps.get(km.name)` with `None` checks.
- **remove_clone/move_clone index/len() a generator; move_clone references undefined `key`** — `utils/curve.py:299-336` (safe) — Materialize `list(all_fcurves(action))`, qualify `utils.key.*`, rename the loop var; or remove these dead clone functions.
- **delete_keyframes removes keyframe_points while iterating the same collection** — `utils/curve.py:713-725` (safe) — Collect matching keyframes, remove in reverse array-index order, then `fcurve.update()`.
- **create_path computes Z from the X dict** — `utils/curve.py:124-127` (safe) — Test/eval the `z` dict: `if z.get(f) is None: points[n].co.z = z['curve'].evaluate(f)`.
- **`('DOPESHEET_EDITOR' or 'TIMELINE')` never matches TIMELINE** — `utils/curve.py:629, 656` (safe) — Use `in {'DOPESHEET_EDITOR','TIMELINE'}`.
- **`('rotation_euler' or 'delta_rotation_euler') in data_path` tests only one substring** — `utils/curve.py:1150` (safe) — `if 'rotation_euler' in data_path or 'delta_rotation_euler' in data_path:`.
- **deselect_all_keyframes_in_editors dereferences context.area; no try around select_all** — `utils/curve.py:648-657` (safe) — Early-return on `context.area is None` and wrap the DOPESHEET/TIMELINE `select_all` in try/except.
- **find_keyframes dereferences active_object/armature without None checks (POSE)** — `utils/curve.py:584-587` (safe) — Guard `active_object`; early-return when `armature is None`.
- **has_selected_keyframes can crash on null space_data or grease_pencil** — `utils/curve.py:664, 688-690` (safe) — Guard `space_data` and `context.grease_pencil` before access.
- **gather_fcurve_keyframes 'ACTION' dereferences active_object.animation_data.action unguarded** — `utils/curve.py:1382` (safe) — Resolve via `getattr` chain and return `[]` if `None` (mirror `gather_fcurves`).
- **valid_obj accesses context.area.type / space_data without None guards** — `utils/curve.py:350-362` (safe) — Guard `context.area`/`space_data` before `.type`/`.dopesheet`.
- **duplicate(selected_keys=True) passes a single FCurve to get_selected()** — `utils/curve.py:201-233` (risky) — Iterate the fcurve's selected `keyframe_points` instead of calling `get_selected` on one curve.
- **key_standard_properties calls scene.frame_set inside a keying helper** — `utils/curve.py:871-882` (risky) — Pass `frame` to `keyframe_insert` without `frame_set`, or batch the frame change once.
- **valid_fcurve reads bone.hide on a PoseBone** — `utils/curve.py:425` (risky) — Use `bone.bone.hide` (visibility lives on the underlying Bone).
- **unregister uses `except RuntimeError or AttributeError` and wraps the whole loop** — `utils/operators.py:163-168` (safe) — Per-class try/except with `except (RuntimeError, AttributeError)`.
- **`if key_i:` treats keyframe index 0 as 'no key found'** — `utils/key.py:206` (safe) — `if key_i is not None:`.
- **evaluate_amp_triggers calls bpy.ops from a property update callback** — `utils/api.py:12-18` (risky) — Defer via a one-shot timer and guard the operator's poll/availability with try/except.
- **get_icon() does `icon_name in custom_icons` without guarding None** — `utils/customIcons.py:89` (safe) — Add `custom_icons is not None` check (mirror `get_icon_id`).
- **Bare `except: pass` in register()/unregister() swallows all failures** — `utils/__init__.py:11-24` (safe) — Catch `Exception` and log, or let it propagate.
- **copy/move_grease_pencil_frame silently no-op when method is absent** — `utils/blender_compat.py:225-235` (risky) — Implement a real GPv3 fallback or raise/log instead of silently passing.
- **unregister() removes menu draw funcs without guard (ValueError)** — `ui/top_sections.py:616-617` (safe) — Wrap the two `.remove()` calls in try/except.
- **Writing prefs.active_section_index inside draw()** — `ui/top_sections.py:479-480, 517-518` (risky) — Clamp the index in the operators that change section count; in draw only read `min(index, len-1)`.
- **Custom GRAPH/DOPESHEET headers reimplement native headers** — `ui/blender_ui.py:244-263` (risky) — Prefer extending/appending to the native header instead of unregistering+replacing; re-validate against 5.1 bl_ui.
- **No poll() and crashes on missing animation data; dead `if True:`** — `anim_curves/anim_curves.py:671-690` (safe) — Add poll + `None` guards on `active_object`/`animation_data`/`action`; remove `if True:`.
- **move_clone subscripts a generator AND references undefined name 'key'** — `anim_curves/anim_curves.py:324-326` (safe) — (Within select_fcurves poll path) `return context.space_data is not None and context.space_data.type in {...}`.
- **share_keyframes POSE branch dereferences active_object without None guard** — `anim_curves/anim_curves.py:1196-1219` (safe) — Report+cancel when `obj is None` before `obj.type`, or add poll.
- **view_anim_curves_* call a polled operator from invoke without context/poll protection** — `anim_curves/anim_curves.py:1997-2132` (safe) — Give wrappers the same poll, or wrap the `bpy.ops` call in try/except.
- **Magic Clean-up deletes F-Curves/resets transforms with no confirmation; ALL scope hits every object** — `anim_curves/anim_curves.py:57-83` (risky) — Add `invoke_confirm` for ALL scope; make the POSE/ALL path call `apply_cleanup` for parity.
- **bpy.ops.ed.undo() from inside a running modal holding RNA references** — `anim_timewarper/anim_timewarper.py:741-754` (risky) — Rebuild internal state immediately after undo (incl. fcurve cache) and replace the hand-maintained undo counter.
- **unregister() never deletes Scene.timewarper_settings** — `anim_timewarper/anim_timewarper.py:1805-1817` (safe) — `if hasattr(bpy.types.Scene,'timewarper_settings'): del ...` in unregister.
- **No None-guard on context.active_object during modal keyframe update** — `anim_timewarper/anim_timewarper.py:777-779` (safe) — Guard `obj`/`animation_data`/`action` at the top of `update_keyframe_positions_proportionally` (and `gather_fcurve_keyframes`).
- **Shift+RightMouse cancel branch is unreachable** — `anim_timewarper/anim_timewarper.py:643-646` (risky) — Handle RMB PRESS vs RELEASE in separate branches.
- **Falsy guards on numeric props make easing vanish at percentage 0.0** — `anim_timewarper/anim_timewarper.py:382-402` (safe) — Use explicit `is None` checks; never `not <float prop>` when 0.0 is valid.
- **update_scope callback operates on stale WM operator records and unguarded context.area** — `anim_timewarper/anim_timewarper.py:1751-1759` (risky) — Guard `context.area`; signal the modal via a flag instead of mutating a stale operator record.
- **Draw handler captures execute-time Context instead of using bpy.context** — `anim_timewarper/anim_timewarper.py:604` (risky) — Register with no args; read `bpy.context` region/area/scene inside the callback.
- **Class-level _is_running/_handles can leak on file load; no @persistent reset** — `anim_timewarper/anim_timewarper.py:653-670` (risky) — Add a `load_post` handler that removes lingering handles and resets state; also remove handlers in unregister.
- **Anim-data precheck and scope source are inconsistent** — `anim_timewarper/anim_timewarper.py:587` (risky) — Read scope from a single source of truth (the scene property) in the precheck.
- **GPU 'TRI_FAN' (and unguarded None shader) in pinned-GUI draw** — `anim_selection_sets/anim_selection_sets.py:1208-1211, 1099-1118` (risky) — Replace `TRI_FAN` quads with `TRIS`/`TRI_STRIP`; `if shader is None: return`.
- **AnimSetMoveElement.invoke indexes preset.sets without bounds check** — `anim_selection_sets/anim_selection_sets.py:948-957` (safe) — Guard `0 <= set_index < len(preset.sets)`.
- **AnimSetSelect issues mode_set/select_all with no failure handling** — `anim_selection_sets/anim_selection_sets.py:266, 276, 323-325` (risky) — Wrap mode changes in try/except and validate context; add `'UNDO'` to bl_options if desired.
- **Global always-on event modal self-cancels on any ESC** — `anim_selection_sets/anim_selection_sets.py:1225-1230` (risky) — Return PASS_THROUGH on ESC or re-arm when `display_gui` is on; prefer a real SpaceView3D modal.
- **poll() dereferences context.area without a None guard** — `anim_lattice/anim_lattice.py:217-219` (safe) — `return context.area is not None and context.area.type == 'GRAPH_EDITOR'`.
- **GPU 'TRI_FAN'/'LINE_LOOP' primitives unsupported on Vulkan/Metal** — `anim_lattice/anim_lattice.py:101,346,840,1346,1375` (risky) — Convert fills to `TRIS`/`TRI_STRIP` and the outline to `LINE_STRIP`.
- **Captured F-Curve/keyframe-index references can go stale during the modal** — `anim_lattice/anim_lattice.py:321-334,377-388,1031-1034,1181-1198` (risky) — Re-validate fcurve liveness/index range before indexing, or block edits; abort gracefully on change.
- **Deferred timer not cancelled on unregister and reads bpy.context.scene** — `anim_flex_mopaths.py:478-487,423-476,1133-1139` (safe) — `bpy.app.timers.unregister(...)` (guarded) in unregister; bail when scene/mp_props missing.
- **Saved show_motion_paths=True does not re-arm the depsgraph handler on load** — `anim_flex_mopaths.py:547-552,1124-1131` (safe) — Add a `load_post` handler that calls `update_handler_registration(scene.mp_props.show_motion_paths)`.
- **Auto-update clears ALL motion paths when active object/bone changes** — `anim_mopaths.py:175-216` (risky) — Pass `only_selected=True` to `paths_clear`, or restrict to the add-on's tracked elements.
- **Pending motion-path timers not cancelled on unregister** — `anim_mopaths.py:218-241, 556-577` (safe) — try/except `bpy.app.timers.unregister(...)` for both callbacks and reset the scheduling flags.
- **poll() dereferences context.area without a None check** — `anim_sculpt.py:602-604` (safe) — `return context.area is not None and context.area.type == 'GRAPH_EDITOR'`.
- **O(n²) keyframe index lookup per smoothing stroke** — `anim_sculpt.py:430-432` (safe) — Pass the index through from `anim_sculpt_brush`, or build an id→index map once per stroke.
- **space_data.use_normalization accessed without verifying the Graph Editor space** — `anim_sculpt.py:954-956, 1022-1026` (safe) — Guard `hasattr(sd,'use_normalization')` in invoke/cancel; store the captured space.
- **register() wraps the whole class loop in one bare try/except** — `anim_stepper/anim_stepper.py:245-250` (safe) — Move try/except inside the loop, narrow to `except Exception as e`, and log the class+error.
- **unregister() loop in one try/except leaves classes registered if one fails** — `anim_stepper/anim_stepper.py:258-262` (risky) — Wrap each `unregister_class` individually.
- **all_fcurves() generator exhausted; redundant/dead ARMATURE re-loop** — `anim_stepper/anim_stepper.py:80-92,152-165` (risky) — Materialize `fcurves = list(...)`, drop the dead ARMATURE re-loop, check `if fcurves:`.
- **remove_draw_handler picks the remove method from the current area.type** — `anim_scrub/anim_scrub.py:384-400` (risky) — Record the space type used in `add_draw_handler` and reuse it on removal.
- **Operator properties declared with `=` instead of `:` annotation** — `anim_scrub/anim_scrub.py:240-242` (safe) — Delete the unused fields or convert to annotations.
- **Operator __init__ sets global prefs.is_scrubbing = True on instantiation** — `anim_scrub/anim_scrub.py:244-274` (risky) — Move `is_scrubbing = True` into `invoke()` where `finish()` guarantees reset.
- **context.area.tag_redraw() in RemoveSteppedModifier.execute can crash when area is None** — `anim_scrub/anim_scrub.py:139-148` (safe) — `if context.area: context.area.tag_redraw()`.
- **found_frames set per-iteration; can be left False/undefined** — `anim_stepper/camera_stepper.py:320-336` (risky) — Init `found_frames = False` before the loop and only ever set it True; don't put the False branch in the loop.
- **bake_and_mark_actions returns CANCELLED for the whole batch on first object lacking animation_data** — `anim_stepper/camera_stepper.py:302-306` (risky) — Use `continue` with a per-object warning.
- **AMP_OT_Disable accesses obj.animation_data.action without checking None** — `anim_stepper/camera_stepper.py:459` (safe) — `if obj.animation_data and obj.animation_data.action is not None:`.
- **Bone/frame-range operators index TIMELINE_object_list without bounds checks (incl. poll)** — `anim_stepper/camera_stepper.py:529-619` (safe) — Add a shared `0 <= index < len(list)` guard in each poll/execute.
- **stick_bone_poses_to_camera forces active object and POSE/OBJECT mode without restoring** — `anim_stepper/camera_stepper.py:219-292` (risky) — Snapshot/restore active object and mode; wrap mode_set in try/except.
- **poll() crashes when context.area is None and always returns truthy** — `anim_offset/support.py:378-389` (safe) — Remove/guard the unused `context.area.type`; `return bool(context.selected_objects)`.
- **Always-true condition `area.type != 'VIEW_3D' or area.type != 'NLA_EDITOR'`** — `anim_offset/ui.py:63` (risky) — `if context.area.type not in {'VIEW_3D','NLA_EDITOR'}:`.
- **bpy.ops.anim.amp_deactivate_anim_offset referenced without ()** — `autoKeying/ui.py:687` (risky) — Call it `()` (guarded) or remove the dead line and rely on the msgbus handler.
- **Reference-curve skip guards check group names that never match** — `anim_offset/support.py:138, 305` (risky) — Use a single canonical group-name constant (compare against `'Magnet'`), or drop the guards.
- **wm.redraw_timer(DRAW_WIN_SWAP) invoked from operator execute()** — `anim_offset/ops.py:119, 165` (risky) — Rely on `area.tag_redraw()` and remove `redraw_timer`.
- **Mask modal writes scene frame range to -100 with no crash-safe restore** — `anim_offset/ops.py:322-328` (risky) — Restore stored ranges in a CANCELLED/finally path; avoid clobbering all four range values.
- **isolate_character handler driven from a property update / depsgraph handler** — `anim_poser/anim_poser.py:45-59 and 94-101` (risky) — Move heavy mutation into the deferred timer; wrap `bpy.ops` with `temp_override`/try-except.
- **except block references `props` which may be unbound** — `anim_poser/anim_poser.py:86-88` (safe) — Init `props = None` before the try; guard `if props is not None:` in except.
- **enable_isolate_character references undefined `armature`; ignores enter_pose_mode** — `anim_poser/anim_poser.py:285-298` (safe) — Track `active_armature = None`; guard the tail on `enter_pose_mode`.
- **bpy.ops.graph.euler_filter() called from a VIEW_3D operator without Graph Editor context** — `anim_euler/anim_euler.py:479` (safe) — Use the in-file `apply_euler_filter_to_action`, or wrap in try/except RuntimeError.
- **Euler Filter operator performs a no-op round-trip** — `anim_euler/anim_euler.py:107-118 and 135-146` (risky) — Implement real continuity-based unwrapping, or disable the operator.
- **SNAP cleanup uses one stale original_first_frame for all F-Curves** — `anim_retimer/anim_retimer.py:97 and 126-142` (safe) — Capture each fcurve's pre-scale first frame in a dict and use the matching value in the SNAP loop.
- **Shifter mutates scene.frame_start/frame_end on every run with no opt-out** — `anim_shifter/anim_shifter.py:259-263` (risky) — Make range adjustment an opt-in BoolProperty; clamp `start<=end`, `start>=0`.
- **Inserted keyframes only get fcurve.update() for editable_fcurves** — `anim_shifter/anim_shifter.py:235-254` (safe) — Track all modified fcurves in a set and `update()` each.
- **toggle_silhouette property update runs bpy.ops and isolation logic** — `anim_poser/anim_silhouette.py:71-141` (risky) — Route the toggle through the operator (set a flag/invoke) or guard ops with `temp_override`/try-except.
- **No poll() and no None guard on context.active_object** — `anim_baker/anim_baker.py:147-153` (safe) — Add `poll()` requiring active object and a defensive `None` guard in execute.
- **clear_nla() removes tracks while iterating the live collection** — `anim_baker/anim_baker.py:371-379` (safe) — `for track in list(tracks): tracks.remove(track)`.
- **Object-level muted-constraint keyframe uses self.range[0] instead of frame_range[0]** — `anim_baker/anim_baker.py:353` (risky) — `frame=frame_range[0]` to match the pose-bone branch.
- **Inverted/incorrect area-type early return in deferred update** — `anim_looper/realtime_looper.py:126` (risky) — Drive the decision off the animation editor where fcurves live, not negated VIEW_3D; stop relying on `bpy.context.area` in a timer.
- **context.area dereferenced without None guard** — `anim_nudger/anim_nudger.py:46-47` (safe) — Guard `area = context.area`; cancel with INFO when `None` or not GRAPH/DOPESHEET.
- **bpy.ops.graph.select_all called inside execute without Graph Editor context** — `anim_slicer/anim_slicer.py:321-322` (risky) — Use a context check/temp_override, or deselect via `kp.select_control_point = False`.
- **register/unregister except block calls nonexistent utils.dutils.dprint** — `anim_experimental/anim_key_poser/anim_key_poser.py:872-888` (safe) — Use `utils.dprint`; register classes individually.
- **Baker register/unregister except block calls nonexistent utils.dutils.dprint** — `anim_experimental/anim_key_poser/anim_key_poser_baker.py:127-142` (safe) — Replace `utils.dutils.dprint` with `utils.dprint`.
- **Pan/zoom sensitivity of 1e-6 truncated to 0** — `anim_experimental/zoom_pan.py:33-52` (risky) — Use realistic factors and accumulate sub-pixel movement instead of int-truncating.
- **Draw handler added only to SpaceGraphEditor although operator runs in Dope Sheet** — `anim_experimental/anim_key_poser/anim_key_poser_time_warper.py:136-165` (risky) — Add the handler to the correct space class per `context.area.type`; remove from the same class.
- **Time-warp marker init/update assume context.active_object is not None** — `anim_experimental/anim_key_poser/anim_key_poser_time_warper.py:243, 256` (safe) — Guard `obj`/`animation_data`; cancel/report if missing.
- **key_start_and_end_frames selects ALL pose bones and force-exits to Object mode** — `anim_experimental/anim_key_poser/anim_key_poser.py:269-289` (risky) — Snapshot/restore mode, per-bone selection, and current frame; don't force OBJECT mode.
- **StartAnimKeyPoser.execute ignores activate_keyposer's CANCELLED return** — `anim_experimental/anim_key_poser/anim_key_poser.py:364-390` (safe) — Capture the return and propagate `{'CANCELLED'}` before refreshing the list.
- **tweak_mode_nla_strip hijacks screen.areas[0].type and may not restore on error** — `anim_experimental/anim_key_poser/anim_key_poser.py:144-163` (risky) — Wrap the override in try/finally; prefer an existing NLA editor over `areas[0]`.
- **AMP_PT_MarkersToolsOptions references unregistered scene prop; wrong draw_markers_lock args** — `markers_tools/markers.py:218, 234` (risky) — Remove the orphaned panel/helpers, or register `markers_tools_props` and fix the call to `draw_markers_lock(operations_row, context)`.
- **inser_makers_on_keyframes dereferences active_object.animation_data.action unguarded** — `markers_tools/markers.py:153-163` (safe) — Guard obj/animation_data/action; iterate fcurves only when an action exists.
- **Dopesheet zoom keymaps registered under the wrong keymap name** — `keymaps/key_graph_editor_zoom_curves.py:54-63, 74-83` (safe) — Change `"name": "Graph Editor"` to `"Dopesheet"` for the two DOPESHEET_EDITOR entries.
- **Duplicate dict key "0.25.10318" silently discards the first changelog entry** — `changelog.py:82 and 111` (safe) — Give the two blocks distinct version keys (restores the archive split count).

---

## Low

- **unregister() deletes Scene.timeline_scrub_settings that register() never creates** — `properties.py:165-173` (safe) — Delete the stray `del Scene.timeline_scrub_settings`; the PropertyGroup is dead.
- **Unused header snapshot references undefined names; never imported** — `dope_header_51.py:1-21` (safe) — Delete the file (or wire it up with imports and version-gated registration).
- **Unused graph-editor header snapshot references undefined names; never imported** — `graph_header_51.py:1-69` (safe) — Delete the file (or wire it up properly).
- **anim_overlap imported but never registered; duplicate/unused imports** — `__init__.py:101, 140` (safe) — Remove the import, drop the duplicate `persistent`, prune unused imports.
- **anim_experimental.unregister() called unconditionally** — `__init__.py:163-164, 184-185` (safe) — Gate the unregister on `prefs.experimental`; replace bare excepts in anim_experimental.
- **unregister() unconditionally unregisters all keymaps** — `register_keymaps.py:300-321` (safe) — Drive unregister through the same per-flag toggle helpers; broaden the except.
- **CaptureKeyInput uses context.area without a None guard** — `operators.py:107, 145, 153, 164` (safe) — Add `poll()` requiring `context.area` and guard each `header_text_set`.
- **register() reads/writes add-on preferences during registration with no guard** — `preferences.py:2085-2090` (safe) — Wrap prefs access in try/except / `in addons` check; set the default lazily.
- **register loop swallows all ValueErrors from register_class** — `preferences.py:2079-2083` (safe) — Skip only the already-registered case, or log the exception.
- **validate_auto_save_path mutates its own property inside its update callback** — `preferences.py:67-70` (safe) — Normalize the `.json` extension at point of use, not in the update callback.
- **set_bar_color (dead): wrong arity to capture_original_theme_colors; shadows _was_save_preferences_true global** — `utils/general.py:1141, 1153-1177` (safe) — Drop the arg at 1141; add `global _was_save_preferences_true` to set_bar_color.
- **keyframe_curves: identical if/else branches, unused force_insert, trailing pass** — `utils/general.py:817-840` (safe) — Collapse to one insert block; remove the redundant branch and trailing `pass`.
- **get_all_actions: `if transform or shape_keys` always True, else unreachable** — `utils/general.py:936-951` (safe) — Test the action values: `if trans_action or sk_action:`.
- **Large blocks of commented-out legacy code retained** — `utils/general.py:115-155, 172-187, 650-688, 1094-1123, 1315-1338` (safe) — Delete the commented-out duplicates.
- **find_owner is O(objects × fcurves), called per-FCurve** — `utils/curve.py:1117-1143` (safe) — Cache the action→owner/fcurve→owner mapping or pass the owning object down.
- **get_slope uses squared coordinates and can divide by zero** — `utils/curve.py:189` (risky) — Use linear differences `(y1-y0)/(x1-x0)` and guard zero denominator.
- **Large commented-out keyframe_targets block** — `utils/curve.py:750-783` (safe) — Remove the commented blocks.
- **Timer and frame handler read addons[base_package] with no guard** — `utils/handlers.py:13-15, 27` (safe) — Use `.get(base_package)` and return early if `None`; wrap timer bodies in try/except.
- **stop_playback timer can be registered repeatedly during a playback loop** — `utils/handlers.py:45-51` (risky) — Guard with `bpy.app.timers.is_registered(stop_playback)` before registering.
- **iter_grease_pencil_layers has two identical branches** — `utils/blender_compat.py:189-197` (safe) — Collapse to a single body.
- **GRAPH_HT_header and GRAPH_MT_editor_menus defined but never registered** — `ui/ui.py:840-914` (safe) — Delete the dead classes and the unused `dopesheet_filter` import.
- **Unused imports (gpu and many button/operator symbols)** — `ui/ui.py:8, 10-19` (safe) — Remove the unused imports.
- **custom_icons preview collection created but never used** — `ui/ui.py:935-947` (safe) — Remove the creation/removal, or guard with `'custom_icons' in globals()`.
- **Unused _get_animated_id staticmethod with unguarded context access** — `ui/side_panles_ui.py:13-24` (safe) — Delete the unused method (or guard context).
- **_get_animated_id dereferences context.object.data without None guard** — `ui/blender_ui.py:231-241` (safe) — `ob = context.object; if ob is None: return None`.
- **init_sections_and_buttons() called twice at startup** — `ui/top_sections.py:166 / 605` (safe) — Call it in exactly one place.
- **delete_unchanged_keyframes removes points without fcurve.update()** — `anim_curves/anim_curves.py:193-210` (safe) — Call `fcurve.update()` after the removal loop.
- **insert_keyframe modal can leave a stray timer if _timer_started is False on TIMER** — `anim_curves/anim_curves.py:585-605` (safe) — Add a `cancel()` that removes the timer; remove the timer on any terminal/early path.
- **Large commented-out duplicate AMP_OT_FrameEditors block** — `anim_curves/anim_curves.py:1950-1987` (safe) — Delete the commented block.
- **unregister() removes keymaps that register() never creates** — `anim_timewarper/anim_timewarper.py:1811-1814` (safe) — Remove the no-op `addon_keymaps` loop or actually register a keymap.
- **Unused get_pin_at_position plus duplicated retiming loops and redundant guards** — `anim_timewarper/anim_timewarper.py:1259-1266` (safe) — Delete dead helper/guard; factor the easing-remap math into one helper.
- **Filled GPU batches drawn with alpha but blending never enabled** — `anim_timewarper/anim_timewarper.py:228-245` (safe) — Wrap draws in `gpu.state.blend_set('ALPHA')` … `'NONE'`.
- **Unused helpers get_unique_set_name and view3d_event_handler** — `anim_selection_sets/anim_selection_sets.py:30-45, 1238-1241` (safe) — Remove both functions.
- **AMP_PT_AnimLatticeOptions defined twice with the same bl_idname** — `anim_lattice/anim_lattice.py:1215-1250` (safe) — Delete the nested copy inside the operator.
- **get_nla_strip_offset imported but only referenced in commented code** — `anim_lattice/anim_lattice.py:9, 303, 310` (safe) — Restore the NLA offset logic or remove the dead import/branches.
- **Redundant mid-file imports** — `anim_mopaths.py:367-368` (safe) — Remove the duplicate `import bpy` / `EnumProperty`.
- **Panel class/bl_idname mismatch** — `anim_mopaths.py:460-462` (risky) — Rename `bl_idname` to match the class (and update references).
- **Deferred realtime handler has no except around scene-attr access** — `anim_mopaths.py:247-313` (safe) — Wrap the body in try/except or guard `getattr(scene,'amp_timeline_tools',None)`.
- **Unused draw_box_on_cursor/draw_box_on_screen use TRI_FAN** — `anim_sculpt.py:23-104` (safe) — Remove the two unused functions (or rebuild as `TRIS`).
- **Dead duplicated smooth function, unreachable SMOOTH_MACRO branch, commented calculate_delta** — `anim_sculpt.py:366-408, 677-680, 701-707` (safe) — Delete the dead duplicate, the SMOOTH_MACRO branch, and the commented `calculate_delta`.
- **add_stepped_modifier_to_fcurve can create duplicate STEPPED modifiers; writes scene state in loop** — `anim_stepper/anim_stepper.py:94-115` (risky) — Match by type/break on first match; write the scene prop once after the loop.
- **apply_frame_limits reads action.use_cyclic without getattr guard** — `anim_scrub/anim_scrub.py:146` (safe) — Use `getattr(action,'use_cyclic',False)`.
- **unregister() unregisters TIMELINE_BakeToCameraProperties twice** — `anim_stepper/camera_stepper.py:998-1004` (safe) — Remove the explicit standalone unregister_class call.
- **Dead/duplicated copy/paste_relative_matrix block and unused frame-range functions** — `anim_stepper/camera_stepper.py:68-93` (risky) — Delete the commented block and unused functions/scene props (verify no external refs).
- **Frame-range expansion ignores frame_start; uses end_range+1 unbounded** — `anim_stepper/camera_stepper.py:320-330` (risky) — Clamp start to `max(scene.frame_start, start_range)`; validate `start_range <= end_range`.
- **mask_in_use may be undefined (NameError) in draw_anim_offset_mask** — `anim_offset/ui.py:281-286` (safe) — Initialize `mask_in_use = False` before the `if`.
- **Unguarded context.area / bpy.context.screen access in execute()** — `anim_offset/ops.py:117, 162` (safe) — Guard `if context.area:` and `screen = bpy.context.screen; if screen:`.
- **Commented-out AMP_OT_modal_test class** — `anim_offset/ops.py:41-86` (safe) — Delete the commented block.
- **Old commented draw_frame implementation left in file** — `autoKeying/utils.py:38-155` (safe) — Remove the commented legacy `draw_frame` block.
- **AMP_OT_Autokeying.poll contains tautological dead logic** — `autoKeying/ui.py:675-679` (safe) — Simplify to `return True` (or a real poll).
- **get_panel_dimensions indexes UI region list assuming it exists** — `autoKeying/utils.py:27` (safe) — `ui = next((r.width for r in area.regions if r.type=='UI'), 0)`.
- **Superseded enable/disable_isolate_character_ and find_layer_collection are dead** — `anim_poser/anim_poser.py:107-225` (safe) — Delete the unused `_`-suffixed functions and `find_layer_collection`.
- **context.area.tag_redraw() without None guard** — `anim_poser/anim_poser.py:503` (safe) — `if context.area: context.area.tag_redraw()`.
- **frame_set to frame_start during retime is never restored** — `anim_retimer/anim_retimer.py:86` (safe) — Capture/restore `frame_current`, or drop the `frame_set`.
- **Unused helper methods collect_material_fcurves/insert_hold_keyframe/shift_keyframes_and_copy_value** — `anim_shifter/anim_shifter.py:80-116` (safe) — Remove the unused methods.
- **AMP_PT_AnimSilhouettePanel defined but commented out of classes** — `anim_poser/anim_silhouette.py:408-412` (safe) — Register or delete the unused panel class.
- **_last_copied_values keyed by FCurve objects is never cleared** — `anim_looper/realtime_looper.py:6, 73-74, 88-102` (safe) — Clear on toggle-off, in unregister, and from a `load_post` handler; consider a stable key.
- **Leftover debug print of entire original_data dict** — `anim_baker/anim_baker.py:165` (safe) — Remove the print (and the store/restore prints).
- **Except branch calls nonexistent utils.dutils.dprint** — `anim_looper/anim_looper.py:337-338, 345-346` (safe) — Use `utils.dprint`; reference the failing class; avoid bare except.
- **Except branch calls nonexistent utils.dutils.dprint** — `anim_keyframer/anim_keyframer.py:230-231, 239-240` (safe) — Replace with `utils.dprint`; avoid bare except.
- **AnimNudger_PT_Panel defined but excluded from classes** — `anim_nudger/anim_nudger.py:361-396` (safe) — Register or remove the panel.
- **Entire anim_overlap module disabled; no-op circular physics bake** — `anim_overlap/anim_overlap.py:1-160` (safe) — Remove the module or finish it (independent sim source; key per rotation_mode).
- **Unregistered duplicate baker with multiple fatal bugs** — `anim_baker/anim_baker_smart_WIP.py:282-287, 259, 272, 510` (safe) — Delete the WIP file (generator/Vector/layered-action issues).
- **Unregistered duplicate baker using direct action.fcurves access** — `anim_baker/anim_baker_WIP.py:229, 510, 7` (safe) — Delete the file, or route fcurve access through the compat helpers.
- **Filename pattern replaces a malformed token '{timestamp)'** — `anim_blast/anim_blast.py:34` (safe) — Remove line 34.
- **zoom_pan module is never imported or registered** — `anim_experimental/zoom_pan.py:100-113` (risky) — Remove the file, or import+register it and make the keymap removal reversible.
- **update_keyframe_position min_frame/max_frame never updated; scene-range expansion dead** — `anim_experimental/anim_key_poser/anim_key_poser_time_warper.py:255-309` (safe) — Remove the dead min/max block or compute min/max from moved markers.
- **Unused import draw_circle_2d** — `anim_experimental/anim_key_poser/anim_key_poser_time_warper.py:5` (safe) — Remove the unused import.
- **start_keyposer dereferences None animation_data (dead code)** — `anim_experimental/anim_key_poser/anim_key_poser.py:8-13` (safe) — Remove the unused function or guard `if anim_data and not anim_data.use_nla:`.
- **Unused update callbacks and keyframe helper** — `anim_experimental/anim_key_poser/anim_key_poser.py:83-128, 308-336` (safe) — Remove the unused functions or wire them up.
- **Pointless unary plus on len()** — `anim_experimental/anim_key_poser/anim_key_poser.py:563` (safe) — Remove the unary `+`; consider `<=` for the minimum check.
- **keymaps.py keymap_config is unused dead code with incompatible schema** — `keymaps/keymaps.py:1-37` (safe) — Delete the file (or rewrite to the keymaps_utils schema).
- **Unused import get_icon** — `changelog.py:489` (safe) — Remove `get_icon` from the import.
