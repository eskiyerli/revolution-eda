# `revedaEditor\backend\undoStack.py`

**Module:** `revedaEditor.backend.undoStack`

## Purpose

Module in `revedaEditor\backend`.

## Classes

- `undoStack(QUndoStack)`
  - `removeLastCommand()`
- `addShapeUndo(QUndoCommand)`
  - `undo()`
  - `redo()`
- `addDeleteShapesUndo(QUndoCommand)`
  - `disable()`
  - `undo()`
  - `redo()`
- `addShapesUndo(QUndoCommand)`
  - `undo()`
  - `redo()`
- `deleteShapeUndo(QUndoCommand)`
  - `undo()`
  - `redo()`
- `deleteShapesUndo(QUndoCommand)`
  - `undo()`
  - `redo()`
- `addDeleteShapeUndo(QUndoCommand)`
  - `undo()`
  - `redo()`
- `addDeleteNetUndo(QUndoCommand)`
  - `undo()`
  - `redo()`
- `updateSymUndo(QUndoCommand)`
  - `undo()`
  - `redo()`
- `moveShapeUndo(QUndoCommand)`
  - `undo()`
  - `redo()`
- `undoRotateShape(QUndoCommand)`
  - `undo()`
  - `redo()`
- `undoMoveByCommand(QUndoCommand)`
  - `redo()`
  - `undo()`
- `undoGroupShapes(QUndoCommand)` — Attach/detach members of a persistent `layoutGroup`.
  - `redo()`
  - `undo()`
  - internals: `_doAttach()`, `_doDetach()`
- `undoStretchShape(QUndoCommand)` — Undo command for stretching a shape in-place.
  - `undo()`
  - `redo()`
- `undoGroupMove(QUndoCommand)`
  - `redo()`
  - `undo()`
- `replaceDesignSnapshotUndo(QUndoCommand)` — Undo command that applies complete persisted-design snapshots.
  - `undo()`
  - `redo()`
  - internals: `_apply()`

## Depends on

- [[revedaEditor\common\layoutShapes|revedaEditor.common.layoutShapes]]
- [[revedaEditor\common\shapes|revedaEditor.common.shapes]]

## Used by

- [[revedaEditor\scenes\editorScene|revedaEditor.scenes.editorScene]]
- [[revedaEditor\scenes\layoutScene|revedaEditor.scenes.layoutScene]]
- [[revedaEditor\scenes\schematicScene|revedaEditor.scenes.schematicScene]]
- [[revedaEditor\scenes\symbolScene|revedaEditor.scenes.symbolScene]]
- [[revedaEditor\tests\test_ai_snapshot_undo|revedaEditor.tests.test_ai_snapshot_undo]]
- [[revedaEditor\tests\test_layout_merge|revedaEditor.tests.test_layout_merge]]
- [[revedaEditor\tests\test_layout_stretch|revedaEditor.tests.test_layout_stretch]]
