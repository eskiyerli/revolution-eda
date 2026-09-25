# `revedaEditor\tests\test_copy_array.py`

**Module:** `revedaEditor.tests.test_copy_array`

## Purpose

Array copy options: rows×columns clipboard paste with X/Y pitch
(Virtuoso-style copy options driven by scene.copyOptions).

## Functions

- `qapp()`
- `_net()`
- `_symbol()`
- `_symbols()`
- `_nets()`
- `test_array_paste_count_and_offsets()`
- `test_array_paste_unique_instance_names()`
- `test_array_single_undo()`
- `test_rearm_rebuilds_group()`
- `test_rearm_without_armed_copy_is_noop()`
- `test_zero_offset_uses_bbox_pitch()`
- `test_layout_array_paste()`

## Depends on

- [[revedaEditor\backend\dataDefinitions|revedaEditor.backend.dataDefinitions]]
- [[revedaEditor\common\net|revedaEditor.common.net]]
- [[revedaEditor\common\shapes|revedaEditor.common.shapes]]
- [[revedaEditor\tests\sceneTestUtils|revedaEditor.tests.sceneTestUtils]]
