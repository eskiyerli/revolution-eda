# `revedaEditor\connectivity\layout.py`

**Module:** `revedaEditor.connectivity.layout`

## Purpose

Qt-free layout connectivity engine.

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
- `_LayerGrid` — Uniform-grid spatial index over shape footprints.
  - `query()`
  - internals: `_coveredCells()`
- `LayoutGeometryReader` — Parse a `layout.json` element list into resolved shapes and vias.
  - `read()`
  - `readAnchors()`
  - internals: `_layerByIndex()`, `_offsetRect()`, `_offsetShape()`, `_offsetVia()`, `_readPath()`, `_readBox()`, `_readPolygon()`, `_readVia()`

## Functions

- `_pathFootprint()` — Bounding box of a drawn path (centerline widened by `width` and
- `_layerBase()` — The `_layersMatch` key for a layer name ("" never matches).
- `_layersMatch()`
- `_viaMatchesShape()` — Check if a shape matches via lower or upper layer.
- `buildConnectivity()` — Group shapes+vias into nets by geometric connectivity.
- `_groupKey()`
- `assignNetNames()` — Attach names to net groups from (name, x, y) anchors.

## Used by

- [[revedaEditor\rcextraction\layoutGeometry|revedaEditor.rcextraction.layoutGeometry]]
- [[revedaEditor\tests\test_layout_connectivity|revedaEditor.tests.test_layout_connectivity]]
