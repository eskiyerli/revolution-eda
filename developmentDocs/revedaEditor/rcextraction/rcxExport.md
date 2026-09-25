# `revedaEditor\rcextraction\rcxExport.py`

**Module:** `revedaEditor.rcextraction.rcxExport`

## Purpose

Build an RCX extraction database (.rcx.json) from LVS results.

## Functions

- `_overlapArea()` — Area of the intersection of two rectangles (0 if disjoint).
- `_bestAnchorNet()` — Return the anchor net whose pin footprint overlaps the group the most.
- `_nameGroups()` — Assign a (net_name, is_port) to each group index.
- `_toRcxShapes()` — Convert a group's geometry into RcxShapes for the extractor.
- `_toRcxVias()`
- `_coerceParam()`
- `_buildDevices()` — Devices from the KLayout-extracted netlist (models/params/net names).
- `buildRcxDatabase()` — Assemble the :class:`RcxDatabase` for `layoutCellName`.
- `exportRcxDatabase()` — Build and write the `.rcx.json` extraction database.
