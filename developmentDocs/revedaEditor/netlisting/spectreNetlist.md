# `revedaEditor\netlisting\spectreNetlist.py`

**Module:** `revedaEditor.netlisting.spectreNetlist`

## Purpose

Spectre netlist generation for schematic editors.

## Classes

- `spectreNetlist` — Generate Cadence Spectre-compatible netlists from schematic designs.
  - `switchViewList()`
  - `switchViewList()`
  - `stopViewList()`
  - `stopViewList()`
  - `configDict()`
  - `configDict()`
  - `writeNetlist()`
  - `collectSubcircuitContent()`
  - `recursiveNetlisting()`
  - `processElementSymbol()`
  - `determineNetlistView()`
  - `createItemLine()`
  - `createSpectreSymbolLine()`
  - `createSpiceLine()`
  - `createTextViewLine()`
  - `createVerilogaLine()`
  - `parseArrayNotation()`
  - `expandPinNames()`
  - internals: `__repr__()`, `_shouldIgnoreSymbol()`, `_exprDefsFor()`, `_getCellItem()`, `_findViewFromSwitchList()`, `_isStopView()`, `_createNetlistLine()`

## Depends on

- [[revedaEditor\backend\dataDefinitions|revedaEditor.backend.dataDefinitions]]
- [[revedaEditor\backend\libBackEnd|revedaEditor.backend.libBackEnd]]
- [[revedaEditor\backend\libraryMethods|revedaEditor.backend.libraryMethods]]
- [[revedaEditor\common\shapes|revedaEditor.common.shapes]]
- [[revedaEditor\netlisting\__init__|revedaEditor.netlisting.__init__]]
- [[revedaEditor\scenes\schematicScene|revedaEditor.scenes.schematicScene]]

## Used by

- [[revedaEditor\netlisting\__init__|revedaEditor.netlisting.__init__]]
