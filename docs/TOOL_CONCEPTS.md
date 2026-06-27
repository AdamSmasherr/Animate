# AniMatePro: two advanced tool concepts

Stage 3 deliverable. Two professional, animator facing tools designed to the ambition tier of Pose Polator and Anim Link, and kept distinct from every existing AniMatePro tool and from each other. They were chosen from 10 candidate ideas generated across five design lenses (timing and spacing, physics and secondary motion, body mechanics, workflow and layering, transfer and reuse), then scored by a review panel on novelty, daily animator value, ambition, prototype feasibility and distinctness. Each spec below is written to be implementation ready: real Blender 5.1 API surfaces, real data paths, and concrete AMP_ class and operator names so a working prototype can be built directly from it.

## The two tools at a glance

**Whiplash**: Whiplash is a non-destructive, velocity-driven overlap engine that lives on top of your hand keys and procedurally generates lag, drag, overshoot, and settle down any FK control chain (tails, hair, capes, ropes, ears, antennae, fingers, spine, dangling props). You point it at a chain; each frame it reads the leading control's velocity and acceleration and propagates springy, delayed follow-through through the descendants with per-bone stiffness, damping, drag, and a falloff that weakens down the chain. It is fully art-directable: sculpt the response with stiffness/drag curves, pin segments to keep crisp control where you want it, add wind/gravity bias, and set collision planes so a tail won't pass through the hip. Because it's a live layer it survives retiming and pose changes for free, and when you're happy you 'stamp' it to real keyframes on twos or threes that automatically match the surrounding key cadence so the result is hand-editable and pipeline-clean. It turns a half-day of mechanical overlap cleanup per shot into a few sliders and a stamp.

**Groundwork**: Groundwork auto-detects contact events by analyzing control velocity and proximity to surfaces, then plants those controls in world space, or onto any moving reference such as the ground, a prop, or another character's rig, as soft weighted pins that are re-solved every refresh instead of baked. Because the plant is live, it survives retiming, pose edits higher up the chain, and IK/FK toggles without the foot ever drifting. Each contact carries an editable peel profile so you shape heel-strike, ball roll, and toe-off as a curve and slide the exact release frame without disturbing neighboring keys. A continuous slip meter reports sub-pixel world-space drift on every active contact and flags the precise frames where a foot that should be locked is actually ice-skating, the error your eye feels but can't locate. When the motion is approved, Groundwork bakes clean keys only on the contact controls, leaving the rest of your animation and your existing IK/FK structure untouched.

---

## Whiplash

### Name
**Whiplash**, a non-destructive, velocity-driven overlap & follow-through engine for AniMatePro.

### Core idea
Whiplash is a *live procedural layer* that sits on top of an animator's hand keys. You point it at an FK control chain (parent → child → grandchild …), and on every evaluated frame it reads the **leading control's motion** (position, velocity, acceleration in world space) and propagates a **spring/damper follow-through** down the descendants. Each bone lags, drags, overshoots, and settles based on per-bone stiffness, damping, drag, and a chain falloff. The result is computed at depsgraph-evaluation time so it survives retiming, pose edits, and scrubbing for free. When the animator is happy, a **Stamp** operation bakes the simulated motion to real, hand-editable keyframes that snap to the surrounding key cadence (on ones/twos/threes).

It is explicitly *kinematic-procedural*, not a rigid-body sim: it never replaces the animator's poses, it only adds the trailing motion the animator would otherwise key by hand.

### What animator problem it solves
Mechanical overlap/follow-through cleanup is one of the most universal and time-expensive parts of polish. For every shot with a tail, cape, hair, rope, antenna, ear, dangling prop, finger, or spine, the animator must hand-offset and hand-overshoot each child control a few frames behind its parent, re-tune it after every timing change, and redo it when the lead pose changes. This is hours of repetitive, physics-intuition work per shot. Whiplash automates the *generation* of that trailing motion while keeping it fully art-directable and bakeable.

### Why it is valuable
- **Daily, universal pain:** nearly every character shot has at least one overlapping appendage.
- **Retime-safe:** because it's a live layer reading velocity per evaluated frame, a TimeWarper/Retimer change automatically re-derives correct lag, no re-cleanup.
- **Pose-safe:** change the lead pose and the follow-through updates instantly.
- **Pipeline-clean:** the Stamp produces ordinary F-Curve keyframes matching the shot's cadence, so downstream animators, leads, and the renderer never see a custom dependency.
- **Flagship-tier novelty:** an art-directable, retime-safe lag-propagation solver that bakes to clean keys is on par with Pose Polator / Anim Link, and is *distinct* from every existing tool (see below).

### How it improves / speeds up the workflow
- Turns a half-day of manual overlap per shot into a few sliders + one Stamp.
- Live preview while scrubbing, no bake-iterate-rebake loop during tuning.
- Per-bone sculpting (stiffness/drag curves, pinning) gives directorial control without giving up automation.
- Re-runnable: tweak a parameter, re-stamp, done. The previous stamp is tracked so it can be cleanly replaced.

### Distinctness from existing AniMatePro tools
- **AnimOffset** only *slides existing keys* behind a magnet/mask, it cannot *invent* trailing motion that the animator never keyed. Whiplash generates new motion from velocity.
- **Flex/Realtime Mopaths** edit *path geometry* in space, not time-domain lag/settle physics.
- **Anim Lattice / Anim Curves / Anim Sculpt** transform existing F-Curve values; they are physics-blind.
- **InBetweens / Nudge / Smart Keyframes / Match Keyframes** are key utilities with no velocity model.
- **Baker** bakes constraints/visual transforms generically; Whiplash bakes its *own* solver output snapped to cadence.
- It is neither **Pose Polator** (pose-space blending) nor **Anim Link** (static relationship rigging with no velocity/lag/settle).

---

### Use cases (concrete)
1. **Cat tail on a run cycle.** Animator keys hip + 2 base tail controls for broad S-shape. Whiplash is pointed at the 9-bone tail chain; it generates whip, drag on direction changes, and a settle when the cat stops. Animator dials stiffness down toward the tip for a loose lash, pins bone 2 to keep the root crisp, adds slight gravity bias, stamps on twos.
2. **Cape on a hero turn.** Character does a sharp 180. Whiplash reads the spine/shoulder lead and trails the cape's FK control chain with overshoot, then adds a wind bias and a collision plane at the back/hip so the cape doesn't intersect the torso. Director asks for the turn to happen 4 frames earlier, animator slides the key in Retimer, the cape lag re-derives automatically, re-stamp.
3. **Antennae / ears on a head bob.** A creature nods; long antennae need delayed counter-motion and a soft settle. Animator uses a falloff curve so the base antenna is stiff and the tip is floppy, scrubs to confirm settle frames, stamps on threes to match the shot's pose cadence.
4. **Dangling prop (keychain / rope / pendant).** A single-chain prop parented under a hand control; Whiplash trails it through fast hand moves and lets it settle on holds. Pin the top segment to the hand, let the rest swing.
5. **Finger drag on a hand wave** (subtle secondary): low-amplitude lag added to finger FK controls for organic offset.

