# `revedaEditor/common/layoutMerge.py`

**Module:** `revedaEditor.common.layoutMerge`

## Purpose

Geometry engine behind layout Merge: union-find over touching same-layer shapes, path merging, rect/polygon unions via gdstk.

## Module docstring

Geometry engine behind the layout editor's Merge operation.

Works on `lshp` items in scene coordinates (`sceneEndPoints` /
`mapToScene` absorb pos/rotation/flip), so the result items are built with
identity transforms at scene coordinates -- the same pos-folded convention the
JSON encoders persist.

Merge rules:
  * `layoutPath`: same layer + same width + collinear (same infinite line)
    + drawn spans overlap or touch -> one longer path. Extends are recomputed
    so the merged path's drawn region equals the union of the inputs.
  * `layoutRect`/`layoutPolygon`: same layer + areas overlap or touch
    (edge or point contact) -> gdstk boolean union -> `layoutPolygon`, or
    `layoutRect` when the union is an exact axis-aligned rectangle.
  * No cross-type merging; other item kinds are ignored.

## Classes

- `_PathGeom(NamedTuple)` — Scene-space line geometry for one layoutPath.
- `_UnionFind`
  - `find()`
  - `union()`
  - `groups()`

## Functions

- `_layerKey()`
- `_pathGeometry()`
- `_pathsMergeable()`
- `_mergePathGroup()`
- `_mergePaths()`
- `_scenePolygon()`
- `_scenePath()`
- `_isAxisAlignedRect()`
- `_mergeShapeGroup()`
- `_mergeShapes()`
- `mergeLayoutItems()` — Merge selected layout items.

## Depends on

- [[revedaEditor/common/layoutShapes|revedaEditor.common.layoutShapes]]

## Used by

- [[revedaEditor/common/layoutBoolean|revedaEditor.common.layoutBoolean]]
- [[revedaEditor/common/layoutFlatten|revedaEditor.common.layoutFlatten]]
- [[revedaEditor/scenes/layoutScene|revedaEditor.scenes.layoutScene]]
- [[revedaEditor/tests/test_layout_merge|revedaEditor.tests.test_layout_merge]]
