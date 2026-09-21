import json
import math
import pathlib
from itertools import chain

import gdstk
from PySide6.QtCore import QLineF, QPoint
from PySide6.QtWidgets import QMainWindow

import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.backend.libBackEnd as libb
import revedaEditor.backend.libraryMethods as libm
import revedaEditor.common.layoutShapes as lshp
import revedaEditor.fileio.layoutEncoder as layenc
from revedaEditor.backend.pdkLoader import lazyPDKModule

fabproc = lazyPDKModule("process")
laylyr = lazyPDKModule("layoutLayers")


def __getattr__(name: str):
    # Deferred module-level constants: resolving the PDK process module here
    # at import time can capture a partially-initialized module during PDK
    # import cycles, so resolve on first access instead.
    if name in ("dbu", "snapGrid", "majorGrid"):
        value = float(getattr(fabproc, name))
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
        self._scale = (self._gdsLibrary.unit * float(fabproc.dbu)) / 1e-6
        self._snapGrid = round(float(fabproc.snapGrid) * float(fabproc.dbu))
        self._processedCells: set[str] = set()
        self._instanceCounters: dict[str, int] = {}
        # Merge mode: when a cell with the same name already exists in the
        # target library, append the imported shapes to its layout view
        # instead of creating a fresh cell. Instance names get re-offset so
        # merged content does not collide with existing instance names.
        self.mergeMode = False

    def _cellItemFor(self, cellName: str):
        """Reuse the existing cell item in merge mode; otherwise create one."""
        if self.mergeMode:
            existing = libm.getCellItem(self._libItem, cellName)
            if existing is not None:
                return existing
        return libb.createNewCellItem(
            self._libItem, self._libItem.libraryPath.joinpath(cellName))

    def _viewItemFor(self, cellItem):
        """Reuse the existing layout view item in merge mode.

        ``createCellviewItem`` truncates the file, so an existing layout.json
        is wrapped in a bare ``viewItem`` (no write) to preserve its records.
        """
        viewPath = cellItem.cellPath.joinpath("layout.json")
        if self.mergeMode:
            existing = libm.getViewItem(cellItem, "layout")
            if existing is not None:
                return existing
            if viewPath.exists():
                return libb.viewItem(viewPath)
        return libb.createCellviewItem("layout", viewPath)

    def importGDS(self):
        for cell in self._topCells:
            cellItem = self._cellItemFor(cell.name)
            viewItem = self._viewItemFor(cellItem)
            self._processInstance(cell, viewItem)
        self._parent.logger.info(f"Imported {self.inputFile.stem} GDS File")
        self._parent.libraryBrowser.designView.reworkDesignLibrariesView(
            self._parent.libraryBrowser.designView.libraryModel.libraryDict
        )

    def _processInstance(self, cell: gdstk.Cell, viewItem: libb.viewItem):
        mergeRecords = []
        if self.mergeMode and viewItem.viewPath.exists():
            try:
                existing = json.loads(viewItem.viewPath.read_text())
                if isinstance(existing, list):
                    mergeRecords = [
                        record for record in existing
                        if isinstance(record, dict)
                        and "viewType" not in record
                        and "snapGrid" not in record
                    ]
                    # Keep merged instance names unique: counters are keyed by
                    # the referenced cell name, so seed each one past the
                    # highest existing counter ("ic") for that cell.
                    for record in mergeRecords:
                        if record.get("type") == "Inst":
                            refCell = record.get("cell", "")
                            counter = int(record.get("ic") or 0)
                            self._instanceCounters[refCell] = max(
                                self._instanceCounters.get(refCell, 0),
                                counter,
                            )
            except (OSError, json.JSONDecodeError):
                mergeRecords = []

        # Open file in context manager and write header
        with viewItem.viewPath.open("w") as file:
            file.write("[\n")
            # Write as floats: loadDesign treats float snapGrid values as
            # layout units and ints as legacy scene-unit values.
            headerRecords = (
                {"viewType": "layout"},
                {"snapGrid": [float(fabproc.majorGrid), float(fabproc.snapGrid)]},
            )
            # Track if we need to write comma between items
            need_comma = False
            records = chain(
                headerRecords, mergeRecords, self._processShapes(cell, viewItem))
            # Process instances
            for record in records:
                if need_comma:
                    file.write(",\n")
                json.dump(record, file, cls=layenc.gdsImportEncoder, indent=4)
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
            cellItem = self._cellItemFor(ref.cell_name)

            # Import the referenced cell once; subsequent references reuse the
            # already-written layout file. This avoids repeated I/O and breaks
            # accidental self-references. In merge mode an existing cell/view is
            # reused so imported shapes append to the current content.
            if ref.cell_name not in self._processedCells:
                self._processedCells.add(ref.cell_name)
                self._processInstance(
                    ref.cell, self._viewItemFor(cellItem)
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
