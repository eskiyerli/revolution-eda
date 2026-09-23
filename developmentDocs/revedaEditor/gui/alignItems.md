# `revedaEditor/gui/alignItems.py`

**Module:** `revedaEditor.gui.alignItems`

## Purpose

Align-items dialog plus the edge/line alignment geometry helpers it invokes.

## Classes

- `alignItemsDialogue(QDialog)`
  - `edgeAlignmentMessageShow()`
  - `lineAlignmentMessageShow()`
  - `showHorizonalAlignments()`
  - `showVerticalAlignments()`

## Functions

- `alignItemsEdgeHorizontally()`
- `alignItemsEdgeVertically()`
- `alignItemsLineHorizontally()`
- `alignItemsLineVertically()`
- `handleAlignAction()`
- `startLineAlign()`
- `startEdgeAlign()`
- `alignToLine()`

## Depends on

- [[revedaEditor/backend/pdkLoader|revedaEditor.backend.pdkLoader]]
- [[revedaEditor/common/shapes|revedaEditor.common.shapes]]
- [[revedaEditor/gui/editFunctions|revedaEditor.gui.editFunctions]]

## Used by

- [[revedaEditor/gui/editorWindow|revedaEditor.gui.editorWindow]]
- [[revedaEditor/scenes/layoutScene|revedaEditor.scenes.layoutScene]]
- [[revedaEditor/scenes/schematicScene|revedaEditor.scenes.schematicScene]]
- [[revedaEditor/scenes/symbolScene|revedaEditor.scenes.symbolScene]]
