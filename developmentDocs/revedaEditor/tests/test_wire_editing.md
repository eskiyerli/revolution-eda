# `revedaEditor/tests/test_wire_editing.py`

**Module:** `revedaEditor.tests.test_wire_editing`

## Purpose

Wire-editing semantics tests.

## Functions

- `qapp()`
- `scene()`
- `_nets()`
- `_endpoints()`
- `_finishAt()`
- `test_auto_route_l_and_single_undo_macro()`
- `test_t_junction_splits_and_auto_terminates()`
- `test_pop_wire_vertex_resumes_chain()`
- `test_body_stretch_slides_segment()`
- `test_body_stretch_rubber_bands_neighbours()`
- `test_net_name_auto_increment()`
- `test_add_stretch_wires_l_route_orientation()`
- `test_uncommitted_wire_leaves_no_undo_entry()`
- `test_wire_draw_mode_cycling()`
- `test_wire_body_snap()`
- `test_snap_does_not_jump_a_grid()`
- `test_snap_terminates_on_grid_coincidence()`
- `test_parallel_wire_not_welded_at_one_grid()`

## Depends on

- [[revedaEditor/common/net|revedaEditor.common.net]]
- [[revedaEditor/tests/sceneTestUtils|revedaEditor.tests.sceneTestUtils]]
