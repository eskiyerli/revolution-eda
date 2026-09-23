# `revedaEditor/fileio/layoutEncoder.py`

**Module:** `revedaEditor.fileio.layoutEncoder`

## Purpose

`layoutEncoder` — json.JSONEncoder mapping layout scene items to `Rect/Path/Via/Pin/Label/Polygon/Inst/Pcell/Multipart/Group` records (scene-origin-relative coordinates, optional `sdl` metadata). `Group` records nest member records in group-local coordinates under `items`.

## Classes

- `layoutEncoder(json.JSONEncoder)`
  - `default()`
  - internals: `_layerIndexFor()`, `_encodeMultipart()`, `_addArrayFields()`, `_encodeLayoutInstance()`, `_addSdlField()`, `_encodeLayoutRect()`, `_encodeLayoutPath()`, `_encodeLayoutViaArray()`, `_encodeLayoutPin()`, `_encodeLayoutLabel()`, `_encodeLayoutPolygon()`, `_encodeLayoutRuler()`, `_encodeLayoutGroup()` … (+1)
- `gdsImportEncoder(layoutEncoder)` — Use the canonical layout encoder for GDS-imported JSON.

## Functions

- `_pcell_parameter_names()` — Return constructor parameters once per PCell class.

## Depends on

- [[revedaEditor/backend/pdkLoader|revedaEditor.backend.pdkLoader]]
- [[revedaEditor/common/layoutShapes|revedaEditor.common.layoutShapes]]

## Used by

- [[revedaEditor/fileio/importGDS|revedaEditor.fileio.importGDS]]
- [[revedaEditor/scenes/layoutScene|revedaEditor.scenes.layoutScene]]
- [[revedaEditor/tests/test_layout_productivity|revedaEditor.tests.test_layout_productivity]]
- [[revedaEditor/tests/test_layout_transforms|revedaEditor.tests.test_layout_transforms]]
