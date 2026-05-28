import json
import pathlib

import gdstk
from PySide6.QtCore import (
    QPoint,
)
from PySide6.QtWidgets import (
    QMainWindow,
)
from numpy import pi

import revedaEditor.backend.data_definitions as ddef
import revedaEditor.backend.lib_back_end as libb
import revedaEditor.common.layout_shapes as lshp
import revedaEditor.fileio.layout_encoder as layenc
from revedaEditor.backend.pdk_loader import importPDKModule

fabproc = importPDKModule("process")
laylyr = importPDKModule("layout_layers")

dbu = float(fabproc.dbu)
snapGrid = float(fabproc.snapGrid)
majorGrid = float(fabproc.majorGrid)
gdsUnit = float(fabproc.gdsUnit)
gdsPrecision = float(fabproc.gdsPrecision)


class GdsImporter:
    def __init__(
            self,
            parent: QMainWindow,
            inputFile: pathlib.Path,
            importLibItem: libb.LibraryItem,
    ):
        self._parent = parent
        self.inputFile = inputFile
        self._gdsLibrary = gdstk.read_gds(str(inputFile))
        self._gdsLibrary.set_property("name", str(inputFile.stem))
        self._libraryModel = self._parent.LibraryBrowser.designView.libraryModel
        self._libItem = importLibItem

        self._topCells = self._gdsLibrary.top_level()
        self._unit = 1

    def import_gds(self):

        for cell in self._topCells:
            cellPath = self._libItem.libraryPath.joinpath(cell.name)
            CellItem = libb.createNewCellItem(self._libItem, cellPath)
            viewPath = CellItem.cellPath.joinpath("layout.json")
            ViewItem = libb.createCellviewItem("layout", viewPath)
            self._processInstance(cell, ViewItem)
        self._parent.logger.info(f"Imported {self.inputFile.stem} GDS File")
        self._parent.LibraryBrowser.designView.reworkDesignLibrariesView(
            self._parent.LibraryBrowser.designView.libraryModel.libraryDict)

    def _processInstance(self, cell: gdstk.Cell, ViewItem: libb.ViewItem):
        # Open file in context manager and write header
        with ViewItem.viewPath.open("w") as file:
            file.write("[\n")
            file.write('    {"viewType": "layout"},\n')
            gridString = f"[{fabproc.majorGrid}, {fabproc.snapGrid}]"
            snapGridLine = '    {"snapGrid": ' + gridString + '},\n'
            file.write(snapGridLine)
            # Track if we need to write comma between items
            need_comma = False

            # Process instances
            for shape in self._processShapes(cell, ViewItem):
                if need_comma:
                    file.write(",\n")
                json.dump(shape, file, cls=layenc.GdsImportEncoder, indent=4)
                need_comma = True

            # Close the JSON array
            file.write("\n]")

        return True  # Or return some status if needed

    def _processShapes(self, cell: gdstk.Cell, ViewItem: libb.ViewItem):
        """Generator that yields shapes one at a time."""
        # Process references
        for ref in cell.references:
            cellPath = self._libItem.libraryPath.joinpath(ref.cell_name)
            CellItem = libb.createNewCellItem(self._libItem, cellPath)
            viewPath = CellItem.cellPath.joinpath("layout.json")
            # Process nested instance first
            self._processInstance(ref.cell, libb.createCellviewItem("layout", viewPath))

            LayoutInstance = lshp.LayoutInstance([])
            LayoutInstance.libraryName = CellItem.parent().libraryName
            LayoutInstance.cellName = CellItem.cellName
            LayoutInstance.viewName = ViewItem.viewName
            LayoutInstance.counter = 1
            LayoutInstance.instanceName = 'I1'
            LayoutInstance.setPos(ref.origin[0] * dbu, ref.origin[1] * dbu)
            LayoutInstance.angle = ref.rotation * 180 / pi
            LayoutInstance.flipTuple = (1, 1)
            yield LayoutInstance

        # Process polygons
        for polygon in cell.polygons:
            layoutLayer = ddef.LayLayer.filterByGDSLayer(
                laylyr.pdkAllLayers, polygon.layer, polygon.datatype
            )
            if layoutLayer:
                points = [QPoint(point[0] * dbu, point[1] * dbu) for point in
                          polygon.points]
                yield lshp.LayoutPolygon(points, layoutLayer)

        # Process paths
        for path in cell.paths:
            for polygon in path.to_polygons():
                layoutLayer = ddef.LayLayer.filterByGDSLayer(
                    laylyr.pdkAllLayers, polygon.layer, polygon.datatype
                )
                if layoutLayer:
                    points = [QPoint(point[0] * dbu, point[1] * dbu) for point in
                              polygon.points]
                    yield lshp.LayoutPolygon(points, layoutLayer)
        # Process labels
        for gds_label in cell.labels:
            textLayer = ddef.LayLayer.filterByGDSLayer(
                laylyr.pdkAllLayers, gds_label.layer, 0)
            if not textLayer:
                continue
            origin = QPoint(gds_label.origin[0] * dbu, gds_label.origin[1] * dbu)
            angle = gds_label.rotation * 180 / pi
            layout_label = lshp.LayoutLabel(origin, gds_label.text, "Arial", "Regular",
                                            "10", "Center", "R0", textLayer)
            layout_label.angle = angle
            yield layout_label
