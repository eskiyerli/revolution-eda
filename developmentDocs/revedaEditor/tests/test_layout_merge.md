# `revedaEditor\tests\test_layout_merge.py`

**Module:** `revedaEditor.tests.test_layout_merge`

## Purpose

Module in `revedaEditor\tests`.

## Functions

- `init_qapp()`
- `_scene_with()`
- `_path()`
- `_rect()`
- `_polygon()`
- `test_collinear_paths_touching_end_to_end()`
- `test_collinear_paths_overlapping()`
- `test_transitive_path_chain()`
- `test_paths_extends_preserved_in_drawn_span()`
- `test_extend_longer_than_segment_does_not_bridge_gap()`
- `test_merged_extends_exact_when_extend_exceeds_length()`
- `test_paths_different_widths_no_merge()`
- `test_paths_different_layers_no_merge()`
- `test_paths_non_collinear_no_merge()`
- `test_paths_parallel_offset_no_merge()`
- `test_paths_disjoint_no_merge()`
- `test_vertical_paths_merge()`
- `test_path_name_preserved()`
- `test_rects_sharing_edge_merge_to_rect()`
- `test_overlapping_rects_merge_to_rect()`
- `test_lshaped_union_produces_polygon()`
- `test_corner_touching_rects_consumed()`
- `test_rect_polygon_overlap_merges()`
- `test_disjoint_shapes_no_merge()`
- `test_shapes_different_layers_no_merge()`
- `test_transitive_shape_chain()`
- `test_merged_polygon_points_are_qpoint()`
- `test_union_with_hole_is_keyhole_polygon()`
- `test_mixed_selection_merges_only_valid_group()`
- `test_paths_and_shapes_merge_independently()`
- `test_single_candidate_no_merge()`
- `test_undo_redo_cycle()`
- `_scene_area()`

## Depends on

- [[defaultPDK\layoutLayers|defaultPDK.layoutLayers]]
- [[revedaEditor\backend\undoStack|revedaEditor.backend.undoStack]]
- [[revedaEditor\common\__init__|revedaEditor.common.__init__]]
- [[revedaEditor\common\layoutMerge|revedaEditor.common.layoutMerge]]
