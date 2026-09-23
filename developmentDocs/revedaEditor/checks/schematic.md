# `revedaEditor/checks/schematic.py`

**Module:** `revedaEditor.checks.schematic`

## Purpose

Schematic check rules producing `checkViolation` records: symbol overlaps, unconnected/dangling nets, floating pins, shorted outputs, net-name conflicts — the data behind the marker browser.

## Module docstring

Schematic check rules.

Each entry in `SCHEMATIC_RULES` is a selectable check (id, display name,
severity, description) whose `run` function returns `checkViolation`
objects carrying a log message and scene-coordinate marker rects. The scene
builds one shared `schematicCheckContext` per check run, so rules reuse a
single connectivity graph instead of rescanning the scene.

## Classes

- `checkSeverity(IntEnum)`
- `pinRecord` — One pin connection point on the schematic (instance or sheet pin).
- `checkViolation`
- `schematicCheckContext` — Scene data collected once and shared by all rules.
- `schematicCheckRule`

## Functions

- `checkSymbolOverlaps()` — Checks if any symbol overlaps with other symbols.
- `checkUnconnectedNets()` — Return dangling net endpoints: ends where no other net terminates and no
- `checkFloatingPins()` — Return pin positions that are not within snap distance of any net
- `_pointMarker()`
- `_pinOwnerName()`
- `_netSceneRect()`
- `buildCheckContext()` — Collect scene data shared by all check rules and build the net
- `_ruleSymbolOverlap()`
- `_ruleDanglingWireEnd()`
- `_ruleFloatingPin()`
- `_ruleFloatingInputPin()`
- `_ruleShortedOutputs()`
- `_ruleNetNameConflict()`
- `_overlappingNetPairs()` — Yield (netA, netB) pairs whose bodies geometrically overlap.
- `_collinearOverlapLength()` — Length of the interval two parallel nets share when they lie on the
- `_ruleOverlappingNets()` — Collinear wire bodies sharing more than an endpoint's worth of
- `_ruleCrossoverNoJunction()` — Perpendicular wire bodies crossing interior-to-interior with no
- `_ruleDuplicateInstName()`
- `_ruleOffGridItems()`
- `_ruleBusWidthMismatch()`
- `runChecks()` — Run every registered rule (or only `enabledIds`) over the shared

## Depends on

- [[revedaEditor/common/net|revedaEditor.common.net]]
- [[revedaEditor/common/shapes|revedaEditor.common.shapes]]

## Used by

- [[revedaEditor/gui/schematicEditor|revedaEditor.gui.schematicEditor]]
- [[revedaEditor/scenes/schematicScene|revedaEditor.scenes.schematicScene]]
- [[revedaEditor/tests/test_schematic_checks|revedaEditor.tests.test_schematic_checks]]
- [[revedaEditor/tests/test_schematic_ux|revedaEditor.tests.test_schematic_ux]]
