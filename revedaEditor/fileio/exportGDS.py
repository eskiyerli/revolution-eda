#    “Commons Clause” License Condition v1.0
#   #
#    The Software is provided to you by the Licensor under the License, as defined
#    below, subject to the following condition.
#
#    Without limiting other conditions in the License, the grant of rights under the
#    License will not include, and the License does not grant to you, the right to
#    Sell the Software.
#
#    For purposes of the foregoing, “Sell” means practicing any or all of the rights
#    granted to you under the License to provide to third parties, for a fee or other
#    consideration (including without limitation fees for hosting) a product or service whose value
#    derives, entirely or substantially, from the functionality of the Software. Any
#    license notice or attribution required by the License must also include this
#    Commons Clause License Condition notice.
#
#   Add-ons and extensions developed for this software may be distributed
#   under their own separate licenses.
#
#    Software: Revolution EDA
#    License: Mozilla Public License 2.0
#    Licensor: Revolution Semiconductor (Registered in the Netherlands)
#

import inspect
import logging
import math
from pathlib import Path
from typing import List, Any, Tuple

import gdstk

import revedaEditor.common.layoutShapes as lshp
from revedaEditor.backend.pdkLoader import importPDKModule

logger = logging.getLogger("reveda")
pcells = importPDKModule('pcells')

# Module-level cache: maps a pcell class -> list of __init__ param names to extract.
# Avoids repeated inspect.signature() calls for identical pcell types.
_pcell_param_cache: dict = {}


class gdsExporter:
    __slots__ = ('_cellname', '_items', '_outputFileObj', '_libraryName',
                 '_unit', '_precision', '_dbu', '_topCell', '_itemCounter',
                 '_cellCache', '_instanceCache')

    DEFAULT_UNIT = 1e-9
    DEFAULT_PRECISION = 1e-9
    DEFAULT_DBU = 1000

    def __init__(self, cellname: str, items: List[Any], outputFileObj: Path):
        self._unit = gdsExporter.DEFAULT_UNIT
        self._precision = gdsExporter.DEFAULT_PRECISION
        self._dbu: int = gdsExporter.DEFAULT_DBU
        self._cellname = cellname
        self._items = items
        self._outputFileObj = outputFileObj
        self._libraryName = None
        self._topCell = None
        self._itemCounter = 0
        self._cellCache = {}
        self._instanceCache: dict = {}  # (lib, cell, view) -> gdstk.Cell

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
        if item_type == lshp.layoutInstance:
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
        else:
            self._process_custom_layout(library, item, parentCell)

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

        # Qt rotation is clockwise-positive; GDS is counter-clockwise-positive.
        angle_rad = math.radians(-item.angle)
        # flipTuple = (sx, sy); x_reflection in GDS means flip around X axis (negate Y).
        x_reflection = (item.flipTuple[1] == -1)
        pos = item.pos()
        ref = gdstk.Reference(
            cellGDS,
            origin=(pos.x(), pos.y()),
            rotation=angle_rad,
            x_reflection=x_reflection,
        )
        parentCell.add(ref)

    def _processRectPin(self, item, parentCell, offset: Tuple[float, float] = (0.0, 0.0)):
        ox, oy = offset
        rect = gdstk.rectangle(
            corner1=(item.start.x() - ox, item.start.y() - oy),
            corner2=(item.end.x() - ox, item.end.y() - oy),
            layer=item.layer.gdsLayer,
            datatype=item.layer.datatype,
        )
        parentCell.add(rect)

    def processPath(self, item, parentCell, offset: Tuple[float, float] = (0.0, 0.0)):
        ox, oy = offset
        p1 = item.draftLine.p1()
        p2 = item.draftLine.p2()
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
        label = gdstk.Label(
            text=item.labelText,
            origin=(item.start.x() - ox, item.start.y() - oy),
            magnification=float(item.fontHeight * self._dbu),
            rotation=item.angle,
            layer=item.layer.gdsLayer,
            texttype=item.layer.datatype,
        )
        parentCell.add(label)

    def _processPolygon(self, item, parentCell, offset: Tuple[float, float] = (0.0, 0.0)):
        ox, oy = offset
        points = [(pt.x() - ox, pt.y() - oy) for pt in item.points]
        polygon = gdstk.Polygon(
            points=points,
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
        viaArray = gdstk.Reference(
            cell=viaCell,
            origin=(item.start.x() - ox, item.start.y() - oy),
            columns=item.xnum,
            rows=item.ynum,
            spacing=(item.xs + item.width, item.ys + item.height),
        )
        parentCell.add(viaArray)

    def _process_custom_layout(self, library, item, parentCell):
        if pcells is not None and isinstance(item, pcells.baseCell):
            pcellParamDict = self.extractPcellInstanceParameters(item)
            pcellNameSuffix = "_".join(
                f"{key}_{value}".replace(".", "p") for key, value in pcellParamDict.items()
            )
            pcellName = (f"{item.libraryName}_{type(item).__name__}_"
                         f"{pcellNameSuffix}_{self._itemCounter}")
            self._itemCounter += 1
            pcellGDS = library.new_cell(pcellName)
            # Pcell shapes store coordinates in the pcell's local coordinate system
            # (Qt child items; toSceneCoord only scales by dbu, no translation).
            # Place them in the GDS cell without any offset, then put the Reference
            # at the pcell's scene position.
            for shape in item.shapes:
                self.createCells(library, shape, pcellGDS)

            # Use pos() (local coords relative to Qt parent) not scenePos().
            # The Reference lives inside the parent GDS cell whose own Reference
            # already carries the parent's scene translation; using scenePos()
            # would double-offset.  pos() == scenePos() when the pcell is at
            # the top level, so this is correct in both cases.
            pos = item.pos()
            angle_rad = math.radians(-getattr(item, 'angle', 0.0))
            x_reflection = (getattr(item, 'flipTuple', (1, 1))[1] == -1)
            ref = gdstk.Reference(
                pcellGDS,
                origin=(pos.x(), pos.y()),
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
