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

import inspect
import logging
import math
from pathlib import Path
from typing import List, Any, Tuple

import gdstk
from PySide6.QtCore import QPointF

import revedaEditor.common.layoutShapes as lshp
from revedaEditor.backend.pdkLoader import importPDKModule

logger = logging.getLogger("reveda")
_process = importPDKModule('process')

# Module-level cache: maps a pcell class -> list of __init__ param names to extract.
# Avoids repeated inspect.signature() calls for identical pcell types.
_pcell_param_cache: dict = {}


class gdsExporter:
    __slots__ = ('_cellname', '_items', '_outputFileObj', '_libraryName',
                 '_unit', '_precision', '_dbu', '_topCell', '_itemCounter',
                 '_cellCache', '_instanceCache', '_pcellCache')

    DEFAULT_UNIT = 1e-9
    DEFAULT_PRECISION = 1e-9
    DEFAULT_DBU = 1000

    def __init__(self, cellname: str, items: List[Any], outputFileObj: Path):
        self._unit = gdsExporter.DEFAULT_UNIT
        self._precision = gdsExporter.DEFAULT_PRECISION
        self._dbu: int = getattr(_process, 'dbu', gdsExporter.DEFAULT_DBU)
        self._cellname = cellname
        self._items = items
        self._outputFileObj = outputFileObj
        self._libraryName = None
        self._topCell = None
        self._itemCounter = 0
        self._cellCache = {}
        self._instanceCache: dict = {}  # (lib, cell, view) -> gdstk.Cell
        self._pcellCache: dict = {}

    def _buildLibrary(self) -> gdstk.Library:
        """Build and populate the gdstk.Library from self._items. Shared by all exporters."""
        self._outputFileObj.parent.mkdir(parents=True, exist_ok=True)
        lib = gdstk.Library(unit=self._unit, precision=self._precision)
        self._topCell = lib.new_cell(self._cellname)
        for item in self._items:
            self.createCells(lib, item, self._topCell)
        return lib

    def gdsExport(self):
        lib = self._buildLibrary()
        lib.write_gds(self._outputFileObj)

    @staticmethod
    def _gdstk_transform(angle: float, flip_tuple: tuple[int, int]) -> tuple[float, bool]:
        """Convert the editor's scale flip and rotation to gdstk parameters."""
        flip_x, flip_y = flip_tuple
        extra_angle = 180.0 if flip_x == -1 else 0.0
        return math.radians(angle + extra_angle), flip_x != flip_y

    def gdsExportThreaded(self, threadPool):
        lib = self._buildLibrary()
        from revedaEditor.backend.startThread import startThread
        writer = startThread(lib.write_gds, str(self._outputFileObj))
        threadPool.start(writer)

    def oasExportThreaded(self, threadPool):
        lib = self._buildLibrary()
        from revedaEditor.backend.startThread import startThread
        writer = startThread(lib.write_oas, str(self._outputFileObj))
        threadPool.start(writer)

    def createCells(self, library: gdstk.Library, item: lshp.layoutShape,
                    parentCell: gdstk.Cell, offset: Tuple[float, float] = (0.0, 0.0)):
        item_type = type(item)
        # layoutPcell subclasses layoutInstance; check it first so pcell
        # subclasses are not dispatched to the plain-instance handler.
        if isinstance(item, lshp.layoutPcell):
            self._process_custom_layout(library, item, parentCell)
        elif item_type == lshp.layoutInstance:
            self._processInstance(library, item, parentCell)
        elif item_type in (lshp.layoutRect, lshp.layoutPin):
            self._processRectPin(item, parentCell, offset)
        elif item_type == lshp.layoutPath:
            self.processPath(item, parentCell, offset)
        elif item_type == lshp.layoutLabel:
            self._processLabel(item, parentCell, offset)
        elif item_type == lshp.layoutPolygon:
            self._processPolygon(item, parentCell, offset)
        elif item_type == lshp.layoutViaArray:
            self._processViaArray(library, item, parentCell, offset)
        elif item_type == lshp.layoutRuler:
            return
        else:
            logger.warning(
                f"Unsupported layout item skipped on export: {type(item).__name__}")

    def _processInstance(self, library, item, parentCell):
        cache_key = (item.libraryName, item.cellName, item.viewName)
        if cache_key not in self._instanceCache:
            # Name the GDS cell libraryName_cellName_viewName; the LVS script maps
            # this back to the schematic subcircuit name via substring matching.
            cellGDSName = f"{item.libraryName}_{item.cellName}_{item.viewName}"
            cellGDS = library.new_cell(cellGDSName)
            # Child shapes are in sub-cell local coordinates — no offset needed.
            for shape in item.shapes:
                self.createCells(library, shape, cellGDS)
            self._instanceCache[cache_key] = cellGDS
        else:
            cellGDS = self._instanceCache[cache_key]

        # Use the parent coordinate of the item's local origin (0,0), not just
        # pos(). This captures the translation from pos(), rotation about the
        # transform origin, and any flip offset, keeping the GDS reference in
        # sync with Qt's scene placement.
        angle_rad, x_reflection = self._gdstk_transform(item.angle, item.flipTuple)
        origin = item.mapToParent(QPointF(0, 0))
        ref = gdstk.Reference(
            cellGDS,
            origin=(origin.x(), origin.y()),
            rotation=angle_rad,
            x_reflection=x_reflection,
        )
        parentCell.add(ref)

    def _processRectPin(self, item, parentCell, offset: Tuple[float, float] = (0.0, 0.0)):
        ox, oy = offset
        corners = (
            item.rect.topLeft(), item.rect.topRight(),
            item.rect.bottomRight(), item.rect.bottomLeft(),
        )
        transformed = [
            (point.x() - ox, point.y() - oy)
            for point in (item.mapToParent(corner) for corner in corners)
        ]

        rect = gdstk.Polygon(
            points=transformed,
            layer=item.layer.gdsLayer,
            datatype=item.layer.datatype,
        )
        parentCell.add(rect)

    def processPath(self, item, parentCell, offset: Tuple[float, float] = (0.0, 0.0)):
        ox, oy = offset
        # draftLine is stored in item-local coordinates where the line is always
        # horizontal (angle reset to 0); the actual direction is carried by the
        # item's Qt rotation transform.  mapToParent() applies that rotation to
        # recover the true endpoints in the parent coordinate system.
        p1 = item.mapToParent(item.draftLine.p1())
        p2 = item.mapToParent(item.draftLine.p2())
        path = gdstk.FlexPath(
            points=[(p1.x() - ox, p1.y() - oy), (p2.x() - ox, p2.y() - oy)],
            width=item.width,
            ends=(item.startExtend, item.endExtend),
            simple_path=True,
            layer=item.layer.gdsLayer,
            datatype=item.layer.datatype,
        )
        parentCell.add(path)

    def _processLabel(self, item, parentCell, offset: Tuple[float, float] = (0.0, 0.0)):
        ox, oy = offset
        # Use the label's placement anchor (item.start) as the GDS origin.
        # boundingRect().center() cannot be used here: boundingRect() mixes
        # scene-dbu coordinates (start) with font-pixel dimensions
        # (QFontMetrics width/height at point size fontHeight*10), so its centre
        # is offset by half the font-pixel size in wrong units — this is the
        # shift seen in the exported GDS.  The export items are recreated from
        # JSON (layoutScene._exportCell round-trips through layoutEncoder), so
        # item.start is already in the parent-local coordinate system that the
        # GDS cell is built in, with pos()=(0,0).
        angle_rad, x_reflection = self._gdstk_transform(item.angle, item.flipTuple)
        origin = item.mapToParent(item.start)
        label = gdstk.Label(
            text=item.labelText,
            origin=(origin.x() - ox, origin.y() - oy),
            magnification=float(item.fontHeight * self._dbu),
            rotation=angle_rad,
            x_reflection=x_reflection,
            layer=item.layer.gdsLayer,
            texttype=item.layer.datatype,
        )
        parentCell.add(label)

    def _processPolygon(self, item, parentCell, offset: Tuple[float, float] = (0.0, 0.0)):
        ox, oy = offset
        transformed = [
            (point.x() - ox, point.y() - oy)
            for point in (item.mapToParent(point) for point in item.points)
        ]

        polygon = gdstk.Polygon(
            points=transformed,
            layer=item.layer.gdsLayer,
            datatype=item.layer.datatype,
        )
        parentCell.add(polygon)

    def _processViaArray(self, library, item, parentCell, offset: Tuple[float, float] = (0.0, 0.0)):
        via_key = (item.via.width, item.via.height, item.via.layer.name,
                   item.via.layer.purpose)
        if via_key not in self._cellCache:
            viaName = f"via_{item.via.width}_{item.via.height}_{item.via.layer.name}_{item.via.layer.purpose}"
            viaCell = library.new_cell(viaName)
            # Define single via at (0, 0) in cell-local coordinates.
            # The Reference origin carries the scene position; mixing both causes a double-offset.
            via = gdstk.rectangle(
                (0, 0),
                (item.via.width, item.via.height),
                layer=item.via.layer.gdsLayer,
                datatype=item.via.layer.datatype,
            )
            viaCell.add(via)
            self._cellCache[via_key] = viaCell
        else:
            viaCell = self._cellCache[via_key]

        ox, oy = offset
        # Place the array using the scene position of its first cut.  gdstk's
        # rotation/flip are applied to the repetition spacing as well, so we
        # decompose the item's flip into an x_reflection and an extra 180°
        # rotation when the X axis is mirrored.
        origin = item.mapToParent(item.start)
        angle_rad, x_reflection = self._gdstk_transform(item.angle, item.flipTuple)
        viaArray = gdstk.Reference(
            cell=viaCell,
            origin=(origin.x() - ox, origin.y() - oy),
            rotation=angle_rad,
            x_reflection=x_reflection,
            columns=item.xnum,
            rows=item.ynum,
            spacing=(item.xs + item.width, item.ys + item.height),
        )
        parentCell.add(viaArray)
        self._processViaEnclosure(item, parentCell, offset)

    def _processViaEnclosure(self, item, parentCell,
                             offset: Tuple[float, float] = (0.0, 0.0)):
        """Emit the connecting-metal layers of a via/via array as GDS polygons.

        A single metal polygon per connecting layer spans the whole array of
        cuts (from the first cut to the last), grown by that layer's enclosure
        margin. The corners are mapped through the item's scene transform so the
        exported metal matches the on-screen rendering even when the array is
        rotated, flipped, or pivoted away from its start point."""
        viaDef = item.via.viaDefTuple
        # Use the via's effective enclosure (per-instance override when set,
        # otherwise the via definition value) so exported metal matches what is
        # drawn on screen.
        enclosureLayers = (
            (getattr(viaDef, "bottomLayer", None), item.via.bottomEnclosure),
            (getattr(viaDef, "topLayer", None), item.via.topEnclosure),
        )
        if not any(layer is not None for layer, _enc in enclosureLayers):
            return

        ox, oy = offset
        # Extent covering every cut, in the same (dbu) coordinate space as cuts.
        xStep = item.xs + item.via.width
        yStep = item.ys + item.via.height
        arrayWidth = (item.xnum - 1) * xStep + item.via.width
        arrayHeight = (item.ynum - 1) * yStep + item.via.height

        base = item.start

        for layer, enclosure in enclosureLayers:
            if layer is None or enclosure <= 0:
                continue
            margin = enclosure * self._dbu
            # Grow the local rectangle by the margin, then map each corner through
            # the array's scene transform.  This keeps the enclosure axis-aligned
            # with the cuts in local coordinates and matches on-screen rendering
            # for arbitrary rotation/flip/pivot.
            margin_offsets = [
                (-margin, -margin),
                (arrayWidth + margin, -margin),
                (arrayWidth + margin, arrayHeight + margin),
                (-margin, arrayHeight + margin),
            ]
            points = []
            for dx, dy in margin_offsets:
                parent_pt = item.mapToParent(QPointF(base.x() + dx, base.y() + dy))
                points.append((parent_pt.x() - ox, parent_pt.y() - oy))
            metal = gdstk.Polygon(
                points=points,
                layer=layer.gdsLayer,
                datatype=layer.datatype,
            )
            parentCell.add(metal)

    def _process_custom_layout(self, library, item, parentCell):
        if isinstance(item, lshp.layoutPcell):
            pcellParamDict = self.extractPcellInstanceParameters(item)
            pcellCacheKey = (
                type(item),
                tuple((key, repr(value)) for key, value in pcellParamDict.items()),
            )
            pcellGDS = self._pcellCache.get(pcellCacheKey)
            if pcellGDS is None:
                pcellNameSuffix = "_".join(
                    f"{key}_{value}".replace(".", "p")
                    for key, value in pcellParamDict.items()
                )
                pcellName = (f"{item.libraryName}_{type(item).__name__}_"
                             f"{pcellNameSuffix}_{self._itemCounter}")
                self._itemCounter += 1
                pcellGDS = library.new_cell(pcellName)
                for shape in item.shapes:
                    self.createCells(library, shape, pcellGDS)
                self._pcellCache[pcellCacheKey] = pcellGDS

            # Use the parent coordinate of the item's local origin (0,0), not
            # just pos(). This captures the translation from pos(), rotation
            # about the transform origin, and any flip offset, keeping the GDS
            # reference in sync with Qt's scene placement.
            origin = item.mapToParent(QPointF(0, 0))
            angle_rad, x_reflection = self._gdstk_transform(
                getattr(item, 'angle', 0.0),
                getattr(item, 'flipTuple', (1, 1)),
            )
            ref = gdstk.Reference(
                pcellGDS,
                origin=(origin.x(), origin.y()),
                rotation=angle_rad,
                x_reflection=x_reflection,
            )
            parentCell.add(ref)

    @staticmethod
    def extractPcellInstanceParameters(instance: lshp.layoutPcell) -> dict:
        cls = instance.__class__
        if cls not in _pcell_param_cache:
            _pcell_param_cache[cls] = [
                param for param in inspect.signature(cls.__init__).parameters
                if param not in ("self", "snapTuple")
            ]
        # A deferred pcell's ctor-param attributes still hold defaults; read
        # the pending params dict instead.
        pending = getattr(instance, "deferredParams", None)
        if pending is not None:
            return {
                arg: pending[arg] if arg in pending else getattr(instance, arg)
                for arg in _pcell_param_cache[cls]
            }
        return {arg: getattr(instance, arg) for arg in _pcell_param_cache[cls]}

    @property
    def unit(self):
        return self._unit

    @unit.setter
    def unit(self, value: float):
        self._unit = value

    @property
    def precision(self):
        return self._precision

    @precision.setter
    def precision(self, value: float):
        self._precision = value

    @property
    def dbu(self):
        return self._dbu

    @dbu.setter
    def dbu(self, value: int):
        self._dbu = value
