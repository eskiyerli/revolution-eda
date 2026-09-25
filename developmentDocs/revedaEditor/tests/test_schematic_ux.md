# `revedaEditor\tests\test_schematic_ux.py`

**Module:** `revedaEditor.tests.test_schematic_ux`

## Purpose

Phase 4 schematic UX: find/replace, marker persistence, bus ripper,
clipboard paste, and descend edit-in-place.

## Functions

- `qapp()`
- `_net()`
- `_symbol()`
- `test_find_nets_by_resolved_name()`
- `test_find_instances_and_prop_filter()`
- `test_find_pins()`
- `test_replace_hit_renames_all_net_segments()`
- `test_replace_instance_and_pin()`
- `test_marker_records_roundtrip()`
- `test_bus_rip_off_trunk()`
- `test_bus_rip_off_bus_pin()`
- `test_no_rip_on_plain_net()`
- `test_bus_rip_descending_trunk()` — Buses like d<7:0> must rip the same way ascending ones do.
- `test_bus_rip_descending_index_bounds()` — The one-shot index is validated against min/max, not lo<=x<=hi.
- `test_bus_rip_member_connects_to_bus()` — A ripped member wire must resolve onto the bus by namesMatch.
- `test_clipboard_copy_paste_roundtrip()`
- `test_paste_rejects_non_fragment_clipboard()`
- `_childLibrary()`
- `test_descend_in_place_ghost_transform()`
- `test_descend_in_place_writeback()`
- `test_ascend_in_place_removes_ghosts()`
- `test_cycle_path_mode()`

## Depends on

- [[revedaEditor\checks\schematic|revedaEditor.checks.schematic]]
- [[revedaEditor\common\net|revedaEditor.common.net]]
- [[revedaEditor\common\shapes|revedaEditor.common.shapes]]
- [[revedaEditor\tests\sceneTestUtils|revedaEditor.tests.sceneTestUtils]]
