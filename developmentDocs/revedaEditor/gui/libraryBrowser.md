# `revedaEditor/gui/libraryBrowser.py`

**Module:** `revedaEditor.gui.libraryBrowser`

## Purpose

`libraryBrowser` — the design-libraries window hosting the column/tree view, context menus, and new/open cellview entry points.

## Classes

- `libraryBrowser(QMainWindow)`
  - `writeLibDefFile()`
  - `openLibClick()`
  - `closeLibClick()`
  - `libraryEditorClick()`
  - `updateLibraryClick()`
  - `updateLibRefClick()`
  - `newCellClick()`
  - `deleteCellClick()`
  - `newCellViewClick()`
  - `selectCellView()`
  - `openCellViewClick()`
  - `deleteCellViewClick()`
  - `selectColumnViewClick()`
  - `selectTreeViewClick()`
  - `closeEvent()`
  - internals: `_createMenuBar()`, `_createActions()`, `_createTriggers()`, `_createToolBars()`
- `libraryBrowserContainer(QWidget)`
  - `initUI()`
  - `switchToTreeView()`
  - `switchToColumnView()`
- `libraryListView(QDialog)`
  - `accept()`

## Depends on

- [[revedaEditor/backend/dataDefinitions|revedaEditor.backend.dataDefinitions]]
- [[revedaEditor/backend/libBackEnd|revedaEditor.backend.libBackEnd]]
- [[revedaEditor/backend/libraryMethods|revedaEditor.backend.libraryMethods]]
- [[revedaEditor/backend/libraryModelView|revedaEditor.backend.libraryModelView]]
- [[revedaEditor/backend/startThread|revedaEditor.backend.startThread]]
- [[revedaEditor/gui/editFunctions|revedaEditor.gui.editFunctions]]
- [[revedaEditor/gui/fileDialogues|revedaEditor.gui.fileDialogues]]

## Used by

- [[revedaEditor/gui/revedaMain|revedaEditor.gui.revedaMain]]
