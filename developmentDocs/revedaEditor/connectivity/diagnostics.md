# `revedaEditor\connectivity\diagnostics.py`

**Module:** `revedaEditor.connectivity.diagnostics`

## Purpose

Headless semantic checks on decoded design arrays.

## Classes

- `RecordDiagnostic` — One semantic finding on a decoded design array.

## Functions

- `_adapterDiagnostic()`
- `_memoizedPinLocator()` — Memoize one pure symbol-pin lookup per cell view for a check pass.
- `_manhattan()`
- `_pointSegDist()`
- `_danglingEnds()` — Seg endpoints joined to nothing: no coincident endpoint, no T-contact
- `checkRecords()` — Semantic check of a decoded schematic design array.
- `_paramDiagnostics()` — Validate `sys.ld` values against symbol paramDefs (CDF-lite).
- `checkLayoutRecords()` — Semantic check of a decoded layout design array.
