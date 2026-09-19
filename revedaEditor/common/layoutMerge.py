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
"""Geometry engine behind the layout editor's Merge operation.

Works on ``lshp`` items in scene coordinates (``sceneEndPoints`` /
``mapToScene`` absorb pos/rotation/flip), so the result items are built with
identity transforms at scene coordinates -- the same pos-folded convention the
JSON encoders persist.

Merge rules:
  * ``layoutPath``: same layer + same width + collinear (same infinite line)
    + drawn spans overlap or touch -> one longer path. Extends are recomputed
    so the merged path's drawn region equals the union of the inputs.
  * ``layoutRect``/``layoutPolygon``: same layer + areas overlap or touch
    (edge or point contact) -> gdstk boolean union -> ``layoutPolygon``, or
    ``layoutRect`` when the union is an exact axis-aligned rectangle.
  * No cross-type merging; other item kinds are ignored.
"""

import math
from typing import NamedTuple, Optional

import gdstk
from PySide6.QtCore import QLineF, QPoint, QPointF
from PySide6.QtGui import QPainterPath, QPolygonF

import revedaEditor.common.layoutShapes as lshp

MERGE_TOLERANCE = 0.5  # scene units (dbu); absorbs fp noise from transformed items
_ANGLE_TOL = 1e-4  # |cross(u1, u2)| threshold for "same direction"
_WIDTH_TOL = 1e-3  # path width equality (dbu)
_GDSTK_PRECISION = 0.001  # gdstk.boolean vertex rounding


class _PathGeom(NamedTuple):
    """Scene-space line geometry for one layoutPath."""

    path: "lshp.layoutPath"
    base: QPointF  # a point on the line
    u: QPointF  # canonical unit direction (dx>0, or dx==0 & dy>0)
    offset: float  # signed perpendicular distance identifying the line
    centreMin: float  # centreline projection interval along u
    centreMax: float
    drawnMin: float  # drawn interval incl. start/end extends
    drawnMax: float


class _UnionFind:
    def __init__(self, n: int):
        self._parent = list(range(n))

    def find(self, i: int) -> int:
        root = i
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[i] != root:
            self._parent[i], i = root, self._parent[i]
        return root

    def union(self, i: int, j: int) -> None:
        ri, rj = self.find(i), self.find(j)
        if ri != rj:
            self._parent[ri] = rj

    def groups(self) -> dict[int, list[int]]:
        result = {}
        for i in range(len(self._parent)):
            result.setdefault(self.find(i), []).append(i)
        return result


def _layerKey(item) -> tuple:
    layer = item.layer
    return (layer.name, layer.purpose)


def _pathGeometry(path: "lshp.layoutPath") -> Optional[_PathGeom]:
    p1, p2 = path.sceneEndPoints
    direction = QPointF(p2) - QPointF(p1)
    length = math.hypot(direction.x(), direction.y())
    if length < 1e-9:
        return None  # degenerate path: no direction to merge along
    u = direction / length
    # Canonical direction removes the p1/p2 sign ambiguity between members.
    if u.x() < 0 or (u.x() == 0 and u.y() < 0):
        u = -u
    s1 = QPointF.dotProduct(QPointF(p1), u)
    s2 = QPointF.dotProduct(QPointF(p2), u)
    offset = u.x() * p1.y() - u.y() * p1.x()
    return _PathGeom(
        path,
        QPointF(p1),
        u,
        offset,
        min(s1, s2),
        max(s1, s2),
        min(s1 - path.startExtend, s2 - path.endExtend),
        max(s1 + path.startExtend, s2 + path.endExtend),
    )


def _pathsMergeable(a: _PathGeom, b: _PathGeom) -> bool:
    if _layerKey(a.path) != _layerKey(b.path):
        return False
    if not math.isclose(a.path.width, b.path.width, abs_tol=_WIDTH_TOL):
        return False
    if abs(a.u.x() * b.u.y() - a.u.y() * b.u.x()) >= _ANGLE_TOL:
        return False
    if abs(a.offset - b.offset) > MERGE_TOLERANCE:
        return False
    # Drawn spans must overlap or touch along the line.
    return max(a.drawnMin, b.drawnMin) - min(a.drawnMax, b.drawnMax) <= MERGE_TOLERANCE


