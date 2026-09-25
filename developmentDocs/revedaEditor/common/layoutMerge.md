# `revedaEditor\common\layoutMerge.py`

**Module:** `revedaEditor.common.layoutMerge`

## Purpose

Geometry engine behind the layout editor's Merge operation.

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

- [[revedaEditor\common\layoutShapes|revedaEditor.common.layoutShapes]]

## Used by

- [[revedaEditor\common\layoutBoolean|revedaEditor.common.layoutBoolean]]
- [[revedaEditor\common\layoutFlatten|revedaEditor.common.layoutFlatten]]
- [[revedaEditor\scenes\layoutScene|revedaEditor.scenes.layoutScene]]
- [[revedaEditor\tests\test_layout_merge|revedaEditor.tests.test_layout_merge]]
- [[revedaEditor\tests\test_layout_productivity|revedaEditor.tests.test_layout_productivity]]