---

### UX design (overall interaction model)
Whiplash lives as a panel in the **3D Viewport N-panel → AniMatePro tab → "Whiplash"** sub-panel, plus a Graph Editor side-panel mirror for curve sculpting. The interaction model is **define chain → live-tune → stamp**:

1. **Define a chain (Setup mode):** select the FK bones in hierarchy order (or click "Auto-detect from selection" which sorts by parenting), press **Create Chain**. A `WhiplashChain` definition is stored on the armature object. The first selected/topmost bone becomes the **lead**; the rest are **followers**.
2. **Live-tune (Solve mode):** Whiplash registers a depsgraph handler and a per-bone "Whiplash" constraint-driver hybrid (see technical section). Scrubbing now shows the procedural follow-through in real time. The animator adjusts global sliders (stiffness, damping, drag, falloff), per-bone overrides, bias forces, and collision planes. A viewport overlay draws the chain, per-bone pin/stiffness state, predicted trail ghosts, and settle markers.
3. **Stamp (Bake):** press **Stamp to Keys**. Whiplash evaluates the solver across the chosen frame range, snaps insertion frames to the detected cadence, and writes keyframes onto each follower bone's transform channels in the active slotted action. The live layer can then be muted/removed, or left on for further iteration (re-stamp replaces the previous stamp via a tracked key-group).

The model is deliberately **two-state and reversible**: nothing is destructive until Stamp, and Stamp is itself re-runnable and undoable.

### Required buttons, modes, and panels

**Panels**
- `AMP_PT_whiplash_main` (Viewport N-panel): chain list, mode toggle, global sliders, Stamp button.
- `AMP_PT_whiplash_perbone` (sub-panel): per-bone stiffness/damping/drag/pin overrides for the active chain bone.
- `AMP_PT_whiplash_forces` (sub-panel): gravity/wind bias, collision planes list.
- `AMP_PT_whiplash_bake` (sub-panel): cadence mode (ones/twos/threes/match), frame range, channel mask, stamp/clear.
- `AMP_PT_whiplash_graph` (Graph Editor): stiffness-along-chain and drag-along-chain falloff curve widgets.

**Buttons / operators (see class list below)**
- Create Chain / Delete Chain / Auto-detect.
- Enable Live Solve (toggle) / Recompute.
- Add Pin / Clear Pin (per selected bone).
- Add Collision Plane (from selected object/empty) / Remove.
- Stamp to Keys / Clear Last Stamp / Re-stamp.
- Reset Chain Defaults, Mirror Chain Settings (L↔R).

**Modes** (enum on the chain): `SETUP`, `SOLVE` (live), `STAMPED` (baked, live layer muted).

