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
"""Flatten selected layout instances into top-level shapes.

Every descendant leaf of a selected ``layoutInstance`` is re-created as a new
top-level item whose geometry is baked in scene coordinates (``mapToScene``
folds in the instance placement, rotation/flip, and -- for mosaics -- each
array element's offset). Results carry identity transforms, matching the
pos-folded convention the JSON encoders persist.

Per-type behaviour:
  * ``layoutRect`` -> ``layoutRect`` when the mapped corners stay axis-aligned,
    otherwise ``layoutPolygon``.
  * ``layoutPolygon`` -> mapped ``layoutPolygon``.
  * ``layoutPath`` -> ``layoutPath`` over the scene end points (any-angle mode).
  * ``layoutPin`` -> ``layoutPin`` when axis-aligned, else a polygon on the
    pin layer plus a mapped label carrying the pin name.
  * ``layoutLabel``/``layoutViaArray`` -> same type; the composed scene
    rotation is carried in ``angle`` (mirrored parents are warned about --
    their text/spacing mirror cannot be re-expressed exactly).
  * ``layoutRuler`` -> mapped ruler (annotation is preserved, any-angle mode).
  * nested ``layoutInstance`` -> recursed into its leaves (mosaics expand).
  * guide items (``layoutLine``/``alignLine``/DRC markers) are skipped.
"""

import itertools
import math

from PySide6.QtCore import QLineF, QPoint, QPointF
from PySide6.QtGui import QPolygonF, QTransform

import revedaEditor.common.layoutShapes as lshp
from revedaEditor.common.layoutMerge import _isAxisAlignedRect

_AXIS_TOL = 0.5  # scene units; mapped rect corners snap to int grid


def _sceneAngle(item) -> float:
    """CCW rotation (degrees) carried by the item's full scene transform."""
    t = item.sceneTransform()
    return math.degrees(math.atan2(-t.m12(), t.m11()))


def _isMirrored(item) -> bool:
    t = item.sceneTransform()
    return (t.m11() * t.m22() - t.m12() * t.m21()) < 0


def _pointsToItem(points: list[QPointF], layer) -> lshp.layoutShape:
    pts = [QPoint(round(p.x()), round(p.y())) for p in points]
    if _isAxisAlignedRect(pts):
        bounds = QPolygonF(pts).boundingRect()
        return lshp.layoutRect(bounds.topLeft().toPoint(), bounds.bottomRight().toPoint(), layer)
    return lshp.layoutPolygon(pts, layer)


def _flattenPin(item, out, logger):
    rect = item.rect
    corners = (
        rect.topLeft(), rect.topRight(), rect.bottomRight(), rect.bottomLeft()
    )
    mapped = [item.mapToScene(QPointF(p)) for p in corners]
    if _isAxisAlignedRect(
            [QPoint(round(p.x()), round(p.y())) for p in mapped]):
        bounds = QPolygonF(mapped).boundingRect()
        pin = lshp.layoutPin(
            bounds.topLeft().toPoint(), bounds.bottomRight().toPoint(),
            item.pinName, item.pinDir, item.pinType, item.layer,
        )
        out.append(pin)
    else:
        out.append(lshp.layoutPolygon(
            [QPoint(round(p.x()), round(p.y())) for p in mapped], item.layer))
        if logger:
            logger.warning(
                f"Pin '{item.pinName}' lost its pin semantics on flatten "
                "(non-orthogonal rotation); emitted as polygon")
    label = getattr(item, "label", None)
    if label is not None:
        _flattenLabel(label, out, logger)


