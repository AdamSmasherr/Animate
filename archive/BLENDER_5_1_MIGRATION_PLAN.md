# AniMatePro Blender 5.1 Migration Plan

Target: make `AMP_AniMatePro` install, register, and work on Blender 5.1 without silently losing support for Blender 4.x unless a maintainer explicitly decides to drop it.

This plan is written as a staged backlog for AI coding agents. Do not try to migrate the whole add-on in one pass. Each stage has a small goal, files to inspect/edit, and a verification gate.

## How To Use This Plan

Every agent should start here, even if they were only assigned one later stage.

1. Inspect the current worktree before editing:
   - `git status --short`
   - `rg -n "GPencil|GPENCIL|gpencil|action\\.fcurves|strip\\.action\\.fcurves|action\\.groups|\\.fcurves\\.new|\\.fcurves\\.remove" AMP_AniMatePro`
   - check `tools/` for existing smoke/probe scripts and previous test output.
2. Read the stage you were assigned and all earlier stage verification gates. If an earlier stage is already implemented, verify it instead of redoing it.
3. Keep changes scoped to the assigned stage. If you discover a later-stage bug, record it in the migration status/checklist instead of mixing it into the current patch.
4. After each stage, update a migration status file, recommended path: `tools/MIGRATION_STATUS.md`. Record:
   - Blender version/build tested;
   - exact command(s) run;
   - pass/fail result;
   - remaining known failures;
   - files changed.
5. Do not update `bl_info["blender"]`, `blender_manifest.toml`, or package metadata to claim Blender 5.1 support until Stage 10.
6. Prefer exact local Blender 5.1 runtime probes over assumptions from docs. Online `current` docs can drift after Blender 5.1.
7. Treat line numbers in this plan as orientation only. Before editing, use `rg` on the current tree because previous agents may already have moved code.

## Sources Checked

- Blender current Python API: `bpy.types.GPencilLayer` is gone/404, while `bpy.types.GreasePencilLayer` and `bpy.types.GreasePencilFrame` exist.
- Blender current Python API: `Action.layers`, `ActionChannelbag.fcurves/groups`, and `AnimData.action_slot/action_suitable_slots` are the current animation model.
- Blender 4.4 Python API release notes: `Action.fcurves`, `Action.groups`, and related members were marked as backward-compatible legacy API.
- Blender 5.0 Python API release notes: the legacy Action API was removed; migration helpers such as `bpy_extras.anim_utils.action_ensure_channelbag_for_slot()` and channelbag `fcurves.ensure()` were added.
- Blender current source UI scripts: `scripts/startup/bl_ui/space_dopesheet.py` and `space_graph.py` include newer action-slot and editor-header controls than the local override copies.

Useful links:

- https://docs.blender.org/api/current/bpy.types.GreasePencilLayer.html
- https://docs.blender.org/api/current/bpy.types.GreasePencilFrame.html
- https://docs.blender.org/api/current/bpy.types.Action.html
- https://docs.blender.org/api/current/bpy.types.ActionChannelbag.html
- https://docs.blender.org/api/current/bpy.types.ActionChannelbagFCurves.html
- https://docs.blender.org/api/current/bpy.types.AnimData.html
- https://developer.blender.org/docs/release_notes/4.4/python_api/
- https://developer.blender.org/docs/release_notes/5.0/python_api/
- https://developer.blender.org/docs/release_notes/5.1/python_api/
- https://projects.blender.org/blender/blender/raw/branch/main/scripts/startup/bl_ui/space_dopesheet.py
- https://projects.blender.org/blender/blender/raw/branch/main/scripts/startup/bl_ui/space_graph.py

## Current Risk Map

### Blocks Installation

- `AMP_AniMatePro/utils/curve.py:1308` annotates `scene_gpencil_frames()` with `bpy.types.GPencilLayer` and `bpy.types.GPencilFrame`. Python evaluates those annotations at import time, so Blender 5.1 fails before registration with: `'module' object has no attribute 'GPencilLayer'`.
- Old object type checks use `"GPENCIL"` in `utils/curve.py`, `utils/operators.py`, `ui/blender_ui.py`, and `ui/top_buttons_definitions.py`. Current object type is `"GREASEPENCIL"` for Grease Pencil v3.

### Likely Runtime Breaks After Import Is Fixed

