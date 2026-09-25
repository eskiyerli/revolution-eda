# `revedaEditor\fileio\exportGDS.py`

**Module:** `revedaEditor.fileio.exportGDS`

## Purpose

Module in `revedaEditor\fileio`.

## Classes

- `gdsExporter`
  - `layerMap()`
  - `layerMap()`
  - `cellNameMap()`
  - `cellNameMap()`
  - `flattenDepth()`
  - `flattenDepth()`
  - `gdsExport()`
  - `gdsExportThreaded()`
  - `oasExportThreaded()`
  - `createCells()`
  - `processPath()`
  - `extractPcellInstanceParameters()`
  - `unit()`
  - `unit()`
  - `precision()`
  - `precision()`
  - `dbu()`
  - `dbu()`
  - internals: `_emitLayer()`, `_mapCellName()`, `_buildLibrary()`, `_gdstk_transform()`, `_processInstance()`, `_processRectPin()`, `_processLabel()`, `_processPolygon()`, `_processViaArray()`, `_processViaEnclosure()`, `_processMultipart()`, `_process_custom_layout()`

## Depends on

- [[revedaEditor\backend\pdkLoader|revedaEditor.backend.pdkLoader]]
- [[revedaEditor\common\layoutShapes|revedaEditor.common.layoutShapes]]

## Used by

- [[revedaEditor\scenes\layoutScene|revedaEditor.scenes.layoutScene]]
- [[revedaEditor\tests\test_layout_transforms|revedaEditor.tests.test_layout_transforms]]
