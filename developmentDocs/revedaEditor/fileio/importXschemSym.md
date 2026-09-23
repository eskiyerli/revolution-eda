# `revedaEditor/fileio/importXschemSym.py`

**Module:** `revedaEditor.fileio.importXschemSym`

## Purpose

Xschem symbol-file import/conversion into symbol cellviews.

## Classes

- `importXschemSym` — Imports a xschem sym file
  - `importSymFile()`
  - `scaleFactor()`
  - `scaleFactor()`
  - `parseLineLine()`
  - `parseTextLine()`
  - `processFormatString()`
  - internals: `_createScaledPoint()`, `_createNLPLabel()`

## Depends on

- [[revedaEditor/backend/libBackEnd|revedaEditor.backend.libBackEnd]]
- [[revedaEditor/backend/libraryMethods|revedaEditor.backend.libraryMethods]]
- [[revedaEditor/backend/libraryModelView|revedaEditor.backend.libraryModelView]]
- [[revedaEditor/backend/pdkLoader|revedaEditor.backend.pdkLoader]]
- [[revedaEditor/common/labels|revedaEditor.common.labels]]
- [[revedaEditor/common/shapes|revedaEditor.common.shapes]]
- [[revedaEditor/fileio/symbolEncoder|revedaEditor.fileio.symbolEncoder]]
- [[revedaEditor/gui/symbolEditor|revedaEditor.gui.symbolEditor]]

## Used by

- [[revedaEditor/gui/revedaMain|revedaEditor.gui.revedaMain]]
