# `revedaEditor/fileio/createSymbols.py`

**Module:** `revedaEditor.fileio.createSymbols`

## Purpose

Symbol generation from schematics (Create→Symbol): derives symbol pins from schematic pins and emits `symbol.json`.

## Functions

- `_paramDefsAttribute()` — Typed `paramDefs` attribute for imported instance parameters.
- `drawBaseSymbol()`
- `createVaSymbol()` — Creates a symbol for a given view item in the library.
- `createSpiceSymbol()`
- `createSpectreSymbol()`
- `createVacaskSymbol()`

## Depends on

- [[revedaEditor/backend/__init__|revedaEditor.backend.__init__]]
- [[revedaEditor/backend/dataDefinitions|revedaEditor.backend.dataDefinitions]]
- [[revedaEditor/backend/hdlBackEnd|revedaEditor.backend.hdlBackEnd]]
- [[revedaEditor/common/params|revedaEditor.common.params]]
- [[revedaEditor/common/shapes|revedaEditor.common.shapes]]
- [[revedaEditor/fileio/__init__|revedaEditor.fileio.__init__]]
- [[revedaEditor/gui/__init__|revedaEditor.gui.__init__]]

## Used by

- [[revedaEditor/fileio/importSpectre|revedaEditor.fileio.importSpectre]]
- [[revedaEditor/fileio/importSpice|revedaEditor.fileio.importSpice]]
- [[revedaEditor/fileio/importVacask|revedaEditor.fileio.importVacask]]
- [[revedaEditor/fileio/importVeriloga|revedaEditor.fileio.importVeriloga]]
