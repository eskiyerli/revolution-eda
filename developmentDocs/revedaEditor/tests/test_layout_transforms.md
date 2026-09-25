# `revedaEditor\tests\test_layout_transforms.py`

**Module:** `revedaEditor.tests.test_layout_transforms`

## Purpose

Module in `revedaEditor\tests`.

## Functions

- `init_qapp()`
- `loader()`
- `test_rect_round_trip_preserves_rotation_and_flip()`
- `test_loader_accepts_legacy_layout_record_without_transform_fields()`
- `test_gdstk_transform_matches_editor_flip_matrix()`
- `test_gds_export_skips_layout_rulers()`
- `test_ruler_record_round_trip()`
- `test_ruler_legacy_rotated_record_recovers_direction()`
- `test_ruler_legacy_flipped_record_recovers_endpoints()`
- `test_delete_all_rulers_cancels_in_progress_ruler()`
- `test_gds_export_reuses_identical_pcell_geometry()`
- `test_gds_export_keeps_via_enclosures_local_to_instance_cell()`
- `test_layout_load_restores_scene_index_after_bulk_insert()`
- `test_layout_loader_skips_unknown_records()`
- `test_layout_loader_stops_recursive_instance_reference()`
- `_writeLayoutCell()`
- `_makeLayoutScene()`
- `test_instance_with_bbox_defers_child_construction()`
- `test_deferred_instance_realises_children_on_shapes_access()`
- `test_instance_without_bbox_computes_bounds_from_dicts()`
- `test_instance_with_unboundable_record_loads_eagerly()`
- `test_nested_deferred_instance_stays_deferred()`
- `test_deferred_recursive_instance_does_not_recurse()`
- `test_deferred_pcell_realises_on_shapes_access()`
- `test_encoder_writes_instance_bbox()`
- `test_encoder_writes_deferred_instance_bbox_without_realising()`

## Depends on

- [[defaultPDK\layoutLayers|defaultPDK.layoutLayers]]
- [[defaultPDK\pcells|defaultPDK.pcells]]
- [[defaultPDK\process|defaultPDK.process]]
- [[revedaEditor\common\__init__|revedaEditor.common.__init__]]
- [[revedaEditor\fileio\exportGDS|revedaEditor.fileio.exportGDS]]
- [[revedaEditor\fileio\layoutEncoder|revedaEditor.fileio.layoutEncoder]]
- [[revedaEditor\fileio\loadJSON|revedaEditor.fileio.loadJSON]]
- [[revedaEditor\scenes\layoutScene|revedaEditor.scenes.layoutScene]]
