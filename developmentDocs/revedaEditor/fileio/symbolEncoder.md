# `revedaEditor/fileio/symbolEncoder.py`

**Module:** `revedaEditor.fileio.symbolEncoder`

## Purpose

`symbolEncoder` — symbol scene items → `symbol.json` records.

## Classes

- `symbolAttribute(object)`
  - `name()`
  - `name()`
  - `definition()`
  - `definition()`
  - internals: `__str__()`, `__repr__()`
- `symbolEncoder(json.JSONEncoder)`
  - `default()`
  - internals: `_encodeSymbolRectangle()`, `_encodeSymbolLine()`, `_encodeSymbolCircle()`, `_encodeSymbolArc()`, `_encodeSymbolPolygon()`, `_encodeSymbolPin()`, `_encodeText()`, `_encodeSymbolLabel()`, `_encodeSymbolAttribute()`, `_subtract_point()`

## Depends on

- [[revedaEditor/common/labels|revedaEditor.common.labels]]
- [[revedaEditor/common/shapes|revedaEditor.common.shapes]]

## Used by

- [[revedaEditor/fileio/importXschemSym|revedaEditor.fileio.importXschemSym]]
- [[revedaEditor/fileio/loadJSON|revedaEditor.fileio.loadJSON]]
- [[revedaEditor/gui/schematicEditor|revedaEditor.gui.schematicEditor]]
- [[revedaEditor/scenes/symbolScene|revedaEditor.scenes.symbolScene]]
