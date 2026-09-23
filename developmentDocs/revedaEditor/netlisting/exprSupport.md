# `revedaEditor/netlisting/exprSupport.py`

**Module:** `revedaEditor.netlisting.exprSupport`

## Purpose

Inherited-connection (netSet / net-expression) support helpers shared by the netlisters.

## Module docstring

Inherited-connection (netSet / net expression) support for netlisters.

Each distinct net-expression name used inside a cell becomes an implicit
subcircuit terminal — appended after the cell's explicit pins. Inside the
subcircuit definition the expression resolves to the terminal name
(identity binding); at instantiation the instance supplies its netSet
override, the expression default, or the bare name.

The helpers here are shared by xyceNetlist, spectreNetlist and
vacaskNetlist so all backends emit identical semantics.

## Functions

- `exprDefsForSchematicView()` — {exprName: default} for a cell's schematic view, from its JSON file.
- `exprNetsForInstance()` — Ordered parent-level nets for an instance's implicit terminals.
- `exprTerminals()` — Implicit terminal names for a subckt header (sorted).
- `terminalNetSet()` — Identity bindings for collecting a subcircuit's internals.
- `globalNets()` — Resolved `!` nets contributed by an instance's expr bindings.

## Depends on

- [[revedaEditor/backend/libraryMethods|revedaEditor.backend.libraryMethods]]
- [[revedaEditor/connectivity/__init__|revedaEditor.connectivity.__init__]]
- [[revedaEditor/fileio/__init__|revedaEditor.fileio.__init__]]
