# `revedaEditor/tests/test_correspondence.py`

**Module:** `revedaEditor.tests.test_correspondence`

## Purpose

Phase 6 tests: `sdl` persistence, incremental `updateFromSchematic` sync, flylines, cross-probing.

## Module docstring

Tests for schematic<->layout correspondence (backend/correspondence.py)
and the layoutScene SDL sync / flyline / cross-probe integration.

## Functions

- `init_qapp()`
- `_sysRecord()`
- `_desc()`
- `test_schematicInstances_extracts_sys_records()`
- `test_sdl_source_canonical_and_legacy_shapes()`
- `test_diff_adds_missing_and_keeps_matched()`
- `test_diff_removes_vanished_source_instances()`
- `test_diff_flags_label_drift()`
- `test_diff_adopts_matching_unsourced_and_skips_foreign()`
- `test_diff_wrong_cell_does_not_adopt()`
- `test_pcellParamsFor_maps_labels_and_reports_missing()`
- `test_flyline_endpoints_resolve_pin_nets()`
- `test_flyline_endpoints_skip_dangling_pins()`
- `_writeLibrary()` — Minimal library: mylib/top/schematic.json + mylib/sub views.
- `_writeSchematic()`
- `_schematicTuple()`
- `_sceneFor()`
- `test_updateFromSchematic_places_and_stamps()`
- `test_updateFromSchematic_is_incremental()`
- `test_updateFromSchematic_removes_and_adopts()`
- `test_sdl_field_persists_round_trip()`
- `test_flylines_draw_for_unrouted_and_clear_when_routed()`
- `test_flylines_track_instance_moves()` — Flylines re-anchor to pin positions on move and drop when the
- `test_cross_probe_targets_for_selected_instance()`
- `test_selectProbeTargets_selects_and_highlights()`

## Depends on

- [[defaultPDK/layoutLayers|defaultPDK.layoutLayers]]
- [[revedaEditor/backend/correspondence|revedaEditor.backend.correspondence]]
- [[revedaEditor/backend/dataDefinitions|revedaEditor.backend.dataDefinitions]]
- [[revedaEditor/backend/libBackEnd|revedaEditor.backend.libBackEnd]]
- [[revedaEditor/common/__init__|revedaEditor.common.__init__]]
- [[revedaEditor/tests/sceneTestUtils|revedaEditor.tests.sceneTestUtils]]
