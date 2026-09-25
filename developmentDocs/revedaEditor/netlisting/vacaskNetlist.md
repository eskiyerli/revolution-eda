# `revedaEditor\netlisting\vacaskNetlist.py`

**Module:** `revedaEditor.netlisting.vacaskNetlist`

## Purpose

VACASK netlist generation for schematic editors.

## Classes

- `vacaskNetlist` — Generate VACASK-compatible netlists from schematic designs.
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
  - `createVacaskSymbolLine()`
  - `createSpiceLine()`
  - `createTextViewLine()`
  - `createVerilogaLine()`
  - `parseArrayNotation()`
  - `expandPinNames()`
  - internals: `__repr__()`, `_shouldIgnoreSymbol()`, `_exprDefsFor()`, `_processGlobalNet()`, `_collectModelLoadInfo()`, `_getCellItem()`, `_getSubcktParams()`, `_findViewFromSwitchList()`, `_isStopView()`, `_createNetlistLine()`, `_resolveVerilogaViewPath()`, `_quoteId()`

## Depends on

- [[revedaEditor\backend\dataDefinitions|revedaEditor.backend.dataDefinitions]]
- [[revedaEditor\backend\libBackEnd|revedaEditor.backend.libBackEnd]]
- [[revedaEditor\backend\libraryMethods|revedaEditor.backend.libraryMethods]]
- [[revedaEditor\common\shapes|revedaEditor.common.shapes]]
- [[revedaEditor\netlisting\__init__|revedaEditor.netlisting.__init__]]
- [[revedaEditor\scenes\schematicScene|revedaEditor.scenes.schematicScene]]

## Used by

- [[revedaEditor\netlisting\__init__|revedaEditor.netlisting.__init__]]