- Direct legacy Action API remains:
  - `utils/curve.py`: `action.fcurves.new`, `action.groups`, `action.fcurves.remove`, `yield from action.fcurves`, `yield from obj.fcurves`.
  - `anim_baker/anim_baker.py`: `strip.action.fcurves`.
  - `anim_shifter/anim_shifter.py`: material and node-tree `action.fcurves`.
  - WIP/experimental files: `anim_baker_*_WIP.py`, `anim_experimental/anim_key_poser/*`.
- `utils/curve.scene_fcurves()` returns a mixed stream of F-Curves and Grease Pencil frames. `gather_keyframes("SCENE")` then does `for kf in fcu.keyframe_points`, which cannot work for Grease Pencil frames.
- `anim_shifter/anim_shifter.py` has Grease Pencil frame-shifting helpers, but `execute()` never calls `shift_gpencil_keyframes()`. The old GP frame path is effectively dead code and needs a proper typed path.
- Local UI header overrides in `ui/blender_ui.py` unregister Blender's native `GRAPH_HT_header` / `DOPESHEET_HT_header` and register copied versions. These copies are behind Blender 5.1 UI, especially around Action slots, `context.active_action`, `show_only_slot_of_active_object`, and current editor buttons.
- Keymap code disables default Blender keymap items and registers global replacements. This must be re-validated against Blender 5.1 default keymaps.
- Draw handlers in `autoKeying/utils.py` use `eval()` to call `bpy.types.Space*.draw_handler_add/remove`. This is not a 5.1 API break by itself, but it is fragile and should be cleaned while testing handlers.
- Several modules rely on `context.area`, `context.space_data`, `context.visible_fcurves`, `context.editable_fcurves`, or editor-specific operators. These should be tested inside the correct editor contexts, not only via background import tests.

## Stage 0 - Baseline, Branch, and Test Harness

Goal: create a reproducible way for later agents to prove each small change.

Dependency: none. This stage should happen before code migration.

Files to inspect:

- `AMP_AniMatePro/__init__.py`
- `AMP_AniMatePro/blender_manifest.toml`
- every module listed in `addon_modules`
- existing files in `tools/`

Tasks:

1. Create a clean working branch/copy before code edits.
2. Record exact Blender target versions: minimum legacy version to keep, and Blender 5.1 build tested.
3. Make sure this plan is available inside the repository root for later agents. If it was moved outside the repo, copy the latest version back into the repo before continuing.
4. Add or update `tools/MIGRATION_STATUS.md`.
5. Add a local `tools/` or `dev/` test script, for example `tools/blender_smoke_test.py`, that can be run by Blender:
   - append the workspace parent to `sys.path`;
   - import `AMP_AniMatePro`;
   - call `register()`;
   - call `unregister()`;
   - print a clear success/failure summary.
6. Add a second smoke script that creates:
   - one object with transform keyframes;
   - one armature with a selected pose bone and pose-bone keyframes;
   - one material/node-tree animated property;
   - one shape-key animated property;
   - one Grease Pencil object with two layers and several frames;
   - optionally one NLA strip using an action.
7. Run syntax-only verification outside Blender:
   - `python -m compileall -q AMP_AniMatePro`

Verification gate:

- Blender 5.1 can run the smoke script and report the current install failure before edits.
- The failure is captured as the baseline issue, not guessed.
- No functional code is changed in this stage.
- `tools/MIGRATION_STATUS.md` exists and records the baseline result.

## Stage 1 - Make the Add-on Importable on Blender 5.1

Goal: fix import-time crashes only. Do not migrate behavior yet.

Dependency: Stage 0 baseline exists.

Primary files:

- `AMP_AniMatePro/utils/curve.py`
- any file found by `rg -n "GPencil|GPENCIL|gpencil|GreasePencil|GREASEPENCIL" AMP_AniMatePro`

Tasks:

1. Add `from __future__ import annotations` to Python files that use `bpy.types.*` in annotations, or convert those annotations to strings / `Any`.
   - If added, it must be the first statement after the module docstring and before normal imports.
2. Replace the invalid runtime annotation:
   - old: `Tuple[bpy.types.Object, bpy.types.GPencilLayer, bpy.types.GPencilFrame]`
   - safe temporary form: `Iterable[Tuple[bpy.types.Object, Any, Any]]`
3. Add small compatibility helpers instead of scattering string checks:
   - `is_grease_pencil_object(obj) -> bool`
   - should accept `"GREASEPENCIL"` for Blender 5.1;
   - may accept `"GPENCIL"` only if legacy support is retained.
   - if Stage 2 compatibility module already exists, put the helper there; otherwise keep it local and move it during Stage 2.
