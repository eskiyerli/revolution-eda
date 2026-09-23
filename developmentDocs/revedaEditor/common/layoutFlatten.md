# `revedaEditor/common/layoutFlatten.py`

**Module:** `revedaEditor.common.layoutFlatten`

## Purpose

Hierarchy restructuring helpers: `flattenInstance` bakes instance subtrees (arrays, rotations, multipart children) to scene-coordinate leaf items; `makeCellFromSelection` writes a new cell and swaps in an instance.

## Module docstring

Flatten selected layout instances into top-level shapes.

Every descendant leaf of a selected `layoutInstance` is re-created as a new
top-level item whose geometry is baked in scene coordinates (`mapToScene`
folds in the instance placement, rotation/flip, and -- for mosaics -- each
array element's offset). Results carry identity transforms, matching the
pos-folded convention the JSON encoders persist.

Per-type behaviour:
  * `layoutRect` -> `layoutRect` when the mapped corners stay axis-aligned,
    otherwise `layoutPolygon`.
  * `layoutPolygon` -> mapped `layoutPolygon`.
  * `layoutPath` -> `layoutPath` over the scene end points (any-angle mode).
  * `layoutPin` -> `layoutPin` when axis-aligned, else a polygon on the
    pin layer plus a mapped label carrying the pin name.
  * `layoutLabel`/`layoutViaArray` -> same type; the composed scene
    rotation is carried in `angle` (mirrored parents are warned about --
    their text/spacing mirror cannot be re-expressed exactly).
  * `layoutRuler` -> mapped ruler (annotation is preserved, any-angle mode).
  * nested `layoutInstance` -> recursed into its leaves (mosaics expand).
  * `layoutGroup` -> transparent: members are flattened through the group.
  * guide items (`layoutLine`/`alignLine`/DRC markers) are skipped.

## Functions

- `_sceneAngle()` — CCW rotation (degrees) carried by the item's full scene transform.
- `_isMirrored()`
- `_pointsToItem()`
- `_flattenPin()`
- `_flattenLabel()`
- `_orientAngle()`
- `_flattenViaArray()`
- `_flattenItem()`
- `flattenInstance()` — Leaf items covering `instance`'s full geometry in scene coordinates.

## Depends on

- [[revedaEditor/common/layoutMerge|revedaEditor.common.layoutMerge]]
- [[revedaEditor/common/layoutShapes|revedaEditor.common.layoutShapes]]

## Used by

- [[revedaEditor/scenes/layoutScene|revedaEditor.scenes.layoutScene]]
- [[revedaEditor/tests/test_layout_productivity|revedaEditor.tests.test_layout_productivity]]