### What data it uses
- **Inputs read per frame:** the lead bone's evaluated world matrix (`pose_bone.matrix` via `object.evaluated_get(depsgraph)`), derived to position/velocity/acceleration using current frame ± a sub-step; armature object world matrix; scene fps + frame range; each follower's *hand-key* rest/target matrix (the pose the animator keyed, used as the spring's anchor target).
- **State stored:** `WhiplashChain` property group on the armature object (`object.amp_whiplash_chains`), holding bone names in order, per-bone params, forces, collision plane refs, cadence settings, and a stamp manifest (which frames/channels were written, for clean clearing).
- **Solver scratch:** per-bone simulated position/velocity carried frame-to-frame in a cache keyed by frame (so scrubbing backward re-seeds deterministically from the range start).
- **Outputs:** simulated follower matrices applied live; on stamp, keyframes on `pose.bones[name]` transform channels in the active action slot.

---

### High-level technical behavior (algorithm)
Whiplash is a **per-bone position-based spring/damper integrator driven by the parent's kinematic motion**, evaluated forward across the frame range. Conceptual per-frame step for follower bone *i* down the chain:

1. **Read lead/parent target.** Compute the parent's evaluated world head/tip and the bone's *desired* (hand-keyed) world position `target_i` for this frame.
2. **Spring toward target.** A virtual point mass at the bone tip is pulled toward `target_i` by a Hookean force `F_spring = stiffness_i * (target_i - pos_i)`.
3. **Damp & drag.** Apply damping `-damping_i * vel_i` and aerodynamic drag `-drag_i * |vel_i| * vel_i`. Damping controls settle; drag controls how much the bone "falls behind" fast moves (the lag/whip feel).
4. **Bias forces.** Add gravity bias and wind bias (constant or noise-modulated vector), scaled by per-bone falloff.
5. **Integrate.** Semi-implicit (symplectic) Euler with `dt = 1/(fps * substeps)`; run *N* substeps per frame for stability on fast moves: `vel += F*dt; pos += vel*dt`.
6. **Length constraint.** Project `pos_i` back onto a sphere of the bone's rest length around the parent's simulated tip (PBD distance constraint), preserving bone length so the chain doesn't stretch.
7. **Collision.** For each collision plane, if `pos_i` is behind the plane, push it to the plane surface and remove the inward velocity component (with restitution/friction params).
8. **Pin handling.** If bone *i* is pinned, skip the spring solve and force `pos_i = target_i` (crisp follow), but still feed its motion to children.
9. **Falloff.** Per-bone effective stiffness/drag are modulated by a chain-falloff curve (index-normalized 0→1), so response weakens toward the tip by default.
10. **Convert to rotation.** Turn the solved tip position into the bone's local rotation (aim the bone from its parent tip toward `pos_i`, preserving roll), producing the pose-bone rotation that is applied live and, on stamp, keyed.

Because the integrator needs history, Whiplash maintains a deterministic cache: when the playhead lands on frame *f*, if cache is cold or *f* precedes the cached front, it re-simulates from the chain's `sim_start` frame forward to *f* (cheap: a few hundred frames × a handful of bones). Forward scrubbing is incremental.

### Which Blender API areas may be involved
- `bpy.app.handlers.frame_change_post` and `depsgraph_update_post` for the live layer; `bpy.app.handlers.persistent` so it survives file reload.
- `depsgraph = context.evaluated_depsgraph_get()`; `obj.evaluated_get(depsgraph)` to read post-constraint lead matrices.
- `pose_bone.matrix`, `.matrix_basis`, `bone.matrix_local`, `bone.length`, `armature.bones` for hierarchy.
- `mathutils` (`Vector`, `Quaternion`, `Matrix`) for the integrator and aim-rotation conversion.
- **Slotted/layered actions (Blender 5.1):** route all F-Curve access through slot-aware helpers, resolve the object's `animation_data.action` + assigned `action_slot`/`action_slot_handle`, get the active `ActionLayer`/`ActionStrip` (`action.layers[0].strips[0]`), and its `channelbag` for the slot via the channelbag helper, then read/create F-Curves from `channelbag.fcurves` rather than the legacy `action.fcurves`. New keys go through `pose_bone.keyframe_insert` with the correct slot active, or directly via `channelbag.fcurves.new(...)` + `keyframe_points.insert`.
- `keyframe_points`, `fcurve.update()`, handle types for clean key creation; `fcurve.evaluate()` to detect existing cadence.
- `gpu` + `gpu_extras.batch.batch_for_shader` and a `bpy.types.SpaceView3D.draw_handler_add` (POST_VIEW) for the overlay; `blf` for settle/frame labels.
- `bpy.types.PropertyGroup`, `PointerProperty`, `CollectionProperty`, `bpy.types.Operator`, `bpy.types.Panel`, `bpy.utils.register_class`.
- Optional: a transient `CHILD_OF`/`COPY_TRANSFORMS`-style application path, but the chosen design applies rotations via `matrix_basis` in the handler rather than real constraints, to stay non-destructive and avoid double-evaluation.

### How it works with pose bones, keyframes, F-Curves, actions, NLA, constraints, markers
- **Pose bones:** the live solver writes solved rotations into follower `pose_bone.matrix_basis` inside `frame_change_post`, *after* the depsgraph evaluates the animator's hand keys (so it layers on top). Lead bone is read-only.
- **Keyframes / F-Curves:** untouched during live solve. On **Stamp**, Whiplash inserts keys on follower rotation channels (and optionally location for non-connected bones). It uses the active slot's channelbag F-Curves; if a channel doesn't exist it's created slot-correctly.
- **Actions (layered/slotted):** all reads/writes resolve the active action **slot** first. Stamp tags created keys in a manifest so "Clear Last Stamp" removes exactly those keys without harming hand keys. A `WHIPLASH_STAMP` key-group/colour tag aids identification.
- **NLA:** live solve reads the *fully evaluated* result (so NLA-stacked motion on the lead is respected). Stamp writes into the active action of the object (the tweak action if in NLA tweak mode); a warning is shown if the object is under a non-tweak NLA strip so the animator stamps into the right place.
- **Constraints:** lead matrices are read post-constraint via the evaluated depsgraph, so IK/spline-IK on the lead is honored. Whiplash does not add permanent constraints.
- **Markers:** cadence detection can optionally snap stamps to timeline markers (e.g., key poses marked by the animator) in addition to existing key spacing.

### Edge cases to consider
- **Scrubbing backward / random seeking:** must re-simulate deterministically from `sim_start`; never produce frame-order-dependent results. Cache invalidation on any param change.
- **First-frame / pre-roll:** velocity at range start is zero unless a pre-roll/settle window is configured; offer "start at rest" vs "start from previous motion".
- **Looping cycles:** option to make the sim periodic (seed end state = start state) so cycles don't pop; tie into Anim Loop if present.
- **Very fast moves / instability:** clamp velocity, increase substeps, and cap max stiffness*dt; PBD length constraint prevents blow-up.
- **Bone length zero / connected vs free bones:** connected bones can only rotate (no location key); handle aim-only conversion.
- **Roll / gimbal:** preserve bone roll when aiming; output quaternion or compatible-euler to avoid flips (reuse Euler Filter on stamp).
- **Mixed rotation modes** across bones (XYZ vs quaternion): detect `rotation_mode` per bone and key the right channels.
- **Retime after stamp:** stamped keys are ordinary keys and will retime like any other; the live layer (if kept) re-derives, warn if both are active to avoid double follow-through.
- **Multiple chains sharing a bone / branching chains** (e.g., two ears off one head): support multiple chains; forbid a follower belonging to two chains.
- **Performance with many bones / multiple characters:** throttle solve to active object during playback; full-quality on stamp only.
- **Undo:** live handler state must rebuild after undo (handlers persistent; cache rebuilt lazily).
- **Library-linked / overridden rigs:** chain data stored on object; respect library override editability, fall back to read-only preview.
- **No assigned action slot:** stamp must create/assign a slot rather than silently failing on Blender 5.1.

### Available modes
- **Setup**, define/edit chains, no solving.
- **Solve (Live)**, procedural follow-through previews on scrub/playback.
- **Stamped**, keys baked; live layer muted (toggle to re-enter Solve for another pass).
- **Solo-bone tuning**, isolate one follower to tune its params with the rest pinned (visual aid).
- Cadence sub-modes for stamping: **Ones / Twos / Threes / Match-cadence / Match-markers**.

### User parameters
**Global (per chain):** `master_stiffness`, `master_damping`, `master_drag`, `chain_falloff` (curve), `substeps`, `gravity` (vector + scale), `wind` (vector + strength + noise freq/amp), `start_mode` (rest/continuous), `loop_solve` (bool), `length_stiffness` (PBD iterations), `solve_range` (start/end).
**Per bone:** `stiffness`, `damping`, `drag`, `pinned` (bool), `pin_weight` (0, 1 blend), `mass`, `falloff_override`, `collision_enabled`.
**Forces / collision:** collision plane list (object/empty ref or co+normal), `restitution`, `friction`, `margin`.
**Bake:** `cadence_mode`, `cadence_step`, `match_tolerance`, `channels` (rot/loc mask), `replace_previous_stamp` (bool), `bake_to_new_slot` (bool), `key_group_tag`.

### Desired visual hints / overlays (GPU)
- **Chain spline** drawn through current solved tip positions, colour-graded root→tip.
- **Per-bone state glyphs:** pinned bones shown as filled squares; stiffness as ring thickness; drag as a trailing comet tail.
- **Predicted trail ghosts:** faint onion-style ghosts of the next/previous N frames' solved positions (reuse Onion Skin GPU infra where possible).
- **Settle markers:** small labels (`blf`) on the timeline/viewport where the chain velocity drops below a settle threshold (helps choose stamp frames).
- **Collision planes** rendered as translucent quads with normals.
- **Lead velocity vector** drawn at the lead tip to make the driving motion legible.
- **Stamp preview:** before committing, ghost the exact frames that will receive keys (cadence dots on the timeline).

### MVP version (what ships first)
- Single linear FK chain per armature; create from selection in hierarchy order.
- Live solver: spring/damper + drag + chain falloff + PBD length constraint, semi-implicit Euler with substeps.
- Global sliders (stiffness/damping/drag/falloff/substeps) + per-bone stiffness override + per-bone **pin**.
- Gravity bias (single vector). No wind, no collision yet.
- Deterministic re-sim cache; live preview on scrub/playback for the active object.
- Minimal viewport overlay: chain spline + pin glyphs + lead velocity vector.
- **Stamp to Keys** with cadence modes Ones/Twos/Threes and Match-cadence, slot-aware F-Curve writing, stamp manifest + Clear Last Stamp.
- Euler-filter pass on stamped rotations.

### Advanced version (later)
- Wind (noise-modulated) and per-bone bias.
- Collision planes (and capsule/sphere colliders) with restitution/friction.
- Stiffness/drag *along-chain* curve widgets in the Graph Editor.
- Branching chains, multi-chain solve, mirror L↔R settings.
- Loop-aware periodic solving integrated with Anim Loop / Realtime Looper.
- Onion-style predicted trail ghosts + settle-frame auto-suggestion for stamp frames.
- Match-markers cadence; stamp directly into a dedicated NLA layer/slot.
- Per-character solve throttling and background pre-bake for heavy chains.
- Presets library (cat tail, cape, rope, antenna) as shareable JSON.
- Integration hooks: read TimeWarper/Retimer remap so live solve stays correct under non-linear retime.

---

### Approximate classes / operators / properties to create

**Property groups**
- `AMP_PG_whiplash_bone`, per-bone params (`stiffness`, `damping`, `drag`, `pinned`, `pin_weight`, `mass`, `falloff_override`, `collision_enabled`, `bone_name`).
- `AMP_PG_whiplash_plane`, collision plane (`object` PointerProperty, `co`, `normal`, `restitution`, `friction`, `margin`).
- `AMP_PG_whiplash_stamp_entry`, manifest row (`bone_name`, `data_path`, `array_index`, `frames`).
- `AMP_PG_whiplash_chain`, the chain (`name`, `lead_bone`, `bones` CollectionProperty of `AMP_PG_whiplash_bone`, `planes`, global params, `cadence_mode`, `solve_mode` enum, `stamp_manifest` CollectionProperty, `enabled`).
- Registered as `Object.amp_whiplash_chains` (CollectionProperty) + `amp_whiplash_active_index`.

**Operators**
- `AMP_OT_whiplash_create_chain`, `AMP_OT_whiplash_delete_chain`, `AMP_OT_whiplash_autodetect_chain`.
- `AMP_OT_whiplash_toggle_live` (enable/disable handler), `AMP_OT_whiplash_recompute`.
- `AMP_OT_whiplash_set_pin`, `AMP_OT_whiplash_clear_pin`.
- `AMP_OT_whiplash_add_plane`, `AMP_OT_whiplash_remove_plane`.
- `AMP_OT_whiplash_stamp`, `AMP_OT_whiplash_clear_last_stamp`, `AMP_OT_whiplash_restamp`.
- `AMP_OT_whiplash_reset_defaults`, `AMP_OT_whiplash_mirror_settings`.

**Panels**
- `AMP_PT_whiplash_main`, `AMP_PT_whiplash_perbone`, `AMP_PT_whiplash_forces`, `AMP_PT_whiplash_bake`, `AMP_PT_whiplash_graph`.

**UIList**
- `AMP_UL_whiplash_chains`, `AMP_UL_whiplash_planes`.

**Core (non-bpy) module**
- `amp_whiplash_solver.py` → `WhiplashSolver` (integrator, cache), `aim_to_rotation()`, `pbd_length_constraint()`, `resolve_collision()`.
- `amp_whiplash_actions.py` → slot-aware helpers: `get_active_channelbag(obj)`, `ensure_fcurve(channelbag, data_path, index)`, `detect_cadence(fcurves, frame_range)`, `snap_frames_to_cadence()`.
- `amp_whiplash_overlay.py` → GPU draw handler.
- `amp_whiplash_handlers.py` → persistent `frame_change_post` callback + registration.

---

### How a working prototype could be implemented (step by step)
1. **Scaffold properties.** Define the `AMP_PG_whiplash_*` groups; register `Object.amp_whiplash_chains` + active index. Add `AMP_PT_whiplash_main` with a `AMP_UL_whiplash_chains` list and a Create button.
2. **Chain creation.** `AMP_OT_whiplash_create_chain`: take `context.selected_pose_bones`, sort by walking `bone.parent` to establish order, store `lead_bone` (topmost) and follower `bones`. Init default params.
3. **Read pipeline.** In a helper, on a given frame, get `depsgraph = context.evaluated_depsgraph_get()`, `eobj = obj.evaluated_get(depsgraph)`, and read `eobj.pose.bones[lead].matrix` (world = `eobj.matrix_world @ pbmatrix`). Compute velocity/accel by also sampling frame−1 from the cache.
4. **Solver core (pure Python).** Implement `WhiplashSolver.step(frame)`: for each follower in order, do spring + damp + drag + bias, semi-implicit Euler over `substeps`, PBD length constraint to parent's simulated tip, optional collision, pin override. Maintain `self.cache[frame] = (positions, velocities)`; if asked for a frame before the cache front, re-sim from `solve_range[0]`.
5. **Apply live.** Implement `aim_to_rotation()` converting each solved tip world position into the follower's `matrix_basis` (compute desired world matrix aiming parent-tip→solved-pos with preserved roll, convert to local via parent matrix and `bone.matrix_local`). Register a `@persistent frame_change_post` handler that, for each enabled chain on the active object, runs the solver for the current frame and writes `pose_bone.matrix_basis`. Tag a flag to avoid recursion with `depsgraph_update_post`.
6. **Tuning UI.** Wire global sliders and per-bone overrides into the panels; on any param change, clear the solver cache so the next scrub re-sims. Add `AMP_OT_whiplash_set_pin`.
7. **Overlay.** In `amp_whiplash_overlay.py`, add a `SpaceView3D.draw_handler_add` POST_VIEW callback using `gpu` + `batch_for_shader('POLYLINE_UNIFORM_COLOR' / 'UNIFORM_COLOR')` to draw the solved chain spline, pin glyphs, and the lead velocity vector; `blf` for settle labels.
8. **Cadence detection.** In `amp_whiplash_actions.py`, `detect_cadence()` inspects the lead/nearby bones' existing `keyframe_points.co.x` deltas in the range to infer the dominant step (1/2/3); `snap_frames_to_cadence()` produces the target stamp frame list.
9. **Slot-aware bake.** `AMP_OT_whiplash_stamp`: resolve `obj.animation_data.action`, its assigned slot (`action_slot`), the active layer/strip channelbag (create if missing, create/assign a slot if none on Blender 5.1). For each follower and each stamp frame: run solver to that frame, read solved local rotation, `ensure_fcurve()` for each rotation channel, `keyframe_points.insert(frame, value)`. Record every written `(bone, data_path, index, frame)` in `stamp_manifest`. Run an Euler-filter pass; call `fcurve.update()`.
10. **Clear / re-stamp.** `AMP_OT_whiplash_clear_last_stamp` deletes exactly the manifest's keys; `AMP_OT_whiplash_restamp` clears then stamps. Toggle chain to `STAMPED` mode (mute live handler) so the baked keys and the live layer don't double up.
11. **Persistence & undo.** Mark handlers `@persistent`; on `load_post` rebuild handler registration from stored chains; rebuild solver cache lazily on first frame change. Verify undo restores both properties and a clean cache.
12. **Hardening.** Add velocity clamping, substep auto-bump on fast frames, zero-length/connected-bone handling, rotation-mode detection, and the NLA-tweak-mode warning. Then layer advanced features (wind, collision planes, falloff curves, branching, loop-aware solve).

---

## Groundwork

A contact-aware planting and slip-correction system for AniMatePro. Groundwork detects when a control touches a surface, holds that control in world space as a live, soft-weighted pin (re-solved every depsgraph refresh, never baked), lets you author the release as a peel curve, continuously measures sub-pixel world-space slip, and finally bakes clean keys onto contact controls only.

---

### Core idea

A *contact* is a time interval `[t_in, t_out]` during which a specific bone/control should hold a fixed world-space relationship to a *target* (world origin, a prop object, the ground mesh, or a bone on another rig). Instead of baking that into keys, Groundwork stores the contact as a lightweight datablock and enforces it **live** via a `frame_change_post` / depsgraph handler that, every frame, computes a corrective world matrix and pushes it onto the control's transform channels through a slot-aware F-Curve writer (or a managed constraint). Because enforcement is recomputed from the current evaluated scene each refresh, the plant automatically follows retimes, upstream pose edits, and IK/FK toggles.

Three things make it more than a constraint:
1. **Auto-detection** of contacts from velocity + proximity heuristics, so the animator does not hand-place every plant.
2. **Authorable peel profiles**, a normalized 0..1 weight curve per contact that shapes how the control releases (heel-strike → ball-roll → toe-off), with a draggable release frame that does not disturb neighbouring keys.
3. **A continuous slip meter** that reports per-frame world-space drift in pixels and Blender units and flags frames where a control that should be locked is actually ice-skating.

---

### What animator problem it solves

- **Foot/hand sliding ("ice-skating"):** the single most common, most visible polish defect. The eye registers it instantly but cannot localize the exact offending frame. Groundwork both prevents it (live plant) and locates it (slip meter flags exact frames).
- **Plants that don't survive editing:** today a manually keyed plant breaks the moment you retime, adjust a hip key, or flip IK↔FK. Groundwork re-solves, so the plant holds.
- **Contact on moving references:** planting a hand on a moving prop, a weapon, or another actor currently means fragile, manually-managed temporary constraints with brittle influence keying. Groundwork makes "stick to that moving thing for these frames" a first-class, peelable operation.
- **Surgical commitment:** when approved, only the contact controls get clean keys; the rest of the animation and the existing IK/FK rig structure is left untouched.

---

### Why it is valuable

- Targets a **universal, daily** defect with **no clean Blender-native solution** (AnimOffset is a contact-unaware sliding mask; constraints have no detection, no slip readout, no peel authoring).
- **Live, not baked** means it composes with the rest of AniMatePro (TimeWarper retime, Anim Sculpt, Stepper) without re-running.
- **Measurable:** the slip meter turns a vague "feels like it's sliding" note into an objective per-frame number, which is reviewable and gradeable.
- **Flagship-tier scope** (detection + live pin + slip measurement + peel authoring + surgical bake) yet **feasible** entirely in the Python API.

---

### How it improves / speeds up the workflow

- One **Scan** pass proposes all contacts on the selected controls across the playback range, no manual scrubbing to find foot-down frames.
- Plants update **interactively** while you keep blocking/polishing upstream; no bake/unbake loop.
- The **release-frame slider** retimes a peel-off without touching adjacent keys, so timing iteration is seconds not minutes.
- The slip overlay **navigates you to the failing frame** (jump-to-worst-slip), collapsing a hunt-and-pixel-peep task into a click.
- Final **surgical bake** produces clean, animator-friendly curves only where needed.

---

### Use cases

1. **Walk/run cycle cleanup.** Animator blocks a run; Groundwork scans the foot IK controls, detects four foot contacts, plants each to world. Slip meter flags 0.8 px drift on the left foot at frames 23, 27 caused by a hip overshoot. Animator fixes the hip; the plant holds the foot rock-solid. Peel profile sharpens the toe-off on frame 26.
2. **Hand on a moving prop.** Character grabs a sword hilt that is parented to a separately animated prop object. Animator selects the hand IK control, sets target = `Sword` object (optionally a vertex/face or an empty on the hilt), marks the grab interval. The hand now rides the moving sword perfectly; releasing is shaped by the peel curve so fingers peel off over 3 frames.
3. **Two-character interaction.** Character A's hand must stay locked on Character B's shoulder bone during a lift while B is animated independently. Target = bone `shoulder.L` on rig B. Live solve keeps contact through both rigs' edits; slip meter confirms zero relative drift.
4. **IK/FK toggle safety.** A planted foot authored in IK survives a mid-shot switch to FK because the plant re-solves against whichever control currently drives the foot (mapping configured per contact).

---

### UX design (overall interaction model)

A dockable **Groundwork** panel in the 3D Viewport sidebar (`View3D > Sidebar > AniMatePro > Groundwork`), backed by a scene-level collection of contact datablocks and a live solver toggle.

Interaction flow:
1. **Select** one or more contact controls (pose bones or objects).
2. **Scan** → Groundwork analyzes the playback range and populates a **Contacts list** (UIList) with proposed contacts (control, target, in/out frames, confidence).
3. **Review/adjust** each contact: nudge in/out frames, pick the target, edit the peel curve in a mini node-less curve widget (CurveMapping), toggle active.
4. **Solve live** is on by default; viewport shows plant markers and the slip overlay updates as you scrub/edit.
5. **Inspect slip** via the overlay and the per-contact slip readout; jump to worst frames.
6. **Bake** selected/all approved contacts to clean keys when done; live solver is automatically muted on baked contacts.

Two enforcement backends, user-switchable per project: **F-Curve write mode** (default, handler writes evaluated channels, no rig changes) and **Constraint mode** (managed `COPY_TRANSFORMS`/`CHILD_OF` with influence driven by the peel weight, for users who prefer constraint-visible behavior).

---

### Required buttons, modes, and panels

**Panel: `AMP_PT_groundwork_main`** (Sidebar, category "AniMatePro")
- `Scan Contacts` (operator button)
- `Add Contact From Selection` / `Remove Contact`
- `Solve Live` toggle (icon: PINNED)
- `Bake Selected` / `Bake All` / `Clear Bake`
- Enforcement-backend enum (F-Curve / Constraint)
- Master slip-overlay toggle + units enum (px / BU / both)

**Sub-panel: `AMP_PT_groundwork_contacts`**
- `AMP_UL_groundwork_contacts` UIList (columns: active checkbox, control name, target icon, in, out, confidence bar, slip-status dot)
- Per-selected-contact detail box: control display, target picker (object + optional subtarget bone/element), in/out frame fields, retime-safe release-frame slider.

**Sub-panel: `AMP_PT_groundwork_peel`**
- CurveMapping widget for the peel profile (X = normalized contact time, Y = plant weight 0..1)
- Preset buttons: `Hard Plant`, `Heel-Ball-Toe`, `Linear Release`, `Soft Settle`
- `Release Frame` slider + `Peel Length` (frames)

**Sub-panel: `AMP_PT_groundwork_slip`**
- Live slip readout (current frame px / BU) for selected contact
- `Worst Frame` indicator + `Jump To Worst` button
- Slip threshold field (flag frames above this)
- `Bake Slip To Marker Notes` (optional, writes timeline markers at flagged frames)

**Detection settings sub-panel: `AMP_PT_groundwork_detect`**
- Velocity threshold, proximity threshold, surface source (world plane Z / named ground object / per-control target), min contact length, smoothing window.

**Header/overlay toggles** (registered in `VIEW3D_HT_header` extension or a redraw overlay): plant markers, slip glyphs, peel ramp ghost.

---

### What data it uses

- **Evaluated world matrices** of the contact control and target each frame: `pose_bone.matrix` combined with `object.matrix_world`, or `object.matrix_world` for object controls; targets via `depsgraph.id_eval_get(...)`.
- **Velocity** = finite difference of evaluated world position across adjacent frames.
- **Proximity** = distance from control world position to the surface source (plane Z, nearest point on ground object via `object.closest_point_on_mesh`, or target origin).
- **F-Curves** of the control's transform channels (slot-aware), used for both writing the plant and the surgical bake.
- **Per-contact stored data** (custom PropertyGroup): control id, target id + subtarget, in/out frames, captured anchor matrix or anchor offset relative to target, peel CurveMapping, release frame, peel length, enforcement mode, baked flag, per-frame cached slip values.
- **Scene playback range** and current frame.

---

### High-level technical behavior (algorithm)

**Detection (Scan):**
1. For each selected control, sample evaluated world position over `[frame_start, frame_end]` (step 1) by advancing a temporary depsgraph evaluation (or reading a pre-collected cache built by stepping `scene.frame_set`).
2. Compute speed `v[f] = |p[f] - p[f-1]|` and surface distance `d[f]`.
3. Mark candidate planted frames where `v < v_thresh AND d < d_thresh`. Smooth the boolean mask (close gaps ≤ `merge_gap`, drop runs shorter than `min_len`).
4. Each surviving run becomes a proposed contact with `confidence = f(min speed, mean proximity, run length)` and a default target (the configured surface source).

**Live solve (per frame, in handler):**
1. For each active, non-baked contact whose `[t_in, t_out]` (extended by peel length) contains the current frame:
2. Evaluate the target's current world matrix `M_target` (or identity for world target).
3. The desired control world matrix = `M_target @ anchor_offset`, where `anchor_offset` was captured at the contact's lock frame as `M_target_lock⁻¹ @ M_control_lock`.
4. Compute current evaluated control world matrix `M_now`.
5. Sample peel weight `w = peel_curve(normalized_time)` (1 = fully planted, 0 = free).
6. Blend: `M_goal = blend_matrix(M_now, desired, w)` (separate lerp for translation, slerp for rotation).
7. Convert `M_goal` back into the control's **local** space and write its transform channels (loc/rot, optional scale), either by setting `pose_bone.matrix` / `object.matrix_world` for viewport display, and on bake by inserting keys.

**Slip measurement (per frame, fully planted region where `w≈1`):**
- `slip_BU[f] = |desired_world_pos[f] - desired_world_pos[t_in]|` measured in the *target's* frame (so a moving target contributes zero slip if the control rides it perfectly). Equivalently, residual = `|M_now_pos - desired_pos|` after solve, which captures cases where the solve can't fully satisfy the pin (e.g., constraint mode with limited influence or IK reach).
- `slip_px[f]` = project both world points to the active region via `view3d_utils.location_3d_to_region_2d` and take pixel distance (sub-pixel float). Frames above `slip_threshold` are flagged.

**Surgical bake:**
1. For each selected approved contact, step frames across `[t_in - peel, t_out + peel]`, solve `M_goal`, and `keyframe_insert` only the contact control's transform channels.
2. Optionally run Smart Keyframes cleanup / decimate on just those channels.
3. Set `baked = True`, mute live solve for that contact, leave all other channels and all constraints untouched.

---

### Which Blender API areas may be involved

- `bpy.app.handlers.frame_change_post` and `depsgraph_update_post` for the live solver; `bpy.app.handlers.persistent` so it survives file load.
- `depsgraph = context.evaluated_depsgraph_get()`, `obj.evaluated_get(depsgraph)`, `depsgraph.id_eval_get(...)` for true evaluated matrices.
- `mathutils` (`Matrix`, `Vector`, `Quaternion`, `.lerp`, `.slerp`) for blends and offsets.
- `pose_bone.matrix`, `pose_bone.matrix_basis`, `object.matrix_world`, `bone.convert_local_to_pose` / manual parent-space math.
- `object.closest_point_on_mesh()` and `BVHTree` (from `mathutils.bvhtree`) for ground proximity.
- F-Curve access through **slot-aware helpers** (see Blender 5.1 note below): `action.layers[].strips[].channelbag(slot)` to find/create the right channelbag, then `fcurves`.
- `bpy_extras.view3d_utils.location_3d_to_region_2d` for pixel slip.
- `gpu` + `gpu_extras.batch.batch_for_shader` and a `SpaceView3D.draw_handler_add` callback for all overlays (plant markers, slip glyphs, peel ramp).
- `keyframe_insert` / `fcurve.keyframe_points` for the bake; `bpy.types.Constraint` (COPY_TRANSFORMS / CHILD_OF) for constraint backend; drivers optional for influence.
- `PropertyGroup`, `CollectionProperty`, `CurveMapping` (via a node tree or `bpy.types.CurveMapping` host) for stored data and the peel curve.

---

### How it works with pose bones, keyframes, F-Curves, actions, NLA, constraints, markers

- **Pose bones:** primary case. Control is identified by `(armature_object, bone_name)`. Solve writes `matrix_basis` (or full `matrix`, decomposed to channels) in F-Curve mode.
- **Keyframes / F-Curves:** live mode never writes keys; it only sets evaluated transforms for display and recomputes each refresh. Bake is the only path that inserts keys, and only on the contact control's loc/rot(/scale) channels. **Slot-aware:** in Blender 5.1.2 layered/slotted actions are default, so all F-Curve lookups go through the active slot's channelbag rather than the legacy `action.fcurves`. A helper `amp_get_channelbag(id_obj, ensure=True)` resolves the object's animation data → action → active layer/strip → slot → channelbag.
- **Actions:** bake targets the active action's active slot. The tool records which slot it wrote to so Clear Bake can remove exactly those keys.
- **NLA:** live solve uses the fully evaluated result (so NLA-stacked motion is respected). Bake writes to the active action; if the object is in NLA tweak mode the user is warned. Optionally bake into a dedicated "Groundwork" NLA strip so plants are separable/mutable.
- **Constraints:** in Constraint mode Groundwork creates and tags managed constraints (named `AMP_GW_<contactid>`), drives influence from the peel weight, and removes them cleanly on bake/clear. It never edits user constraints. IK/FK toggle is handled by mapping the contact to whichever control currently drives the limb.
- **Markers:** optional output, flagged slip frames can be written as timeline markers / notes, and existing markers can seed manual contact intervals.

---

### Edge cases to consider

- **Moving target with its own retime:** anchor offset is stored relative to the target, so target motion is correct by construction; only re-capture if the user changes the lock frame.
- **IK reach / unreachable goal:** solve can't place the control exactly → residual slip is reported honestly rather than hidden.
- **Target deleted or renamed:** contact goes invalid; UIList shows an error dot, solver skips it.
- **Overlapping contacts on the same control** (e.g., bad scan): detect and warn; allow merge.
- **Handler recursion / depsgraph thrash:** guard with a re-entrancy flag; throttle to one solve per frame change; avoid writing channels that retrigger `depsgraph_update_post` infinitely.
- **Scale and non-uniform parent scale:** decompose carefully; offer translate-only plant option.
- **Render/playback performance:** cache offsets; skip overlay draw during animation playback if `is_playing` and overlay set to "edit only".
- **Undo:** live solver must not pollute undo stack; use evaluated-only display and only push undo on explicit bake/edit operators.
- **Slot/layer absence:** object with no action yet → bake creates a slotted action; live mode needs none.
- **Camera-relative pixel slip:** px depends on viewport; report BU as the authoritative number and px as a perceptual aid tied to the active 3D view.
- **Library-linked/overridden rigs:** writing channels may be blocked → fall back to constraint mode or warn.

---

### Available modes

- **Enforcement backend:** `FCURVE` (default, handler-driven evaluated write) | `CONSTRAINT` (managed constraints + influence).
- **Plant space:** `WORLD` | `TARGET_OBJECT` | `TARGET_BONE` | `TARGET_ELEMENT` (vertex/face on a mesh).
- **Detection mode:** `AUTO` (velocity+proximity scan) | `MARKER_SEEDED` (use markers) | `MANUAL` (user paints intervals).
- **Plant DOF:** `TRANSLATE` | `TRANSLATE_ROTATE` | `FULL` (incl. scale).
- **Slip units:** `PX` | `BU` | `BOTH`.
- **Overlay verbosity:** `OFF` | `EDIT_ONLY` | `ALWAYS`.

---

### User parameters

Detection: `velocity_threshold` (BU/frame), `proximity_threshold` (BU), `surface_source` (plane Z value / ground object / per-target), `min_contact_length` (frames), `merge_gap` (frames), `smoothing_window` (frames), `confidence_floor`.

Per contact: `control`, `target_object`, `target_subtarget`, `frame_in`, `frame_out`, `lock_frame`, `release_frame`, `peel_length`, `peel_curve` (CurveMapping), `plant_dof`, `enforcement_mode`, `active`, `baked`.

Slip: `slip_threshold` (px and/or BU), `slip_sample_step`.

Bake: `bake_step` (1 = every frame, or use detected keys), `bake_cleanup` (bool, decimate), `bake_to_nla_strip` (bool).

---

### Desired visual hints / overlays (gpu module)

- **Plant marker:** a small GPU disc/ring drawn at the planted world position, colored by state (green = locked, amber = peeling, red = slipping above threshold).
- **Slip glyph:** a short line from desired→actual control position, length exaggerated ×N for visibility, plus a numeric px/BU label near the control.
- **Slip ribbon in timeline/overlay:** a per-frame strip (reuse Time Visualizer style) showing slip magnitude as a heat ramp; flagged frames pop. Drawn via a 2D gpu batch in the timeline editor or as a sidebar mini-graph.
- **Peel ramp ghost:** a faint curve drawn along the contact interval showing the weight falloff and the release frame as a draggable vertical tick.
- All overlays via `SpaceView3D.draw_handler_add` (3D) and an editor draw handler (2D), using `gpu.shader.from_builtin('UNIFORM_COLOR'/'POLYLINE_UNIFORM_COLOR')` and `batch_for_shader`.

---

### MVP version (what ships first)

1. Scene PropertyGroups + Contacts UIList.
2. **Manual + auto Scan** detection for **pose-bone foot/hand controls**, world and single-object targets.
3. **F-Curve live solver** (translate + rotate) via `frame_change_post`, with re-entrancy guard and persistent handler.
4. Hard plant + a basic peel (linear release with editable release frame and peel length; CurveMapping optional but present with a couple presets).
5. **Slip meter:** BU and px readout for the selected contact, worst-frame jump, threshold flagging.
6. Minimal GPU overlay: plant markers + slip glyph + numeric label.
7. **Surgical bake** of selected contacts to the active slot, with baked-flag muting and Clear Bake.
8. Slot-aware channelbag helper for all F-Curve access.

### Advanced version (later)

- Constraint backend with peel-driven influence and clean teardown.
- Target = **bone on another rig** and **mesh element (vertex/face)** with BVH closest-point ground.
- Full CurveMapping peel authoring with Heel-Ball-Toe multi-segment presets and per-DOF weighting.
- Timeline slip ribbon heat-map integrated with Time Visualizer; bake slip to markers.
- Multi-character batch scan, contact templates/Selection-Set integration.
- IK/FK auto-mapping and survival across toggles; NLA "Groundwork" strip bake.
- Performance: background cache thread, decimate/cleanup on bake, playback-aware overlay throttling.
- Auto-suggest corrections (e.g., "hip overshoot at f23 caused 0.8px slip").

---

### Approximate classes / operators / properties

**Property groups**
- `AMP_PG_groundwork_contact`, one contact (control, target, frames, peel CurveMapping ptr, modes, baked, cached slip).
- `AMP_PG_groundwork_settings`, scene-level detection/slip/bake params, enforcement backend, overlay mode, contacts `CollectionProperty`, active index.

**Operators**
- `AMP_OT_groundwork_scan`, run detection over playback range.
- `AMP_OT_groundwork_add_contact` / `AMP_OT_groundwork_remove_contact`.
- `AMP_OT_groundwork_set_target` (target picker incl. eyedropper).
- `AMP_OT_groundwork_capture_anchor` (re-capture offset at lock frame).
- `AMP_OT_groundwork_toggle_solver` (enable/disable live handler).
- `AMP_OT_groundwork_set_release_frame` (retime-safe release drag).
- `AMP_OT_groundwork_apply_peel_preset`.
- `AMP_OT_groundwork_jump_worst_slip`.
- `AMP_OT_groundwork_bake` (selected/all) / `AMP_OT_groundwork_clear_bake`.
- `AMP_OT_groundwork_paint_interval` (modal manual mode).

**UI**
- `AMP_UL_groundwork_contacts` (UIList).
- `AMP_PT_groundwork_main`, `AMP_PT_groundwork_contacts`, `AMP_PT_groundwork_peel`, `AMP_PT_groundwork_slip`, `AMP_PT_groundwork_detect`.

**Helpers / non-UI**
- `amp_get_channelbag(id_obj, slot=None, ensure=False)`, slot-aware F-Curve access for Blender 5.1.2.
- `amp_groundwork_solve_frame(scene, depsgraph)`, handler body.
- `amp_groundwork_compute_slip(contact, depsgraph, region, rv3d)`.
- `amp_groundwork_draw_3d` / `amp_groundwork_draw_2d`, gpu draw handlers.
- `amp_world_to_local(control, M_goal)` / `amp_blend_matrix(a, b, w)`.

**Registered handler refs:** `_amp_gw_frame_handler`, `_amp_gw_depsgraph_handler`, `_amp_gw_draw3d_handle`, `_amp_gw_draw2d_handle`.

---

### How a working prototype could be implemented (step by step)

1. **Scaffold data.** Define `AMP_PG_groundwork_contact` and `AMP_PG_groundwork_settings`; attach settings to `bpy.types.Scene.amp_groundwork`. Host the peel `CurveMapping` (e.g., via a hidden node group or a `bpy.types.CurveMapping`-bearing helper) and store a pointer/index per contact.
2. **Slot-aware F-Curve helper.** Implement `amp_get_channelbag`: walk `id_obj.animation_data.action` → active `layers` → `strips` → `channelbag(slot)`; create layer/strip/slot when `ensure=True`. Route all reads/writes through it (never `action.fcurves`).
3. **Evaluated sampling utility.** Write a function that, given a control and a frame range, steps `scene.frame_set(f)`, fetches the evaluated depsgraph, and records world position/matrix. Use it for both scan and bake. Guard against modifying user state (restore current frame).
4. **Detection.** Implement `AMP_OT_groundwork_scan`: build position arrays, compute speed and proximity (plane Z first; BVH/closest-point later), threshold + smooth into runs, create contacts with confidence and default target. Populate the UIList.
5. **Anchor capture.** On contact creation, at `lock_frame` capture `anchor_offset = M_target_lock.inverted() @ M_control_lock` (identity target = world).
6. **Live solver.** Implement `amp_groundwork_solve_frame(scene, depsgraph)` registered as a `@persistent frame_change_post` handler. For each active, non-baked contact in range: evaluate target matrix, build `desired = M_target @ anchor_offset`, sample peel weight, blend with current evaluated matrix, convert to local, and set `pose_bone.matrix` / `object.matrix_world`. Add a module-level re-entrancy flag and skip when already solving.
7. **Toggle + persistence.** `AMP_OT_groundwork_toggle_solver` adds/removes the handler; register/unregister on addon load; mark handlers `@persistent` so they survive file open. Also hook `load_post` to re-validate contact references.
8. **Slip measurement.** In `amp_groundwork_compute_slip`, after solve, compute residual world distance (BU) and project to region for px via `location_3d_to_region_2d`. Cache per-frame into the contact; expose current-frame readout, worst frame, and threshold flags in `AMP_PT_groundwork_slip`. Implement `AMP_OT_groundwork_jump_worst_slip` to set `scene.frame_current`.
9. **Overlays.** Register `SpaceView3D.draw_handler_add` (3D) drawing plant rings + slip glyph + numeric labels with the `gpu` module and `batch_for_shader`; register a 2D editor draw handler for the slip ribbon. Respect overlay-mode and playback throttling.
10. **Peel authoring.** Draw the CurveMapping in `AMP_PT_groundwork_peel`; wire presets via `AMP_OT_groundwork_apply_peel_preset`; implement the retime-safe `AMP_OT_groundwork_set_release_frame` that shifts only the peel window (no neighbouring key edits, since live mode holds no keys).
11. **Surgical bake.** `AMP_OT_groundwork_bake`: for each selected approved contact, step frames over `[in-peel, out+peel]`, solve `M_goal`, `keyframe_insert` only that control's loc/rot(/scale) via the slot-aware channelbag; set `baked=True` and mute its live solve; optional decimate; record written slot for `Clear Bake`.
12. **Constraint backend (advanced).** Behind the enum, instead of writing channels, create/maintain `AMP_GW_<id>` COPY_TRANSFORMS/CHILD_OF constraints with influence = peel weight (driver or per-frame set), and remove them cleanly on bake/clear.
13. **Polish & guards.** Validation dots in the UIList, undo-safety (evaluated-only live writes), library-override fallback to constraint mode, and registration/unregistration of all classes, handlers, and draw handles in `register()`/`unregister()`.

---

## Why the other candidates were set aside

Cadence (rhythm/beats): genuinely novel metric/audio-transient timing model and strong for action/dance/comedy, but narrower than the winners (rhythm-heavy shots only) and its global-conform behavior risks fighting an animator's hand-set spacing; strong runner-up. Cadence (blocking-to-spline, duplicate name): overlaps heavily with Ladder and with Stepper, and its core promise is narrower than a full flagship. Ladder (bodywide spacing chart): excellent craft idea but stays in tangent/spacing-reshaping territory adjacent to Anim Curves/Anim Sculpt, and is more a refinement instrument than a generative powerhouse. Ballistic (Newtonian interpolation): clever but thematically crowds Whiplash (physics) while serving far fewer shots (thrown/bouncing/airborne only). Ballast (weight/COM/support polygon): novel and appealing, but overlaps Groundwork's physical-body territory and the COM-settle solver is the least feasible/most failure-prone part to prototype reliably. Strata (non-destructive layers + takes): highly ambitious and valuable, but borders on reimplementing Blender's existing NLA/action-layer infrastructure and is a large system rather than a focused tool, lowering prototype feasibility. Anim Quarry (motion matching/reuse): impressive but depends on a feature-indexed studio corpus most users don't have, making it the least feasible and least 'daily' for solo animators. Verve (style/motion-texture transfer): strong novelty via frequency-band intent/texture split, but capturing a robust transferable signature and grafting it cleanly per-bone is research-heavy and riskier to ship than the two winners, and it sits thematically near Whiplash in the 'add life' space.