4. Update old object type checks from `"GPENCIL"` to the helper. Do not yet rewrite frame movement logic.
5. Update `bl_info["blender"]` and `blender_manifest.toml` only after the add-on truly supports 5.1. At this stage, keep metadata conservative or add a comment in the plan, not a false compatibility claim.

Verification gate:

- `python -m compileall -q AMP_AniMatePro`
- Blender 5.1 import smoke test reaches `register()` instead of failing on `GPencilLayer`.
- Blender 5.1 add-on install/enable reaches the next actual error, if any.
- Blender 4.x import still works if backward compatibility is required.

## Stage 2 - Create a Single Blender Compatibility Layer

Goal: stop every tool from inventing its own Action/Grease Pencil migration.

Dependency: Stage 1 import/register path is known and no longer fails on annotation-only errors.

New or edited files:

- new recommended file: `AMP_AniMatePro/utils/blender_compat.py`
- `AMP_AniMatePro/utils/__init__.py`
- `AMP_AniMatePro/utils/curve.py`

Tasks:

1. Create version/capability helpers:
   - `BLENDER_VERSION = bpy.app.version`
   - `has_layered_actions()`
   - `has_grease_pencil_v3()`
   - `is_action_layered(action)`
2. Create Action helpers:
   - `iter_action_fcurves(action, *, slot=None, include_all_slots=False)`
   - `iter_action_groups(action, *, slot=None, include_all_slots=False)`
   - `get_action_slot(animated_id)` using `animated_id.animation_data.action_slot` when available.
   - `get_channelbag(action, slot, *, ensure=False)` using current API and `bpy_extras.anim_utils` helpers where available.
   - `ensure_fcurve(action_or_animated_id, data_path, index=0, group_name=None, slot=None)` for new helper curves and clones.
   - `remove_fcurve(action, fcurve)` for current channelbag removal and legacy fallback if retained.
   - The helper must support both an animated ID with `animation_data` and a bare `Action`, because the add-on also creates service actions such as `amp_action`.
3. Important: iteration helpers must not mutate user actions. Avoid `ensure=True` while merely reading. The current `utils/curve.get_active_groups()` calls `strip.channelbag(slot, ensure=True)` during iteration, which can create channelbags unexpectedly.
4. Create animation-source helpers:
   - object action;
   - shape-key action;
   - material action;
   - material node-tree action;
   - NLA strip actions;
   - selected element / selected bone action.
5. Keep legacy fallbacks only inside the compatibility module. All migrated tools should call the helpers, never `action.fcurves` directly.

Verification gate:

- Add a temporary Blender 5.1 probe script that prints fcurve counts for object, shape keys, material, node-tree, and NLA action.
- No direct `action.fcurves` writes remain outside the compatibility layer.
- Direct `action.fcurves` reads outside the compatibility layer are either removed or explicitly listed as deferred WIP/experimental exclusions.

Search gate:

- `rg -n "action\\.fcurves|strip\\.action\\.fcurves|action\\.groups|\\.fcurves\\.new|\\.fcurves\\.remove" AMP_AniMatePro`
- Expected result: only compatibility module and documented legacy fallback code.
- If a hit is in a comment, update or remove the stale comment unless it documents an intentional legacy fallback.

## Stage 3 - Normalize Keyframe and F-Curve Collection

Goal: fix the mixed F-Curve/Grease Pencil frame data model.

Dependency: Stage 2 compatibility layer exists or the stage must create the missing collection helpers there first.

Primary files:

- `AMP_AniMatePro/utils/curve.py`
- `AMP_AniMatePro/anim_shifter/anim_shifter.py`
- `AMP_AniMatePro/anim_timewarper/anim_timewarper.py`
- `AMP_AniMatePro/anim_lattice/anim_lattice.py`
- `AMP_AniMatePro/anim_nudger/anim_nudger.py`
- `AMP_AniMatePro/anim_sculpt/anim_sculpt.py`
- `AMP_AniMatePro/anim_looper/*`

Tasks:

1. Split collection APIs by type:
   - `gather_fcurves(scope, context) -> list[FCurve]`
   - `gather_fcurve_keyframes(scope, context) -> list[Keyframe]`
   - `gather_grease_pencil_frames(scope, context) -> list[GreasePencilFrameRef]`
