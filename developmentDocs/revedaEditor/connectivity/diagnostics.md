# `revedaEditor/connectivity/diagnostics.py`

**Module:** `revedaEditor.connectivity.diagnostics`

## Purpose

Headless semantic checks on decoded design arrays (dangling ends, param problems, layout record diagnostics).

## Module docstring

Headless semantic checks on decoded design arrays.

These are the record-level counterparts of the scene check rules: they run
the *same* connectivity engine on raw JSON records, so aiTerminal design
ops, importers, and batch tooling validate against identical semantics to
the GUI.

    checkRecords(records, pinLocator)        -> schematic diagnostics
    checkLayoutRecords(records, layers, ...) -> layout diagnostics

A schematic `pinLocator` maps (lib, cell, view) -> {pinName: (x, y),
"directions": {pinName: dir}} in symbol coordinates; build one from a
library dict with `loadJSON.makeSymbolPinLocator` or supply your own.

## Classes

- `RecordDiagnostic` — One semantic finding on a decoded design array.

## Functions

- `_adapterDiagnostic()`
- `_manhattan()`
- `_pointSegDist()`
- `_danglingEnds()` — Seg endpoints joined to nothing: no coincident endpoint, no T-contact
- `checkRecords()` — Semantic check of a decoded schematic design array.
- `_paramDiagnostics()` — Validate `sys.ld` values against symbol paramDefs (CDF-lite).
- `checkLayoutRecords()` — Semantic check of a decoded layout design array.
