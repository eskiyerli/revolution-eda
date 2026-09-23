# `revedaEditor/netlisting/vacaskNetlist.py`

**Module:** `revedaEditor.netlisting.vacaskNetlist`

## Purpose

VACASK netlist writer built on the unified connectivity engine.

## Module docstring

VACASK netlist generation for schematic editors.

This module provides the vacaskNetlist class for generating VACASK-compatible
netlists from schematic designs. It supports hierarchical netlisting with config views,
array notation for buses, and various netlist formats including VACASK, Verilog-A, and
LVS modes.

VACASK format differences from Spectre:
- Uses `ground` directive instead of `global` for reference nodes
- Uses `load` directive for OSDI/Verilog-A devices instead of `ahdl_include`
- Requires `model` statements for all device types
- Supports `parameters` block for parameter declarations
- Supports `control`/`endc` block for simulation setup
- Supports `embed` directive for embedded files
- Supports section-based includes with `include "file" section=name`
- Subcircuit blocks use `subckt` / `ends` (same as Spectre)
- Include directives use `include "file"` (same as Spectre)
- Comments use `//` (same as Spectre)

Device loading categories:
- **Built-in** (vsource, isource, vcvs, vccs, ccvs, cccs, mutual):
  No `load` needed; `VacaskModelLine` provides the `model` statement.
- **Built-in OSDI** (resistor, capacitor, inductor, diode, opamp):
  `VacaskLoadFile` is a bare filename (e.g. `resistor.osdi`);
  `VacaskModelLine` provides the `model` statement.
- **Custom Verilog-A/OSDI**: `VacaskLoadFile` is a full path, or if absent
  the path is auto-constructed as `{cellPath}/{cellName}.va`;
  `VacaskModelLine` provides the `model` statement.
- **Library includes**: `VacaskIncludeLib` emits an `include` directive
  and suppresses that symbol's `VacaskModelLine` (the library provides it).

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

- [[revedaEditor/backend/dataDefinitions|revedaEditor.backend.dataDefinitions]]
- [[revedaEditor/backend/libBackEnd|revedaEditor.backend.libBackEnd]]
- [[revedaEditor/backend/libraryMethods|revedaEditor.backend.libraryMethods]]
- [[revedaEditor/common/shapes|revedaEditor.common.shapes]]
- [[revedaEditor/netlisting/__init__|revedaEditor.netlisting.__init__]]
- [[revedaEditor/scenes/schematicScene|revedaEditor.scenes.schematicScene]]

## Used by

- [[revedaEditor/netlisting/__init__|revedaEditor.netlisting.__init__]]