2. Define a small `GreasePencilFrameRef` dataclass or tuple-like object:
   - `object`
   - `layer`
   - `frame`
   - `frame_number`
   - selected/visible flags if available
3. Do not return Grease Pencil frames from `scene_fcurves()`. Rename or split the existing function so callers cannot accidentally treat frames as F-Curves.
4. Audit every caller of:
   - `gather_keyframes`
   - `gather_fcurves`
   - `scene_fcurves`
   - `selected_elements_fcurves`
   - `get_active_fcurves_obj`
5. For tools that only support F-Curves, explicitly ignore Grease Pencil and report a helpful warning.
6. For tools that claim Grease Pencil support, wire the new GP frame collection path.

Verification gate:

- In Blender 5.1, run object/pose/material/shape-key/NLA fcurve gathering and confirm no mutation.
- In a scene with Grease Pencil frames, `gather_fcurves("SCENE")` returns only F-Curves.
- `gather_grease_pencil_frames("SCENE")` returns only Grease Pencil frame refs.
- No caller crashes with `'GreasePencilFrame' object has no attribute 'keyframe_points'`.

## Stage 4 - Migrate Grease Pencil Support Properly

Goal: make Grease Pencil tools work with the Blender 5.1 Grease Pencil v3 API.

Dependency: Stage 3 has separated F-Curve keyframes from Grease Pencil frame refs.

Primary files:

- `AMP_AniMatePro/utils/curve.py`
- `AMP_AniMatePro/anim_shifter/anim_shifter.py`
- `AMP_AniMatePro/utils/operators.py`
- `AMP_AniMatePro/ui/blender_ui.py`
- `AMP_AniMatePro/ui/top_buttons_definitions.py`

Tasks:

1. Runtime-probe Blender 5.1 for Grease Pencil frame collection methods:
   - `layer.frames`
   - `layer.get_frame_at(frame_number)`
   - `layer.current_frame()`
   - whether `layer.frames.move(old, new)` exists;
   - whether `layer.frames.copy(old, new)` exists;
   - whether new/remove APIs require a drawing parameter.
2. Implement compatibility functions:
   - `iter_grease_pencil_layers(obj)`
   - `iter_grease_pencil_frames(obj_or_scene)`
   - `get_grease_pencil_frame(layer, frame_number)`
   - `copy_grease_pencil_frame(layer, source_frame, target_frame)`
   - `move_grease_pencil_frame(layer, old_frame, new_frame)`
3. Update `anim_shifter.execute()` so it has two separate paths:
   - shift F-Curve keyframes;
   - shift Grease Pencil frames when scope includes scene/selected GP objects.
4. Fix existing bug in `anim_shifter.shift_gpencil_keyframes()`:
   - `self.find_next_frame(self.current_frame)` is missing the `layer` argument.
5. Decide and document how selected Grease Pencil layers/frames are detected in Blender 5.1. If frame selection is not available through Python, implement scope as active/visible layers and report that limitation.
6. Update UI strings and enum descriptions from old GPencil naming only where user-facing text should remain "Grease Pencil".

Verification gate:

- Add a Blender smoke scene with a Grease Pencil object, two layers, and frames at 1, 10, 20.
- Run Anim Shifter with positive and negative shift.
- Confirm frames move/copy as expected, scene range updates, and no F-Curve code touches GP frames.
- Confirm Graph/Dope/Editor switch button opens Grease Pencil mode if Blender 5.1 still exposes `st.mode == "GPENCIL"` for Dope Sheet; if not, update the mode enum dynamically.

## Stage 5 - Replace Legacy Action API in Shared and High-Risk Tools

Goal: migrate the shared Action/FCurve paths and highest-risk tools to current layered/slotted Action data. Stage 9 is the later full sweep for all remaining tools.

Dependency: Stage 2 compatibility helpers are available and Stage 3 collection APIs are stable.

Primary files with high priority:

- `AMP_AniMatePro/utils/curve.py`
- `AMP_AniMatePro/anim_baker/anim_baker.py`
- `AMP_AniMatePro/anim_shifter/anim_shifter.py`
- `AMP_AniMatePro/anim_offset/support.py`
- `AMP_AniMatePro/anim_offset/props.py`
- `AMP_AniMatePro/anim_curves/anim_curves.py`
- `AMP_AniMatePro/anim_euler/anim_euler.py`
- `AMP_AniMatePro/anim_nudger/anim_nudger.py`
- `AMP_AniMatePro/anim_lattice/anim_lattice.py`
- `AMP_AniMatePro/anim_sculpt/anim_sculpt.py`
- `AMP_AniMatePro/anim_timewarper/anim_timewarper.py`
- `AMP_AniMatePro/anim_looper/*`

