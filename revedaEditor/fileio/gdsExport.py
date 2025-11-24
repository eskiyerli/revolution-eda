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

import gdstk
import revedaEditor.common.layoutShapes as lshp
import inspect
from typing import List, Dict, Tuple, Any
from pathlib import Path
from revedaEditor.backend.pdkPaths import importPDKModule
pcells = importPDKModule('pcells')

class gdsExporter:
    __slots__ = ('_cellname', '_items', '_outputFileObj', '_libraryName',
                 '_unit', '_precision', '_topCell', '_itemCounter', '_cellCache')

    DEFAULT_UNIT = 1e-6
    DEFAULT_PRECISION = 1e-9

    def __init__(self, cellname: str, items: List[Any], outputFileObj: Path):
        self._unit = self.DEFAULT_UNIT
        self._precision = self.DEFAULT_PRECISION
        self._cellname = cellname
        self._items = items
        self._outputFileObj = outputFileObj
        self._libraryName = None
        self._topCell = None
        self._itemCounter = 0
        self._cellCache = {}
        
    def gdsExport(self):
        self._outputFileObj.parent.mkdir(parents=True, exist_ok=True)
        lib = gdstk.Library(unit=self._unit, precision=self._precision)
        self._topCell = lib.new_cell(self._cellname)  # top Cell
        for item in self._items:
            self.createCells(lib, item, self._topCell)

        lib.write_gds(self._outputFileObj)

    def createCells(self, library: gdstk.Library, item: lshp.layoutShape, parentCell: gdstk.Cell):
        item_type = type(item)
        if item_type == lshp.layoutInstance:
            self._processInstance(library, item, parentCell)
        elif item_type in (lshp.layoutRect, lshp.layoutPin):
            self._processRectPin(item, parentCell)
        elif item_type == lshp.layoutPath:
            self.processPath(item, parentCell)
        elif item_type == lshp.layoutLabel:
            self._processLabel(item, parentCell)
        elif item_type == lshp.layoutPolygon:
            self._processPolygon(item, parentCell)
        elif item_type == lshp.layoutViaArray:
            self._processViaArray(library, item, parentCell)
        else:
            self._process_custom_layout(library, item, parentCell)

    def _processInstance(self, library, item, parentCell):
        cellGDSName = f"{item.libraryName}_{item.cellName}_{item.viewName}_{self._itemCounter}"
        self._itemCounter += 1
        cellGDS = library.new_cell(cellGDSName)
        for shape in item.shapes:
            self.createCells(library, shape, cellGDS)
        ref = gdstk.Reference(
            cellGDS,
            (0,0)
        )
        parentCell.add(ref)

    def _processRectPin(self, item, parentCell):
        rect = gdstk.rectangle(
            corner1=item.mapToScene(item.start).toPoint().toTuple(),
            corner2=item.mapToScene(item.end).toPoint().toTuple(),
            layer=item.layer.gdsLayer,
            datatype=item.layer.datatype,
        )
        parentCell.add(rect)

    def processPath(self, item, parentCell):
        path = gdstk.FlexPath(
            points=[item.sceneEndPoints[0].toTuple(), item.sceneEndPoints[1].toTuple()],
            width=item.width,
            ends=(item.startExtend, item.endExtend),
            simple_path=True,
            layer=item.layer.gdsLayer,
            datatype=item.layer.datatype,
        )
        parentCell.add(path)

    def _processLabel(self, item, parentCell):
        label = gdstk.Label(
            text=item.labelText,
            origin=item.mapToScene(item.start).toPoint().toTuple(),
            magnification= float(item.fontHeight),
            rotation=item.angle,
            layer=item.layer.gdsLayer,
        )
        parentCell.add(label)

    def _processPolygon(self, item, parentCell):
        points = [item.mapToScene(point).toPoint().toTuple() for point in item.points]
        polygon = gdstk.Polygon(
            points=points,
            layer=item.layer.gdsLayer,
            datatype=item.layer.datatype,
        )
        parentCell.add(polygon)

    def _processViaArray(self, library, item, parentCell):
        via_key = (item.via.width, item.via.height, item.via.layer.name, item.via.layer.purpose)
        if via_key not in self._cellCache:
            viaName = f"via_{item.via.width}_{item.via.height}_{item.via.layer.name}_{item.via.layer.purpose}"
            viaCell = library.new_cell(viaName)
            via = gdstk.rectangle(
                item.mapToScene(item.via.rect.topLeft()).toTuple(),
                item.mapToScene(item.via.rect.bottomRight()).toTuple(),
                layer=item.via.layer.gdsLayer,
                datatype=item.via.layer.datatype,
            )
            viaCell.add(via)
            self._cellCache[via_key] = viaCell
        else:
            viaCell = self._cellCache[via_key]

        viaArray = gdstk.Reference(
            cell=viaCell,
            origin=item.start.toTuple(),
            columns=item.xnum,
            rows=item.ynum,
            spacing=(item.xs + item.width, item.ys + item.height),
        )
        parentCell.add(viaArray)

    def _process_custom_layout(self, library, item, parentCell):
        if isinstance(item, pcells.baseCell):
            pcellParamDict = self.extractPcellInstanceParameters(item)
            pcellNameSuffix = "_".join(
                f"{key}_{value}".replace(".", "p") for key, value in pcellParamDict.items()
            )
            pcellName = (f"{item.libraryName}_{type(item).__name__}_"
                         f"{pcellNameSuffix}_{self._itemCounter}")
            self._itemCounter += 1
            pcellGDS = library.new_cell(pcellName)
            for shape in item.shapes:
                self.createCells(library, shape, pcellGDS)

            ref = gdstk.Reference(
                pcellGDS,
                (0,0),
            )
            parentCell.add(ref)

    @staticmethod
    def extractPcellInstanceParameters(instance: lshp.layoutPcell) -> dict:
        initArgs = inspect.signature(instance.__class__.__init__).parameters
        argsUsed = [
            param for param in initArgs if (param != "self" and param != "snapTuple")
        ]
        argDict = {arg: getattr(instance, arg) for arg in argsUsed}
        return argDict

    @property
    def unit(self):
        return self._unit

    @unit.setter
    def unit(self, value):
        self._unit = value

    @property
    def precision(self):
        return self._precision

    @precision.setter
    def precision(self, value):
        self._precision = value