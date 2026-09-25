# `revedaEditor\connectivity\primitives.py`

**Module:** `revedaEditor.connectivity.primitives`

## Purpose

Qt-free connectivity primitives.

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