Deferred or isolate:

- `AMP_AniMatePro/anim_baker/anim_baker_WIP.py`
- `AMP_AniMatePro/anim_baker/anim_baker_smart_WIP.py`
- `AMP_AniMatePro/anim_experimental/anim_key_poser/*`

Tasks:

1. Replace helper curve creation:
   - `utils/curve.new()` currently calls `action.fcurves.new(...)`.
   - It must call compatibility `ensure_fcurve(...)` or current channelbag `fcurves.new/ensure(...)`.
2. Replace clone creation:
   - `utils/curve.duplicate()` currently calls `action.fcurves.new(...)`.
3. Replace material/node-tree fcurve collection in `anim_shifter.collect_material_fcurves()`.
4. Replace NLA strip `strip.action.fcurves` loops in baker modules with compatibility iteration.
5. Replace all direct `getattr(action, "fcurves", None)` logic for the `amp_action` mask with compatibility helpers.
6. Treat active slot correctly:
   - For "active object/action" tools, operate on `AnimData.action_slot` only.
   - For "scene" tools, either operate on all slots intentionally or on the slots assigned to each animated ID. Do not blindly mutate all slots unless the tool description says scene-wide all slots.
7. Preserve action groups by name through channelbag groups.
8. Audit `find_owner(fcurve)` and any use of `fcurve.id_data`: in layered actions, `id_data` can still be the Action, but owner/slot must be inferred from the animated ID and channelbag context when needed.

Verification gate:

- Search gate from Stage 2 stays clean.
- In Blender 5.1, these tools work on a simple layered action with an assigned slot:
  - Curves cleanup/select/isolate basics;
  - Anim Shifter on object fcurves;
  - Anim Baker with active action and NLA strip;
  - Anim Offset mask create/update/remove;
  - Nudger and Timewarper on selected keys.
- Verify that running read-only gatherers does not create new layers/strips/channelbags.

## Stage 6 - Update Dope Sheet / Graph Header Integration

Goal: stop overriding stale Blender headers.

Dependency: Stage 4 has clarified Grease Pencil editor modes, and Stage 5 has stabilized action/slot helpers used by UI panels.

Primary files:

- `AMP_AniMatePro/ui/blender_ui.py`
- `AMP_AniMatePro/ui/ui.py`
- `AMP_AniMatePro/ui/top_sections.py`
- `AMP_AniMatePro/ui/top_buttons_definitions.py`
- `AMP_AniMatePro/preferences.py`

Tasks:

1. Prefer appending AniMatePro controls to Blender menus/headers instead of unregistering built-in header classes.
2. If full header replacement is still required by design, copy the Blender 5.1 versions of:
   - `GRAPH_HT_header`
   - `DOPESHEET_HT_header`
   - `DOPESHEET_HT_editor_buttons`
   and re-apply only the AniMatePro changes.
3. Ensure current 5.1 elements are preserved:
   - action selector via `template_action`;
   - action slot selector;
   - slot filtering such as `show_only_slot_of_active_object` if present;
   - timeline overlay controls;
   - updated filter/snapping/proportional controls;
   - `context.active_action` behavior.
4. Replace checks of `st.mode` with capability/enum checks where possible. Do not assume `"GPENCIL"` exists without checking `st.bl_rna.properties["mode"].enum_items`.
5. Make header toggle preferences fail closed:
   - if replacement cannot register, restore Blender native header and report warning.
6. Avoid broad `except RuntimeError or AttributeError`; in Python this does not catch the way it appears to. Use `except (RuntimeError, AttributeError):`.

Verification gate:

- Enable/disable top-right Graph and Dope header toggles repeatedly in Blender 5.1.
- Confirm native header controls do not disappear.
- Switch between Graph, Dope Sheet, Action, Shape Key, Grease Pencil, Mask, Cache File, NLA.
- Confirm no class stays unregistered after add-on disable.

## Stage 7 - Keymaps and Operator Contexts

Goal: make shortcuts predictable and safe on Blender 5.1.

Dependency: Stage 6 has stabilized editor/header integration, so keymaps can be validated against the final UI behavior.

Primary files:

