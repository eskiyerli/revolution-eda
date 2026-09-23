# `revedaEditor/connectivity/__init__.py`

**Module:** `revedaEditor.connectivity.__init__`

## Purpose

Package facade re-exporting the unified connectivity engine API used by GUI scenes, decoded JSON records, importers and tests.

## Module docstring

Unified connectivity engine — one implementation for GUI scenes, decoded
JSON records (aiTerminal ops, importers, batch tooling), and tests.

Public API:
    analyzeItems(netItems, pinItems, ...)  — live scene/duck-typed items
    analyzeRecords(records, pinLocator, ...) — decoded design arrays
    resolve(segs, ports, ...)              — primitives-level entry point

## Functions

- `analyzeItems()` — Resolve connectivity for live (duck-typed) scene items.
- `analyzeRecords()` — Resolve connectivity for a decoded schematic JSON design array.
- `analyzeLayoutItems()` — Group live layout items into named nets.

## Used by

- [[revedaEditor/backend/correspondence|revedaEditor.backend.correspondence]]
- [[revedaEditor/netlisting/exprSupport|revedaEditor.netlisting.exprSupport]]
- [[revedaEditor/scenes/layoutScene|revedaEditor.scenes.layoutScene]]
- [[revedaEditor/scenes/schematicScene|revedaEditor.scenes.schematicScene]]
- [[revedaEditor/scenes/symbolScene|revedaEditor.scenes.symbolScene]]
- [[revedaEditor/tests/test_connectivity|revedaEditor.tests.test_connectivity]]
- [[revedaEditor/tests/test_diagnostics|revedaEditor.tests.test_diagnostics]]
- [[revedaEditor/tests/test_layout_connectivity|revedaEditor.tests.test_layout_connectivity]]
- [[revedaEditor/tests/test_netexpr|revedaEditor.tests.test_netexpr]]
