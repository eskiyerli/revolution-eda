#
# Revolution EDA
#
# Copyright (c) 2026 Revolution Semiconductor
#
# This Source Code Form is subject to the terms of the
# Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
"""Boolean and size operations on selected layout shapes.

Same scene-coordinate convention as ``layoutMerge``: operands are mapped
through ``mapToScene`` so results are built with identity transforms at scene
coordinates -- the frame the JSON encoders persist.

Operations (``op`` argument):
  * ``"or"``/``"and"``/``"xor"``: applied per layer group over the selected
    ``layoutRect``/``layoutPolygon`` items; the result replaces the whole
    group (empty intersections consume nothing and produce nothing).
  * ``"not"``: for each layer group A, subtracts the union of the selected
    shapes on all *other* layers (Virtuoso A-NOT-B). Items on the B layers
    stay in the scene; only A's source items are consumed. Selection with a
    single layer produces nothing.
  * ``"grow"``/``"shrink"``: ``gdstk.offset`` by ``amount`` scene units per
    selected shape, keeping each shape's layer. One source may fan out to
    several result polygons.

Other item kinds are ignored. Returns ``(produced, consumed)`` lists for the
caller to push through the undo stack.
"""

import gdstk
from PySide6.QtCore import QPoint
from PySide6.QtGui import QPolygonF

import revedaEditor.common.layoutShapes as lshp
from revedaEditor.common.layoutMerge import (
    _GDSTK_PRECISION,
    _isAxisAlignedRect,
    _layerKey,
    _scenePolygon,
)

_BOOLEAN_OPS = ("or", "and", "xor")
_SIZE_OPS = ("grow", "shrink")


def _polygonsToItems(polys, layer) -> list:
    """Build editable items from gdstk result polygons on ``layer``."""
    produced = []
    for poly in polys:
        # layoutPolygon stretch logic expects integer QPoint vertices.
        points = [QPoint(round(x), round(y)) for x, y in poly.points]
        if len(points) < 3:
            continue
        if _isAxisAlignedRect(points):
            bounds = QPolygonF(points).boundingRect()
            produced.append(
                lshp.layoutRect(
                    bounds.topLeft().toPoint(), bounds.bottomRight().toPoint(), layer
                )
            )
        else:
            produced.append(lshp.layoutPolygon(points, layer))
    return produced


def _sceneOperand(item) -> list:
    return [(p.x(), p.y()) for p in _scenePolygon(item)]


def _booleanPerLayer(byLayer: dict, op: str) -> tuple[list, list]:
    produced, consumed = [], []
    for items in byLayer.values():
        if len(items) < 2:
            # A boolean of one shape is the shape itself; skip the churn.
            continue
        operand = [_sceneOperand(item) for item in items]
        if op in ("and", "xor"):
            # gdstk "and"/"xor" operate between operand1 and operand2, so a
            # group result is a sequential fold over the selected shapes
            # (an empty operand2 would yield A and empty = empty / A xor
            # empty = A).
            results = [operand[0]]
            for poly in operand[1:]:
                results = gdstk.boolean(
                    results, [poly], op, precision=_GDSTK_PRECISION)
                # xor must keep folding: an empty intermediate (identical
                # operands) still xors against later shapes.
                if not results and op == "and":
                    break
        else:
            results = gdstk.boolean(
                operand, [], op, precision=_GDSTK_PRECISION)
        newItems = _polygonsToItems(results, items[0].layer)
        if newItems:
            produced.extend(newItems)
            consumed.extend(items)
    return produced, consumed


def _notAcrossLayers(byLayer: dict) -> tuple[list, list]:
    produced, consumed = [], []
    if len(byLayer) < 2:
        return produced, consumed
    for layerKey, items in byLayer.items():
        subtrahend = [
            _sceneOperand(item)
            for otherKey, otherItems in byLayer.items()
            if otherKey != layerKey
            for item in otherItems
        ]
        operand = [_sceneOperand(item) for item in items]
        results = gdstk.boolean(operand, subtrahend, "not", precision=_GDSTK_PRECISION)
        newItems = _polygonsToItems(results, items[0].layer)
        if newItems:
            produced.extend(newItems)
            consumed.extend(items)
    return produced, consumed


def _sizeShapes(items: list, op: str, amount: float) -> tuple[list, list]:
    distance = amount if op == "grow" else -amount
    produced, consumed = [], []
    for item in items:
        # gdstk.offset takes a sequence of polygons, not a bare point list.
        results = gdstk.offset(
            [_sceneOperand(item)], distance, precision=_GDSTK_PRECISION
        )
        newItems = _polygonsToItems(results, item.layer)
        if newItems:
            produced.extend(newItems)
            consumed.append(item)
    return produced, consumed


def booleanLayerItems(items: list, op: str, amount: float = 0.0, logger=None) -> tuple[list, list]:
    """Run a boolean/size operation on selected layout shapes.

    ``op`` is one of ``"or"``, ``"and"``, ``"xor"``, ``"not"``, ``"grow"`` or
    ``"shrink"``; ``amount`` is the sizing distance in scene units (dbu) for
    the size ops. Returns ``(produced, consumed)``; the caller pushes both
    through the undo stack.
    """
    shapes = [
        item
        for item in items
        if isinstance(item, (lshp.layoutRect, lshp.layoutPolygon))
    ]
    if op in _SIZE_OPS:
        if amount <= 0:
            if logger:
                logger.warning(f"Size operation '{op}' needs a positive amount")
            return [], []
        return _sizeShapes(shapes, op, amount)
    byLayer = {}
    for item in shapes:
        byLayer.setdefault(_layerKey(item), []).append(item)
    if op == "not":
        return _notAcrossLayers(byLayer)
    if op in _BOOLEAN_OPS:
        return _booleanPerLayer(byLayer, op)
    if logger:
        logger.warning(f"Unknown layer operation '{op}'")
    return [], []
