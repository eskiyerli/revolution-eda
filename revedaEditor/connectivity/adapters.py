#
# Revolution EDA
#
# Copyright (c) 2026 Revolution Semiconductor
#
# This Source Code Form is subject to the terms of the
# Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
##

"""Adapters mapping live scene items and decoded JSON records onto
connectivity primitives.

Both functions are Qt-free: scene items are duck-typed (they only need
``sceneEndPoints``/``name``/``nameStrength`` on nets and
``pinName``/``pinDir``/``mapToScene(start)`` on pins), so the same code path
serves the GUI, aiTerminal ops on record arrays, and unit tests.
"""

from __future__ import annotations

import math
from typing import Callable, Iterable, Optional

from .netexpr import parseNetSet
from .primitives import INHERIT, NONAME, SET, WEAK, Port, Seg

# Map a persisted/enum strength value to the primitive int levels.
_STRENGTH_TO_INT = {0: NONAME, 1: WEAK, 2: INHERIT, 3: SET}


def _strengthInt(value) -> int:
    """Accept int or an enum with a .value attribute."""
    return _STRENGTH_TO_INT[int(getattr(value, "value", value))]


def _pointTuple(point) -> tuple[float, float]:
    """Accept QPoint/QPointF or a (x, y) tuple."""
    toTuple = getattr(point, "toTuple", None)
    if toTuple is not None:
        x, y = toTuple()
        return float(x), float(y)
    x, y = point
    return float(x), float(y)


def fromSceneItems(netItems: Iterable, pinItems: Iterable,
                   ) -> tuple[list[Seg], list[Port], dict[int, object],
                              dict[int, object]]:
    """Build primitives from live items.

    Args:
        netItems: schematicNet items (or anything with sceneEndPoints, name,
            nameStrength).
        pinItems: symbolPin and schematicPin items (duck-typed: pinName,
            pinDir, start, mapToScene). Symbol pins are detected by having a
            parentItem with an instanceName.

    Returns:
        (segs, ports, segItemById, portItemById) — the id maps let callers
        push resolved names/conflicts back onto the original items.
    """
    segs: list[Seg] = []
    segItemById: dict[int, object] = {}
    for segId, netItem in enumerate(netItems):
        p1, p2 = (_pointTuple(p) for p in netItem.sceneEndPoints)
        segs.append(Seg(id=segId, p1=p1, p2=p2, name=netItem.name,
                        strength=_strengthInt(netItem.nameStrength),
                        expr=getattr(netItem, "netExpr", "") or ""))
        segItemById[segId] = netItem

    ports: list[Port] = []
    portItemById: dict[int, object] = {}
    for portId, pinItem in enumerate(pinItems):
        point = _pointTuple(pinItem.mapToScene(pinItem.start))
        parentItem = pinItem.parentItem()
        owner = getattr(parentItem, "instanceName", "") if parentItem else ""
        kind = "symbolPin" if owner else "schemPin"
        ports.append(Port(id=portId, name=pinItem.pinName,
                          direction=pinItem.pinDir, point=point, kind=kind,
                          owner=owner or pinItem.pinName,
                          expr=getattr(pinItem, "netExpr", "") or "",
                          netSet=dict(getattr(parentItem, "netSet", {}) or {})
                          if kind == "symbolPin" else {}))
        portItemById[portId] = pinItem
    return segs, ports, segItemById, portItemById


def _transformedPinPoint(pinPos: tuple[float, float], loc: tuple[float, float],
                         angle: float,
                         flip: tuple[float, float]) -> tuple[float, float]:
    """Map a symbol-space pin position into sheet coordinates.

    Mirrors the QGraphicsItem transform used by schematicSymbol:
    rotate by angle (degrees, counterclockwise-positive), scale by
    flipTuple, translate by loc.
    """
    # The live item's effective transform is T(loc) * S(flip) * R(angle):
    # flipTuple is post-multiplied into the manual transform matrix, which
    # Qt composes *outside* the rotation property — so the point rotates
    # first, then flips. Qt's rotate() maps (1,0) -> (cos, sin).
    x, y = pinPos
    if angle:
        rad = math.radians(angle)
        cosA, sinA = math.cos(rad), math.sin(rad)
        x, y = x * cosA - y * sinA, x * sinA + y * cosA
    return loc[0] + x * flip[0], loc[1] + y * flip[1]


