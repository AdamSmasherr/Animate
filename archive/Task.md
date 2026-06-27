You are working as a senior software architect, Blender add-on developer, and animation tools designer.

Context:

- This is my Blender add-on.
- Target Blender version: 5.1.2.
- I want you to treat this as a serious real-world product, not as a quick patch.
- Think deeply, plan carefully, verify your work, and use agents/subagents if your environment supports them.

After this prompt, I will provide descriptions of 2 features that need to be implemented.

Your work must be divided into 3 large separate stages:

1. Full codebase audit
2. Implementation of the 2 features I describe below
3. Conceptual design of 2 additional advanced animation tools

Important:
Do not jump into coding immediately. First, inspect the project structure and understand the architecture, modules, UI, Blender operators, property groups, class registration, dependencies, data flow, naming conventions, and current coding style.

---

## Stage 1: Full Code Audit

Perform a deep audit of the entire add-on. It was previously only compatible with Blender 4.4 and lower. There may be still some compatibility issues. (You may check for better understanding BLENDER_5_1_MIGRATION_PLAN.md that I used)

Check:

- overall architecture;
- file and module structure;
- separation of responsibilities;
- Blender class registration/unregistration;
- operators, panels, property groups, handlers, timers, and keymaps;
- compatibility with Blender 5.1.2;
- potential runtime bugs;
- UI/UX issues;
- illogical tool behavior;
- duplicated code;
- dead or outdated code;
- fragile code paths;
- naming, typing, and state management issues;
- edge cases;
- performance risks;
- memory or state leaks;
- undo/redo issues;
- selection and context handling problems;
- issues related to armatures, pose bones, constraints, actions, F-Curves, NLA, keyframes;
- places where the user’s scene could be accidentally damaged;
- places that need better error handling;
- minor bugs, strange conditions, or non-obvious side effects.

After the audit:

- list all discovered issues;
- group them by priority: Critical / High / Medium / Low;
- explain why each issue is a problem;
- point to specific files/locations;
- propose improvements;
- immediately implement improvements that are safe and logical;
- if an improvement is risky or may change add-on behavior, clearly explain the risk first and either implement it cautiously or leave a TODO with an explanation.

Do not perform a large refactor just for the sake of refactoring. However, if an architectural improvement is genuinely needed for stability, maintainability, or future feature implementation, do it.

---

## Stage 2: Implement the 2 Features

After the audit, implement the two features described below.

For each feature, handle it separately:

1. Requirements analysis
2. Clarification of behavior if something is ambiguous
3. Implementation plan
4. Identify which files/modules need to change
5. Implementation
6. Integration into the add-on UI
7. Edge case handling
8. Blender 5.1.2 compatibility check
9. Testing or manual verification instructions in Blender
10. Short user-facing documentation

During implementation:

- follow the existing project style;
- do not break existing features;
- do not remove existing behavior unless necessary;
- preserve backward compatibility where possible;
- write code that is easy to extend;
- add comments only where the logic is genuinely complex;
- check edge cases for armature/object/pose mode/context;
- respect Blender’s undo stack;
- avoid destructive operations without explicit confirmation or a safe fallback;
- if new properties, operators, panels, or helpers are needed, add them cleanly and consistently.

After implementing both features:

- provide a list of changed files;
- explain what was changed;
- provide instructions for testing each feature in Blender;
- mention any known limitations or future improvements.

---

## Stage 3: Invent 2 Additional Advanced Tools

After implementing the features, invent 2 new tools for my add-on.

The level of ideas should be comparable to tools such as:

- Pose Polator
- Anim Link

These should not be small utility buttons. They should be powerful, modern, professional tools for animators.

Implementation complexity does not matter. I want the best possible concepts.

For each of the 2 tools, describe in detail:

- name;
- core idea;
- what animator problem it solves;
- why it is valuable;
- how it improves or speeds up the workflow;
- use cases;
- UX design;
- required buttons, modes, and panels;
- what data it uses;
- high-level technical behavior;
- which Blender API areas may be involved;
- how it works with pose bones, keyframes, F-Curves, actions, NLA, constraints, or markers;
- edge cases to consider;
- available modes;
- user parameters;
- desired visual hints or overlays;
- MVP version;
- advanced version;
- approximate classes/operators/properties that would need to be created;
- how a working prototype could be implemented.

These concepts must be detailed enough that working prototypes can later be implemented from them.

---

## Working Style

Work in large, structured tasks.

Before each major stage:

- create a plan;
- explain what you will investigate;
- use agents/subagents for parallel analysis if available;
- do not rush conclusions;
- read the code first, then modify it;
- summarize the result after each stage.

During the work:

- be autonomous;
- do not stop after superficial analysis;
- if you see an obvious issue, fix it;
- if something is ambiguous, make the best engineering assumption and explain it;
- if clarification is needed, ask a specific question, but do not block unnecessarily;
- think like a developer of a production-grade Blender add-on;
- prioritize stability, architectural quality, good animator UX, and Blender 5.1.2 compatibility.

Final response format:

