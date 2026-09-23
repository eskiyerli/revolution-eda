# `revedaEditor/common`

Shared graphics items and geometry/parameter helpers.

## Modules

- [[revedaEditor/common/__init__|__init__.py]] — Package marker for shared graphics items and helpers
- [[revedaEditor/common/fileCache|fileCache.py]] — `FileCache` — file-content cache keyed by modification time, used to avoid re-reading unchanged JSON
- [[revedaEditor/common/labels|labels.py]] — Label items (`schematicLabel`, `symbolLabel`) and PyLabel machinery
- [[revedaEditor/common/layoutBoolean|layoutBoolean.py]] — Phase 5 boolean layer operations
- [[revedaEditor/common/layoutFlatten|layoutFlatten.py]] — Hierarchy restructuring helpers: `flattenInstance` bakes instance subtrees (arrays, rotations, multipart children) to scene-coordinate leaf…
- [[revedaEditor/common/layoutMerge|layoutMerge.py]] — Geometry engine behind layout Merge: union-find over touching same-layer shapes, path merging, rect/polygon unions via gdstk
- [[revedaEditor/common/layoutShapes|layoutShapes.py]] — All layout graphics items
- [[revedaEditor/common/net|net.py]] — Schematic wire/bus graphics items (`schematicNet`), net-name label items, and name-strength machinery
- [[revedaEditor/common/params|params.py]] — Typed instance-parameter model (CDF-lite): `ParamDef` definitions, validation/normalization, default resolution, and…
- [[revedaEditor/common/shapes|shapes.py]] — Schematic/symbol graphics items: base `symbolShape` classes, pins, rectangles, lines, arcs, circles, polygons, text, and the…
