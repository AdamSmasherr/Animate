# AniMatePro new tools

Two tools added in this work: **Time Visualizer** and **Onion Skin**. Both target
Blender 5.1 and follow the existing add on conventions (modern `gpu` module
drawing, per scene property groups, header section buttons).

---

## Time Visualizer (View section)

A GPU overlay for the **Dope Sheet** and **Timeline** (optionally the Graph
Editor) that makes time spacing readable directly on the time axis.

### What it draws
- **Checker bands**: alternating shaded bands, one band per step. The step
  defaults to the scene FPS so each band equals one second.
- **Second lines**: a vertical line at every whole second.
- **Second labels**: a text label at every whole second, either a plain second
  count (`1s`, `2s`) or a `m:ss` timecode.
- **Frame ticks**: a small tick at every frame, shown only when the editor is
  zoomed in enough to read them.

### Where to find it
- Open the **Graph Editor** or **Dope Sheet / Timeline** header. In the
  **View** category there is a clock (`TIME`) button.
  - Click the clock to toggle the overlay on or off.
  - Click the small arrow next to it to open the settings popover (colours,
    step, opacity, what to show, Graph Editor toggle, timecode).

### How it works
A single persistent `POST_PIXEL` draw handler is installed per editor type and
gated by the per scene `enabled` toggle, so there is no add / remove churn and
no handler leak. Frames are mapped to pixels through `region.view2d`, so the
overlay tracks panning and zooming exactly. Counts are capped so an extremely
zoomed out view never tries to draw thousands of primitives.

### Test in Blender
1. Open an animation with a few seconds of action and switch an editor to the
   Timeline or Dope Sheet.
2. In the View category click the clock button. Checker bands, second lines and
   second labels appear over the time axis.
3. Pan and zoom: the marks stay locked to real frames; zooming in far enough
   reveals per frame ticks.
4. Open the popover and change the step, colours and opacity; the overlay
   updates live. Toggle **Also In Graph Editor** and confirm it appears there.
5. Change the scene FPS and confirm the one second bands rescale.

---

## Onion Skin (Tools section)

GPU viewport ghosting for **armatures and any animated object** (meshes,
empties driving meshes, and so on). Semi transparent copies of the animated
mesh are drawn at other points in time so past and future poses are visible at
once. Multiple targets can be onion skinned at the same time, each with fully
independent settings.

### Getting started
1. Select an armature or animated object.
2. Open the **Onion Skins** panel: 3D Viewport sidebar (`N`) under the
   **Animation** tab, or the popover on the **Onion Skin** button in the Tools
   category of the Graph / Dope header.
3. Click **+** to add the active object as a target. For an armature the
   related deforming meshes are discovered automatically (parented, modifier
   linked or constraint targeted). Click **-** to remove a target and clean up
   its cache and Mesh In Front state.

### Modes
Each target picks one of four modes from the mode dropdown.

- **Snapshots**: manually place snapshots on specific frames. Add captures the
  current frame, the eye toggles each one, the frame number is editable, Prev /
  Next jump the playhead between snapshots, the trash clears all.
- **Frame Step**: onion skins at a regular interval, anchored to a grid that
  starts at the range start so the steps stay consistent as you scrub. Step
  Size, Before amount and After amount. Changing the counts does not force a
  re bake, only changing the step size does.
- **On Keyframes**: onion skins on the keyframe positions of the active pose
  bone (armatures) or all animated channels (other objects). Reads the active
  action through the slot aware compatibility layer and also scans stashed and
  pushed down NLA actions. Before / After amounts cap how many keys per side.
- **Before / After**: explicit per item frame offsets relative to the playhead
  (negative is past, positive is future), each with its own eye toggle. A new
  target starts with the default pair at -3 and +3, and Reset restores it.

### Drawing settings (gear on the target row)
- **Before / After colours** with independent eye toggles for each side.
- **Alpha gradient**: Alpha Start is the opacity of the nearest skin, Alpha End
  the farthest, interpolated by distance. Skins under 1% alpha are skipped.
- **Render modes**: X-Ray (see through), Solid (opaque, depth tested, back face
  culled). The dither variants are present and currently render as their base
  mode (see limitations).
- **Mesh In Front**: forces the related meshes to draw in front while active and
  restores their original state when disabled or removed.

### Refresh and caching
Geometry is produced by frame stepping: the playhead is moved to each needed
frame, the dependency graph is evaluated and every related mesh is read as
world space triangles. Results are cached per target by absolute frame, so
scrubbing only bakes newly needed frames. All baking is deferred to a one shot
timer, never run inside a draw or frame change handler.
- **Auto refresh**: editing animation invalidates the affected target through
  the depsgraph and a re bake is queued.
- **Manual refresh**: the refresh icon next to the mode dropdown forces a full
  re bake of the active target.

### Range limiting and global visibility
- The **Limit to Range** toggle in the panel header constrains baked and
  displayed frames to the preview range (if active) or the scene range.
- The eye at the top left toggles **all** onion skins at once. This is also the
  operator `anim.amp_onionskin_toggle`, which can be bound to a shortcut.

### Multi target
Add several armatures and objects. Each keeps its own mode, colours, alpha,
render mode, amounts, snapshots and Before / After list. Reorder targets with
the up / down arrows.

### Test in Blender
1. Open a character or animate a cube (a couple of location keys is enough).
2. Select it, open the Onion Skins panel, click **+**.
3. Mode **Frame Step**, Step Size 2, Before 2, After 2: four ghost copies
   appear around the playhead. Scrub and watch them follow.
4. Switch to **On Keyframes**: ghosts snap to the object or active bone keys.
5. Switch to **Snapshots**, click **Add** on a few frames, toggle eyes, edit a
   frame number; use Prev / Next to jump between them.
6. Open the gear, change Before / After colours, alpha and render mode; toggle
   Mesh In Front.
7. Add a second object as another target and confirm independent settings.
8. Toggle the top left eye to hide and show everything at once.

### Known limitations and future work
- Screen door dithering shaders for the X-Ray Dither and Solid Dither modes are
  not implemented yet; those modes currently fall back to their base render.
- Per element configuration lists and per element vertex group filtering are
  not in this build; a target uses all related meshes.
- Before / After uses frame stepping rather than the NLA strip duplication
  approach, which keeps it universal across object types.
- On disk presets are not implemented yet.
- Frame stepping bake is correct and universal but heavier than an NLA based
  bake on very dense rigs; baked frames per target are capped for safety.
