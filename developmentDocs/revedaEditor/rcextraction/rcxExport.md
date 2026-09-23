# `revedaEditor/rcextraction/rcxExport.py`

**Module:** `revedaEditor.rcextraction.rcxExport`

## Purpose

RCX database export helpers.

## Module docstring

Build an RCX extraction database (.rcx.json) from LVS results.

This bridges LVS and RC extraction (PEX). The parasitic geometry comes from
the Revolution EDA `layout.json` cellview (real drawn Paths/Rects/Vias on
real PDK layers with real widths) -- NOT from the KLayout `.lvsdb`, whose
per-net shapes live on internal rule-deck layers with no physical dimensions
and would yield degenerate, identical R/C values.

Pipeline:
  1. Read geometry from `layout.json` (see :mod:`layoutGeometry`).
  2. Group shapes into nets by geometric connectivity (union-find over
     touching shapes; vias stitch metal layers; Pcell pins bridge terminals).
  3. Name each net:
       * top-level layout pins carry the port net name directly;
       * otherwise adopt the LVS/schematic net name whose LVSDB label position
         falls inside one of the group's shapes;
       * unnamed groups get a synthetic `DNET<n>` name.
  4. Emit devices from the KLayout-extracted netlist (real models, params,
     terminal-to-net connectivity).

The schema comes from :mod:`rcx_schema`, shared with the extractor.

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
