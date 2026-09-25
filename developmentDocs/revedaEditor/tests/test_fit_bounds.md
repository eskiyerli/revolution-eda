# `revedaEditor\tests\test_fit_bounds.py`

**Module:** `revedaEditor.tests.test_fit_bounds`

## Purpose

Regression test: fitItemsInView must not feed back through items whose
boundingRect depends on the current view zoom (layoutRuler's inverse-scaled
label margin). Each 'f' press used to zoom out further.

## Functions

- `init_qapp()`
- `test_fit_items_in_view_stable_with_ruler()`

## Depends on

- [[defaultPDK\layoutLayers|defaultPDK.layoutLayers]]
- [[revedaEditor\common\layoutShapes|revedaEditor.common.layoutShapes]]
- [[revedaEditor\tests\sceneTestUtils|revedaEditor.tests.sceneTestUtils]]