- `AMP_AniMatePro/register_keymaps.py`
- `AMP_AniMatePro/keymaps/keymaps_utils.py`
- all files in `AMP_AniMatePro/keymaps/`
- `AMP_AniMatePro/utils/operators.py`
- `AMP_AniMatePro/utils/key.py`
- `AMP_AniMatePro/anim_curves/anim_curves.py`

Tasks:

1. Generate a Blender 5.1 keymap inventory for every item the add-on toggles:
   - Space playback/search/toolbars;
   - Ctrl/Cmd+G frame jump;
   - Graph/Dope transform/zoom/select mappings;
   - Insert keyframe panel mappings.
2. Update `match_keymap_item()` if Blender 5.1 changed modifier properties or keymap item fields.
3. Add defensive checks before disabling defaults:
   - if a default item is not found, log once and continue;
   - do not assume exact default keymap names if Blender changed them.
4. Validate `space_type`, `region_type`, event `value`, and `direction` for each registered keymap.
5. In `utils/operators.AMP_OT_AnimationEditors`, build `ui_type_map` dynamically where possible and verify current editor `mode` enum before assigning.
6. Audit `bpy.ops.*` calls that require a specific area. Use `context.temp_override()` where needed instead of mutating `context.area.type`.

Verification gate:

- Fresh Blender 5.1 preferences: enable add-on, inspect keymap page, no console errors.
- Toggle each keymap preference on/off twice.
- Confirm add-on disable restores default playback/search/frame-jump keymaps.
- Run primary shortcuts in View3D, Graph Editor, Dope Sheet, and Timeline.

## Stage 8 - Handlers, Draw Handlers, Message Bus, and Modal Tools

Goal: ensure long-running UI features do not leak handlers or break redraws.

Dependency: Stage 7 has stabilized operator context assumptions and shortcut behavior.

Primary files:

- `AMP_AniMatePro/autoKeying/utils.py`
- `AMP_AniMatePro/anim_offset/support.py`
- `AMP_AniMatePro/anim_offset/ops.py`
- `AMP_AniMatePro/anim_sculpt/anim_sculpt.py`
- `AMP_AniMatePro/anim_lattice/anim_lattice.py`
- `AMP_AniMatePro/anim_timewarper/anim_timewarper.py`
- `AMP_AniMatePro/anim_scrub/anim_scrub.py`
- `AMP_AniMatePro/anim_mopaths/*`
- `AMP_AniMatePro/utils/handlers.py`

Tasks:

1. Replace `eval()` draw-handler calls in `autoKeying/utils.py` with an explicit mapping:
   - `"SpaceView3D": bpy.types.SpaceView3D`
   - `"SpaceDopeSheetEditor": bpy.types.SpaceDopeSheetEditor`
   - `"SpaceGraphEditor": bpy.types.SpaceGraphEditor`
   - `"SpaceNLA": bpy.types.SpaceNLA`
2. Make unregister idempotent:
   - only remove handlers that exist;
   - clear handler dictionaries after removal;
   - tolerate add-on reload.
3. Verify `bpy.msgbus.subscribe_rna()` owners are stable and cleared on unregister.
4. Audit handlers that remove themselves while running, especially `magnet_handlers()`.
5. For modal operators, verify:
   - cursor restore;
   - draw handler removal on cancel/finish/error;
   - undo/redo calls still valid;
   - `context.area` not assumed after area switch.

Verification gate:

- Enable/disable add-on three times in one Blender session.
- Toggle Auto Keying frame overlay on/off.
- Start/cancel Anim Sculpt, Anim Lattice, Timewarper, Scrub.
- No duplicate draw handlers, no stuck cursor, no console exceptions after disable.

## Stage 9 - Tool-by-Tool Functional Migration

Goal: migrate features in small, testable groups.

Dependency: Stages 1-8 are complete or explicitly marked as complete in `tools/MIGRATION_STATUS.md`. This stage is the functional sweep, not a place to redesign the compatibility layer.

Recommended order:

1. Core utils:
   - `utils/curve.py`
   - `utils/key.py`
   - `utils/general.py`
   - `utils/handlers.py`
2. Action/curve tools:
   - `anim_curves`
   - `anim_nudger`
   - `anim_retimer`
   - `anim_timewarper`
   - `anim_lattice`
   - `anim_sculpt`
3. Frame/time tools:
   - `anim_shifter`
   - `anim_slicer`
   - `anim_baker`
   - `anim_stepper`
   - `anim_looper`
