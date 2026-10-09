# `revedaEditor\tests\test_sdl_persistence.py`

**Module:** `revedaEditor.tests.test_sdl_persistence`

## Purpose

Persistence compatibility for RevSDL metadata owned by the free core.

## Functions

- `initQapp()`
- `_layoutRecord()`
- `_layoutData()`
- `_writeReferencedViews()`
- `_instance()`
- `_pcell()`
- `test_strict_schema_accepts_canonical_sdl()`
- `test_strict_schema_rejects_noncanonical_sdl()`
- `test_encoder_writes_only_canonical_sdl()`
- `test_plugin_absent_load_save_preserves_canonical_sdl()`
- `test_absent_sdl_remains_absent_across_load_save()`
- `test_loader_ignores_noncanonical_persisted_sdl()`
- `test_layout_with_sdl_rejects_unsupported_future_schema()`
- `test_flyline_overlay_is_excluded_from_saved_layout()`

## Depends on

- [[defaultPDK\__init__|defaultPDK.__init__]]
- [[revedaEditor\common\__init__|revedaEditor.common.__init__]]
- [[revedaEditor\fileio\__init__|revedaEditor.fileio.__init__]]
- [[revedaEditor\fileio\layoutEncoder|revedaEditor.fileio.layoutEncoder]]
- [[revedaEditor\fileio\loadJSON|revedaEditor.fileio.loadJSON]]
- [[revedaEditor\tests\sceneTestUtils|revedaEditor.tests.sceneTestUtils]]
