# `revedaEditor\netlisting\exprSupport.py`

**Module:** `revedaEditor.netlisting.exprSupport`

## Purpose

Inherited-connection (netSet / net expression) support for netlisters.

## Functions

- `exprDefsForSchematicView()` — {exprName: default} for a cell's schematic view, from its JSON file.
- `exprNetsForInstance()` — Ordered parent-level nets for an instance's implicit terminals.
- `exprTerminals()` — Implicit terminal names for a subckt header (sorted).
- `terminalNetSet()` — Identity bindings for collecting a subcircuit's internals.
- `globalNets()` — Resolved `!` nets contributed by an instance's expr bindings.

## Depends on

- [[revedaEditor\backend\libraryMethods|revedaEditor.backend.libraryMethods]]
- [[revedaEditor\connectivity\__init__|revedaEditor.connectivity.__init__]]
- [[revedaEditor\fileio\__init__|revedaEditor.fileio.__init__]]
