# `revedaEditor/connectivity/resolve.py`

**Module:** `revedaEditor.connectivity.resolve`

## Purpose

Net-name resolution — the single implementation behind `nameSceneNets` semantics (sheet pins, SET-strength wire names, conflict handling).

## Module docstring

Net name resolution — single implementation of nameSceneNets semantics.

Priority order (mirroring `schematicScene.nameSceneNets`):

1. global symbol pins (name ends with `!`) — name applied SET;
2. schematic (sheet) pins — name applied INHERIT, with SET-name conflict and
   bus-width checks;
3. SET-named segments — name propagates through the group;
4. everything else — auto `net<N>` names, WEAK.

Differences from the legacy implementation, by design:

- traversal order is deterministic (sorted by id / position), so auto net
  numbering is stable across runs;
- conflicts are collected as data instead of aborting the whole pass on the
  first one;
- two different pin names on one group are flagged `pinNameConflict`
  (legacy code silently let the last pin win).

## Functions

- `_attachPorts()` — Map each port to the group containing a segment within portTol.
- `_resolveGroup()`
- `resolve()` — Build connectivity for one sheet and resolve all net names.