def _mergePathGroup(paths: list["lshp.layoutPath"], logger=None) -> "lshp.layoutPath":
    geoms = [_pathGeometry(path) for path in paths]
    u = geoms[0].u
    base = geoms[0].base
    centreMin = min(g.centreMin for g in geoms)
    centreMax = max(g.centreMax for g in geoms)
    drawnMin = min(g.drawnMin for g in geoms)
    drawnMax = max(g.drawnMax for g in geoms)
    anchor = base - u * QPointF.dotProduct(base, u)
    p1 = anchor + u * centreMin
    p2 = anchor + u * centreMax
    first = paths[0]
    merged = lshp.layoutPath(
        QLineF(p1, p2),
        first.layer,
        first.width,
        round(centreMin - drawnMin),
        round(drawnMax - centreMax),
        first.mode,
    )
    names = [path.name for path in paths if path.name]
    if names:
        merged.name = names[0]
        if logger and len(set(names)) > 1:
            logger.warning(
                f"Merged paths had different names {set(names)}; kept '{names[0]}'"
            )
    return merged


def _mergePaths(paths: list["lshp.layoutPath"], logger=None) -> tuple[list, list]:
    geoms = [g for g in (_pathGeometry(path) for path in paths) if g is not None]
    uf = _UnionFind(len(geoms))
    for i in range(len(geoms)):
        for j in range(i + 1, len(geoms)):
            if _pathsMergeable(geoms[i], geoms[j]):
                uf.union(i, j)
    produced, consumed = [], []
    for indices in uf.groups().values():
        if len(indices) < 2:
            continue
        group = [geoms[i].path for i in indices]
        produced.append(_mergePathGroup(group, logger))
        consumed.extend(group)
    return produced, consumed


def _scenePolygon(item) -> QPolygonF:
    if isinstance(item, lshp.layoutRect):
        rect = item.rect
        corners = (rect.topLeft(), rect.topRight(), rect.bottomRight(), rect.bottomLeft())
    else:  # layoutPolygon
        corners = item.points
    return QPolygonF([item.mapToScene(QPointF(p)) for p in corners])


def _scenePath(item) -> QPainterPath:
    path = QPainterPath()
    path.addPolygon(_scenePolygon(item))
    path.closeSubpath()
    return path


def _isAxisAlignedRect(points: list[QPointF]) -> bool:
    if len(points) != 4:
        return False
    xs = {round(p.x(), 3) for p in points}
    ys = {round(p.y(), 3) for p in points}
    return len(xs) == 2 and len(ys) == 2


def _mergeShapeGroup(items: list) -> list:
    operand = [
        [(p.x(), p.y()) for p in _scenePolygon(item)]
        for item in items
    ]
    results = gdstk.boolean(operand, [], "or", precision=_GDSTK_PRECISION)
    layer = items[0].layer
    produced = []
    for poly in results:
        # layoutPolygon stretch logic expects integer QPoint vertices.
        points = [QPoint(round(x), round(y)) for x, y in poly.points]
        if _isAxisAlignedRect(points):
            bounds = QPolygonF(points).boundingRect()
            produced.append(
                lshp.layoutRect(bounds.topLeft().toPoint(), bounds.bottomRight().toPoint(), layer)
            )
        else:
            produced.append(lshp.layoutPolygon(points, layer))
    return produced


def _mergeShapes(shapes: list) -> tuple[list, list]:
    byLayer = {}
    for item in shapes:
        byLayer.setdefault(_layerKey(item), []).append(item)
    produced, consumed = [], []
    for layerItems in byLayer.values():
        paths = [_scenePath(item) for item in layerItems]
        uf = _UnionFind(len(layerItems))
        for i in range(len(layerItems)):
            for j in range(i + 1, len(layerItems)):
                if paths[i].intersects(paths[j]):
                    uf.union(i, j)
        for indices in uf.groups().values():
            if len(indices) < 2:
                continue
            group = [layerItems[i] for i in indices]
            produced.extend(_mergeShapeGroup(group))
            consumed.extend(group)
    return produced, consumed


def mergeLayoutItems(items: list, logger=None) -> tuple[list, list]:
    """Merge selected layout items.

    Returns ``(produced, consumed)``: new items to add and source items the
    merge consumed (caller adds/removes via the undo stack). Singleton groups
    and non-mergeable kinds are left out of both lists.
    """
    paths = [item for item in items if isinstance(item, lshp.layoutPath)]
    shapes = [
        item
        for item in items
        if isinstance(item, (lshp.layoutRect, lshp.layoutPolygon))
    ]
    produced, consumed = _mergePaths(paths, logger)
    shapeProduced, shapeConsumed = _mergeShapes(shapes)
    produced.extend(shapeProduced)
    consumed.extend(shapeConsumed)
    return produced, consumed
