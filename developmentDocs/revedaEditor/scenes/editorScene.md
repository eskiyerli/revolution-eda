# `revedaEditor/scenes/editorScene.py`

**Module:** `revedaEditor.scenes.editorScene`

## Purpose

`editorScene` — QGraphicsScene base: edit modes, selection machinery, undo stack, mouse dispatch, grid settings, read-only event filter, `_safeLoadDesign`/`reloadScene`.

## Classes

- `editorScene(QGraphicsScene)`
  - `contextMenuEvent()`
  - `mousePressEvent()`
  - `mouseMoveEvent()`
  - `mouseReleaseEvent()`
  - `setSelectedItems()`
  - `snapToGrid()`
  - `snapToBase()`
  - `rotateSelectedItems()`
  - `rotateAnItem()`
  - `eventFilter()`
  - `copySelectedItems()`
  - `copySelectionToClipboard()`
  - `pasteClipboard()`
  - `beginClipboardPaste()`
  - `cancelArmedCopy()`
  - `rearmClipboardPaste()` — Rebuild the armed floating copy with current `copyOptions` (options-form Apply/Ok).
  - `flipHorizontal()`
  - `flipVertical()`
  - `selectAll()`
  - `deselectAll()`
  - `deleteSelectedItems()`
  - `stretchSelectedItems()`
  - `reloadScene()`
  - `loadDesign()`
  - `fitItemsInView()`
  - `zoomToRect()`
  - `zoomInBy2()`
  - `zoomOutBy2()`
  - `zoomToRect()`
  - `moveSceneLeft()`
  - `moveSceneRight()`
  - `moveSceneUp()`
  - `moveSceneDown()`
  - `centerViewOnPoint()`
  - `addUndoStack()`
  - `deleteUndoStack()`
  - `addListUndoStack()`
  - `deleteListUndoStack()`
  - `undoGroupMoveStack()`
  - `addUndoMacroStack()`
  - `moveBySelectedItems()`
  - `cellNameComplete()`
  - `viewNameComplete()`
  - `measureDuration()`
  - `draftPen()`
  - internals: `_filterBySelectModes()`, `_snapPoint()`, `_handleMouseRelease()`, `_safeLoadDesign()`, `_applyMoveConstraint()`, `_clipboardShapes()`, `_clipboardShapesArray()` (rows×columns array per `copyOptions`), `_fixClipboardShapes()`, `_clipboardTopLeft()`

## Depends on

- [[revedaEditor/backend/dataDefinitions|revedaEditor.backend.dataDefinitions]]
- [[revedaEditor/backend/undoStack|revedaEditor.backend.undoStack]]
- [[revedaEditor/gui/propertyDialogues|revedaEditor.gui.propertyDialogues]]

## Used by

- [[revedaEditor/gui/editorViews|revedaEditor.gui.editorViews]]
- [[revedaEditor/gui/editorWindow|revedaEditor.gui.editorWindow]]
- [[revedaEditor/scenes/layoutScene|revedaEditor.scenes.layoutScene]]
- [[revedaEditor/scenes/schematicScene|revedaEditor.scenes.schematicScene]]
- [[revedaEditor/scenes/symbolScene|revedaEditor.scenes.symbolScene]]
- [[revedaEditor/tests/test_selection_state|revedaEditor.tests.test_selection_state]]