def fromRecords(records: Iterable[dict],
                pinLocator: Optional[Callable[[str, str, str], dict]] = None,
                ) -> tuple[list[Seg], list[Port], list[str]]:
    """Build primitives from a decoded schematic JSON design array.

    Record fields (schematicEncoder):
        scn: st/end points, nam name, ns strength
        scp: st point, pn name, pd direction
        sys: lib/cell/view instance; pin positions come from pinLocator.

    Args:
        records: iterable of record dicts (the header entry without "type"
            is skipped).
        pinLocator: callable (libName, cellName, viewName) ->
            {pinName: (x, y)} in symbol coordinates, plus optional
            {"directions": {pinName: dir}} entries. Instances are skipped
            (with a diagnostic) when no locator or no result is available.

    Returns:
        (segs, ports, diagnostics) — diagnostics are human-readable strings
        for unresolved instances or malformed records; callers decide how to
        surface them.
    """
    segs: list[Seg] = []
    ports: list[Port] = []
    diagnostics: list[str] = []

    for record in records:
        recType = record.get("type")
        try:
            if recType == "scn":
                segs.append(Seg(
                    id=len(segs),
                    p1=(float(record["st"][0]), float(record["st"][1])),
                    p2=(float(record["end"][0]), float(record["end"][1])),
                    name=record.get("nam", "") or "",
                    strength=_strengthInt(record.get("ns", 0)),
                    expr=record.get("nx", "") or ""))
            elif recType == "scp":
                ports.append(Port(
                    id=len(ports),
                    name=record.get("pn", ""),
                    direction=record.get("pd", ""),
                    point=(float(record["st"][0]), float(record["st"][1])),
                    kind="schemPin",
                    owner=record.get("pn", ""),
                    expr=record.get("nx", "") or ""))
            elif recType == "sys":
                _portsFromInstanceRecord(record, ports, pinLocator,
                                         diagnostics)
        except (KeyError, TypeError, ValueError, IndexError) as e:
            diagnostics.append(f"Malformed {recType} record skipped: {e}")
    return segs, ports, diagnostics


# Keys in a pinLocator result that are metadata, not pin positions.
_PINMAP_META_KEYS = {"directions", "paramDefs", "pinExprs"}


def _portsFromInstanceRecord(record: dict, ports: list[Port],
                             pinLocator, diagnostics: list[str]) -> None:
    instName = record.get("nam", "")
    if pinLocator is None:
        diagnostics.append(
            f"Instance {instName} skipped: no pin locator provided.")
        return
    pinMap = pinLocator(record.get("lib", ""), record.get("cell", ""),
                        record.get("view", "symbol"))
    if not pinMap:
        diagnostics.append(
            f"Instance {instName} ({record.get('lib')}/{record.get('cell')}) "
            f"skipped: symbol pins not found.")
        return
    directions = pinMap.get("directions", {})
    pinExprs = pinMap.get("pinExprs", {})
    instNetSet = parseNetSet(record.get("nst"))
    loc = record.get("loc", (0, 0))
    angle = float(record.get("ang", 0) or 0)
    flip = record.get("fl", (1, 1))
    for pinName, pinPos in pinMap.items():
        if pinName in _PINMAP_META_KEYS:
            continue
        if not (isinstance(pinPos, (list, tuple)) and len(pinPos) == 2):
            diagnostics.append(
                f"Instance {instName}: pin '{pinName}' has malformed "
                f"position {pinPos!r}, skipped.")
            continue
        ports.append(Port(
            id=len(ports), name=pinName,
            direction=directions.get(pinName, ""),
            point=_transformedPinPoint(pinPos, loc, angle, flip),
            kind="symbolPin", owner=instName,
            expr=pinExprs.get(pinName, "") or "",
            netSet=instNetSet))


# ---------------------------------------------------------------------------
# Layout items -> connectivity.layout primitives
# ---------------------------------------------------------------------------


def _layRectFromSceneRect(rect) -> "LayRect":
    """QRectF/QRect -> LayRect (normalized)."""
    from .layout import LayRect
    r = rect.normalized()
    return LayRect(float(r.left()), float(r.top()),
                   float(r.right()), float(r.bottom()))


def _layRectFromPoints(p1, p2) -> "LayRect":
    from .layout import LayRect
    x1, y1 = _pointTuple(p1)
    x2, y2 = _pointTuple(p2)
    return LayRect(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))


def _viaLayers(viaDefTuple) -> tuple[str, str, str]:
    """(via_type, lower_layer_name, upper_layer_name) from a viaDefTuple."""
    lower = getattr(viaDefTuple, "bottomLayer", None)
    upper = getattr(viaDefTuple, "topLayer", None)
    return (
        getattr(viaDefTuple, "name", "") or "",
        getattr(lower, "name", "") or "",
        getattr(upper, "name", "") or "",
    )