1. Audit summary
2. Fixes implemented after the audit
3. Implemented feature 1
4. Implemented feature 2
5. How to test
6. Changed files
7. Known limitations
8. New tool concept 1
9. New tool concept 2
10. Recommended next steps

---

Below are the descriptions of the 2 features to implement:

FEATURE 1:
Time Visualizer (View Category)
Displays different visual aid markers like seconds or checker marks on the timeline to easily visualize frames together with frames.

FEATURE 2:
Onion Skin (Tools Category)
GPU-accelerated onion skinning directly in the 3D viewport for armatures and any animated object, with four flexible modes, multiple rendering styles, smart caching with incremental updates, presets, and fine-grained configuration.

Visualize animation motion across time with ghosted mesh overlays rendered via GPU. Onion Skin renders semi-transparent overlays of an animated object's mesh at different points in time, allowing animators to see past and future poses simultaneously. The system supports armatures and any animated object (meshes, empties, cameras, lights, etc.) and allows multiple targets to be onion-skinned simultaneously, each with fully independent settings.

**Getting Started**
Adding a Target

1. Select an armature or animated object in the viewport.
2. Open the Onion Skins panel (located in the 3D Viewport sidebar or popover).
3. Click the + button next to the target list to add the active object.
When an armature is added, it automatically discovers all related mesh objects (parented, modifier-linked, or constraint-targeted) and uses them for the onion skin overlay. For non-armature objects, the object itself (if it is a mesh) and any related meshes are used.
Removing a Target
Select the target in the list and click the - button. All associated onion skin data (collections, caches, snapshots) is cleaned up automatically.
Modes
Each target can use one of four display modes, selectable from the Mode dropdown.

▼ Snapshots
The default mode. Manually place snapshots on specific frames and they will be drawn as onion skins in the viewport. This gives you full control over exactly which frames are visualized.
Feature
Description
Add Snapshot
Captures the current frame's mesh pose and adds it to the snapshot list.
Delete Snapshot
Removes a single snapshot from the list (via the X button on each item).
Remove All
Clears every snapshot at once.
Prev / Next
Navigation buttons jump the playhead to the previous or next snapshot frame.
Enable /Disable
Each snapshot has an eye icon toggle to show or hide it independently.
Editable Frame
The frame number on each snapshot is editable - changing it re-bakes the snapshot at the new frame and reorders the list.
Snapshots are drawn with Before / After color coding based on whether the snapshot frame is before or after the current frame. Alpha is gradient-based from closest to furthest snapshot.

▼ Frame Step
Automatically displays onion skins at regular frame intervals around the current frame, anchored to a grid starting at the scene or preview range start.
Setting
Description
Step Size
The interval between onion skin frames (e.g., every 5 frames). Changing this triggers a re-bake of the step grid.
Before Amount
Number of onion skins to display before the current frame.
After Amount
Number of onion skins to display after the current frame.
The step grid is anchored at the range start (scene start or preview range start) so steps remain consistent regardless of the current frame position. Before/After amounts can be adjusted without triggering a re-bake - only changing the step size requires one.
▼On Keyframes
Displays onion skins on the keyframe positions of the active pose bone (for armatures) or on all animated channels (for other objects). This is the most animation-aware mode.
Setting
Description
Before Amount
Maximum number of keyframes to show before the current frame.
After Amount
Maximum number of keyframes to show after the current frame.
The displayed keyframes update dynamically as you select different pose bones or when the active object changes. In Object mode, the last-active pose bone is remembered and continues to drive the keyframe display.
For slotted actions (Blender 4.4+), the system correctly reads F-Curves from the active action slot's channelbag. NLA tracks with stashed or pushed-down actions are also scanned for keyframes.

▼Before/After
The classic NLA-based approach. Each onion skin item has an explicit frame offset and its own hidden collection containing duplicated objects with NLA strips shifted in time.
Feature
Description
Add / Remove Items
Manually add or remove onion skin entries from the Before/After list.
Offset
Each item's frame offset (positive = future, negative = past). Changing it updates the NLA strip.
Visibility Toggle
Per-item eye icon to show/hide individual onion skins.
Reorder
Move items up/down in the list with arrow buttons.
Reset
Recreates the default pair of Before/After items at offsets -3 and +3.
When adding a new target, two default Before/After items at offsets -3 and +3 are automatically created. Best suited for workflows where you want persistent, manually placed reference poses at fixed offsets.

**Drawing Settings**
Click the gear icon (0) next to the mode selector to expand the drawing settings panel. These settings control how onion skins are visually rendered.
**Colors**
Before Color: the color used for onion skins in the past (frames before current). Default: red.
After Color: the color used for onion skins in the future (frames after current). Default: blue.
Before / After Toggle: independently show or hide the before (past) or after (future) side via eye icons.
**Alpha Gradient**
Setting
Description
Alpha Start
Opacity of the closest onion skin (the one nearest to the current frame). Range: 0.0-1.0. Default: 0.5.
Alpha End
Opacity of the farthest onion skin. Range: 0.0-1.0. Default: 0.1.
Alpha is interpolated linearly between Start and End based on distance or order from the current frame. When only one onion skin exists on a side, it uses Alpha Start. Onion skins with an alpha below 1% are automatically skipped for performance.

