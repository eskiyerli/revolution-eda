# `revedaEditor\connectivity\adapters.py`

**Module:** `revedaEditor.connectivity.adapters`

## Purpose

Adapters mapping live scene items and decoded JSON records onto
connectivity primitives.

## Functions

- `_strengthInt()` — Accept int or an enum with a .value attribute.
- `_pointTuple()` — Accept QPoint/QPointF or a (x, y) tuple.
- `fromSceneItems()` — Build primitives from live items.
- `_transformedPinPoint()` — Map a symbol-space pin position into sheet coordinates.
- `fromRecords()` — Build primitives from a decoded schematic JSON design array.
- `_portsFromInstanceRecord()`
- `_layRectFromSceneRect()` — QRectF/QRect -> LayRect (normalized).
- `_layRectFromPoints()`
- `_viaLayers()` — (via_type, lower_layer_name, upper_layer_name) from a viaDefTuple.
- `fromLayoutItems()` — Build layout connectivity primitives from live scene items.
- `_layoutShape()`

## Used by

- [[revedaEditor\tests\test_connectivity|revedaEditor.tests.test_connectivity]]
