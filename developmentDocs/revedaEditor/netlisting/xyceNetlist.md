# `revedaEditor\netlisting\xyceNetlist.py`

**Module:** `revedaEditor.netlisting.xyceNetlist`

## Purpose

Xyce netlist generation for schematic editors.

## Classes

- `xyceNetlist` — Generate Xyce-compatible netlists from schematic designs.
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
  - `createXyceSymbolLine()`
  - `createSpiceLine()`
  - `createTextViewLine()`
  - `parseArrayNotation()`
  - `expandPinNames()`
  - internals: `__repr__()`, `_exprDefsFor()`, `_getCellItem()`, `_findViewFromSwitchList()`, `_isStopView()`, `_createNetlistLine()`

## Depends on

- [[revedaEditor\backend\dataDefinitions|revedaEditor.backend.dataDefinitions]]
- [[revedaEditor\backend\libBackEnd|revedaEditor.backend.libBackEnd]]
- [[revedaEditor\backend\libraryMethods|revedaEditor.backend.libraryMethods]]
- [[revedaEditor\common\shapes|revedaEditor.common.shapes]]
- [[revedaEditor\netlisting\__init__|revedaEditor.netlisting.__init__]]
- [[revedaEditor\scenes\schematicScene|revedaEditor.scenes.schematicScene]]

## Used by

- [[revedaEditor\netlisting\__init__|revedaEditor.netlisting.__init__]]
- [[revedaEditor\tests\test_netexpr|revedaEditor.tests.test_netexpr]]
- [[revedaEditor\tests\test_netlisting|revedaEditor.tests.test_netlisting]]
