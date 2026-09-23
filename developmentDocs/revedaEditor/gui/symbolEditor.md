# `revedaEditor/gui/symbolEditor.py`

**Module:** `revedaEditor.gui.symbolEditor`

## Purpose

`symbolEditor` window + `symbolContainer`: symbol drawing actions, label/attribute dialogs.

## Classes

- `symbolEditor(edw.editorWindow)`
  - `init_UI()`
  - `objPropClick()`
  - `selectPinClick()`
  - `selectShapeClick()`
  - `selectLabelClick()`
  - `selectTextClick()`
  - `removeSelectFilterClick()`
  - `checkSaveCell()`
  - `saveCell()`
  - `createRectClick()`
  - `createLineClick()`
  - `createPolyClick()`
  - `createArcClick()`
  - `createCircleClick()`
  - `createPinClick()`
  - `rotateItemClick()`
  - `copyClick()`
  - `viewPropClick()`
  - `loadSymbol()`
  - `createLabelClick()`
  - `closeEvent()`
  - internals: `_createShortcuts()`, `_createToolBars()`, `_addActions()`, `_createTriggers()`, `_symbolContextMenu()`
- `symbolContainer(edw.editorContainer)`
  - `init_UI()`

## Depends on

- [[revedaEditor/backend/dataDefinitions|revedaEditor.backend.dataDefinitions]]
- [[revedaEditor/backend/libBackEnd|revedaEditor.backend.libBackEnd]]
- [[revedaEditor/backend/libraryModelView|revedaEditor.backend.libraryModelView]]
- [[revedaEditor/gui/editorViews|revedaEditor.gui.editorViews]]
- [[revedaEditor/gui/editorWindow|revedaEditor.gui.editorWindow]]
- [[revedaEditor/gui/propertyDialogues|revedaEditor.gui.propertyDialogues]]
- [[revedaEditor/scenes/symbolScene|revedaEditor.scenes.symbolScene]]

## Used by

- [[revedaEditor/fileio/importXschemSym|revedaEditor.fileio.importXschemSym]]
