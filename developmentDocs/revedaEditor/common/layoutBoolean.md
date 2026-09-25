# `revedaEditor\common\layoutBoolean.py`

**Module:** `revedaEditor.common.layoutBoolean`

## Purpose

Boolean and size operations on selected layout shapes.

## Functions

- `_polygonsToItems()` — Build editable items from gdstk result polygons on `layer`.
- `_sceneOperand()`
- `_booleanPerLayer()`
- `_notAcrossLayers()`
- `_sizeShapes()`
- `booleanLayerItems()` — Run a boolean/size operation on selected layout shapes.

## Depends on

- [[revedaEditor\common\layoutMerge|revedaEditor.common.layoutMerge]]
- [[revedaEditor\common\layoutShapes|revedaEditor.common.layoutShapes]]

## Used by

- [[revedaEditor\scenes\layoutScene|revedaEditor.scenes.layoutScene]]
- [[revedaEditor\tests\test_layout_productivity|revedaEditor.tests.test_layout_productivity]]
