# AniMate Pro tool reference

Every tool in the add-on, grouped by the category it appears under in the Graph Editor and Dope Sheet header toolbar (plus the sidebar tools). Each entry says what the tool does and how to use it. For the two flagship overlays see also [FEATURES.md](FEATURES.md).

## Contents

- [Flagship tools (new in this build)](#flagship-tools-new-in-this-build)
- [Tools](#tools)
- [Keyframes](#keyframes)
- [Toggles](#toggles)
- [Utils](#utils)
- [View](#view)
- [Selection](#selection)
- [Editor switches (Action)](#editor-switches-action)
- [Other and sidebar tools](#other-and-sidebar-tools)

## Flagship tools (new in this build)

GPU overlays added in this build.

### Onion Skin
*GPU onion skinning that shows ghost copies of your animated object at surrounding frames directly in the 3D viewport.*

**What it does:** It bakes evaluated world-space mesh geometry at selected frames by stepping the playhead, then draws those frames as colored translucent ghosts in the 3D viewport using a persistent GPU draw handler (the bake is deferred to a timer so it never runs inside the draw/frame-change callback). It works universally for armatures, meshes, and anything deformed by modifiers, constraints or drivers, and supports multiple independent targets, each with its own settings. Each target offers four frame-selection modes (Snapshots = manually placed frames, Frame Step = regular interval around the playhead, On Keyframes = the active bone/object's keys, Before/After = explicit per-item offsets) plus Before/After color coding with a distance-based alpha gradient, X-Ray vs Solid render modes, Mesh In Front, and a Limit to Range option. Baking auto-refreshes when the target's geometry or transform changes, and there is a manual Refresh as well (capped at 64 baked frames per target).

**How to use:** In the Graph Editor or Dope Sheet header find the AniMatePro top bar 'Tools' section. The Onion Skin control is a two-part button: click the ghost icon (anim.amp_onionskin_toggle) to toggle all onion skins on/off, and click the small arrow next to it to open the settings popover. In the popover, select an object in the viewport and press the + (Add Onion Target) button, then pick a Mode from the dropdown; for Snapshots use Add to capture the current frame, for Before/After use Add to create offset items, for Frame Step/On Keyframes set the Before/After counts. Expand a target's gear (Drawing Settings) row to set Before/After colors and visibility, Alpha Start/End, the render mode (X-Ray / X-Ray Dither / Solid / Solid Dither), and Mesh In Front. The ghosts appear in the 3D viewport, not in the editor itself.

**Tip:** For armatures, On Keyframes mode filters to the active pose bone's keyframes when a bone is active, so select a bone to focus the ghosts on just that control. Use the Refresh (circular arrow) button if a ghost looks stale, and Limit to Range (the arrow toggle in the popover header) to keep skins inside the preview/scene frame range.

### Time Visualizer
*An overlay that draws second lines, alternating checker bands, frame ticks and timecode labels over the Dope Sheet / Timeline so you can read spacing in real time units.*

**What it does:** It installs a persistent per-editor GPU/blf draw handler that overlays time aids on the Dope Sheet / Timeline (and optionally the Graph Editor), mapping frames to pixels via the region's view2d. It can draw alternating shaded checker bands (one band per step, default one second based on scene FPS), vertical lines at every whole second, small per-frame ticks (only shown when zoomed in far enough to be readable), and text labels at each second shown either as a plain second count or as mm:ss timecode. Every element has its own color and the whole overlay has a global opacity multiplier; the handler is always installed and simply gated by a per-scene Enabled toggle so there is no handler churn. It reads the scene render FPS to position the seconds, so it reflects your actual playback rate.

**How to use:** In the Graph Editor or Dope Sheet header, open the AniMatePro top bar 'View' section. The Time Visualizer is a two-part control: click the clock icon (anim.amp_time_visualizer_toggle) to turn the overlay on/off, and click the small arrow beside it to open the settings popover. In the popover toggle Checker Bands, Second Lines, Second Labels and Frame Ticks independently, set the Step (band width in frames; 0 means one band per second), choose Timecode for mm:ss labels, adjust Text Size, per-element colors, and the global Opacity. Enable 'Also In Graph Editor' to draw it there too. The overlay renders on the time axis of the editor itself.

**Tip:** Frame ticks only appear when the view is zoomed in enough (at least ~6 pixels per frame), so if you do not see them zoom into the timeline. Leave Step at 0 to keep the checker bands locked to one-second intervals as you change the scene FPS.

## Tools

The main animation editing tools, shown in the Tools section of the Graph Editor and Dope Sheet header.

### Anim Loop
*Makes an action cyclical by adding Cycles F-Curve modifiers and matching the start/end poses.*

**What it does:** Triggers the anim.amp_anim_loop operator (AMP_OT_AnimLoop), which adds a named "AnimLooper" CYCLES modifier to each target F-Curve so the animation repeats, mirrors, or offsets before and after its range. It can ensure keyframes exist at the start and end frames, copy the first pose to the last (or vice versa) so the loop matches seamlessly, and set the interpolation/handle types on those boundary keyframes. The loop range is taken from the whole action, the active scene/preview range, or per-F-Curve min/max, and it also enables Cycle-Aware Keying. Running it with the Cyclical option off instead strips the Cycles modifiers back out.

**How to use:** In the Graph Editor or Dope Sheet, open the AniMatePro header toolbar and find the "Tools" section; click the Anim Loop button to apply with defaults. Hold SHIFT while clicking to open the options dialog where you set Before/After mode (Repeat, Mirror, Offset, None), cycle counts, Range, Match Loop direction, and the start/end handle and interpolation types.

**Tip:** Use the Match Loop option (Start to End / End to Start) so the first and last poses are identical, otherwise the cycle will visibly pop. To remove looping, open the dialog and turn off "Add/Remove Cyclical Modifier".

### Anim Sculpt
*A modal brush that sculpts F-Curves directly in the Graph Editor by dragging keyframes.*

**What it does:** Triggers the anim.amp_anim_sculpt operator (AMP_OT_anim_sculpt), a modal brush tool that edits keyframes under the cursor within an adjustable radius and falloff. Left-click drag tweaks/moves keyframes, SHIFT+drag smooths them against their neighbours, and CTRL+SHIFT+drag averages them toward the selected keyframe value. The brush has Radius (100% influence), Blend Radius (falloff to 0%), and Strength settings, and it accounts for rotation-curve unit conversion when averaging.

**How to use:** This tool only works in the Graph Editor. In the AniMatePro header toolbar "Tools" section, click Anim Sculpt to enter the modal brush, then drag over the curve: LMB to move, SHIFT+LMB to smooth, CTRL+SHIFT+LMB to average. Adjust brush radius/strength via the on-screen interaction before releasing.

**Tip:** The button is disabled in the Dope Sheet; switch to the Graph Editor to use it since it operates on actual curve values.

### Anim Curves
*A settings popover controlling how F-Curves are isolated, zoomed, and selected in the editors.*

**What it does:** Opens the AMP_PT_anim_curves_properties popover rather than running an operator. It exposes preference toggles that govern AniMatePro's curve-isolation behaviour: Zoom to whole visible F-Curves, Smart zoom to a frame range (with a frame-range value), Cycle F-Curves, Isolate F-Curves, and Expand Curve Groups. It also holds Graph/Dope editor tweaks such as Auto-Lock Key Axis and "Move Playhead to Keyframe" hotkeys, plus a Scrubber tweak to select keyframes on the current frame.

**How to use:** In the Graph Editor or Dope Sheet, open the AniMatePro header toolbar "Tools" section and click the Anim Curves button to open the popover. Toggle the options for how curves zoom and isolate when you select keyframes; changes apply immediately as add-on preferences.

**Tip:** If selecting a control causes the Graph Editor to zoom or hide other curves unexpectedly, this popover is where you turn Isolate F-Curves and the zoom behaviours on or off.

### Anim TimeWarper
*A modal on-screen rig of pins and bars for retiming keyframes interactively.*

**What it does:** Triggers the anim.amp_anim_timewarper operator (AMP_OT_timewarp), a modal tool that draws draggable pins, bars, and easing handles over the timeline so you can warp (retime) keyframes by dragging instead of editing values numerically. A Scope property decides what is affected: the whole Scene, the active Action, Selected Elements (objects/pose bones), all Visible F-Curves, or only Selected Keys. It can optionally snap keyframes to the nearest whole frame while you drag.

**How to use:** In the Graph Editor or Dope Sheet, open the AniMatePro header toolbar "Tools" section and click Anim TimeWarper to start the modal session, then drag the pins/bars to stretch or compress timing. Hold SHIFT while clicking the button to open the options panel first, where you set Scope and Snap to Frame.

**Tip:** Set the Scope to "Selected Keys" when you only want to retime a portion of the animation without affecting everything in the action.

### Anim Shift
*Shifts all keyframes after (or before) the playhead by a set number of frames.*

**What it does:** Triggers the anim.amp_anim_shifter operator (AMP_OT_AnimShifter). Using the current frame as the pivot, a positive Shift Amount moves every keyframe to the right of the playhead later, and a negative amount moves every keyframe to the left earlier, expanding the scene frame range to match. It can insert a hold keyframe at the playhead before shifting and add a keyframe at the slice/target frame so values are preserved, and it handles Grease Pencil frames as well as F-Curves. The Scope property targets the Scene, Action, Selected Elements, Visible F-Curves, or Selected Keys.

**How to use:** Place the playhead where you want to insert or remove time, then in the AniMatePro header toolbar "Tools" section (Graph Editor or Dope Sheet) click Anim Shift. Hold SHIFT while clicking to open the options panel and set Scope, Shift Amount, Add Keyframe on Slice, and Add Hold Keyframes.

**Tip:** A positive amount pushes downstream keys later (making room); a negative amount pulls them earlier (closing a gap). The scene end/start frame is adjusted automatically so nothing falls off the timeline.

### Scrubbing
*A toggle that enables AniMatePro's timeline scrubbing keymap (Space) in the editors.*

**What it does:** This button is a toggle, not an operator: it flips the add-on preference scrub_timeline_keymap_kmi_active ("Anim Scrub - Timeline", bound to Space). When enabled, the Space hotkey activates the modal AMP_OT_scrub tool, which lets you scrub the playhead by dragging in the timeline, with modifier-key variants for snapping to markers (CTRL) and keyframes (SHIFT) and an on-screen GUI toggle. The header icon reflects the on/off state.

**How to use:** In the Graph Editor or Dope Sheet header, the AniMatePro toolbar "Tools" section shows the Scrubbing button; click it to toggle the scrubbing keymap on or off (icon changes between scrubber on/off). With it on, press and drag with Space in the viewport/timeline to scrub.

**Tip:** This is a display/toggle button only (the same setting also lives in the add-on preferences); it does not start scrubbing by itself, it just enables the Space keymap that does.

### Anim Lattice
*A modal bounding-box lattice for scaling/proportionally transforming keyframes in the Graph Editor.*

**What it does:** Triggers the anim.amp_anim_lattice operator (AMP_OT_anim_lattice), a modal tool that draws a bounding box with draggable control points around the keyframes; dragging a corner or edge scales the enclosed keyframes (and their handles) proportionally in time and/or value. It can snap keyframe frames to whole integers and temporarily adjusts normalization/zoom so the lattice is usable. It uses NumPy arrays internally to transform many keyframes at once and supports undo of the drag.

**How to use:** This tool requires the Graph Editor. In the AniMatePro header toolbar "Tools" section click Anim Lattice to wrap the keyframes in the lattice cage, then drag the control points to scale them. Hold SHIFT while clicking the button to launch with its options panel (Snap to Full Frames, Zoom Out Times).

**Tip:** Use it to uniformly scale the amplitude or timing of a block of keys at once. It is disabled in the Dope Sheet, so switch to the Graph Editor first.

### Anim Slice
*Bulk-inserts keyframes across a range on markers, frame steps, or stored frames.*

**What it does:** Triggers the anim.amp_anim_slicer operator (AMP_OT_AnimSlicer), which inserts ("slices") keyframes onto F-Curves throughout a range. The Insertion Type can be On Markers, every N frames (Frame Step), both, Closest Full Frame (snap subframe keys to the nearest whole frame), or a Stored Slice Frames list. Selection Mode targets only selected F-Curves or all F-Curves of the selected objects/bones, and the Range comes from selected keyframes, the preview range, or the whole scene. Keying can be limited to Available channels or to Location/Rotation/Scale/Custom properties.

**How to use:** In the Graph Editor (the button is disabled in the Dope Sheet), open the AniMatePro header toolbar "Tools" section and click Anim Slice. Hold SHIFT to open the options dialog and choose Insertion Type, Frame Step, Range, Selection Mode, and which transform channels to key. Hold CTRL while clicking to store the current selected F-Curves' frames for the Stored Slice Frames mode.

**Tip:** Use "Closest Full Frame" to clean an action that has keys on subframes by snapping them to whole frames, or "On Markers" to convert marker beats into keyframes.

### Anim Blast
*Renders a quick OpenGL viewport playblast of the animation to an MP4 file.*

**What it does:** Triggers the anim.amp_anim_blast operator (AMP_OT_AnimBlast), which does an OpenGL viewport render of the frame range to an H.264 MP4 using FFMPEG. The Source can be the current/first 3D Viewport or the scene's Active Camera, and you set a resolution percentage of the scene render size. Output goes to the temp folder or a custom path with a filename pattern supporting {blend_name} and {timestamp} tokens, and it can auto-open the file when done. It saves and restores your render settings, camera perspective, and current frame afterward so your scene is left unchanged.

**How to use:** Click the Anim Blast button (camera/render-animation icon) in the AniMatePro header toolbar "Tools" section of any editor; it opens a dialog where you pick Source, Playblast Resolution %, output path/filename pattern, and Auto Open, then confirm to render. The same settings panel also appears in the AniMatePro N-panel under "Anim Blast".

**Tip:** Set Source to "Active Camera" to playblast through the scene camera; otherwise it captures whatever the chosen 3D Viewport currently shows. Lower the Resolution % for a faster preview render.

## Keyframes

Pose and keyframe operations.

### Copy/Paste Pose
*Copy the current pose, then stamp it across a whole frame range as keyframes.*

**What it does:** This is a two-button pair: the first button runs Blender's native pose.copy to copy the current pose of the selected bones, and the second runs anim.amp_propagate_pose_to_range, which pastes that pose onto every keyframed frame in a range and inserts location, rotation (quaternion and euler) and scale keyframes on each. The range is chosen by priority: the Preview Range if one is set, otherwise the span between the first and last selected keyframes, otherwise the entire scene. It works only in Pose Mode on an armature (the paste operator polls for an active pose bone), so it is exposed in the Graph Editor header only, not the Dope Sheet.

**How to use:** Open the AniMatePro header toolbar in the Graph Editor and find the Keyframes group. Enter Pose Mode, select the bones, click the Copy (pose copy) icon, then click the Paste-to-Range icon next to it to propagate the held pose across the range.

**Tip:** Set a Preview Range or select a start and end keyframe first to control exactly which frames get the pose; with nothing set it fills the entire scene.

### AnimOffset
*A 'magnet' mode that offsets surrounding keyframes when you tweak a pose, so you don't break timing.*

**What it does:** AnimOffset toggles a depsgraph handler (the 'magnet' handler) via anim.amp_activate_anim_offset / anim.amp_deactivate_anim_offset; while active, editing a pose on the current frame offsets the neighboring animation by the same amount instead of leaving a single broken key. The Mask button (anim.amp_add_anim_offset_mask / amp_delete_anim_offset_mask) restricts the effect to a frame range, and when a mask is in use two sliders appear, ao_mask_range (the affected range) and ao_blend_range (the falloff on each side). A settings popover exposes 'Auto Key outside margins' (insert_outside_keys) plus the mask blend easing and interpolation. It is available in both the Graph Editor and Dope Sheet headers.

**How to use:** In the AniMatePro header (Graph Editor or Dope Sheet), Keyframes group, click the AnimOffset (magnet) icon to activate, then move/tweak your pose on the current frame. Optionally click Mask to limit the offset to a range and drag the range/blend sliders; use the gear/preferences popover for blend easing and auto-key options.

**Tip:** Activate the Mask and tune the blend range when you only want part of the timeline to absorb the offset; remember to deactivate AnimOffset when done, as it stays live as a handler.

### Match Keyframes
*Snap selected keyframe values to match the nearest keyframe on the left or right.*

**What it does:** Two buttons drive anim.amp_match_selected_keyframe_values with to_right=False (left) or to_right=True (right). For each selected, visible F-curve it finds the closest keyframe just outside the selected range in the chosen direction and copies that keyframe's value (and handle Y) onto all selected keyframes, flattening them to the neighbor's value. It reports an error if nothing is selected or if there is no keyframe in that direction. It is a Graph Editor header tool only.

**How to use:** In the Graph Editor's AniMatePro header, Keyframes group, select the keyframes you want to change, then click the left-match icon to match the previous keyframe's value or the right-match icon to match the next keyframe's value.

**Tip:** Great for creating holds: select a span of keys and match-left so they all hold the value of the key before them.

### Keyframer
*A popover gathering Blender's graph smoothing, blending, cleanup, and rotation operators in one place.*

**What it does:** The Keyframer button opens the AMP_PT_AnimKeyframerPopover panel, which is a curated menu of native Graph Editor operators grouped into sections. Smooth offers Gaussian Smooth, Smooth, and Butterworth Smooth; Blend offers Breakdown, Blend to Neighbor/Default/Ease, Ease, Blend Offset, Match Slope, Push/Pull, Shear, Scale Average/From Neighbor, and Time Offset; Cleanup offers Clean Keyframes, Clean Channels, Decimate, Bake Keys, and Channels Bake plus AniMatePro's reset-keyframe-value buttons; Rotation offers Euler Filter. It is a Graph Editor header popover (the same panel also appears in the Graph Editor sidebar under Animation).

**How to use:** In the Graph Editor AniMatePro header, Keyframes group, click the Keyframer icon to open the popover, select your keyframes in the curve area first, then click the operator you want (e.g. Gaussian Smooth or Ease).

**Tip:** These are standard Blender graph tools, so they act on the currently selected keyframes/handles; select before opening the popover for predictable results.

### Share Keyframes
*Give every selected object/bone keyframes on every frame where any of them is keyed.*

**What it does:** anim.amp_share_keyframes collects the set of frames that hold keyframes across all selected elements, then for each element inserts a keyframe on any of those frames it is missing, sampling the value from the F-curve's evaluation. It supports Object mode (selected objects) and Pose mode (selected bones of the active armature), and new keys are created with Bezier interpolation and AUTO_CLAMPED handles. The result is that all selected elements end up keyed on a unified, shared set of frames. It is available in both the Graph Editor and Dope Sheet headers.

**How to use:** Select the objects (Object Mode) or bones (Pose Mode) you want aligned, then in the AniMatePro header Keyframes group click the Share Keyframes icon.

**Tip:** Use this to synchronize timing across a set of controls so they all have matching keyframe columns before further editing.

### Nudge Keyframes
*Shift keyframes left or right by a set number of frames, with smart fallbacks.*

**What it does:** Two arrow buttons run anim.timeline_anim_nudger with direction LEFT/RIGHT, and a small numeric field sets frames_to_nudge (the per-click amount). Its behavior adapts: if keyframes are selected it moves only those (keys plus handles); if none are selected but there are keys on the current frame it moves those keys and the playhead together; if neither, it snaps the nearest keyframe in that direction onto the playhead. It only runs inside the Graph Editor or Dope Sheet and updates the affected F-curves afterward.

**How to use:** In the AniMatePro header (Graph Editor or Dope Sheet), Keyframes group, set the frames value in the small field, then click the left or right nudge arrow. Select keyframes first to nudge a specific selection.

**Tip:** Leave nothing selected and park the playhead between keys to use it as a 'pull nearest key to playhead' tool.

### InBetweens
*Insert or remove a single in-between frame, shifting later keyframes and the scene range.*

**What it does:** Two buttons run anim.anim_pusher with operation ADD or REMOVE. Add shifts every keyframe at or after the playhead forward by one frame (opening a one-frame gap) and extends the scene end frame by one; Remove shifts every keyframe strictly after the playhead back by one frame and shortens the scene end, but refuses to run if a keyframe sits on the current frame (to avoid deleting it). It processes the active F-curves of all selected objects. It is available in both the Graph Editor and Dope Sheet headers.

**How to use:** Place the playhead where you want to open or close time, select the relevant objects, then in the AniMatePro header Keyframes group click the Add icon to insert a frame or the Remove icon to close one.

**Tip:** To remove an in-between, move the playhead to an empty frame (no keyframe on it) first, or the operator will warn and cancel.

## Toggles

On/off overlays and helpers.

### Isolate Character
*Toggle that temporarily hides everything except the selected character so you can pose/animate it in isolation.*

**What it does:** This is an on/off toggle bound to scene.anim_poser_props.isolate_character. When enabled it creates a dedicated "amp_character_isolation" view layer and collection containing the selected armature (plus, depending on preferences, its skinned meshes, objects driven by modifiers/constraints like Child Of / Copy Transforms / Armature, and the armature's children), excludes all other collections, switches the window to that view layer and enters Pose Mode. It installs a depsgraph handler that auto-isolates whenever you enter Pose Mode and restores your original view layer when you leave. Turning it off removes the handler, restores the original view layer and clears the isolation state.

**How to use:** In the Graph Editor or Dope Sheet header (AniMatePro top bar, "Toggles" group) click the Isolate Character icon to toggle it; the button highlights when active. It is also exposed as a checkbox in the 3D Viewport "Anim Poser Options" panel (AMP_PT_AnimPoserOptions). Select your character armature first, then toggle it on.

**Tip:** What gets pulled into isolation alongside the armature is controlled by the add-on preferences (include armature-modifier meshes, include other modifier/constraint targets, include children), so adjust those if a needed prop or mesh is missing.

### Realtime Looper
*Toggle that keeps the first and last keyframes of selected curves identical for seamless looping animation.*

**What it does:** Backed by the operator anim.amp_toggle_anim_looper_handler, this toggles a depsgraph handler (scene.realtime_looper_handler_active) that continuously ensures continuity between the first and last keyframe of each selected editable F-Curve. As you edit, it guarantees a keyframe exists at the first and last frame and copies the value and handle shape from whichever end you changed to the other end, so the loop stays seamless. Enabling it also turns on Blender's Cycle-Aware Keying (use_keyframe_cycle_aware); disabling it removes the handler and turns that off again.

**How to use:** In the Graph Editor header AniMatePro top bar, "Toggles" group, click the Realtime Looper icon to toggle it on/off (it depresses/highlights when active). Select the bones/curves you want looped, then edit their keys normally; the first/last frames update automatically. It is a Graph-Editor tool (not shown in the Dope Sheet).

**Tip:** Because it edits whichever end you did not touch, animate freely on the start OR end key and let it mirror to the opposite end rather than editing both manually.

### Flex Mopaths
*Persistent, list-based motion paths for chosen objects/bones with a popover of display options.*

**What it does:** The button's main icon runs anim.amp_fmp_toggle_show_motion_paths, toggling scene.mp_props.show_motion_paths to draw or hide a custom (GPU-drawn) set of motion paths for a managed list of elements. Unlike Blender's native paths, elements are added to a persistent list (objects or pose bones, each with its own empty/collection reference and an "Always Show" flag) that updates live via a registered handler. The attached popover (AMP_FMP_PT_FlexMoPathsPanel) exposes the element list (add/remove/reorder, select element) and display options: Bake to Active Camera (4.2+), Lines on/off, line Thickness (1-6), Custom Color with separate Before/After colors, and frame numbers.

**How to use:** In the Graph Editor or Dope Sheet header AniMatePro "Toggles" group, click the Flex Mopaths icon to show/hide the paths, and click the small arrow next to it to open the popover. In the popover use the + button to add the selected object/bone to the list, adjust options, and use Refresh All to rebuild paths. Also available as the "Flex MoPaths" sidebar panel in the Graph Editor, Dope Sheet and 3D View.

**Tip:** Toggle "Always Show" on a list element so its path stays visible even when it is not the active/selected element; use Custom Color Before/After to distinguish multiple characters.

### Realtime Mopaths
*Toggle that auto-updates Blender's native motion paths as you adjust keyframes, plus a popover of quick path actions.*

**What it does:** The main icon runs anim.amp_realtime_motion_paths, a toggle (prefs.is_mopaths_active) that registers a depsgraph handler to recalculate the active object/pose-bone motion paths automatically as keyframes or the selection move. The attached popover (AMP_PT_AnimMopathsPop) exposes options - Timer Interval (seconds between updates), Realtime Mograph (update live vs only after an edit finishes), and Clear Previous Paths - plus one-click actions via anim.amp_quick_motion_paths: Quick (calculate without deleting), Update All, Delete Current, and Delete All. When active the button turns red/alert to warn it is continuously updating.

**How to use:** In the Graph Editor or Dope Sheet header AniMatePro "Toggles" group, click the Realtime Mopaths icon to start/stop auto-updating, and click the adjacent arrow to open the popover for the Quick/Update All/Delete buttons and the Settings sub-options. Works on the active object in Object Mode or the active pose bone in Pose Mode.

**Tip:** Realtime updates can slow Blender on heavy rigs; raise the Timer Interval or turn off Realtime Mograph (so paths refresh only after you release an edit), or just use the "Quick"/"Update All" buttons on demand instead of the live toggle.

### Silhouette
*Toggle that flattens the viewport to a flat black-on-white silhouette for readability of poses.*

**What it does:** Bound to scene.amp_silhouette.toggle_silhouette (operator anim.amp_toggle_silhouette for the per-viewport header version), this toggles a flat silhouette display across 3D viewports. It stores each viewport's current shading/overlay state, then forces Solid shading with Flat lighting, a single foreground color over a viewport background color (taken from the add-on's poser foreground/background color preferences), disables shadows, cavity, backface culling and overlays. Toggling off restores each viewport's saved shading exactly. If an armature is selected it also engages Isolate Character (without forcing Pose Mode) so only the character is shown in silhouette.

**How to use:** In the Graph Editor or Dope Sheet header AniMatePro "Toggles" group, click the Silhouette icon to toggle it; the icon shows on/off state. A matching toggle can also appear directly in the 3D Viewport header (enabled via the "poser_silohuette_button" preference).

**Tip:** Use it to judge pose readability and clean silhouettes; set the silhouette and background colors via the AniMatePro Poser foreground/background color preferences.

## Utils

Cleanup and marker utilities.

### Euler Filter
*Recomputes Euler rotation keyframes across a range to remove sudden flips and discontinuities.*

**What it does:** Runs the anim.amp_euler_filter operator ("Euler Filter to Range"). For every selected object (and every pose bone of selected armatures) it finds the X/Y/Z rotation_euler F-curves, then steps frame by frame through the range, converting each evaluated Euler triple to a quaternion and back to Euler in the channel's rotation order, rewriting the keyframe values while preserving each key's existing handle deltas. The processed range is chosen by priority: the preview range if one is set, otherwise the span between the first and last selected keyframes, otherwise the whole scene. It only touches objects/bones that already have all three Euler rotation curves.

**How to use:** Open the Graph Editor or Dope Sheet, find the AniMatePro toolbar in the header and locate the "Utils" section. Select the objects/bones whose rotation you want to clean, optionally set a preview range or select the keyframes to limit the range, then click the Euler Filter button (the Euler curves icon, first button in Utils).

**Tip:** Set a preview range or select a span of keyframes first to control exactly which frames get refiltered; with nothing selected and no preview range it processes the entire scene.

### Euler Gimbal
*Opens a popup that ranks Euler rotation orders by gimbal-lock risk and lets you bake to the best one.*

**What it does:** The button runs anim.amp_euler_rotation_recommendations, which clears any previous result and pops up the Rotation Mode Recommendation panel. From there the "Calculate Recommended Euler Order" operator analyzes the active object or pose bone's animation, scoring all six Euler orders (XYZ, XZY, YXZ, YZX, ZXY, ZYX) by average gimbal-lock risk across its rotation keyframes and showing them ranked best-to-worst. The panel then offers "Bake to <mode>" buttons (including Quaternion) that convert the animation to the chosen rotation order at every rotation keyframe while preserving the visual pose, with an optional "Key Rotation Mode on First Keyframe" toggle.

**How to use:** In the Graph Editor or Dope Sheet header AniMatePro toolbar, "Utils" section, click the Euler Gimbal button (gimbal icon, second in Utils) to open the popup. Select an object or pose bone, click "Calculate Recommended Euler Order" to see the ranking, then click "Bake to <mode>" for the recommended (highlighted) order.

**Tip:** The recommended order is the one with the lowest average gimbal risk and appears highlighted in the bake list; baking re-keys every rotation frame, so do it before refining handles.

### Smart Keyframes
*One-click cleanup that strips F-curves from locked channels and removes redundant keyframes.*

**What it does:** Runs anim.amp_cleanup_keyframes_from_locked_transforms ("Magic Clean-up"), a REGISTER/UNDO operator with toggleable options exposed in its redo panel. By default it deletes F-curves on locked transform channels (Delete Locked) and resets those locked channels back to their default values (Reset Locked to default). Optional toggles add Delete Unchanged Keyframes (removes keys whose value does not change) and Delete Unnecessary Keyframes (removes channels that only hold default values). An Affect Scope enum targets either All or only Selected bones/objects, and it works in both Object and Pose mode across location, rotation_euler, rotation_quaternion, and scale.

**How to use:** In the Graph Editor or Dope Sheet header AniMatePro toolbar, "Utils" section, click the Smart Keyframes button (cleanup icon, third in Utils). After it runs, open the operator redo panel (bottom-left) to toggle Delete Locked, Reset to default, Delete Unchanged, Cleanup Keyframes, and switch Affect Scope between All and Selected.

**Tip:** Lock the transform channels you don't want animated (in the N-panel) before running, then leave Delete Locked on so those channels are stripped automatically; default scope is Selected, so set it to All to clean everything at once.

### Markers
*Opens a dialog that inserts timeline markers across a range by frame step, divisions, or on keyframes.*

**What it does:** Runs anim.amp_markers_tools ("Insert Markers"), which opens a props dialog. It can insert markers by one of three criteria: every X frames (Frame Step, with a start offset), dividing the range into a set number of segments (Divisions), or on every keyframe of the active object's action (On Keyframes). A Range option chooses Preview Range, Selected keyframes, or whole Scene; First/Last toggles add markers on the first and last frames; and a Clear Others toggle (with Keep Camera Markers) wipes existing markers first by calling the delete operator. New markers are named F<frame>.

**How to use:** In the Graph Editor or Dope Sheet header AniMatePro toolbar, "Utils" section, click the Markers button (markers tools icon, fourth in Utils). In the dialog pick an Insertion Type, set Frame Step / Sections and start offset, choose the Range, toggle First/Last and Clearing options, then confirm.

**Tip:** Leave Clear Others on with Keep Camera Markers enabled to regenerate timing markers without destroying camera-bound markers; use the "On Keyframes" mode to mark every key of the active object.

### Delete All Markers
*Deletes timeline markers, removing selected ones if any are selected, otherwise all of them.*

**What it does:** Runs anim.amp_delete_markers. If any (non-camera) markers are selected it deletes only the selected markers; if none are selected it deletes all unselected markers, effectively clearing the timeline. Its Keep Camera Markers property (on by default) skips markers bound to a camera so camera bindings survive the wipe. It reports how many markers were removed.

**How to use:** In the Graph Editor or Dope Sheet header AniMatePro toolbar, "Utils" section, click the Delete All Markers button (delete-all icon, fifth in Utils). Select specific markers first to delete only those, or leave none selected to clear them all.

**Tip:** Keep Camera Markers defaults to on, so camera-bound markers are preserved; select the markers you want gone first if you only need to remove a few.

### Lock/Unlock Markers
*Toggle that locks or unlocks all timeline markers to prevent accidental moving or editing.*

**What it does:** This is a direct toggle bound to Blender's scene tool setting context.scene.tool_settings.lock_markers, not a custom operator. When enabled, markers on the timeline are locked so they cannot be selected, moved, or deleted by normal interaction; when disabled they are editable again. The button icon and depressed state reflect the current lock_markers value (locked vs unlocked icon).

**How to use:** In the Graph Editor or Dope Sheet header AniMatePro toolbar, "Utils" section, click the Lock/Unlock Markers button (last in Utils) to flip the locked state. The icon switches between locked and unlocked to show the current state.

**Tip:** Lock markers once your timing is set so you don't drag them by accident while editing keyframes; this is the same setting as Blender's native marker lock, so it stays in sync everywhere.

## View

Framing, zooming and isolating in the editors.

### Normalize
*Toggles Graph Editor F-curve value normalization, with an auto-renormalize sub-toggle.*

**What it does:** This control exposes Blender's two built-in Graph Editor normalization properties in the AniMatePro header rather than a custom operator. The first toggle (NORMALIZE_FCURVES icon) flips space_data.use_normalization, which rescales every visible F-curve into a shared -1..1 range so curves with very different magnitudes (for example location in meters versus rotation in radians) can be viewed and edited side by side. The second toggle (FILE_REFRESH icon) flips use_auto_normalization, which re-computes the normalization automatically as curve values change. It only affects how curves are displayed, not the stored keyframe values.

**How to use:** Graph Editor only (the button is hidden in the Dope Sheet). In the View section of the AniMatePro header click the Normalize (NORMALIZE_FCURVES) icon to turn normalization on or off; click the refresh icon immediately to its right to toggle auto-normalization.

**Tip:** The auto-normalization (refresh) button is greyed out until Normalize is enabled. Normalize is a view aid only and never changes your actual keyframe values.

### Smart Zoom
*Zooms the editor to a frame window centered on the playhead and fits the visible curve values within it.*

**What it does:** The icon runs anim.amp_smart_zoom_frame_editors (AMP_OT_SmartZoom), passing 0 so it falls back to the preference value. It builds a horizontal window around the current frame, from current - range - 1 to current + range + 1, where range is the add-on preference 'Frame Range to Zoom to' (default 15, minimum 2). It then fits the vertical value range of the visible F-curves that fall inside that window, adding vertical padding (50 px) and honoring normalization if it is on. In the Graph Editor it first calls view_all and then frames the computed window; in the Dope Sheet it frames the horizontal window. The small number field beside the icon edits that frame-range preference live.

**How to use:** In the View section of the AniMatePro header (Graph Editor or Dope Sheet), click the Smart Zoom icon to zoom in around the playhead. Type a value into the narrow number field next to the icon to change how many frames on each side of the current frame are included.

**Tip:** The number field is the half-width in frames around the current frame, so lower it for a tighter zoom and raise it to see more surrounding keys.

### Frame selected/all
*Fits all keyframes in the editor and snaps the scene Start/End frames to the active action's range.*

**What it does:** This button (frame-action icon) runs anim.amp_timeline_tools_frame_action_range (AMP_OT_frame_action_range) with scene_range_to_action enabled. It first calls the active editor's View All - graph.view_all in the Graph Editor, action.view_all in the Dope Sheet, or nla.view_all in the NLA - so every keyframe is fit into view. It then sets the scene's Start and End frames to the active object's action range: it uses the action's manual frame range when Use Frame Range is enabled, otherwise it computes the min/max from the action's keyframes. It warns if there is no active action or the action has no keyframes.

**How to use:** In the View section of the AniMatePro header (Graph Editor / Dope Sheet / NLA), click this button once. It both fits the keyframes in view and rewrites the scene frame range to match the action.

**Tip:** Unlike a plain view-all, this also changes the scene Start/End frames, so use it to re-fit the playback range after you add or trim keyframes.

### Frame Action
*Toggles the editor view between framing all keyframes and framing only the selected keyframes.*

**What it does:** This button runs anim.amp_zoom_frame_editors (AMP_OT_FrameEditors, 'Frame sel/all Keyframes'). If any keyframes are selected it calls View Selected to fit just those; if nothing is selected it calls View All to fit everything. The Graph Editor uses graph.view_*, while the Dope Sheet uses action.view_*. Its icon updates with state - a 'zoom selected' icon when keyframes are selected and a 'zoom all' icon otherwise. This is a pure view operation and never changes keyframes, ranges, or selection.

**How to use:** In the View section of the AniMatePro header (Graph Editor / Dope Sheet), select the keyframes you want to focus on and click to frame just those; click with nothing selected to frame all keyframes.

**Tip:** Watch the button icon - it switches between the selected-zoom and all-zoom glyphs to show which action the next click will perform.

### Solo
*Toggle that isolates the F-curves holding selected keyframes and hides the rest; press again to restore.*

**What it does:** Runs anim.amp_isolate_selected_fcurves (AMP_OT_isolate_selected_fcurves), a toggle that is shown depressed while active (tracked by the solo_fcurve preference). When solo is off, it selects the F-curves that contain selected keyframes, hides all unselected curves via graph.hide(unselected=True), and turns solo on; if exactly one curve is isolated it also sets the channel list's filter_text to that bone or object name. When solo is already on, it clears the filter text and calls graph.reveal to bring every curve back, restoring visibility. The button is greyed out unless there are selected keyframes or solo is currently active.

**How to use:** Graph Editor only, View section. Select one or more keyframes on the curves you want to focus on, then click Solo to hide all other curves; click Solo again to reveal everything.

**Tip:** Default keyboard shortcut is W. Isolating a single curve also filters the channel list down to that bone/object name so the editor stays uncluttered.

## Selection

Selection sets and channel selection by transform type.

### Selection Sets
*Popover for creating, organizing, and one-click selecting named groups of objects/bones.*

**What it does:** Opens the AMP_PT_AnimSetsPanelPop panel where you build named Selection Sets from the currently selected objects or bones and organize them into Presets. Each set is drawn as a clickable button (with optional color/icon) that re-selects all of its members via the anim.amp_anim_set_select operator; clicking replaces the selection, SHIFT adds to it, and CTRL toggles it. Sets remember whether they hold objects or bones (set_type), so adding/toggling bone sets is blocked while in Object mode and vice-versa. You can add/remove members, pin sets, reorder them, and copy/paste whole presets.

**How to use:** In the Graph Editor or Dope Sheet AniMatePro header, open the 'Selection' category and click the Selection Sets icon to open the popover. Select some objects/bones, press the + (Add) button to create a set, then click any set button later to reselect those members (SHIFT to add, CTRL to toggle). Use the gear/Settings toggle to reveal the configuration list, presets, and color/icon/order options.

**Tip:** Pinned sets are the ones shown as quick buttons, and up to 9 pinned presets get numbered color swatches for fast preset switching.

### Select All
*Selects (and isolates) every animation F-curve of the selected objects/bones.*

**What it does:** Runs anim.view_anim_curves_all, which calls the anim.amp_toggle_fcurves_selection operator with action_type=ALL and deselects everything first. By default it selects all F-curves for the active selection and isolates them (hiding other channels) when the isolate preference is on. Modifier keys change the behavior: SHIFT shows/toggles all curves (exits isolate), CTRL (or the OS key) cycles through curves one at a time, and ALT toggles channel visibility.

**How to use:** Select your object or pose bones, then in the Graph Editor / Dope Sheet AniMatePro header open the 'Selection' category and click the 'Select All' (all curves) button. Hold SHIFT, CTRL, or ALT while clicking to toggle-all, cycle, or toggle-visibility respectively.

**Tip:** Whether it isolates (hides) the non-matching curves is controlled by the Anim Curves options popover (isolate/cycle/solo preferences) in the 'Tools' section.

### Select Loc
*Selects/isolates only the Location (translation) F-curves.*

**What it does:** Runs anim.view_anim_curves_loc, delegating to anim.amp_toggle_fcurves_selection with action_type=TRANSLATION and a deselect-all-first step, so only location channels of the selected objects/bones remain selected. With the isolate preference active it also hides the other channels. SHIFT toggles all curves, CTRL cycles through them one by one, and ALT toggles their visibility.

**How to use:** Select an object/bones, then in the AniMatePro header 'Selection' category of the Graph Editor or Dope Sheet click the 'Select Loc' button to isolate the location curves. Use SHIFT/CTRL/ALT for show-all, cycle, or visibility toggle.

### Select Rot
*Selects/isolates only the Rotation F-curves.*

**What it does:** Runs anim.view_anim_curves_rot, which calls anim.amp_toggle_fcurves_selection with action_type=ROTATION after deselecting all curves, leaving only the rotation channels selected (and isolated if that preference is enabled). The same modifier scheme applies: SHIFT shows/toggles all, CTRL cycles through curves, ALT toggles visibility.

**How to use:** With an object or bones selected, open the 'Selection' category in the Graph Editor / Dope Sheet AniMatePro header and click 'Select Rot'. Hold SHIFT/CTRL/ALT to change behavior as above.

**Tip:** Pairs well with the Euler Filter / Euler Gimbal tools in the 'Utils' section when cleaning up rotation curves.

### Select Scale
*Selects/isolates only the Scale F-curves.*

**What it does:** Runs anim.view_anim_curves_scale, calling anim.amp_toggle_fcurves_selection with action_type=SCALE and deselecting everything first, so only scale channels of the selected objects/bones are selected (and isolated when the isolate preference is on). SHIFT toggles all curves, CTRL cycles through them, and ALT toggles channel visibility.

**How to use:** Select your object/bones, then in the AniMatePro header 'Selection' category of the Graph Editor or Dope Sheet click 'Select Scale'. Use SHIFT/CTRL/ALT for show-all, cycle, or visibility toggle.

### Select CustomProps
*Selects/isolates the F-curves driving custom properties.*

**What it does:** Runs anim.view_anim_curves_custom_props, which invokes anim.amp_toggle_fcurves_selection with action_type=CUSTOMPROPS after a deselect-all, isolating the F-curves that animate custom properties (e.g. rig controls and IK/FK switches) on the selected objects/bones. Modifier keys behave as elsewhere: SHIFT shows/toggles all, CTRL cycles one curve at a time, ALT toggles visibility.

**How to use:** Select a rig control or object, then in the Graph Editor / Dope Sheet AniMatePro header open the 'Selection' category and click 'Select CustomProps'. Hold SHIFT/CTRL/ALT to modify the action.

**Tip:** Handy for quickly grabbing animated rig sliders that are not part of the standard location/rotation/scale channels.

### Select ShapeKeys
*Selects/isolates shape-key animation F-curves.*

**What it does:** Runs anim.view_anim_curves_shapes, calling anim.amp_toggle_fcurves_selection with action_type=SHAPES and deselecting all first, so only shape-key value channels are selected (and isolated if that preference is on). SHIFT shows/toggles all, CTRL cycles through curves, ALT toggles visibility. By default this button is configured inactive in both the Graph Editor and Dope Sheet headers and is meant to be enabled via the header customization toggles.

**How to use:** Select the deforming object, then in the AniMatePro header 'Selection' category click 'Select ShapeKeys' (enable it first in the header customization if it appears dimmed). Use SHIFT/CTRL/ALT for show-all, cycle, or visibility toggle.

**Tip:** Best used together with the Shape Key Editor button in the 'Action' section when working on facial or corrective shapes.

### Select Constraints
*Selects/isolates F-curves that animate constraint influence.*

**What it does:** Runs anim.view_anim_curves_constraints, which calls anim.amp_toggle_fcurves_selection with action_type=CONST after deselecting all, leaving only the constraint-influence channels of the selected objects/bones selected (and isolated when that preference is on). The usual modifiers apply: SHIFT shows/toggles all, CTRL cycles, ALT toggles visibility. Like Select ShapeKeys, this button defaults to inactive in both editor headers and is intended to be turned on via header customization.

**How to use:** Select the constrained object/bone, then in the Graph Editor / Dope Sheet AniMatePro header 'Selection' category click 'Select Constraints' (enable it in header customization if dimmed). Hold SHIFT/CTRL/ALT to change behavior.

**Tip:** Useful for animating IK/FK or snap blends where only the constraint influence value is keyed.

### Show Handles
*Graph Editor toggle for showing or hiding Bezier handles.*

**What it does:** This is a direct toggle on the Graph Editor's space setting (space_data.show_handles) rather than a custom operator. When on, F-curve Bezier handles are drawn so you can grab and tweak them; when off, only the keyframe points are shown. The button icon reflects the current state (handles on/off) and it only functions in the Graph Editor.

**How to use:** In the Graph Editor AniMatePro header, open the 'Selection' category and click the 'Show Handles' toggle to turn handle display on or off. It is a simple on/off toggle and is inactive outside the Graph Editor.

**Tip:** Turn this off to declutter dense curves; pair it with 'Only Handles for Selected' to show handles only where you are working.

### Only Handles for Selected
*Graph Editor toggle to draw handles only on selected keyframes.*

**What it does:** Toggles the Graph Editor's space_data.use_only_selected_keyframe_handles setting (drawn with an inverted checkbox), so handles appear only for currently selected keyframes instead of every visible key. Its row is only active when 'Show Handles' is enabled, and the icon switches between 'selected-only' and 'all' handle states. It is a Graph-Editor-only toggle with no effect in the Dope Sheet.

**How to use:** In the Graph Editor AniMatePro header 'Selection' category, make sure 'Show Handles' is on, then click 'Only Handles for Selected' to limit handle drawing to selected keys (click again to show handles for all keys).

**Tip:** Great for cleaning up a crowded Graph Editor so only the keys you are editing display their handles.

## Editor switches (Action)

Quick switches that turn the active editor into a specific animation editor.

### Graph Editor
*Switches the current animation editor area in place to Blender's Graph (F-Curve) Editor.*

**What it does:** Calls the AniMatePro space.amp_animation_editors operator with space_type GRAPH_EDITOR, which sets the active area's ui_type to FCURVES. It converts whatever animation editor you are currently in (Dope Sheet, Action, etc.) into the Graph Editor without opening a new window or losing your screen layout. The button highlights (depresses) when the current area's ui_type is already FCURVES, so it doubles as a live indicator of the active editor.

**How to use:** In the AniMatePro top header bar of the Graph Editor or Dope Sheet, find the 'Action' section and click the Graph (curve) icon. The area you clicked from instantly becomes the Graph Editor.

**Tip:** Use this together with the Dope Sheet and Action Editor buttons next to it to flip the same panel between editors quickly instead of changing the editor type from Blender's corner dropdown.

### Dope Sheet
*Switches the current animation editor area to the Dope Sheet in its basic Dope Sheet mode.*

**What it does:** Runs space.amp_animation_editors with space_type DOPESHEET_EDITOR and subspace_type DOPESHEET, which sets the area's ui_type to DOPESHEET and then sets the space's mode to DOPESHEET. This gives you the standard all-channels Dope Sheet view of keyframes for the scene. The button depresses when the area is already a Dope Sheet in DOPESHEET mode.

**How to use:** In the 'Action' section of the AniMatePro top header (visible in the Graph Editor and Dope Sheet), click the Dope Sheet (action) icon. The current area switches to the Dope Sheet.

**Tip:** The Dope Sheet, Action Editor, Shape Key, Grease Pencil, Mask and Cache File buttons all target the same DOPESHEET editor and just change its internal mode, so they share one panel.

### Action Editor
*Switches the current area to the Dope Sheet's Action Editor mode for editing a single action.*

**What it does:** Calls space.amp_animation_editors with space_type DOPESHEET_EDITOR and subspace_type ACTION. It sets the area ui_type to DOPESHEET and then sets the space mode to ACTION, giving you the Action Editor where you can assign, browse and stash a single active action on the selected object. The button is highlighted when the Dope Sheet is already in ACTION mode.

**How to use:** In the 'Action' section of the AniMatePro top header, click the Action Editor (object data) icon. The area becomes the Dope Sheet in Action Editor mode.

**Tip:** Use the Action Editor when you want to manage and swap whole actions on a rig; switch to plain Dope Sheet when you want to see all animated channels at once.

### Shape Key Editor
*Switches the current area to the Dope Sheet's Shape Key mode for animating shape key values.*

**What it does:** Runs space.amp_animation_editors with space_type DOPESHEET_EDITOR and subspace_type SHAPEKEY, setting the area ui_type to DOPESHEET and the space mode to SHAPEKEY. This shows only shape-key (morph target) channels and their keyframes, which is useful for facial and corrective shape animation. It depresses when the Dope Sheet is already in SHAPEKEY mode.

**How to use:** In the 'Action' section of the AniMatePro top header, click the Shape Key (shapekey data) icon. The area switches to the Shape Key channel view of the Dope Sheet. By default this button is hidden in the header until enabled in the section customization, where it appears in the button list.

**Tip:** This view only shows meaningful channels when the active object has shape keys; if it looks empty, select a mesh that has shape keys.

### Grease Pencil Editor
*Switches the current area to the Dope Sheet's Grease Pencil mode for editing drawing frames.*

**What it does:** Calls space.amp_animation_editors with space_type DOPESHEET_EDITOR and subspace_type GPENCIL. It sets the area to DOPESHEET and then to the Grease Pencil mode, with a version-aware fallback that picks GPENCIL, GREASEPENCIL or GREASE_PENCIL depending on which identifier the running Blender exposes. This shows Grease Pencil layers and their drawing keyframes so you can time 2D frames. The button highlights when the Dope Sheet is already in a Grease Pencil mode.

**How to use:** In the 'Action' section of the AniMatePro top header, click the Grease Pencil icon. The area becomes the Grease Pencil timeline. By default it is hidden in the header until you enable it in the section customization list.

**Tip:** Because the mode name changed across Blender versions, this button automatically maps to the correct Grease Pencil mode for your version, so it works on both legacy and new Grease Pencil.

### Mask Editor
*Switches the current area to the Dope Sheet's Mask mode for animating mask shapes.*

**What it does:** Runs space.amp_animation_editors with space_type DOPESHEET_EDITOR and subspace_type MASK, setting the area ui_type to DOPESHEET and the space mode to MASK. This displays mask layers and their animated keyframes, used for compositing and rotoscoping masks. The button depresses when the Dope Sheet is already in MASK mode.

**How to use:** In the 'Action' section of the AniMatePro top header, click the Mask (mask modifier) icon. The area switches to the mask keyframe view. By default it is hidden in the header until enabled in the section customization.

**Tip:** Mask animation channels only appear when a mask datablock exists; this mode pairs with masks created in the Image/Clip editors.

### Cache File Editor
*Switches the current area to the Dope Sheet's Cache File mode for Alembic/USD cache timing.*

**What it does:** Calls space.amp_animation_editors with space_type DOPESHEET_EDITOR and subspace_type CACHEFILE. It sets the area to DOPESHEET and the space mode to CACHEFILE, exposing imported cache file (Alembic/USD) channels and their timing in the Dope Sheet. The button is highlighted when the Dope Sheet is already in CACHEFILE mode.

**How to use:** In the 'Action' section of the AniMatePro top header, click the Cache File (file) icon. The area switches to the cache file channel view. By default this button is hidden in the header until enabled in the section customization list.

**Tip:** This is only relevant when your scene has imported geometry cache files; it lets you retime or inspect their keyed channels alongside other animation.

### NLA Editor
*Switches the current area to Blender's Nonlinear Animation (NLA) Editor.*

**What it does:** Runs space.amp_animation_editors with space_type NLA_EDITOR, which maps to ui_type NLA_EDITOR and switches the active area to the NLA Editor. Unlike the other Action buttons it sets no subspace mode, since the NLA Editor has no Dope Sheet submodes. There you can layer, blend and reorder action strips for nonlinear animation. The button depresses when the area's ui_type is already NLA_EDITOR.

**How to use:** In the 'Action' section of the AniMatePro top header (Graph Editor or Dope Sheet), click the NLA icon. The current area converts into the NLA Editor.

**Tip:** Pair this with the Action Editor button: push an action down to an NLA strip in the Action Editor, then switch here with this button to arrange and blend your strips.

## Other and sidebar tools

Tools that live in the 3D Viewport sidebar or their own popovers.

### Stepper
*Adds a Stepped F-Curve modifier to selected (or all) objects so playback snaps to a held-pose look without baking keys.*

**What it does:** Stepper runs the anim.amp_anim_stepper operator, which loops over the F-Curves of the active action (including armature pose-bone channels) and adds a Blender 'STEPPED' F-Curve modifier named 'AnimStep', or updates the existing one. It exposes Step (number of frames to skip, default 2), Offset (phase shift of the stepping, default 0), and 'Affect All in Scene' to target every object instead of just the selection. Because it is a non-destructive F-Curve modifier, the underlying keyframes are untouched and a companion Remove operator (anim.amp_remove_anim_stepper) strips the AnimStep modifier off selected objects or the whole scene.

**How to use:** In the Graph Editor or Dope Sheet header, click the Stepper button (AMP_anim_step icon) to open its popover. Select your object(s)/bones, set Step and Offset, then click 'Add Anim Stepper' (or 'Update Scene' to affect all). Use 'Remove from selected' / 'Remove from All' in the same popover to clear the modifier. The popover's 'Affect All in Scene' checkbox toggles whether the add button targets the whole scene.

**Tip:** Step is non-destructive: it stacks a Stepped modifier on top of your curves, so you can dial in or remove the stepped look at any time without losing your original keyframes.

### Camera Stepper
*Bakes objects or bones so they hold their screen-space position relative to the scene camera across keyframe intervals.*

**What it does:** Camera Stepper manages a per-scene list (TIMELINE_object_list) of objects/armatures and bakes a duplicate action (suffix '_baked_to_scene_camera') in which each tracked element keeps its matrix relative to the active scene camera. For every interval between existing keyframes it captures the element's camera-relative matrix and re-applies it, inserting Loc/Rot/Scale keys (per selected bone for armatures), optionally limited to user-defined frame ranges. Each list item has a 'Use Baked Action' toggle that swaps the object between its original and the camera-stepped baked action, and Disable removes the baked action and the list entry.

**How to use:** In the Graph Editor or Dope Sheet header, click the Camera Stepper button (AMP_anim_cam_step icon) to open its popover. Select objects/bones and press the '+' (Enable) to add them to the list; for armatures, expand and add specific bones. Add Frame Ranges if you only want part of the timeline. Use the FILE_REFRESH button to Bake the selected item, then toggle 'Use Baked Action' per item to view the camera-locked result; '-' (Disable) removes the bake.

**Tip:** Requires an active scene camera (baking aborts with an error if none is set). The baked action is a separate copy, so toggling 'Use Baked Action' lets you compare the camera-locked version against your original animation.

### AutoKeying
*Toggles Blender's auto-keyframe insertion with an added visual 'recording' theme, viewport frame, and on-screen text.*

**What it does:** AutoKeying drives Blender's tool_settings.use_keyframe_insert_auto. The anim.amp_autokeying_toggle operator flips auto-key on/off, deactivating AnimOffset when enabling and applying/resetting a custom recording theme (selection color, pose-bone outline, playhead, and editor header highlights) via the addon preferences. A companion settings panel (ANIMATEPRO_PT_AutoKeying_Properties) lets you configure an optional colored viewport FRAME (inner frame + passepartout, with per-editor frames for Timeline/Graph/NLA), configurable on-screen TEXT, and OFFSET controls to position those overlays.

**How to use:** Click the AutoKeying button (red dot icon) in the sidebar/header to toggle auto-keying; when on, the recording theme and viewport frame/text overlays appear. Open its settings panel to expand FRAME, TEXT, and OFFSETS sections and toggle each overlay (eye icons) and tune color, width, position, and per-editor frames. The THEME (Experimental) section enables selection/pose-bone/playhead/header highlight colors.

**Tip:** This is a toggle, not a one-shot: with it on, every transform you make inserts keyframes automatically. The colored frame and red theme are deliberate visual cues that you are 'recording' so you don't accidentally key over your animation.

### Anim Baker
*Bakes selected channels to keyframes via a props dialog, with a shape-preserving Smart mode or a regular-interval Step mode.*

**What it does:** Anim Baker runs anim.amp_anim_baker, which wraps Blender's nla.bake but adds a 'Smart' bake that stores each original keyframe's value/interpolation/handles, bakes, then deletes the extra in-between keys and restores the originals so the curve shape and key count are preserved; 'Step' mode instead keys at a fixed Step interval. It exposes scope/range, interpolation type (Bezier/Linear/Constant/Preserve) and handle type, channel filters (Location, Rotation, Scale, B-Bone, Props), Pose vs Object data, and options like Only Selected Bones, Visual Keying, Clear/ Mute Constraints (with Key Muted Constraints), Clear Parents, Overwrite Current Action, Clear NLA Tracks, and Clean Curves. After baking it also sets the action to HOLD extrapolation / REPLACE blend / full influence and can wipe NLA tracks.

**How to use:** In the Graph Editor or Dope Sheet header, click the Anim Baker button (AMP_anim_baker icon). A props dialog opens: choose Bake Type (Smart or Step + Step value), set Only Selected Bones / Overwrite Current Action / Clear NLA / Visual Keying, pick interpolation and handles, configure constraint/parent handling, choose Pose or Object data, and enable the channel toggles you want. Click OK to bake.

**Tip:** Use 'Smart' to consolidate NLA strips, constraints, or visual transforms into a single action while keeping your exact keyframe timing and curve shape; use 'Step' only when you actually want keys on every Nth frame. For Smart bakes, Blender's NLA tracks should be in Replace or Combine for correct evaluation of source interpolation and handles.
