# `revedaEditor\scenes\editorScene.py`

**Module:** `revedaEditor.scenes.editorScene`

## Purpose

Module in `revedaEditor\scenes`.

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
  - `copySelectionToClipboard()`
  - `pasteClipboard()`
  - `armedCopyScene()`
  - `beginClipboardPaste()`
  - `cancelArmedCopy()`
  - `rearmClipboardPaste()`
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
  - internals: `_filterBySelectModes()`, `_snapPoint()`, `_handleMouseRelease()`, `_clipboardRecords()`, `_clipboardAcceptable()`, `_clipboardShapes()`, `_clipboardShapesArray()`, `_fixClipboardShapes()`, `_clipboardTopLeft()`, `_commitCopyGroup()`, `_safeLoadDesign()`, `_fitBoundsRect()` … (+1)

## Depends on

- [[revedaEditor\backend\dataDefinitions|revedaEditor.backend.dataDefinitions]]
- [[revedaEditor\backend\undoStack|revedaEditor.backend.undoStack]]
- [[revedaEditor\gui\propertyDialogues|revedaEditor.gui.propertyDialogues]]

## Used by

- [[revedaEditor\gui\editorViews|revedaEditor.gui.editorViews]]
- [[revedaEditor\gui\editorWindow|revedaEditor.gui.editorWindow]]
- [[revedaEditor\scenes\layoutScene|revedaEditor.scenes.layoutScene]]
- [[revedaEditor\scenes\schematicScene|revedaEditor.scenes.schematicScene]]
- [[revedaEditor\scenes\symbolScene|revedaEditor.scenes.symbolScene]]
- [[revedaEditor\tests\test_selection_state|revedaEditor.tests.test_selection_state]]
