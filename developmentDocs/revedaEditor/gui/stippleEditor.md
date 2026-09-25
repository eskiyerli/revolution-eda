# `revedaEditor\gui\stippleEditor.py`

**Module:** `revedaEditor.gui.stippleEditor`

## Purpose

Module in `revedaEditor\gui`.

## Classes

- `stippleView(QGraphicsView)`
  - `drawGrid()`
  - `drawDot()`
  - `clearDot()`
  - `mousePressEvent()`
  - `size()`
  - `size()`
  - `gridStep()`
- `stippleScene(QGraphicsScene)`
- `stippleEditor(QMainWindow)`
  - `clearPattern()`
  - `exportPatternAsImage()`
  - `imageExportToFile()`
  - `exportPatternAsText()`
  - `loadPatternFromText()`
  - `loadPatternFromFile()`
  - `matrixSizeChanged()`
  - internals: `_createActions()`, `_createMenuBar()`, `_createToolBar()`

## Used by

- [[revedaEditor\fileio\importLayp|revedaEditor.fileio.importLayp]]
- [[revedaEditor\gui\revedaMain|revedaEditor.gui.revedaMain]]
