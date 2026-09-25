# `revedaEditor\fileio\importGDS.py`

**Module:** `revedaEditor.fileio.importGDS`

## Purpose

Module in `revedaEditor\fileio`.

## Classes

- `gdsImporter`
  - `importGDS()`
  - internals: `_cellItemFor()`, `_viewItemFor()`, `_processInstance()`, `_sceneValue()`, `_scenePoint()`, `_isConstantWidth()`, `_pathExtensions()`, `_processGdsPath()`, `_processShapes()`

## Functions

- `__getattr__()`

## Depends on

- [[revedaEditor\backend\dataDefinitions|revedaEditor.backend.dataDefinitions]]
- [[revedaEditor\backend\libBackEnd|revedaEditor.backend.libBackEnd]]
- [[revedaEditor\backend\libraryMethods|revedaEditor.backend.libraryMethods]]
- [[revedaEditor\backend\pdkLoader|revedaEditor.backend.pdkLoader]]
- [[revedaEditor\common\layoutShapes|revedaEditor.common.layoutShapes]]
- [[revedaEditor\fileio\layoutEncoder|revedaEditor.fileio.layoutEncoder]]
- [[revedaEditor\fileio\schemaValidation|revedaEditor.fileio.schemaValidation]]

## Used by

- [[revedaEditor\gui\revedaMain|revedaEditor.gui.revedaMain]]
- [[revedaEditor\tests\test_import_gds|revedaEditor.tests.test_import_gds]]
