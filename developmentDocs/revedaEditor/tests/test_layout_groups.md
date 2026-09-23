# `revedaEditor/tests/test_layout_groups.py`

**Module:** `revedaEditor.tests.test_layout_groups`

## Purpose

Persistent layout item group tests (`layoutGroup` + `Group` records):
group/ungroup behaviour, selection-as-unit, transform composition on
release, undo/redo, encoder/factory round-trips, clipboard, connectivity
anchors, `LayoutGeometryReader` expansion, and nested groups.

## Functions

- `init_qapp()`
- `_rect()`
- `_group_two()`
- `_top_lefts()`
- `test_group_selected_items_creates_container()`
- `test_group_requires_two_items()`
- `test_group_moves_members_as_unit()`
- `test_ungroup_restores_toplevel_items()`
- `test_ungroup_after_move_preserves_positions()`
- `test_rotated_group_ungroup_composes_member_transforms()`
- `test_group_undo_redo()`
- `test_ungroup_undo_regroups_members()`
- `test_ungroup_undo_on_moved_group_restores_children()`
- `test_group_encodes_and_recreates()`
- `test_moved_group_record_preserves_transform()`
- `test_grouped_pin_still_anchors_net()`
- `test_grouped_label_still_anchors_net()`
- `test_group_copies_to_clipboard_as_group()`
- `test_paste_recreates_group()`
- `test_reader_expands_group_records()`
- `test_reader_shifts_grouped_anchors()`
- `test_nested_groups_ungroup_one_level()`

## Depends on

- [[defaultPDK/layoutLayers|defaultPDK.layoutLayers]]
- [[revedaEditor/common/layoutShapes|revedaEditor.common.layoutShapes]]
- [[revedaEditor/connectivity/__init__|revedaEditor.connectivity.__init__]]
- [[revedaEditor/fileio/layoutEncoder|revedaEditor.fileio.layoutEncoder]]
- [[revedaEditor/fileio/loadJSON|revedaEditor.fileio.loadJSON]]
- [[revedaEditor/tests/sceneTestUtils|revedaEditor.tests.sceneTestUtils]]
