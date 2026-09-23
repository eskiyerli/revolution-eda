# `revedaEditor/fileio/importGDS.py`

**Module:** `revedaEditor.fileio.importGDS`

## Purpose

GDS stream-in: `gdsImporter` reads gdstk records into `lib/cell/layout.json` files, with merge mode that appends to existing cells.

## Classes

- `gdsImporter`
  - `importGDS()`
  - internals: `_cellItemFor()`, `_viewItemFor()`, `_processInstance()`, `_sceneValue()`, `_scenePoint()`, `_isConstantWidth()`, `_pathExtensions()`, `_processGdsPath()`, `_processShapes()`

## Depends on

- [[revedaEditor/backend/dataDefinitions|revedaEditor.backend.dataDefinitions]]
- [[revedaEditor/backend/libBackEnd|revedaEditor.backend.libBackEnd]]
- [[revedaEditor/backend/libraryMethods|revedaEditor.backend.libraryMethods]]
- [[revedaEditor/backend/pdkLoader|revedaEditor.backend.pdkLoader]]
- [[revedaEditor/common/layoutShapes|revedaEditor.common.layoutShapes]]
- [[revedaEditor/fileio/layoutEncoder|revedaEditor.fileio.layoutEncoder]]

## Used by

- [[revedaEditor/gui/revedaMain|revedaEditor.gui.revedaMain]]
- [[revedaEditor/tests/test_import_gds|revedaEditor.tests.test_import_gds]]
