#
# Copyright (c) 2024-2026 Revolution Semiconductor (Registered in the Netherlands)
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this file, You can obtain one at
# https://mozilla.org/MPL/2.0/.
#
# Add-ons and extensions developed for this software may be distributed
# under their own separate licenses.
#
"""Qt-free layout connectivity engine.

This is the shared geometric connectivity implementation for layout data.
It is consumed two ways:

  * live ``layoutScene`` items (via :func:`adapters.fromLayoutItems`) for
    layout net identity and highlight-net;
  * decoded ``layout.json`` records (via
    :class:`rcextraction.layoutGeometry.LayoutGeometryReader`) for RCX,
    batch tooling, and importers.

Grouping semantics:

  * shapes on the same layer merge when their footprints touch/overlap;
  * a via merges the lower-layer and upper-layer shapes it lands on;
  * a Pcell instance acts as a connectivity *bridge*: routing that lands on
    the same Pcell terminal (pin) is tied together. Pcell internal geometry
    is not treated as interconnect parasitics -- device internals belong to
    the device model, per standard PEX convention.

Net *names* come from layout pins and text labels through
:func:`assignNetNames`; unnamed groups receive deterministic ``net<N>``
names.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Optional


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

    ``kind`` is one of ``"path"``, ``"rect"``, ``"polygon"``, ``"pin"``.
    Vias are handled separately (see :class:`LayVia`). ``footprint`` is the
    drawn bounding box used for connectivity. For paths, ``centerline`` +
    ``width`` drive R/C so the extractor gets an accurate length/width
    rather than a bounding box.
    """

    kind: str
    layer_name: str
    gds_layer: int
    footprint: LayRect
    # Path-only: centerline endpoints (dbu) and drawn width (dbu)
    centerline: Optional[tuple[float, float, float, float]] = None
    width: float = 0.0
    group: int = -1  # union-find group id, assigned during connectivity
    item: Optional[object] = None  # back-reference to the source item/record


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
    item: Optional[object] = None  # back-reference to the source item/record


@dataclass
class NetGroup:
    """A connected group of shapes = one net.

    ``name`` is filled by :func:`assignNetNames`; it is left empty by
    :func:`buildConnectivity` so callers that apply their own naming
    (e.g. RCX LVS-anchor naming) are unaffected.
    """

    shapes: list[LayShape] = field(default_factory=list)
    vias: list[LayVia] = field(default_factory=list)
    name: str = ""


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


def _layerBase(name: Optional[str]) -> str:
    """The ``_layersMatch`` key for a layer name ("" never matches)."""
    return name.lower().split("_")[0] if name else ""


def _layersMatch(l1: Optional[str], l2: Optional[str]) -> bool:
    if not l1 or not l2:
        return False
    a = l1.lower().split("_")[0]
    b = l2.lower().split("_")[0]
    return a == b


