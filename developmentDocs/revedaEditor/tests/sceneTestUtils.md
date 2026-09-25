# `revedaEditor\tests\sceneTestUtils.py`

**Module:** `revedaEditor.tests.sceneTestUtils`

## Purpose

Helpers for building an offscreen schematicScene in tests without
pytest-qt: a QObject container with a stubbed editor window.

## Classes

- `_Container(QObject)`

## Functions

- `makeSchematicScene()`
- `makeLayoutScene()` — Build an offscreen layoutScene with a stubbed editor window.

## Depends on

- [[revedaEditor\scenes\schematicScene|revedaEditor.scenes.schematicScene]]

## Used by

- [[revedaEditor\tests\test_connectivity|revedaEditor.tests.test_connectivity]]
- [[revedaEditor\tests\test_copy_array|revedaEditor.tests.test_copy_array]]
- [[revedaEditor\tests\test_correspondence|revedaEditor.tests.test_correspondence]]
- [[revedaEditor\tests\test_fit_bounds|revedaEditor.tests.test_fit_bounds]]
- [[revedaEditor\tests\test_layout_connectivity|revedaEditor.tests.test_layout_connectivity]]
- [[revedaEditor\tests\test_layout_groups|revedaEditor.tests.test_layout_groups]]
- [[revedaEditor\tests\test_layout_productivity|revedaEditor.tests.test_layout_productivity]]
- [[revedaEditor\tests\test_netexpr|revedaEditor.tests.test_netexpr]]
- [[revedaEditor\tests\test_netlisting|revedaEditor.tests.test_netlisting]]
- [[revedaEditor\tests\test_pitch_repro|revedaEditor.tests.test_pitch_repro]]
- [[revedaEditor\tests\test_schematic_checks|revedaEditor.tests.test_schematic_checks]]
- [[revedaEditor\tests\test_schematic_ux|revedaEditor.tests.test_schematic_ux]]
- [[revedaEditor\tests\test_sdl_adapter|revedaEditor.tests.test_sdl_adapter]]
- [[revedaEditor\tests\test_sdl_free_baseline|revedaEditor.tests.test_sdl_free_baseline]]
- [[revedaEditor\tests\test_sdl_persistence|revedaEditor.tests.test_sdl_persistence]]
- [[revedaEditor\tests\test_wire_editing|revedaEditor.tests.test_wire_editing]]
