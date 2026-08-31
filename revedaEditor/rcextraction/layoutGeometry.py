#
# Copyright (c) 2024-2026 Revolution Semiconductor (Registered in the Netherlands)
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this file, You can obtain one at
# https://mozilla.org/MPL/2.0/.
#
# Add-ons and extensions developed for this software may be distributed
# under their own separate licenses.

"""Read real routing geometry from a Revolution EDA ``layout.json`` and group
it into nets for RC extraction.

Why this exists
---------------
The KLayout ``.lvsdb`` is a *connectivity* database: its per-net shapes live on
internal rule-deck layers that carry no GDS mapping, so they cannot be resolved
to physical metal layers or real dimensions. Feeding them to the extractor
yields degenerate, identical R/C values.

The ``layout.json`` cellview, by contrast, holds the actual drawn interconnect
(``Path``/``Rect``/``Via`` on real PDK layers with real widths and
coordinates). This module reads that geometry, resolves each shape's PDK layer
(name + GDS number), and performs a geometric connectivity pass (union-find) to
group shapes into nets:

  * shapes on the same layer merge when their footprints touch/overlap;
  * a via merges the lower-layer and upper-layer shapes it lands on;
  * a Pcell instance acts as a connectivity *bridge*: routing that lands on the
    same Pcell terminal (pin) is tied together. Pcell internal geometry is not
    treated as interconnect parasitics -- device internals belong to the device
    model, per standard PEX convention.

The module is GUI-independent: it takes the parsed layout JSON, the PDK
``layoutLayers`` module, and the PDK via definitions. Net *names* are attached
separately (see :mod:`rcxExport`) using label positions from the LVSDB.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("reveda")


# ---------------------------------------------------------------------------
# Internal geometry representation
# ---------------------------------------------------------------------------


@dataclass
class LayRect:
    """An axis-aligned rectangle footprint in scene (dbu) coordinates."""

    x1: float
    y1: float
    x2: float
    y2: float

    def intersects(self, other: "LayRect", tol: float = 0.0) -> bool:
        """True if the two rectangles overlap or touch (within ``tol``)."""
        return not (
            self.x2 + tol < other.x1
            or other.x2 + tol < self.x1
            or self.y2 + tol < other.y1
            or other.y2 + tol < self.y1
        )

    def contains_point(self, x: float, y: float, tol: float = 0.0) -> bool:
        return (
            self.x1 - tol <= x <= self.x2 + tol
            and self.y1 - tol <= y <= self.y2 + tol
        )


@dataclass
class LayShape:
    """A resolved layout shape with the data both connectivity and the
    extractor need.

    ``kind`` is one of ``"path"``, ``"rect"``. Vias are handled separately
    (see :class:`LayVia`). ``footprint`` is the drawn bounding box used for
    connectivity. For paths, ``centerline`` + ``width`` drive R/C so the
    extractor gets an accurate length/width rather than a bounding box.
    """

    kind: str
    layer_name: str
    gds_layer: int
    footprint: LayRect
    # Path-only: centerline endpoints (dbu) and drawn width (dbu)
    centerline: Optional[tuple[float, float, float, float]] = None
    width: float = 0.0
    group: int = -1  # union-find group id, assigned during connectivity


@dataclass
class LayVia:
    """A via/cut array connecting a lower and an upper metal layer."""

    via_type: str
    lower_layer: str
    upper_layer: str
    footprint: LayRect  # overall array footprint (dbu)
    nx: int = 1
    ny: int = 1
    spacing_x: float = 0.0
    spacing_y: float = 0.0
    width: float = 0.0   # single-cut width (dbu)
    height: float = 0.0  # single-cut height (dbu)
    group: int = -1


@dataclass
class NetGroup:
    """A connected group of shapes = one net."""

    shapes: list[LayShape] = field(default_factory=list)
    vias: list[LayVia] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------


def _pathFootprint(
    x1: float, y1: float, x2: float, y2: float, width: float,
    startExtend: float, endExtend: float,
) -> LayRect:
    """Bounding box of a drawn path (centerline widened by ``width`` and
    extended by the start/end extensions).

    This is an axis-aligned bound, which is exact for Manhattan paths (the
    common case) and a safe over-approximation for diagonal paths -- fine for
    the touch test used in connectivity.
    """
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    hw = width / 2.0
    if length == 0:
        return LayRect(x1 - hw, y1 - hw, x1 + hw, y1 + hw)
    ux, uy = dx / length, dy / length  # unit direction
    # Extend endpoints along the path direction
    ex1, ey1 = x1 - ux * startExtend, y1 - uy * startExtend
    ex2, ey2 = x2 + ux * endExtend, y2 + uy * endExtend
    # Perpendicular half-width offsets
    px, py = -uy * hw, ux * hw
    xs = [ex1 + px, ex1 - px, ex2 + px, ex2 - px]
    ys = [ey1 + py, ey1 - py, ey2 + py, ey2 - py]
    return LayRect(min(xs), min(ys), max(xs), max(ys))


# ---------------------------------------------------------------------------
# Layout JSON reader
# ---------------------------------------------------------------------------


class LayoutGeometryReader:
    """Parse a ``layout.json`` element list into resolved shapes and vias."""

    def __init__(self, layoutLayers: Any, processModule: Any):
        """Args:
        layoutLayers: the PDK ``layoutLayers`` module (provides
            ``pdkAllLayers`` indexed by the JSON ``ln`` field).
        processModule: the PDK ``process`` module (provides ``processVias``
            for resolving via ``vdt`` -> lower/upper metal layers).
        """
        self._layers = layoutLayers
        self._pdkAllLayers = getattr(layoutLayers, "pdkAllLayers", [])
        # Build vdt -> viaDef lookup
        self._viaDefs: dict[str, Any] = {}
        for viaDef in getattr(processModule, "processVias", []):
            self._viaDefs[viaDef.name] = viaDef

    def _layerByIndex(self, ln: int):
        if 0 <= ln < len(self._pdkAllLayers):
            return self._pdkAllLayers[ln]
        return None

    def read(self, layoutElements: list[dict]) -> tuple[list[LayShape], list[LayVia]]:
        """Return (shapes, vias) parsed from the layout element list.

        The first two entries of a ``layout.json`` array are the view header
        and scene settings; they are skipped.
        """
        shapes: list[LayShape] = []
        vias: list[LayVia] = []

        for elem in layoutElements:
            if not isinstance(elem, dict):
                continue
            etype = elem.get("type")
            if etype == "Path":
                shape = self._readPath(elem)
                if shape is not None:
                    shapes.append(shape)
            elif etype == "Rect":
                shape = self._readRect(elem)
                if shape is not None:
                    shapes.append(shape)
            elif etype == "Via":
                via = self._readVia(elem)
                if via is not None:
                    vias.append(via)
            # Pcell instances are handled by the caller (they need pin
            # footprints, resolved via the layout scene). Labels/pins/text
            # carry no interconnect area.

        return shapes, vias

    def _readPath(self, elem: dict) -> Optional[LayShape]:
        layer = self._layerByIndex(elem.get("ln", -1))
        if layer is None:
            return None
        p1 = elem.get("dfl1")
        p2 = elem.get("dfl2")
        if not p1 or not p2:
            return None
        x1, y1 = float(p1[0]), float(p1[1])
        x2, y2 = float(p2[0]), float(p2[1])
        width = float(elem.get("w", 0.0))
        se = float(elem.get("se", 0))
        ee = float(elem.get("ee", 0))
        footprint = _pathFootprint(x1, y1, x2, y2, width, se, ee)
        return LayShape(
            kind="path",
            layer_name=layer.name,
            gds_layer=int(getattr(layer, "gdsLayer", 0) or 0),
            footprint=footprint,
            centerline=(x1, y1, x2, y2),
            width=width,
        )

    def _readRect(self, elem: dict) -> Optional[LayShape]:
        layer = self._layerByIndex(elem.get("ln", -1))
        if layer is None:
            return None
        tl = elem.get("tl")
        br = elem.get("br")
        if not tl or not br:
            return None
        x1, y1 = float(tl[0]), float(tl[1])
        x2, y2 = float(br[0]), float(br[1])
        footprint = LayRect(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
        return LayShape(
            kind="rect",
            layer_name=layer.name,
            gds_layer=int(getattr(layer, "gdsLayer", 0) or 0),
            footprint=footprint,
        )

    def _readVia(self, elem: dict) -> Optional[LayVia]:
        viaData = elem.get("via", {})
        vdt = viaData.get("vdt", "")
        viaDef = self._viaDefs.get(vdt)
        st = elem.get("st")
        if st is None:
            st = viaData.get("st")
        if st is None:
            return None
        x0, y0 = float(st[0]), float(st[1])
        w = float(viaData.get("w", 0.0))
        h = float(viaData.get("h", 0.0))
        nx = int(elem.get("xn", 1))
        ny = int(elem.get("yn", 1))
        xs = float(elem.get("xs", 0.0))
        ys = float(elem.get("ys", 0.0))
        # Array footprint: nx*ny cuts stepped by (xs + w, ys + h)
        x_step = xs + w
        y_step = ys + h
        x_end = x0 + (nx - 1) * x_step + w
        y_end = y0 + (ny - 1) * y_step + h
        footprint = LayRect(
            min(x0, x_end),
            min(y0, y_end),
            max(x0, x_end),
            max(y0, y_end),
        )
        # Resolve lower/upper metal layer names from the via definition.
        lower = upper = ""
        if viaDef is not None:
            if getattr(viaDef, "bottomLayer", None) is not None:
                lower = viaDef.bottomLayer.name
            if getattr(viaDef, "topLayer", None) is not None:
                upper = viaDef.topLayer.name
        return LayVia(
            via_type=vdt,
            lower_layer=lower,
            upper_layer=upper,
            footprint=footprint,
            nx=nx,
            ny=ny,
            spacing_x=xs,
            spacing_y=ys,
            width=w,
            height=h,
        )


# ---------------------------------------------------------------------------
# Union-find connectivity
# ---------------------------------------------------------------------------


class _UnionFind:
    def __init__(self, n: int):
        self._parent = list(range(n))

    def find(self, i: int) -> int:
        root = i
        while self._parent[root] != root:
            root = self._parent[root]
        # Path compression
        while self._parent[i] != root:
            self._parent[i], i = root, self._parent[i]
        return root

    def union(self, i: int, j: int) -> None:
        ri, rj = self.find(i), self.find(j)
        if ri != rj:
            self._parent[ri] = rj


@dataclass
class PcellBridge:
    """A Pcell terminal footprint that ties overlapping routing together.

    ``pin_name`` distinguishes terminals: only shapes landing on the *same*
    pin are merged, so a transistor does not short its own drain to its gate.
    """

    pin_name: str
    footprint: LayRect
    layer_name: Optional[str] = None


def _layersMatch(l1: Optional[str], l2: Optional[str]) -> bool:
    if not l1 or not l2:
        return False
    a = l1.lower().split("_")[0]
    b = l2.lower().split("_")[0]
    return a == b


def _viaMatchesShape(via: LayVia, shape: LayShape) -> tuple[bool, str]:
    """Check if a shape matches via lower or upper layer.
    Returns (matches, 'lower'|'upper'|'').
    """
    if _layersMatch(shape.layer_name, via.lower_layer):
        return True, "lower"
    if _layersMatch(shape.layer_name, via.upper_layer):
        return True, "upper"
    return False, ""


def buildConnectivity(
    shapes: list[LayShape],
    vias: list[LayVia],
    pcellBridges: Optional[list[list[PcellBridge]]] = None,
    touchTolerance: float = 0.0,
) -> list[NetGroup]:
    """Group shapes+vias into nets by geometric connectivity.

    Args:
        shapes: resolved metal/poly shapes.
        vias: resolved via arrays.
        pcellBridges: one list of :class:`PcellBridge` per Pcell instance. All
            shapes overlapping a bridge with the *same* pin name are merged.
        touchTolerance: slack (dbu) added to the overlap test to absorb tiny
            gaps from rounding/snapping.

    Returns:
        A list of :class:`NetGroup`, one per connected net.
    """
    n = len(shapes)
    uf = _UnionFind(n) if n else _UnionFind(1)

    # 1) Same-layer shape-to-shape merges.
    for i in range(n):
        for j in range(i + 1, n):
            if not _layersMatch(shapes[i].layer_name, shapes[j].layer_name):
                continue
            if shapes[i].footprint.intersects(shapes[j].footprint, touchTolerance):
                uf.union(i, j)

    # 2) Vias merge a lower-layer shape with an upper-layer shape.
    for via in vias:
        lowerHit = -1
        upperHit = -1
        for idx, shape in enumerate(shapes):
            if not shape.footprint.intersects(via.footprint, touchTolerance):
                continue
            matches, pos = _viaMatchesShape(via, shape)
            if not matches:
                continue
            if pos == "lower":
                if lowerHit == -1:
                    lowerHit = idx
                else:
                    uf.union(idx, lowerHit)
            elif pos == "upper":
                if upperHit == -1:
                    upperHit = idx
                else:
                    uf.union(idx, upperHit)
        if lowerHit != -1 and upperHit != -1:
            uf.union(lowerHit, upperHit)

    # 3) Pcell bridges: shapes overlapping the same pin footprint on matching layer are one net.
    if pcellBridges:
        for bridges in pcellBridges:
            by_pin: dict[str, list[PcellBridge]] = {}
            for bridge in bridges:
                by_pin.setdefault(bridge.pin_name.upper(), []).append(bridge)

            for pin_name, pin_bridges in by_pin.items():
                anchor = -1
                for bridge in pin_bridges:
                    for idx, shape in enumerate(shapes):
                        if not _layersMatch(shape.layer_name, bridge.layer_name):
                            continue
                        if shape.footprint.intersects(bridge.footprint, touchTolerance):
                            if anchor == -1:
                                anchor = idx
                            else:
                                uf.union(anchor, idx)

    # Collect groups.
    groups: dict[int, NetGroup] = {}
    for idx, shape in enumerate(shapes):
        root = uf.find(idx)
        shape.group = root
        groups.setdefault(root, NetGroup()).shapes.append(shape)

    # Assign each via to the group of a shape it lands on (prefer lower layer).
    for via in vias:
        assigned = None
        for shape in shapes:
            if shape.footprint.intersects(via.footprint, touchTolerance):
                matches, _ = _viaMatchesShape(via, shape)
                if matches:
                    assigned = shape.group
                    break
        if assigned is not None:
            groups[assigned].vias.append(via)
        else:
            # Orphan via (no metal landed): keep it in its own group so its
            # resistance is not silently dropped.
            orphan = NetGroup(vias=[via])
            groups[id(via)] = orphan

    return list(groups.values())