class _LayerGrid:
    """Uniform-grid spatial index over shape footprints.

    Shapes are bucketed by their ``_layerBase`` key, then hashed into grid
    cells sized by the bucket's median footprint dimension.  Candidate
    queries return only shapes whose (tolerance-expanded) footprints share a
    cell -- the caller still runs the exact ``intersects`` test, so results
    are identical to a pairwise scan, just without the O(n^2) cost.

    Footprints spanning more than ``_MAX_CELLS`` cells (e.g. a chip-size
    ground plate) are kept on a per-layer "always candidate" list so a
    single huge shape cannot blow up the cell count.
    """

    _MAX_CELLS = 256

    def __init__(self, shapes: list[LayShape], tol: float):
        self._tol = tol
        self._grids: dict[str, dict[tuple[int, int], list[int]]] = {}
        self._cellSize: dict[str, float] = {}
        self._spans: dict[str, list[int]] = {}

        byLayer: dict[str, list[int]] = {}
        for idx, shape in enumerate(shapes):
            key = _layerBase(shape.layer_name)
            if key:
                byLayer.setdefault(key, []).append(idx)
        for key, indices in byLayer.items():
            dims = sorted(
                max(shapes[i].footprint.x2 - shapes[i].footprint.x1,
                    shapes[i].footprint.y2 - shapes[i].footprint.y1)
                for i in indices)
            cell = max(dims[len(dims) // 2], 1.0)
            self._cellSize[key] = cell
            grid: dict[tuple[int, int], list[int]] = {}
            for idx in indices:
                cells = self._coveredCells(shapes[idx].footprint, cell)
                if len(cells) > self._MAX_CELLS:
                    self._spans.setdefault(key, []).append(idx)
                    continue
                for c in cells:
                    grid.setdefault(c, []).append(idx)
            self._grids[key] = grid

    def _coveredCells(self, fp: LayRect, cell: float) -> list:
        tol = self._tol
        cx1 = math.floor((fp.x1 - tol) / cell)
        cy1 = math.floor((fp.y1 - tol) / cell)
        cx2 = math.floor((fp.x2 + tol) / cell)
        cy2 = math.floor((fp.y2 + tol) / cell)
        return [(cx, cy)
                for cx in range(cx1, cx2 + 1)
                for cy in range(cy1, cy2 + 1)]

    def query(self, layer_name: Optional[str], fp: LayRect) -> list[int]:
        """Indices of shapes on ``layer_name``'s layer base whose footprints
        may touch ``fp`` (within the index tolerance)."""
        key = _layerBase(layer_name)
        if not key or key not in self._cellSize:
            return []
        out = list(self._spans.get(key, ()))
        grid = self._grids[key]
        for c in self._coveredCells(fp, self._cellSize[key]):
            out.extend(grid.get(c, ()))
        return out


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
        A list of :class:`NetGroup`, one per connected net. Ordering is
        deterministic: groups appear in first-shape index order, followed by
        orphan-via groups.
    """
    n = len(shapes)
    uf = _UnionFind(n) if n else _UnionFind(1)
    grid = _LayerGrid(shapes, touchTolerance)

    # 1) Same-layer shape-to-shape merges.  The grid supplies candidate
    # pairs (already same layer base); ``stamp`` dedupes pairs sharing
    # several cells.
    stamp = [-1] * n
    for i, shape in enumerate(shapes):
        for j in grid.query(shape.layer_name, shape.footprint):
            if j <= i or stamp[j] == i:
                continue
            stamp[j] = i
            if shape.footprint.intersects(shapes[j].footprint, touchTolerance):
                uf.union(i, j)

    # 2) Vias merge a lower-layer shape with an upper-layer shape.
    # ``viaHits`` remembers each via's hits so the group-assignment pass
    # below doesn't scan the shapes again.
    viaHits: list[tuple[int, int]] = []
    for via in vias:
        lowerHit = -1
        upperHit = -1
        candidates = set(grid.query(via.lower_layer, via.footprint))
        candidates.update(grid.query(via.upper_layer, via.footprint))
        # Sorted to keep the original ascending-index hit semantics.
        for idx in sorted(candidates):
            shape = shapes[idx]
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
        viaHits.append((lowerHit, upperHit))
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
                    candidates = set(grid.query(bridge.layer_name,
                                                bridge.footprint))
                    for idx in sorted(candidates):
                        shape = shapes[idx]
                        if not _layersMatch(shape.layer_name,
                                            bridge.layer_name):
                            continue
                        if shape.footprint.intersects(bridge.footprint, touchTolerance):
                            if anchor == -1:
                                anchor = idx
                            else:
                                uf.union(anchor, idx)

    # Collect groups. ``uf.find`` returns the highest-index member as the
    # root (union always attaches the lower root under the higher), so sort
    # the collected roots by minimum member index for deterministic order.
    groups: dict[int, NetGroup] = {}
    for idx, shape in enumerate(shapes):
        root = uf.find(idx)
        shape.group = root
        groups.setdefault(root, NetGroup()).shapes.append(shape)

    # Assign each via to the group of a shape it lands on (prefer lower layer).
    # All hit shapes were unioned in step 2, so any hit's group is the via's.
    for via, (lowerHit, upperHit) in zip(vias, viaHits):
        hit = lowerHit if lowerHit != -1 else upperHit
        if hit != -1:
            groups[shapes[hit].group].vias.append(via)
        else:
            # Orphan via (no metal landed): keep it in its own group so its
            # resistance is not silently dropped.
            orphan = NetGroup(vias=[via])
            groups[id(via)] = orphan

    # Canonical ordering by top-left footprint corner: net identity and
    # auto-names are stable regardless of the input item order.
    return sorted(groups.values(), key=_groupKey)


def _groupKey(group: NetGroup) -> tuple[float, float]:
    footprints = [s.footprint for s in group.shapes]
    footprints.extend(v.footprint for v in group.vias)
    return (min(f.x1 for f in footprints), min(f.y1 for f in footprints))


# ---------------------------------------------------------------------------
# Layout JSON record adapter
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

    def read(self, layoutElements: list[dict],
             _offset: tuple[float, float] = (0.0, 0.0),
             ) -> tuple[list[LayShape], list[LayVia]]:
        """Return (shapes, vias) parsed from the layout element list.

        The first two entries of a ``layout.json`` array are the view header
        and scene settings; they are skipped. ``_offset`` is the
        accumulated parent translation for records nested inside ``Group``
        records (member coordinates are group-local).
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
                    shapes.append(self._offsetShape(shape, _offset))
            elif etype == "Rect":
                shape = self._readBox(elem, "rect")
                if shape is not None:
                    shapes.append(self._offsetShape(shape, _offset))
            elif etype == "Pin":
                # A layout pin is metal on its layer (same as the live
                # layoutPin item in fromLayoutItems); it is also a name
                # anchor via readAnchors().
                shape = self._readBox(elem, "pin")
                if shape is not None:
                    shapes.append(self._offsetShape(shape, _offset))
            elif etype == "Polygon":
                # Live connectivity currently uses polygon bounding boxes;
                # preserve that same contract for decoded records.
                shape = self._readPolygon(elem)
                if shape is not None:
                    shapes.append(self._offsetShape(shape, _offset))
            elif etype == "Via":
                via = self._readVia(elem)
                if via is not None:
                    vias.append(self._offsetVia(via, _offset))
            elif etype == "Group":
                # Group members are stored in group-local coordinates;
                # ``loc`` re-anchors them. Group rotation/flip are ignored
                # at record level, matching how ``ang`` is ignored for
                # every other record type here.
                loc = elem.get("loc") or (0.0, 0.0)
                subShapes, subVias = self.read(
                    elem.get("items", []),
                    (_offset[0] + float(loc[0]), _offset[1] + float(loc[1])))
                shapes.extend(subShapes)
                vias.extend(subVias)
            # Pcell instances are handled by the caller (they need pin
            # footprints, resolved via the layout scene). Labels and text
            # carry no interconnect area.

        return shapes, vias

    @staticmethod
    def _offsetRect(rect: LayRect, offset) -> LayRect:
        dx, dy = offset
        if not (dx or dy):
            return rect
        return LayRect(rect.x1 + dx, rect.y1 + dy,
                       rect.x2 + dx, rect.y2 + dy)

    @classmethod
    def _offsetShape(cls, shape: LayShape, offset) -> LayShape:
        if not (offset[0] or offset[1]):
            return shape
        shape.footprint = cls._offsetRect(shape.footprint, offset)
        if shape.centerline is not None:
            x1, y1, x2, y2 = shape.centerline
            dx, dy = offset
            shape.centerline = (x1 + dx, y1 + dy, x2 + dx, y2 + dy)
        return shape

    @classmethod
    def _offsetVia(cls, via: LayVia, offset) -> LayVia:
        via.footprint = cls._offsetRect(via.footprint, offset)
        return via

    def readAnchors(self, layoutElements: list[dict],
                    _offset: tuple[float, float] = (0.0, 0.0),
                    ) -> list[tuple[str, float, float]]:
        """Return (name, x, y) anchors from Pin and Label records.

        Pin records anchor at their top-left corner (``tl``); label records
        anchor at ``st`` -- both are pos-folded scene coordinates written by
        ``layoutEncoder``. Anchors inside ``Group`` records are group-local
        and shifted by the group's ``loc``.
        """
        dx, dy = _offset
        anchors: list[tuple[str, float, float]] = []
        for elem in layoutElements:
            if not isinstance(elem, dict):
                continue
            etype = elem.get("type")
            if etype == "Pin":
                name = elem.get("pn", "")
                tl = elem.get("tl")
                if name and tl:
                    anchors.append(
                        (name, float(tl[0]) + dx, float(tl[1]) + dy))
            elif etype == "Label":
                name = elem.get("lt", "")
                st = elem.get("st")
                if name and st:
                    anchors.append(
                        (name, float(st[0]) + dx, float(st[1]) + dy))
            elif etype == "Group":
                loc = elem.get("loc") or (0.0, 0.0)
                anchors.extend(self.readAnchors(
                    elem.get("items", []),
                    (dx + float(loc[0]), dy + float(loc[1]))))
        return anchors

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

    def _readBox(self, elem: dict, kind: str) -> Optional[LayShape]:
        """Read Rect and Pin records, which share geometry and layer fields."""
        layer = self._layerByIndex(elem.get("ln", -1))
        tl = elem.get("tl")
        br = elem.get("br")
        if layer is None or not tl or not br:
            return None
        x1, y1 = float(tl[0]), float(tl[1])
        x2, y2 = float(br[0]), float(br[1])
        return LayShape(
            kind=kind,
            layer_name=layer.name,
            gds_layer=int(getattr(layer, "gdsLayer", 0) or 0),
            footprint=LayRect(min(x1, x2), min(y1, y2),
                              max(x1, x2), max(y1, y2)),
        )

    def _readPolygon(self, elem: dict) -> Optional[LayShape]:
        """Read a Polygon using the shared bounding-box connectivity model."""
        layer = self._layerByIndex(elem.get("ln", -1))
        points = elem.get("ps")
        if layer is None or not isinstance(points, (list, tuple)) \
                or len(points) < 3:
            return None
        try:
            xs = [float(point[0]) for point in points]
            ys = [float(point[1]) for point in points]
        except (IndexError, TypeError, ValueError):
            return None
        return LayShape(
            kind="polygon",
            layer_name=layer.name,
            gds_layer=int(getattr(layer, "gdsLayer", 0) or 0),
            footprint=LayRect(min(xs), min(ys), max(xs), max(ys)),
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
# Net naming
# ---------------------------------------------------------------------------


def assignNetNames(
    groups: list[NetGroup],
    anchors: list[tuple[str, float, float]],
    touchTolerance: float = 0.0,
    autoPrefix: str = "net",
) -> list[str]:
    """Attach names to net groups from (name, x, y) anchors.

    Anchors come from layout pins and text labels. The first anchor (in
    list order) whose point lands inside a member shape or via footprint
    names that group; additional anchors with a different name are
    recorded as conflicts in ``NetGroup`` order and the group keeps its
    first name. Groups with no anchor receive deterministic
    ``<autoPrefix><N>`` names, skipping any name already in use.

    Side effect: ``group.name`` is set on each group.

    Returns:
        ``(names, conflicts, autoCount)`` — parallel name list, a list of
        conflict description strings, and the next free auto-name counter.
    """
    names: list[str] = [""] * len(groups)
    conflicts: list[str] = []

    for name, x, y in anchors:
        if not name:
            continue
        for gi, group in enumerate(groups):
            hit = any(
                shape.footprint.contains_point(x, y, touchTolerance)
                for shape in group.shapes
            ) or any(
                via.footprint.contains_point(x, y, touchTolerance)
                for via in group.vias
            )
            if not hit:
                continue
            if names[gi] and names[gi] != name:
                conflicts.append(
                    f"Layout net name conflict on '{names[gi]}': anchor "
                    f"'{name}' also lands on the same net"
                )
            elif not names[gi]:
                names[gi] = name
            break

    used = set(names)
    autoCount = 0
    for gi, group in enumerate(groups):
        if names[gi]:
            group.name = names[gi]
            continue
        while f"{autoPrefix}{autoCount}" in used:
            autoCount += 1
        auto = f"{autoPrefix}{autoCount}"
        autoCount += 1
        names[gi] = auto
        used.add(auto)
        group.name = auto
    return names, conflicts, autoCount