**Render Mode**
Mode
Description
X-Ray
Classic semi-transparent rendering. All faces are drawn with alpha blending, including back-faces. Produces a glass-like see-through look.
Xray Dither
X-ray style with screen-door dithering. Uses distance-based alpha falloff with temporal variation across 20 distinct 4x4 dithering patterns to reduce banding artifacts.
Solid
Opaque rendering. Onion skins are drawn as fully solid meshes with depth testing. No overlap issues but no transparency.
Solid Dither
Solid colors with back-face culling and a 4x4 Bayer matrix dithering pattern to simulate transparency while maintaining proper depth testing.
**Mesh In Front**
When enabled, automatically sets Object > Viewport Display > In Front on all related meshes while onion skinning is active. The original In Front state of each mesh is stored and restored when the target is disabled or removed from the system. Default: Off.
**Configured Elements**
By default, Onion Skin uses all mesh objects related to the target (e.g. all meshes parented to or deformed by an armature). You can override this with a configured elements list.
**Enabling Configuration**
Click the gear icon () on the target entry in the main list. This toggles the configuration panel and shows an elements sub-list below. When first enabled, the list is auto-populated with all related mesh objects.

**Managing Elements**
Action
Description
Add Element
Adds the currently selected object(s) to the configuration list. Objects already in the list or matching the target itself are skipped.
Remove Element
Removes the selected element from the list. In Before/After mode, the associated copies are also removed from onion collections.
Move Up /Down
Reorder elements in the list.
**Vertex Group Filtering**
Each element entry has an optional Vertex Group field. When a vertex group name is specified, only triangles belonging to vertices assigned to that group (with weight > 0) are included in the onion skin. This allows you to display onion skins for specific parts of a mesh (e.g. only the character's hands or head). When the vertex group name is changed, all caches for the parent target are refreshed automatically.

**Refresh & Caching**
Available for Snapshots, Frame Step, and On Keyframes modes.
**Auto Refresh**
When enabled (default), the system automatically detects keyframe changes via the depsgraph and incrementally updates only the affected onion skin frames. It uses a "most unfavorable segment" algorithm: when a keyframe changes, the system finds the widest segment across all animated channels that could be affected and re-bakes only the frames within that segment. When disabled, onion skins are only updated manually via the Refresh button.
**Update Mode**
Mode
Description
On Frame Change
Queues updates until the playhead moves to a different frame. Keyframe edits are logged and processed on the next frame change. More efficient during intensive editing.
On Keyframe
Updates immediately when a keyframe is inserted or modified. Provides instant feedback but may be slightly less performant during rapid edits.
**Manual Refresh**
The refresh icon (G) next to the mode dropdown forces a complete re-bake of all cached frames for the selected target. This is useful when:
Auto Refresh is disabled and you want to manually update.
Something looks out of sync after complex editing operations.
You've changed configuration (elements, vertex groups) and want to ensure everything is current.

**Range Limiting**
Controlled by the addon preference Limit to Range:
Enabled (default): onion skins are constrained to the Preview Range (if active) or the Scene Start/End range. Frames outside this range are not baked or displayed.
Disabled: the calculation range is derived from the animation length (action frame range or keyframe extents), allowing onion skins to cover the full extent of the animation.
This affects Frame Step grid boundaries, On Keyframes filtering, and Snapshot visibility. When the preview or scene range is edited, the system debounces the change and only bakes the newly visible frames without wiping the existing cache.

**Global Visibility**
The eye icon at the top-left of the Onion Skins panel toggles all onion skins on or off at once without changing individual per-target settings.
When toggling off, each item's current visibility is stored.
When toggling back on, each item's previous visibility is restored.
This toggle is also available as the operator anim.amp_onionskin_toggle and can be mapped to a keyboard shortcut.

**Multi-Target Support**
Multiple armatures and objects can be onion-skinned simultaneously. Each target in the list maintains its own independent settings:
Display mode
Colors and alpha gradient
Render mode
Step/keyframe amounts
Element configuration
Snapshots list
Targets can be reordered in the list using the up/down arrow buttons.

**Presets**
Onion skin settings can be saved and loaded as presets, stored in the Blender preset directory under
amp/onion_skinning
Action
Description
Save Preset
Saves the current settings of the active target as a named preset.
Load Preset
Applies a previously saved preset to the active target.
Remove Preset
Opens a dialog to select and delete a saved preset file.
**Saved Properties**
Presets store: Mode, Auto Refresh, Update Mode, Alpha Start/End, Step Size, Render Mode, Mesh In Front, Before/After Colors, Before/After Enabled, Step Amount Before/After, and Keyframe Amount Before/After.

**Compatibility**
Armatures: full support including per-bone keyframe filtering in On Keyframes mode.
Mesh Objects: supported as targets with all modes. Related meshes are collected automatically.
Any Animated Object: empties, cameras, lights, and other object types can be used as targets.
Blender 4.4+ Slotted Actions: fully supported. The system reads keyframes from the correct action slot and channelbag, and tracks slot changes to update the display.
NLA Tracks: keyframes from stashed and pushed-down actions are included in On Keyframes mode.