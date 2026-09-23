# `revedaEditor/gui/editorWindow.py`

**Module:** `revedaEditor.gui.editorWindow`

## Purpose

`editorWindow` — QMainWindow base class for all editors: menus/toolbars/actions, hardcoded+bindkey shortcuts, cellview lock acquisition, autosave timer, autosave-restore prompt, print/export plumbing.

## Classes

- `editorWindow(QMainWindow)` — Base class for editor windows.
  - `init_UI()`
  - `helpClick()`
  - `aboutClick()`
  - `autosaveCellview()`
  - `checkSaveCell()`
  - `saveCell()`
  - `dispConfigEdit()`
  - `configureGridSettings()`
  - `selectConfigEdit()`
  - `readOnlyCellClick()`
  - `updateDesignScene()`
  - `printClick()`
  - `printPreviewClick()`
  - `imageExportClick()`
  - `deleteClick()`
  - `selectAllClick()`
  - `deselectAllClick()`
  - `stretchClick()`
  - `moveClick()`
  - `constrainedMoveClick()`
  - `moveByClick()`
  - `rotateClick()`
  - `panView()`
  - `alignItemsClick()`
  - `goUpHierarchy()`
  - `fitToWindow()`
  - `copyClick()`
  - `pasteClick()`
  - `toggleCopyOptionsDialogue()` — Show/hide the F3 copy-options form (rows/columns/Delta X/Y).
  - `horizontalFlipClick()`
  - `verticalFlipClick()`
  - `zoomIn()`
  - `zoomOut()`
  - `closeWindow()`
  - `closeEvent()`
  - `moveOrigin()`
  - `undoClick()`
  - `redoClick()`
  - `rotateItemClick()`
  - `redraw()`
  - `addPluginAction()`
  - `measureDuration()`
  - internals: `__repr__()`, `_createMenuBar()`, `_createActions()`, `_createToolBars()`, `_addActions()`, `_createTriggers()`, `_createShortcuts()`, `_initSessionState()`, `_acquireCellviewLock()`, `_applyLockContention()`, `_saveCellviewTo()`, `_resolveLoadPath()` … (+13)
- `editorContainer(QWidget)`

## Depends on

- [[revedaEditor/backend/bindkeys|revedaEditor.backend.bindkeys]]
- [[revedaEditor/backend/cellviewState|revedaEditor.backend.cellviewState]]
- [[revedaEditor/backend/dataDefinitions|revedaEditor.backend.dataDefinitions]]
- [[revedaEditor/backend/libBackEnd|revedaEditor.backend.libBackEnd]]
- [[revedaEditor/backend/libraryModelView|revedaEditor.backend.libraryModelView]]
- [[revedaEditor/backend/processManager|revedaEditor.backend.processManager]]
- [[revedaEditor/backend/startThread|revedaEditor.backend.startThread]]
- [[revedaEditor/gui/alignItems|revedaEditor.gui.alignItems]]
- [[revedaEditor/gui/editorViews|revedaEditor.gui.editorViews]]
- [[revedaEditor/gui/fileDialogues|revedaEditor.gui.fileDialogues]]
- [[revedaEditor/gui/helpBrowser|revedaEditor.gui.helpBrowser]]
- [[revedaEditor/gui/propertyDialogues|revedaEditor.gui.propertyDialogues]]
- [[revedaEditor/resources/resources|revedaEditor.resources.resources]]
- [[revedaEditor/scenes/editorScene|revedaEditor.scenes.editorScene]]

## Used by

- [[revedaEditor/gui/layoutEditor|revedaEditor.gui.layoutEditor]]
- [[revedaEditor/gui/schematicEditor|revedaEditor.gui.schematicEditor]]
- [[revedaEditor/gui/symbolEditor|revedaEditor.gui.symbolEditor]]
- [[revedaEditor/tests/test_platform_hardening|revedaEditor.tests.test_platform_hardening]]
