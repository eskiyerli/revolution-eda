# `revedaEditor\tests\test_layout_productivity.py`

**Module:** `revedaEditor.tests.test_layout_productivity`

## Purpose

Phase 5 layout-editing productivity tests.

## Functions

- `init_qapp()`
- `scene()`
- `_rect()`
- `_encode()`
- `_instanceWithRect()`
- `test_instance_defaults_not_arrayed()`
- `test_instance_array_fields_encode_round_trip()`
- `test_instance_array_loads_from_record()`
- `test_instance_array_bounds_cover_all_elements()`
- `test_instance_array_export_emits_aref()`
- `test_array_clones_realize_as_children()`
- `test_guard_ring_builds_rects_and_vias()`
- `test_guard_ring_without_via_builds_rects_only()`
- `test_shielded_path_offsets()`
- `test_bus_route_fanout()`
- `test_multipart_record_round_trip()`
- `test_multipart_setparams_rebuilds()`
- `test_multipart_export_children_in_parent_frame()`
- `test_scene_multipart_draw_two_clicks()`
- `_rectTuple()` — Axis-aligned rect corners as (left, top, right, bottom).
- `test_boolean_or_merges_overlapping()`
- `test_boolean_or_l_shape_returns_polygon()`
- `test_boolean_or_via_scene_is_undoable()`
- `test_boolean_and_intersects_group()`
- `_sceneArea()` — Shoelace area of the item's scene-space polygon.
- `test_boolean_xor()`
- `test_boolean_xor_identical_then_third()`
- `test_boolean_not_across_layers()`
- `test_boolean_grow_shrink()`
- `test_boolean_ignores_non_polygonal()`
- `test_flatten_rotated_instance()`
- `test_flatten_arrayed_instance_expands()`
- `test_flatten_selection_undoable()`
- `test_make_cell_from_selection()`
- `_exportLib()`
- `test_layer_map_remaps_output()`
- `test_cell_name_map()`
- `test_flatten_depth_keeps_top_ref()`
- `test_flatten_depth_zero_flattens_all()`
- `test_export_dialog_parsers()`
- `test_ruler_delta_label()`
- `test_ruler_delta_label_diagonal()`
- `test_ruler_mode_option_applies_to_draft()` — F3 ruler options: scene.rulerMode seeds new rulers and
- `test_ruler_snap_toggle()` — rulerSnapToEdge=False leaves the ruler start at the raw click.
- `test_delete_selected_rulers()`
- `test_delete_all_rulers_kept()`
- `test_guard_ring_via_arrays_stay_within_ring()` — Via centres must not overshoot the ring: xs is a *gap*, so the array
- `test_guard_ring_via_pitch_matches_min_pitch()` — For a ring sized to an exact multiple of min pitch the gap passed to
- `_labelItem()`
- `test_flatten_label_orient_under_rotated_parent()`
- `test_flattened_label_ang_round_trip()`
- `test_flatten_label_unrotated_parent_keeps_orient_only()`
- `test_flatten_via_array_rotation_round_trip()`
- `test_make_cell_refuses_overwrite()`
- `test_make_cell_registers_in_library_model()`

## Depends on

- [[defaultPDK\layoutLayers|defaultPDK.layoutLayers]]
- [[defaultPDK\process|defaultPDK.process]]
- [[revedaEditor\common\layoutBoolean|revedaEditor.common.layoutBoolean]]
- [[revedaEditor\common\layoutFlatten|revedaEditor.common.layoutFlatten]]
- [[revedaEditor\common\layoutMerge|revedaEditor.common.layoutMerge]]
- [[revedaEditor\common\layoutShapes|revedaEditor.common.layoutShapes]]
- [[revedaEditor\fileio\layoutEncoder|revedaEditor.fileio.layoutEncoder]]
- [[revedaEditor\fileio\loadJSON|revedaEditor.fileio.loadJSON]]
- [[revedaEditor\tests\sceneTestUtils|revedaEditor.tests.sceneTestUtils]]