def fromLayoutItems(items: Iterable,
                    ) -> tuple[list, list, list, dict[int, object],
                               dict[int, object], dict[int, object]]:
    """Build layout connectivity primitives from live scene items.

    Duck-typed by class name so the adapter stays Qt-free:

        layoutPath     -> LayShape(kind="path") with centerline/width
        layoutRect     -> LayShape(kind="rect") from sceneBoundingRect
        layoutPolygon  -> LayShape(kind="polygon") from sceneBoundingRect
        layoutPin      -> LayShape(kind="pin") + name anchor at its start
        layoutLabel    -> name anchor at mapToScene(start) (not a shape)
        layoutVia      -> LayVia (cut footprint = start/end mapped to scene)
        layoutViaArray -> LayVia (array cut footprint like the JSON reader)

    Container items (``layoutInstance``/``layoutPcell``/``layoutMultipart``
    and subclasses — anything exposing a ``shapes`` list) are expanded:
    their children, including realized mosaic ``arrayShapes`` and nested
    instances, are resolved in scene coordinates so highlight-net reaches
    through the hierarchy (e.g. metal inside a substrate-tap instance).
    Internal pins are shapes like any other metal but contribute no name
    anchors — naming stays a top-level concern and instance terminal names
    must not rename or conflict with the nets they join.

    Returns:
        (shapes, vias, anchors, shapeItemByIdx, viaItemByIdx,
         anchorItemByIdx) — anchors are (name, x, y) tuples; the id maps let
        callers trace primitives back to their source items.
    """
    from .layout import LayVia, _pathFootprint

    shapes: list = []
    vias: list = []
    anchors: list = []
    shapeItemByIdx: dict[int, object] = {}
    viaItemByIdx: dict[int, object] = {}
    anchorItemByIdx: dict[int, object] = {}
    seenContainers: set[int] = set()

    def addAnchor(name, point, item):
        if not name:
            return
        x, y = _pointTuple(point)
        anchorItemByIdx[len(anchors)] = item
        anchors.append((name, x, y))

    def process(item, internal: bool):
        clsName = type(item).__name__
        if hasattr(item, "shapes"):
            if id(item) in seenContainers:
                return
            seenContainers.add(id(item))
            for child in item.shapes:
                process(child, True)
            for child in getattr(item, "arrayShapes", None) or ():
                process(child, True)
        elif clsName == "layoutPath":
            ends = item.sceneEndPoints
            x1, y1 = _pointTuple(ends[0])
            x2, y2 = _pointTuple(ends[1])
            width = float(item.width)
            se = float(item.startExtend)
            ee = float(item.endExtend)
            footprint = _pathFootprint(x1, y1, x2, y2, width, se, ee)
            shapeItemByIdx[len(shapes)] = item
            shape = _layoutShape(
                kind="path", layer=item.layer, footprint=footprint,
                centerline=(x1, y1, x2, y2), width=width)
            shape.item = item
            shapes.append(shape)
        elif clsName in ("layoutRect", "layoutPolygon", "layoutPin"):
            footprint = _layRectFromSceneRect(item.sceneBoundingRect())
            shapeItemByIdx[len(shapes)] = item
            shape = _layoutShape(
                kind="pin" if clsName == "layoutPin" else
                "rect" if clsName == "layoutRect" else "polygon",
                layer=item.layer, footprint=footprint)
            shape.item = item
            shapes.append(shape)
            if clsName == "layoutPin" and not internal:
                addAnchor(item.pinName, item.mapToScene(item.start), item)
        elif clsName == "layoutLabel":
            if not internal:
                addAnchor(item.labelText, item.mapToScene(item.start), item)
        elif clsName in ("layoutVia", "layoutViaArray"):
            if clsName == "layoutVia":
                viaDef = item.viaDefTuple
                rect = item.rect.normalized()
                footprint = _layRectFromPoints(
                    item.mapToScene(rect.topLeft()),
                    item.mapToScene(rect.bottomRight()))
                nx = ny = 1
                xs = ys = 0.0
            else:
                viaDef = item.via.viaDefTuple
                nx = int(item.xnum)
                ny = int(item.ynum)
                xs = float(item.xs)
                ys = float(item.ys)
                # Map all four corners of the local array bbox so rotated
                # arrays get a correct axis-aligned bound.
                from PySide6.QtCore import QPointF
                w = float(item.width)
                h = float(item.height)
                xExt = (nx - 1) * (xs + w) + w
                yExt = (ny - 1) * (ys + h) + h
                corners = [
                    item.mapToScene(QPointF(item.start) + QPointF(dx, dy))
                    for dx, dy in ((0, 0), (xExt, 0), (0, yExt),
                                   (xExt, yExt))
                ]
                from .layout import LayRect
                xs_s = [_pointTuple(c)[0] for c in corners]
                ys_s = [_pointTuple(c)[1] for c in corners]
                footprint = LayRect(min(xs_s), min(ys_s),
                                    max(xs_s), max(ys_s))
            viaType, lower, upper = _viaLayers(viaDef)
            viaItemByIdx[len(vias)] = item
            via = LayVia(
                via_type=viaType, lower_layer=lower, upper_layer=upper,
                footprint=footprint, nx=nx, ny=ny,
                spacing_x=xs, spacing_y=ys,
                width=float(item.width), height=float(item.height))
            via.item = item
            vias.append(via)

    for item in items:
        process(item, False)
    return shapes, vias, anchors, shapeItemByIdx, viaItemByIdx, anchorItemByIdx


def _layoutShape(kind: str, layer, footprint, centerline=None,
                 width: float = 0.0):
    from .layout import LayShape
    return LayShape(
        kind=kind,
        layer_name=getattr(layer, "name", "") or "",
        gds_layer=int(getattr(layer, "gdsLayer", 0) or 0),
        footprint=footprint,
        centerline=centerline,
        width=width,
    )
