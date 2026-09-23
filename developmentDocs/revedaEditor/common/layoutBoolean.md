# `revedaEditor/common/layoutBoolean.py`

**Module:** `revedaEditor.common.layoutBoolean`

## Purpose

Phase 5 boolean layer operations — per-layer or/and/xor, A-NOT-B subtraction, grow/shrink via `gdstk`; returns `(produced, consumed)` items for undo commands.

## Module docstring

Boolean and size operations on selected layout shapes.

Same scene-coordinate convention as `layoutMerge`: operands are mapped
through `mapToScene` so results are built with identity transforms at scene
coordinates -- the frame the JSON encoders persist.

Operations (`op` argument):
  * `"or"`/`"and"`/`"xor"`: applied per layer group over the selected
    `layoutRect`/`layoutPolygon` items; the result replaces the whole
    group (empty intersections consume nothing and produce nothing).
  * `"not"`: for each layer group A, subtracts the union of the selected
    shapes on all *other* layers (Virtuoso A-NOT-B). Items on the B layers
    stay in the scene; only A's source items are consumed. Selection with a
    single layer produces nothing.
  * `"grow"`/`"shrink"`: `gdstk.offset` by `amount` scene units per
    selected shape, keeping each shape's layer. One source may fan out to
    several result polygons.

Other item kinds are ignored. Returns `(produced, consumed)` lists for the
caller to push through the undo stack.

## Functions

- `_polygonsToItems()` — Build editable items from gdstk result polygons on `layer`.
- `_sceneOperand()`
- `_booleanPerLayer()`
- `_notAcrossLayers()`
- `_sizeShapes()`
- `booleanLayerItems()` — Run a boolean/size operation on selected layout shapes.

## Depends on

- [[revedaEditor/common/layoutMerge|revedaEditor.common.layoutMerge]]
- [[revedaEditor/common/layoutShapes|revedaEditor.common.layoutShapes]]

## Used by

- [[revedaEditor/scenes/layoutScene|revedaEditor.scenes.layoutScene]]
- [[revedaEditor/tests/test_layout_productivity|revedaEditor.tests.test_layout_productivity]]
