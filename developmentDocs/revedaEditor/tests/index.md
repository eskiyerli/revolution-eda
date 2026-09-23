# `revedaEditor/tests`

pytest suite (offscreen Qt) covering connectivity, encoders, layout ops, correspondence and platform hardening.

## Modules

- [[revedaEditor/tests/__init__|__init__.py]] — Test package marker
- [[revedaEditor/tests/conftest|conftest.py]] — pytest fixtures: offscreen `QApplication` and a minimal `qtbot` shim (no pytest-qt dependency)
- [[revedaEditor/tests/sceneTestUtils|sceneTestUtils.py]] — Headless scene construction helpers
- [[revedaEditor/tests/test_ai_snapshot_undo|test_ai_snapshot_undo.py]] — aiTerminal snapshot/undo integration tests
- [[revedaEditor/tests/test_connectivity|test_connectivity.py]] — Connectivity engine tests
- [[revedaEditor/tests/test_correspondence|test_correspondence.py]] — Phase 6 tests: `sdl` persistence, incremental `updateFromSchematic` sync, flylines, cross-probing
- [[revedaEditor/tests/test_diagnostics|test_diagnostics.py]] — Headless connectivity-diagnostics tests
- [[revedaEditor/tests/test_import_gds|test_import_gds.py]] — GDS import tests, including merge mode and grid snapping
- [[revedaEditor/tests/test_labels_nlp|test_labels_nlp.py]] — Label/PyLabel evaluation tests
- [[revedaEditor/tests/test_layout_connectivity|test_layout_connectivity.py]] — Layout connectivity and hierarchy-aware net-highlight tests (instance internals, mosaics, tap cells)
- [[revedaEditor/tests/test_layout_merge|test_layout_merge.py]] — Layout merge-geometry tests
- [[revedaEditor/tests/test_layout_groups|test_layout_groups.py]] — Persistent layout item group tests (layoutGroup, Group records, transforms, undo, connectivity, clipboard)
- [[revedaEditor/tests/test_layout_productivity|test_layout_productivity.py]] — Phase 5 tests: instance mosaics, multipart items, boolean layer ops, flatten/make-cell, stream options, rulers
- [[revedaEditor/tests/test_layout_ruler|test_layout_ruler.py]] — Ruler item tests
- [[revedaEditor/tests/test_layout_stretch|test_layout_stretch.py]] — Layout stretch-edit tests
- [[revedaEditor/tests/test_layout_transforms|test_layout_transforms.py]] — Layout transform/rotation tests
- [[revedaEditor/tests/test_lvs_mismatch_view|test_lvs_mismatch_view.py]] — LVS mismatch view tests
- [[revedaEditor/tests/test_net|test_net.py]] — Schematic net item tests
- [[revedaEditor/tests/test_netexpr|test_netexpr.py]] — Net-expression / netSet tests
- [[revedaEditor/tests/test_netlisting|test_netlisting.py]] — Netlister output tests
- [[revedaEditor/tests/test_params|test_params.py]] — CDF-lite parameter-model tests
- [[revedaEditor/tests/test_platform_hardening|test_platform_hardening.py]] — Phase 7 tests: lock files, autosave/crash recovery, bindkeys, session save/restore
- [[revedaEditor/tests/test_schema_validation|test_schema_validation.py]] — JSON schema-validation tests
- [[revedaEditor/tests/test_schematic_checks|test_schematic_checks.py]] — Schematic check-rule tests
- [[revedaEditor/tests/test_schematic_ux|test_schematic_ux.py]] — Schematic UX tests (Phase 4: find/replace, bus ripper, clipboard, edit-in-place)
- [[revedaEditor/tests/test_selection_state|test_selection_state.py]] — Selection-state machinery tests
- [[revedaEditor/tests/test_spiceNetlist|test_spiceNetlist.py]] — SPICE netlist-parsing tests
- [[revedaEditor/tests/test_symbol_pins|test_symbol_pins.py]] — Symbol pin and pin-locator tests
- [[revedaEditor/tests/test_wire_editing|test_wire_editing.py]] — Wire-editing semantics tests
