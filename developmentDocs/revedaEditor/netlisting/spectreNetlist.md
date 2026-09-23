# `revedaEditor/netlisting/spectreNetlist.py`

**Module:** `revedaEditor.netlisting.spectreNetlist`

## Purpose

Spectre netlist writer built on the unified connectivity engine.

## Module docstring

Spectre netlist generation for schematic editors.

Untested code.

This module provides the spectreNetlist class for generating Cadence Spectre-compatible
netlists from schematic designs. It supports hierarchical netlisting with config views,
array notation for buses, and various netlist formats including Spectre, Verilog-A, and
LVS modes.

Spectre format differences from SPICE/Xyce:
- Comments use `//` instead of `*`
- Global declarations use `global gnd!` instead of `.GLOBAL gnd!`
- Subcircuit blocks use `subckt` / `ends` instead of `.SUBCKT` / `.ENDS`
- Include directives use `include "file"` instead of `.INC "file"`
- Verilog-A includes use `ahdl_include "file"` instead of `*.HDL`
- Instance netlist lines are expected in Spectre syntax
  (`instName (n1 n2) modelName param=value`)

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

- [[revedaEditor/backend/dataDefinitions|revedaEditor.backend.dataDefinitions]]
- [[revedaEditor/backend/libBackEnd|revedaEditor.backend.libBackEnd]]
- [[revedaEditor/backend/libraryMethods|revedaEditor.backend.libraryMethods]]
- [[revedaEditor/common/shapes|revedaEditor.common.shapes]]
- [[revedaEditor/netlisting/__init__|revedaEditor.netlisting.__init__]]
- [[revedaEditor/scenes/schematicScene|revedaEditor.scenes.schematicScene]]

## Used by

- [[revedaEditor/netlisting/__init__|revedaEditor.netlisting.__init__]]
