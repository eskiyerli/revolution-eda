# `revedaEditor/connectivity/adapters.py`

**Module:** `revedaEditor.connectivity.adapters`

## Purpose

Adapters converting decoded records and live scene items into engine shapes — including hierarchy expansion of `layoutInstance`/`layoutPcell`/multipart children for net highlight. `layoutGroup` containers are traversed transparently (members stay at the group's hierarchy level, so grouped pins/labels still anchor net names).

## Module docstring

Adapters mapping live scene items and decoded JSON records onto
connectivity primitives.

Both functions are Qt-free: scene items are duck-typed (they only need
`sceneEndPoints`/`name`/`nameStrength` on nets and
`pinName`/`pinDir`/`mapToScene(start)` on pins), so the same code path
serves the GUI, aiTerminal ops on record arrays, and unit tests.

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
