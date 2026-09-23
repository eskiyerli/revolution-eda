# `revedaEditor/gui/configEditor.py`

**Module:** `revedaEditor.gui.configEditor`

## Purpose

Hierarchy config-view editor: `configEditor` window + container driving switch/stop view traversal.

## Classes

- `configEditor(QMainWindow)`
  - `configDict()`
  - `configDict()`
  - `schViewItem()`
  - `schViewItem()`
  - `loadConfig()`
  - `updateClick()`
  - `updateConfigDict()`
  - `saveCell()`
  - `closeEvent()`
  - internals: `_splitViewList()`, `_uiSwitchViews()`, `_uiStopViews()`, `_configFromView()`, `_openSchematicView()`, `_onViewChanged()`, `_createMenuBar()`, `_createActions()`, `_addActions()`, `_createTriggers()`, `_refreshConfigTable()`
- `configEditorContainer(QWidget)`
- `configModel(QStandardItemModel)`
  - internals: `_normalizeEntry()`
- `configTable(QTableView)`
  - `updateModel()`
  - internals: `_addViewCombo()`, `_onComboChanged()`

## Functions

- `createNewConfigView()` — Create a new config view from dialog parameters.
- `openConfigEditWindow()` — Open an existing config view for editing.

## Depends on

- [[revedaEditor/backend/dataDefinitions|revedaEditor.backend.dataDefinitions]]
- [[revedaEditor/backend/libBackEnd|revedaEditor.backend.libBackEnd]]
- [[revedaEditor/backend/libraryMethods|revedaEditor.backend.libraryMethods]]
- [[revedaEditor/gui/editFunctions|revedaEditor.gui.editFunctions]]
- [[revedaEditor/gui/schematicEditor|revedaEditor.gui.schematicEditor]]
- [[revedaEditor/resources/resources|revedaEditor.resources.resources]]

## Used by

- [[revedaEditor/backend/libraryModelView|revedaEditor.backend.libraryModelView]]
