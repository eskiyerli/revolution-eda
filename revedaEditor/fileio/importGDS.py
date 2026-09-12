import json
import math
import pathlib

import gdstk
from PySide6.QtCore import QLineF, QPoint
from PySide6.QtWidgets import QMainWindow

import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.backend.libBackEnd as libb
import revedaEditor.common.layoutShapes as lshp
import revedaEditor.fileio.layoutEncoder as layenc
from revedaEditor.backend.pdkLoader import importPDKModule

fabproc = importPDKModule("process")
laylyr = importPDKModule("layoutLayers")

dbu = float(fabproc.dbu)
snapGrid = float(fabproc.snapGrid)
majorGrid = float(fabproc.majorGrid)


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

        # Scene unit: 1 / dbu layout units.  gdstk returns coordinates in the
        # GDS user unit (meters).  Scale from gdstk user units to scene units:
        #   scene = gdstk_value * unit(m) / (1e-6 / dbu)
        self._scale = (self._gdsLibrary.unit * dbu) / 1e-6
        self._snapGrid = round(snapGrid * dbu)
        self._processedCells: set[str] = set()
        self._instanceCounters: dict[str, int] = {}

    def importGDS(self):
        for cell in self._topCells:
            cellPath = self._libItem.libraryPath.joinpath(cell.name)
            cellItem = libb.createNewCellItem(self._libItem, cellPath)
            viewPath = cellItem.cellPath.joinpath("layout.json")
            viewItem = libb.createCellviewItem("layout", viewPath)
            self._processInstance(cell, viewItem)
        self._parent.logger.info(f"Imported {self.inputFile.stem} GDS File")
        self._parent.libraryBrowser.designView.reworkDesignLibrariesView(
            self._parent.libraryBrowser.designView.libraryModel.libraryDict
        )

    def _processInstance(self, cell: gdstk.Cell, viewItem: libb.viewItem):
        # Open file in context manager and write header
        with viewItem.viewPath.open("w") as file:
            file.write("[\n")
            file.write('    {"viewType": "layout"},\n')
            # Write as floats: loadDesign treats float snapGrid values as
            # layout units and ints as legacy scene-unit values.
            gridString = f"[{float(majorGrid)}, {float(snapGrid)}]"
            snapGridLine = '    {"snapGrid": ' + gridString + "},\n"
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

        return True

    def _sceneValue(self, value: float) -> int:
        """Convert a gdstk coordinate to a snapped scene integer."""
        scaled = value * self._scale
        if self._snapGrid > 0:
            scaled = round(scaled / self._snapGrid) * self._snapGrid
        return int(round(scaled))

    def _scenePoint(self, point) -> QPoint:
        """Convert a gdstk point to a snapped QPoint."""
        return QPoint(self._sceneValue(point[0]), self._sceneValue(point[1]))

    @staticmethod
    def _isConstantWidth(widths) -> bool:
        """Check whether a gdstk width array is constant along the path."""
        first = float(widths.flat[0])
        return all(abs(float(width) - first) < 1e-12 for width in widths.flat)

    def _pathExtensions(self, ends, width: float) -> tuple[int, int]:
        """Map gdstk end-cap style to reVEDA start/end extensions (scene units)."""
        if ends == "flush":
            return 0, 0
        if ends in ("extended", "extendend"):
            half = int(round(width / 2))
            return half, half
        if isinstance(ends, tuple) and len(ends) == 2:
            return int(round(float(ends[0]) * self._scale)), int(
                round(float(ends[1]) * self._scale)
            )
        raise ValueError(f"Unsupported end cap style: {ends!r}")

    def _processGdsPath(self, path: gdstk.FlexPath):
        """Yield editable layoutPath items for simple GDS paths; keep complex ones as polygons."""
        spines = path.path_spines()
        widths = path.widths()
        polygons = path.to_polygons()
        for i, spine in enumerate(spines):
            layoutLayer = ddef.layLayer.filterByGDSLayer(
                laylyr.pdkAllLayers, path.layers[i], path.datatypes[i]
            )
            if not layoutLayer:
                continue
            width = float(widths[0, i]) * self._scale
            if len(spine) == 2 and self._isConstantWidth(widths[:, i]):
                try:
                    start_extend, end_extend = self._pathExtensions(path.ends[i], width)
                except ValueError:
                    # Unsupported cap style (e.g. round): fall back to polygon.
                    yield lshp.layoutPolygon(
                        [self._scenePoint(point) for point in polygons[i].points],
                        layoutLayer,
                    )
                    continue
                p1 = self._scenePoint(spine[0])
                p2 = self._scenePoint(spine[1])
                yield lshp.layoutPath(
                    QLineF(p1, p2),
                    layoutLayer,
                    width,
                    start_extend,
                    end_extend,
                    2,  # any-angle mode preserves the imported orientation
                )
            else:
                yield lshp.layoutPolygon(
                    [self._scenePoint(point) for point in polygons[i].points],
                    layoutLayer,
                )

    def _processShapes(self, cell: gdstk.Cell, viewItem: libb.viewItem):
        """Generator that yields shapes one at a time."""
        # Process references
        for ref in cell.references:
            if ref.cell is None:
                self._parent.logger.warning(
                    f"Skipping unresolved GDS reference to '{ref.cell_name}'"
                )
                continue
            cellPath = self._libItem.libraryPath.joinpath(ref.cell_name)
            cellItem = libb.createNewCellItem(self._libItem, cellPath)
            viewPath = cellItem.cellPath.joinpath("layout.json")

            # Import the referenced cell once; subsequent references reuse the
            # already-written layout file. This avoids repeated I/O and breaks
            # accidental self-references.
            if ref.cell_name not in self._processedCells:
                self._processedCells.add(ref.cell_name)
                self._processInstance(
                    ref.cell, libb.createCellviewItem("layout", viewPath)
                )

            counter = self._instanceCounters.get(ref.cell_name, 0) + 1
            self._instanceCounters[ref.cell_name] = counter

            layoutInstance = lshp.layoutInstance([])
            layoutInstance.libraryName = cellItem.parent().libraryName
            layoutInstance.cellName = cellItem.cellName
            layoutInstance.viewName = viewItem.viewName
            layoutInstance.counter = counter
            layoutInstance.instanceName = f"I{counter}"
            origin = self._scenePoint(ref.origin)
            layoutInstance.setPos(origin)
            # gdstk rotates/flips around the reference origin, so match that
            # pivot in the editor.
            layoutInstance.setTransformOriginPoint(origin)
            layoutInstance.angle = math.degrees(ref.rotation or 0.0)
            # gdstk only exposes x_reflection; map it to a flip across Y.
            layoutInstance.flipTuple = (1, -1) if ref.x_reflection else (1, 1)
            yield layoutInstance

        # Process polygons
        for polygon in cell.polygons:
            layoutLayer = ddef.layLayer.filterByGDSLayer(
                laylyr.pdkAllLayers, polygon.layer, polygon.datatype
            )
            if layoutLayer:
                points = [self._scenePoint(point) for point in polygon.points]
                yield lshp.layoutPolygon(points, layoutLayer)

        # Process paths.  Simple two-point constant-width paths become editable
        # layoutPath items; everything else is kept as polygons.
        for path in cell.paths:
            for shape in self._processGdsPath(path):
                yield shape

        # Process labels
        for gds_label in cell.labels:
            textLayer = ddef.layLayer.filterByGDSLayer(
                laylyr.pdkAllLayers, gds_label.layer, gds_label.texttype
            )
            if not textLayer:
                continue
            origin = self._scenePoint(gds_label.origin)
            layout_label = lshp.layoutLabel(
                origin,
                gds_label.text,
                "Arial",
                "Regular",
                "10",
                "Center",
                "R0",
                textLayer,
            )
            layout_label.angle = math.degrees(gds_label.rotation or 0.0)
            layout_label.flipTuple = (1, -1) if gds_label.x_reflection else (1, 1)
            yield layout_label
