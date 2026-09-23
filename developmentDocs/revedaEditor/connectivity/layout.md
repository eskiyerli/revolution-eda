# `revedaEditor/connectivity/layout.py`

**Module:** `revedaEditor.connectivity.layout`

## Purpose

Layout-domain connectivity analysis: `analyzeLayoutItems`, net naming, via stacks and PCell pin bridging.

## Module docstring

Qt-free layout connectivity engine.

This is the shared geometric connectivity implementation for layout data.
It is consumed two ways:

  * live `layoutScene` items (via :func:`adapters.fromLayoutItems`) for
    layout net identity and highlight-net;
  * decoded `layout.json` records (via
    :class:`rcextraction.layoutGeometry.LayoutGeometryReader`) for RCX,
    batch tooling, and importers.

Grouping semantics:

  * shapes on the same layer merge when their footprints touch/overlap;
  * a via merges the lower-layer and upper-layer shapes it lands on;
  * a Pcell instance acts as a connectivity *bridge*: routing that lands on
    the same Pcell terminal (pin) is tied together. Pcell internal geometry
    is not treated as interconnect parasitics -- device internals belong to
    the device model, per standard PEX convention.

Net *names* come from layout pins and text labels through
:func:`assignNetNames`; unnamed groups receive deterministic `net<N>`
names.

## Classes

- `LayRect` — An axis-aligned rectangle footprint in scene (dbu) coordinates.
  - `intersects()`
  - `contains_point()`
- `LayShape` — A resolved layout shape with the data both connectivity and the
- `LayVia` — A via/cut array connecting a lower and an upper metal layer.
- `NetGroup` — A connected group of shapes = one net.
- `_UnionFind`
  - `find()`
  - `union()`
- `PcellBridge` — A Pcell terminal footprint that ties overlapping routing together.
- `LayoutGeometryReader` — Parse a `layout.json` element list into resolved shapes and vias.
  `Group` records are expanded recursively, shifted by the group's `loc`
  (member coordinates are group-local; group `ang`/`fl` are ignored at
  record level, matching `ang` handling on other record types).
  - `read()`
  - `readAnchors()`
  - internals: `_layerByIndex()`, `_readPath()`, `_readBox()`, `_readPolygon()`, `_readVia()`, `_offsetRect()`, `_offsetShape()`, `_offsetVia()`

## Functions

- `_pathFootprint()` — Bounding box of a drawn path (centerline widened by `width` and
- `_layersMatch()`
- `_viaMatchesShape()` — Check if a shape matches via lower or upper layer.
- `buildConnectivity()` — Group shapes+vias into nets by geometric connectivity.
- `_groupKey()`
- `assignNetNames()` — Attach names to net groups from (name, x, y) anchors.

## Used by

- [[revedaEditor/rcextraction/layoutGeometry|revedaEditor.rcextraction.layoutGeometry]]
- [[revedaEditor/tests/test_layout_connectivity|revedaEditor.tests.test_layout_connectivity]]
