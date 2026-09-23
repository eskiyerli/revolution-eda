# `revedaEditor/gui/editorViews.py`

**Module:** `revedaEditor.gui.editorViews`

## Purpose

`editorView` (QGraphicsView): zoom/pan, `viewRect` tracking, grid/line background rendering, mouse/key event forwarding to the scene.

## Classes

- `editorView(QGraphicsView)` — The qgraphicsview for qgraphicsscene. It is used for both schematic and layout editors.
  - `init_UI()`
  - `wheelEvent()`
  - `determineViewRect()`
  - `drawBackground()`
  - `findCoords()`
  - `keyPressEvent()`
  - `printView()`
  - `cycleSelection()`
  - `clearStretchItems()`
  - internals: `_drawPrintOverlays()`
- `symbolView(editorView)`
  - `keyPressEvent()`
- `schematicView(editorView)`
  - `mousePressEvent()`
  - `mouseReleaseEvent()`
  - `pruneShortNets()`
  - `mergeSplitViewNets()`
  - `drawBackground()`
  - `keyPressEvent()`
  - `mouseDoubleClickEvent()`
  - internals: `_drawPrintOverlays()`
- `layoutView(editorView)`
  - `keyPressEvent()`

## Depends on

- [[revedaEditor/backend/pdkLoader|revedaEditor.backend.pdkLoader]]
- [[revedaEditor/common/net|revedaEditor.common.net]]
- [[revedaEditor/scenes/editorScene|revedaEditor.scenes.editorScene]]
- [[revedaEditor/scenes/layoutScene|revedaEditor.scenes.layoutScene]]
- [[revedaEditor/scenes/schematicScene|revedaEditor.scenes.schematicScene]]
- [[revedaEditor/scenes/symbolScene|revedaEditor.scenes.symbolScene]]

## Used by

- [[revedaEditor/gui/editorWindow|revedaEditor.gui.editorWindow]]
- [[revedaEditor/gui/layoutEditor|revedaEditor.gui.layoutEditor]]
- [[revedaEditor/gui/schematicEditor|revedaEditor.gui.schematicEditor]]
- [[revedaEditor/gui/symbolEditor|revedaEditor.gui.symbolEditor]]
