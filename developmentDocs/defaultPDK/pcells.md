# `defaultPDK/pcells.py`

**Module:** `defaultPDK.pcells`

## Purpose

Parameterized-cell classes for the default PDK; exposed through the `pcells` registry dict.

## Classes

- `nmos(lshp.layoutPcell)`
  - `createGeometry()`
  - `width()`
  - `width()`
  - `length()`
  - `length()`
  - `nf()`
  - `nf()`
  - internals: `__call__()`
- `pmos(lshp.layoutPcell)`

## Depends on

- [[revedaEditor/backend/pdkLoader|revedaEditor.backend.pdkLoader]]
- [[revedaEditor/common/layoutShapes|revedaEditor.common.layoutShapes]]

## Used by

- [[revedaEditor/tests/test_layout_transforms|revedaEditor.tests.test_layout_transforms]]
