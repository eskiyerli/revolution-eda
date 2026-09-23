# `revedaEditor/tests/test_import_gds.py`

**Module:** `revedaEditor.tests.test_import_gds`

## Purpose

GDS import tests, including merge mode and grid snapping.

## Functions

- `init_qapp()`
- `_make_parent()`
- `_make_import_lib()`
- `test_import_snaps_polygons_to_pdk_grid()` — Off-grid GDS coordinates must snap to the PDK snap grid.
- `test_import_scales_by_gds_unit_not_assumes_one_um()` — A GDS with 1 nm user unit must scale differently than one with 1 um.
- `test_import_reuses_referenced_cells()` — Referenced cells should be imported once, not once per reference.
- `test_import_converts_simple_gds_path_to_layout_path()` — A simple two-point GDS path with square caps becomes an editable layoutPath.
- `test_import_keeps_complex_paths_as_polygons()` — Multi-segment or round-cap paths stay as polygons.
- `test_import_round_cap_path_fallback_to_polygon()` — Round end caps cannot be represented by layoutPath and stay as polygons.
- `test_import_preserves_reference_rotation_and_flip()` — Reference rotation and x_reflection should round-trip to ang/fl.
- `test_import_merge_mode_appends_to_existing_cell()` — With mergeMode on, a second import appends shapes to the same cell
- `test_import_merge_mode_creates_missing_cell()` — Merge mode still creates cells that do not exist yet.

## Depends on

- [[revedaEditor/backend/libBackEnd|revedaEditor.backend.libBackEnd]]
- [[revedaEditor/fileio/importGDS|revedaEditor.fileio.importGDS]]