def _flattenLabel(item, out, logger):
    mappedStart = item.mapToScene(QPointF(item.start)).toPoint()
    label = lshp.layoutLabel(
        mappedStart, item.labelText, item.fontFamily, item.fontStyle,
        item.fontHeight, item.labelAlign, item.labelOrient, item.layer,
    )
    # labelOrient encodes the label's own rotation/flip (setOrient already
    # ran in __init__).  Everything above it -- the parent chain's rotation
    # plus any extra 'ang' rotation this label already carries -- is folded
    # into the persisted 'ang' field, which the loader applies additively on
    # top of the orient rotation.
    parent = item.parentItem()
    parentT = parent.sceneTransform() if parent is not None else QTransform()
    if (parentT.m11() * parentT.m22() - parentT.m12() * parentT.m21()) < 0 \
            and logger:
        logger.warning(
            f"Label '{item.labelText}' sits under a mirrored instance; "
            "orientation after flatten is approximate")
    extraAngle = math.degrees(
        math.atan2(parentT.m12(), parentT.m11())) + item.angle
    if abs(extraAngle) > 1e-6:
        label.addExtraRotation(extraAngle)
    out.append(label)


def _flattenViaArray(item, out, logger):
    newVia = lshp.layoutViaArray(
        item.mapToScene(QPointF(item.start)).toPoint(),
        item.via, item.xs, item.ys, item.xnum, item.ynum,
        legacyStart=True,
    )
    if _isMirrored(item) and logger:
        logger.warning(
            "Via array under a mirrored instance flattened without the "
            "mirror in its spacing vectors")
    # -_sceneAngle() is the composed Qt rotation (parent chain + the item's
    # own angle); layoutViaArray.angle feeds setRotation directly.
    qtAngle = -_sceneAngle(item)
    if abs(qtAngle) > 1e-6:
        newVia.angle = qtAngle
    out.append(newVia)


def _flattenItem(item, out, logger) -> None:
    if isinstance(item, lshp.layoutInstance):
        item._ensureShapes()
        for child in itertools.chain(item.shapes, item._arrayShapes):
            _flattenItem(child, out, logger)
        return
    if isinstance(item, lshp.layoutMultipart):
        # Composite children are parented to the multipart, so mapToScene
        # folds in the item's own transform on each leaf.
        for child in item.shapes:
            _flattenItem(child, out, logger)
        return
    if isinstance(item, lshp.layoutGroup):
        # Groups are transparent selection structure; flatten through them.
        for child in item.shapes:
            _flattenItem(child, out, logger)
        return
    if isinstance(item, lshp.layoutRect):
        rect = item.rect
        mapped = [
            item.mapToScene(QPointF(p))
            for p in (rect.topLeft(), rect.topRight(),
                      rect.bottomRight(), rect.bottomLeft())
        ]
        out.append(_pointsToItem(mapped, item.layer))
    elif isinstance(item, lshp.layoutPolygon):
        out.append(lshp.layoutPolygon(
            [item.mapToScene(QPointF(p)).toPoint() for p in item.points],
            item.layer))
    elif isinstance(item, lshp.layoutPath):
        p1, p2 = item.sceneEndPoints
        path = lshp.layoutPath(
            QLineF(p1, p2), item.layer, item.width,
            round(item.startExtend), round(item.endExtend), 2,
        )
        if item.name:
            path.name = item.name
        out.append(path)
    elif isinstance(item, lshp.layoutPin):
        _flattenPin(item, out, logger)
    elif isinstance(item, lshp.layoutViaArray):
        _flattenViaArray(item, out, logger)
    elif isinstance(item, lshp.layoutLabel):
        _flattenLabel(item, out, logger)
    elif isinstance(item, lshp.layoutRuler):
        p1, p2 = item.sceneEndPoints
        out.append(lshp.layoutRuler(
            QLineF(p1, p2), item.width, item.tickFont, item.mode,
        ))
    # Guide/annotation leftovers (layoutLine, alignLine, drc markers) are
    # intentionally not carried into the flattened content.


def flattenInstance(instance: lshp.layoutInstance, logger=None) -> list:
    """Leaf items covering ``instance``'s full geometry in scene coordinates.

    Realises deferred children first and expands mosaic elements (the array
    clones carry each element's offset in their own transforms). Also accepts
    a ``layoutMultipart``: its composite children are exploded the same way."""
    if hasattr(instance, "_ensureShapes"):
        instance._ensureShapes()
    produced = []
    children = itertools.chain(
        instance.shapes, getattr(instance, "_arrayShapes", []))
    for child in children:
        _flattenItem(child, produced, logger)
    return produced
