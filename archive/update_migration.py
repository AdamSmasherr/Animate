import sys

content = """
### Stage 5 - Replace Legacy Action API in Shared and High-Risk Tools
- **Status**: PASSED
- **Result**:
  - Replaced legacy `action.fcurves` with `utils.curve.get_active_fcurves_obj()` in all high-risk curve tools (`anim_curves`, `anim_nudger`, `anim_lattice`, `anim_sculpt`, `anim_timewarper`, `anim_shifter`, `anim_baker`).
  - Implemented proper fallback/iterators in `utils/blender_compat.py`.
- **Files Changed**:
  - Multiple `anim_*/*.py` tools and `utils/curve.py`.

### Stage 6 - Update Dope Sheet / Graph Header Integration
- **Status**: PASSED
- **Commands Run**:
  ```powershell
  & "D:\\GOG\\steamapps\\common\\Blender\\blender.exe" --background --factory-startup --python tools\\blender_smoke_test.py
  & "D:\\GOG\\steamapps\\common\\Blender\\blender.exe" --background --factory-startup --python tools\\blender_create_smoke_scene.py
  ```
- **Result**:
  - Smoke tests `blender_smoke_test.py` and `blender_create_smoke_scene.py` passed without any errors.
  - Successfully replaced legacy headers with current Blender 5.1 header clones with only `use_normalization` hidden.
  - Ensured toggle properties fallback safely if rendering custom headers fails.
  - `GPENCIL` to `GREASEPENCIL` enum capability checks updated.
- **Files Changed**:
  - `AMP_AniMatePro/ui/blender_ui.py`
  - `AMP_AniMatePro/utils/operators.py`
"""

with open(r'D:\Code\AMP_AniMatePro\AMP_AniMatePro_v0.25.10318\tools\MIGRATION_STATUS.md', 'a', encoding='utf-8') as f:
    f.write(content)
