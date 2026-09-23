# `revedaEditor/scenes/symbolScene.py`

**Module:** `revedaEditor.scenes.symbolScene`

## Purpose

`symbolScene` — symbol drawing editing: `saveSymbolCell`/`loadDesign`, attribute list.

## Classes

- `symbolScene(editorScene)` — Scene for Symbol editor.
  - `drawMode()`
  - `mouseMoveEvent()`
  - `mouseReleaseEvent()`
  - `mouseDoubleClickEvent()`
  - `lineDraw()`
  - `rectDraw()`
  - `circleDraw()`
  - `arcDraw()`
  - `pinDraw()`
  - `labelDraw()`
  - `addProperty()`
  - `startPolygon()`
  - `finishPolygon()`
  - `moveBySelectedItems()`
  - `stretchSelectedItems()`
  - `itemProperties()`
  - `updateSymbolRectangle()`
  - `updateSymbolCircle()`
  - `updateSymbolLine()`
  - `updateSymbolArc()`
  - `updateSymbolLabel()`
  - `updateSymbolPin()`
  - `updateSymbolPolygon()`
  - `loadDesign()`
  - `createSymbolItems()`
  - `saveSymbolCell()`
  - `viewSymbolProperties()`
  - `copySelectedItems()`
  - internals: `_handleMouseRelease()`, `_handleAlignItemLine()`, `_filterBySelectModes()`, `_itemPassesFilter()`

## Depends on

- [[revedaEditor/backend/dataDefinitions|revedaEditor.backend.dataDefinitions]]
- [[revedaEditor/backend/pdkLoader|revedaEditor.backend.pdkLoader]]
- [[revedaEditor/backend/undoStack|revedaEditor.backend.undoStack]]
- [[revedaEditor/common/labels|revedaEditor.common.labels]]
- [[revedaEditor/common/params|revedaEditor.common.params]]
- [[revedaEditor/common/shapes|revedaEditor.common.shapes]]
- [[revedaEditor/connectivity/__init__|revedaEditor.connectivity.__init__]]
- [[revedaEditor/fileio/loadJSON|revedaEditor.fileio.loadJSON]]
- [[revedaEditor/fileio/schemaValidation|revedaEditor.fileio.schemaValidation]]
- [[revedaEditor/fileio/symbolEncoder|revedaEditor.fileio.symbolEncoder]]
- [[revedaEditor/gui/alignItems|revedaEditor.gui.alignItems]]
- [[revedaEditor/gui/propertyDialogues|revedaEditor.gui.propertyDialogues]]
- [[revedaEditor/scenes/editorScene|revedaEditor.scenes.editorScene]]

## Used by

- [[revedaEditor/gui/editorViews|revedaEditor.gui.editorViews]]
- [[revedaEditor/gui/symbolEditor|revedaEditor.gui.symbolEditor]]
