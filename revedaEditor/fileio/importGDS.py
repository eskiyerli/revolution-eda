from PySide6.QtWidgets import (
    QMainWindow,
)
from PySide6.QtCore import (
    QPoint,
)
import pathlib
import json
import revedaEditor.fileio.layoutEncoder as layenc
from numpy import pi

import gdstk
import revedaEditor.common.layoutShapes as lshp
import revedaEditor.backend.libBackEnd as libb
import revedaEditor.backend.dataDefinitions as ddef
from revedaEditor.backend.pdkPaths import importPDKModule

fabproc = importPDKModule("process")
laylyr = importPDKModule("layoutLayers")


class gdsImporter:
    def __init__(
        self,
        parent: QMainWindow,
        inputFile: pathlib.Path,
        importLibItem: libb.libraryItem,
    ):
        self._parent = parent
        self.inputFile = inputFile
        self._gdsLibrary = gdstk.read_gds(str(inputFile))
        self._gdsLibrary.set_property("name", str(inputFile.stem))
        self._libraryModel = self._parent.libraryBrowser.designView.libraryModel
        self._libItem = importLibItem

        self._topCells = self._gdsLibrary.top_level()
        self._unit = 1

    def importGDS(self):

        for cell in self._topCells:
            cellPath = self._libItem.libraryPath.joinpath(cell.name)
            cellItem = libb.createNewCellItem(self._libItem, cellPath)
            viewPath = cellItem.cellPath.joinpath("layout.json")
            viewItem = libb.createCellviewItem("layout", viewPath)
            self._processInstance(cell, viewItem)
        self._parent.logger.info(f"Imported {self.inputFile.stem} GDS File")
        self._parent.libraryBrowser.designView.reworkDesignLibrariesView(self._parent.libraryBrowser.designView.libraryModel.libraryDict)

    def _processInstance(self, cell: gdstk.Cell, viewItem: libb.viewItem):
        # Open file in context manager and write header
        with viewItem.viewPath.open("w") as file:
            file.write("[\n")
            file.write('    {"viewType": "layout"},\n')
            gridString = f"[{fabproc.majorGrid}, {fabproc.snapGrid}]"
            snapGridLine = '    {"snapGrid": ' + gridString + '},\n'
            file.write(snapGridLine)
            # Track if we need to write comma between items
            need_comma = False
            
            # Process instances
            for shape in self._processShapes(cell, viewItem):
                if need_comma:
                    file.write(",\n")
                json.dump(shape, file, cls=layenc.gdsImportEncoder, indent=4)
                need_comma = True
            
            # Close the JSON array
            file.write("\n]")
        
        return True  # Or return some status if needed

    def _processShapes(self, cell: gdstk.Cell, viewItem: libb.viewItem):
        """Generator that yields shapes one at a time."""
        # Process references
        for ref in cell.references:
            cellPath = self._libItem.libraryPath.joinpath(ref.cell_name)
            cellItem = libb.createNewCellItem(self._libItem, cellPath)
            viewPath = cellItem.cellPath.joinpath("layout.json")
            # Process nested instance first
            self._processInstance(ref.cell, libb.createCellviewItem("layout", viewPath))
            
            layoutInstance = lshp.layoutInstance([])
            layoutInstance.libraryName = cellItem.parent().libraryName
            layoutInstance.cellName = cellItem.cellName
            layoutInstance.viewName = viewItem.viewName
            layoutInstance.counter = 1
            layoutInstance.instanceName = 'I1'
            layoutInstance.setPos(ref.origin[0]*fabproc.dbu, ref.origin[1]*fabproc.dbu)
            layoutInstance.angle = ref.rotation * 180 / pi
            layoutInstance.flipTuple = (1,1)
            yield layoutInstance

        # Process polygons
        for polygon in cell.polygons:
            layoutLayer = ddef.layLayer.filterByGDSLayer(
                laylyr.pdkAllLayers, polygon.layer, polygon.datatype
            )
            if layoutLayer:
                points = [QPoint(point[0]*fabproc.dbu, point[1]*fabproc.dbu) for point in polygon.points]
                yield lshp.layoutPolygon(points, layoutLayer)

        # Process paths
        for path in cell.paths:
            for polygon in path.to_polygons():
                layoutLayer = ddef.layLayer.filterByGDSLayer(
                    laylyr.pdkAllLayers, polygon.layer, polygon.datatype
                )
                if layoutLayer:
                    points = [QPoint(point[0]*fabproc.dbu, point[1]*fabproc.dbu) for point in polygon.points]
                    yield lshp.layoutPolygon(points, layoutLayer)
        # Process labels
        for gds_label in cell.labels:
            textLayer = ddef.layLayer.filterByGDSLayer(
                laylyr.pdkAllLayers, gds_label.layer, 0)
            if not textLayer:
                continue
            origin = QPoint(gds_label.origin[0]*fabproc.dbu, gds_label.origin[1]*fabproc.dbu)
            angle = gds_label.rotation * 180 / pi
            layout_label = lshp.layoutLabel(origin, gds_label.text, "Arial", "Regular", "10", "Center", "R0", textLayer)
            layout_label.angle = angle
            yield layout_label

