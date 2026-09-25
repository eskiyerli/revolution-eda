# `revedaEditor\common\layoutFlatten.py`

**Module:** `revedaEditor.common.layoutFlatten`

## Purpose

Flatten selected layout instances into top-level shapes.

## Functions

- `_sceneAngle()` — CCW rotation (degrees) carried by the item's full scene transform.
- `_isMirrored()`
- `_pointsToItem()`
- `_flattenPin()`
- `_flattenLabel()`
- `_flattenViaArray()`
- `_flattenItem()`
- `flattenInstance()` — Leaf items covering `instance`'s full geometry in scene coordinates.

## Depends on

- [[revedaEditor\common\layoutMerge|revedaEditor.common.layoutMerge]]
- [[revedaEditor\common\layoutShapes|revedaEditor.common.layoutShapes]]

## Used by

- [[revedaEditor\scenes\layoutScene|revedaEditor.scenes.layoutScene]]
- [[revedaEditor\tests\test_layout_productivity|revedaEditor.tests.test_layout_productivity]]
