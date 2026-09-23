# `revedaEditor/fileio/loadJSON.py`

**Module:** `revedaEditor.fileio.loadJSON`

## Purpose

JSON→scene reconstruction: `schematicItems`/`layoutItems` loaders, symbol pin locators, draft-symbol fallback for missing libraries, PCell instance creation.

## Classes

- `symbolItems`
  - `create()`
  - `createRectItem()`
  - `createCircleItem()`
  - `createArcItem()`
  - `createLineItem()`
  - `createPinItem()`
  - `createLabelItem()`
  - `createTextItem()`
  - `createPolygonItem()`
  - `createSymbolAttribute()`
  - `createSimpleTextItem()`
  - `createQRectItem()`
  - `unknownItem()`
- `schematicItems`
  - `create()`
  - `createDraftSymbol()`
  - `unknownItem()`
  - internals: `_load_sym_json()`, `_createText()`, `_createPin()`, `_createNet()`, `_createSymbolShape()`
- `PCellCache`
  - `getPCellDef()`
  - `getPCellClass()`
  - `clear_caches()`
- `layoutItems`
  - `create()`
  - `createPcellInstance()`
  - `createLayoutInstance()`
  - `createRectShape()`
  - `createPathShape()`
  - `createRulerShape()`
  - `createLabelShape()`
  - `createPinShape()`
  - `createPolygonShape()`
  - `createViaArrayShape()`
  - `createMultipartShape()`
  - `createGroupShape()`
  - `unknownItem()`
  - internals: `_get_library_path()`, `_load_json_file()`, `_set_common_attrs()`, `_dictsBounds()`, `_applyRecordTransform()`, `_recordBounds()`, `_labelDictBounds()`, `_get_via_def()`

## Functions

- `clear_symbol_cache()` — Clear the symbol JSON loading cache.
- `makeSymbolPinLocator()` — Return a pinLocator for `connectivity.checkRecords`.

## Depends on

- [[revedaEditor/backend/pdkLoader|revedaEditor.backend.pdkLoader]]
- [[revedaEditor/common/labels|revedaEditor.common.labels]]
- [[revedaEditor/common/layoutShapes|revedaEditor.common.layoutShapes]]
- [[revedaEditor/common/net|revedaEditor.common.net]]
- [[revedaEditor/common/params|revedaEditor.common.params]]
- [[revedaEditor/common/shapes|revedaEditor.common.shapes]]
- [[revedaEditor/fileio/symbolEncoder|revedaEditor.fileio.symbolEncoder]]

## Used by

- [[revedaEditor/gui/schematicEditor|revedaEditor.gui.schematicEditor]]
- [[revedaEditor/scenes/layoutScene|revedaEditor.scenes.layoutScene]]
- [[revedaEditor/scenes/schematicScene|revedaEditor.scenes.schematicScene]]
- [[revedaEditor/scenes/symbolScene|revedaEditor.scenes.symbolScene]]
- [[revedaEditor/tests/test_diagnostics|revedaEditor.tests.test_diagnostics]]
- [[revedaEditor/tests/test_layout_productivity|revedaEditor.tests.test_layout_productivity]]
- [[revedaEditor/tests/test_layout_transforms|revedaEditor.tests.test_layout_transforms]]
