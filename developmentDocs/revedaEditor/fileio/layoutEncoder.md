# `revedaEditor\fileio\layoutEncoder.py`

**Module:** `revedaEditor.fileio.layoutEncoder`

## Purpose

Module in `revedaEditor\fileio`.

## Classes

- `layoutEncoder(json.JSONEncoder)`
  - `default()`
  - internals: `_layerIndexFor()`, `_encodeMultipart()`, `_addArrayFields()`, `_encodeLayoutInstance()`, `_addSdlField()`, `_encodeLayoutRect()`, `_encodeLayoutPath()`, `_encodeLayoutViaArray()`, `_encodeLayoutPin()`, `_encodeLayoutLabel()`, `_encodeLayoutPolygon()`, `_encodeLayoutRuler()` … (+2)
- `gdsImportEncoder(layoutEncoder)` — Use the canonical layout encoder for GDS-imported JSON.

## Functions

- `_pcell_parameter_names()` — Return constructor parameters once per PCell class.

## Depends on

- [[revedaEditor\backend\pdkLoader|revedaEditor.backend.pdkLoader]]
- [[revedaEditor\common\layoutShapes|revedaEditor.common.layoutShapes]]
- [[revedaEditor\fileio\schemaValidation|revedaEditor.fileio.schemaValidation]]

## Used by

- [[revedaEditor\fileio\importGDS|revedaEditor.fileio.importGDS]]
- [[revedaEditor\scenes\layoutScene|revedaEditor.scenes.layoutScene]]
- [[revedaEditor\tests\test_layout_productivity|revedaEditor.tests.test_layout_productivity]]
- [[revedaEditor\tests\test_layout_transforms|revedaEditor.tests.test_layout_transforms]]
- [[revedaEditor\tests\test_sdl_persistence|revedaEditor.tests.test_sdl_persistence]]