4. Pose/object tools:
   - `anim_poser`
   - `anim_euler`
   - `anim_selection_sets`
   - `anim_mopaths`
5. UI/preferences/keymaps polish.
6. Experimental/WIP:
   - either migrate after core is green;
   - or prevent registration/import in Blender 5.1 unless explicitly enabled.

For each tool:

1. Read the whole module and list every Blender API access.
2. Replace Action/FCurve access with compatibility helpers.
3. Replace Grease Pencil access with compatibility helpers or explicitly mark unsupported.
4. Replace unsafe context/operator usage with correct overrides.
5. Check whether the tool was already partially migrated in Stage 5. If yes, only complete missing behavior and run the test.
6. Run the smallest manual Blender test for that tool.
7. Add the test result to `tools/MIGRATION_STATUS.md`.

Verification gate:

- No tool is marked "done" because it imports. It must execute its main operator once in Blender 5.1.
- All remaining direct legacy API hits are either removed, isolated in compatibility fallback code, or documented as intentionally disabled WIP/experimental code.

## Stage 10 - Metadata, Packaging, and Release Validation

Goal: only claim Blender 5.1 compatibility after tests pass.

Dependency: Stage 9 migration status says all required tool groups pass or have documented non-support warnings.

Primary files:

- `AMP_AniMatePro/__init__.py`
- `AMP_AniMatePro/blender_manifest.toml`
- `AMP_AniMatePro/changelog.py`

Tasks:

1. Update `bl_info["blender"]` to the real supported minimum.
2. Update `blender_manifest.toml`:
   - `version`
   - `blender_version_min`
   - permissions if changed.
3. Add a changelog entry:
   - Blender 5.1 support;
   - Grease Pencil v3 migration;
   - Action slots/layered actions migration;
   - any dropped legacy Blender support.
4. Zip/package the add-on exactly as Blender expects.
5. Install from zip into a clean Blender 5.1 user profile.
6. Disable, re-enable, uninstall, reinstall.

Final verification gate:

- Clean install succeeds.
- Enable/disable succeeds with no console errors.
- Smoke scene passes all tool groups.
- Keymaps restore on disable.
- Draw handlers and message bus owners are cleared.
- No direct legacy Action API remains outside compatibility fallback code.
- Grease Pencil frame operations work or unsupported operations report clear warnings.


## Blender Test Command Examples

Adjust the Blender executable path for the local machine. Keep the exact command and output summary in `tools/MIGRATION_STATUS.md`.

```powershell
# Import/register/unregister smoke test.
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background --factory-startup --python tools\blender_smoke_test.py

# Scene creation and API probe smoke test.
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background --factory-startup --python tools\blender_create_smoke_scene.py

# Stage-specific probes if present.
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background --factory-startup --python tools\test_stage2_compat.py
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background --factory-startup --python tools\test_stage9_operators.py
```

If Blender is not installed at that path, find the executable first and record the actual path used. Do not mark a stage verified from CPython-only tests; `python -m compileall` is useful but not enough for Blender API compatibility.

## Known Concrete Search Targets

Run these after each relevant stage:

```powershell
rg -n "GPencil|GPENCIL|gpencil" AMP_AniMatePro
rg -n "action\.fcurves|strip\.action\.fcurves|action\.groups|\.fcurves\.new|\.fcurves\.remove" AMP_AniMatePro
rg -n "visible_fcurves|selected_visible_fcurves|editable_fcurves|context\.area|context\.space_data" AMP_AniMatePro
rg -n "unregister_class\(.*bl_ui|class GRAPH_HT_header|class DOPESHEET_HT_header|DOPESHEET_HT_editor_buttons" AMP_AniMatePro
rg -n "\beval\(|\bexec\(" AMP_AniMatePro
python -m compileall -q AMP_AniMatePro
```

## Do Not Miss

- The install error is an import-time annotation problem, but the real migration is the Action API removal plus Grease Pencil v3.
- `hasattr(action, "layers")` is not a complete migration strategy.
- Iteration should not create channelbags.
- Scene-wide operations need a policy for slots: active assigned slots per animated ID vs all slots.
- Grease Pencil frames are not F-Curve keyframe points.
- UI header replacement can hide new Blender 5.1 controls.
- Keymaps and handlers must be tested across enable/disable cycles, not only during first registration.

## If needed
- Blender.exe path is D:\GOG\steamapps\common\Blender
