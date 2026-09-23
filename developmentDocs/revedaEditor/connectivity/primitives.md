# `revedaEditor/connectivity/primitives.py`

**Module:** `revedaEditor.connectivity.primitives`

## Purpose

Shared primitives: shape-record normalization and point/segment/rect predicates consumed by the engine.

## Module docstring

Qt-free connectivity primitives.

The connectivity engine works on plain data records so the same code path
serves live scenes (GUI), decoded JSON design arrays (aiTerminal ops,
importers, batch netlisting) and unit tests. Scenes and records are mapped
into these primitives by `adapters.py`.

Name strengths mirror `netNameStrengthEnum` in `common/net.py`; they are
plain ints here so this module stays importable without Qt.

## Classes

- `Seg` — One wire segment: endpoints in scene/sheet coordinates.
- `Port` — A pin attachment point (symbol pin or schematic pin).
  - `isGlobal()`
- `NetGroup` — A physically joined set of segments plus attached ports.
- `Conflict` — A semantic conflict discovered during name resolution.
- `ConnectivityResult` — Output of the connectivity engine for one sheet.
  - `groupOf()`
  - `signalKey()`

## Functions

- `parseArrayNotation()` — Parse 'name<start:end>' / 'name<i>' into (baseName, (start, end)).
- `namesMatch()` — Bus-aware name equality, mirroring `schematicNet._namesMatch`:
- `busWidth()` — Bus width of an array-notation name, or None for scalars.
