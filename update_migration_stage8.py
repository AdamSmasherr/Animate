import sys

content = """
### Stage 8 - Handlers, Draw Handlers, Message Bus, and Modal Tools
- **Status**: PASSED
- **Commands Run**:
  ```powershell
  & "D:\\GOG\\steamapps\\common\\Blender\\blender.exe" --background --factory-startup --python tools\\blender_smoke_test.py
  ```
- **Result**:
  - Replaced dangerous and slow string `eval()` loops registering/unregistering draw handlers in `autoKeying/utils.py` with static UI dictionaries mapping to `bpy.types.Space*`.
  - Added full idempotency (`try...except ValueError`) checks to all modal operators performing global GUI `.draw_handler_remove()` (`anim_scrub`, `anim_sculpt`, `anim_lattice`, `anim_timewarper`, and `utils/general`). Operators can now safely be interrupted/reloaded.
  - Verified `msgbus.subscribe_rna` registrations correctly track owners (`MSG_BUS_OWNER`, `"AUTOKEYING_ANIM_OFFSET"`) and execute `.clear_by_owner()` safely.
  - Hardened `anim_offset/support.py:magnet_handlers()` and `anim_poser.py` self-removal from `bpy.app.handlers.depsgraph_update_post` using `if handler in handler_list` guards, averting crashes if multiple updates happen concurrently.
- **Files Changed**:
  - `AMP_AniMatePro/autoKeying/utils.py`
  - `AMP_AniMatePro/anim_scrub/anim_scrub.py`
  - `AMP_AniMatePro/anim_sculpt/anim_sculpt.py`
  - `AMP_AniMatePro/anim_lattice/anim_lattice.py`
  - `AMP_AniMatePro/anim_timewarper/anim_timewarper.py`
  - `AMP_AniMatePro/utils/general.py`
  - `AMP_AniMatePro/anim_offset/support.py`
"""

with open(r'D:\Code\AMP_AniMatePro\AMP_AniMatePro_v0.25.10318\tools\MIGRATION_STATUS.md', 'a', encoding='utf-8') as f:
    f.write(content)
