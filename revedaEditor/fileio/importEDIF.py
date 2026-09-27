# SPDX-License-Identifier: MPL-2.0
#
# Copyright (c) 2024-2026 Revolution Semiconductor (Registered in the Netherlands)
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this file, You can obtain one at
# https://mozilla.org/MPL/2.0/.
#
# Add-ons and extensions developed for this software may be distributed
# under their own separate licenses.

"""EDIF 2 0 0 schematic importer.

Converts the semantic model produced by ``backend.edifBackEnd.edifC`` into
file-backed schematic and symbol JSON cellviews, following the
``importGDS`` convention of writing records directly instead of driving a
live editor.

Per imported EDIF cell a ``schematic`` view (instances, wires, sheet pins)
and a generated ``symbol`` view (interface ports, NLP parameter labels,
``paramDefs``/``pinOrder`` attributes) are written into the target library.
Instances referencing internal EDIF libraries resolve to the imported
cells; ``external`` references are resolved by cell name against the
currently loaded libraries and fall back to generated stub symbols.

EDIF placement/transform and net figure geometry are honoured when present
(coordinates are normalised onto the schematic snap grid).  When a net has
no figure, connectivity is preserved through short SET-named stub wires on
each referenced pin — the connect-by-name convention also used by the LVS
extracted-schematic generator.
"""

import itertools
import json
import math
import pathlib
import re
from collections.abc import Iterable

from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QMainWindow

import revedaEditor.backend.libBackEnd as libb
import revedaEditor.backend.libraryMethods as libm
import revedaEditor.common.params as prm
import revedaEditor.fileio.schemaValidation as sv
from revedaEditor.backend.edifBackEnd import (
    EdifCell,
    EdifInstance,
    EdifNet,
    EdifPort,
    EdifView,
    edifC,
)

# Schematic editor defaults (schematicEditor.MAJOR/SNAP_GRID_DEFAULT).
MAJOR_GRID = 20
SNAP_GRID = 10

# Generated-symbol geometry, matching createSymbols.drawBaseSymbol.
STUB_LENGTH = 60
PIN_DISTANCE = 80
PIN_STUB = 30

# Fallback instance placement when EDIF carries no transform data.
COL_SPACING = 800
ROW_SPACING = 500
ROWS_PER_COL = 8

# Target scene-unit span for normalising EDIF figure coordinates.
TARGET_SPAN = 4000

_PIN_TYPES = {"Signal", "Ground", "Power", "Clock", "Digital", "Analog"}


def _snap(value: float, grid: int = SNAP_GRID) -> int:
    return int(round(value / grid) * grid)


def _safeName(name: str, fallback: str = "unnamed") -> str:
    """Filesystem/record-safe rendering of an EDIF display name."""
    cleaned = re.sub(r"[^\w\-.<>[\]()&!%+]", "_", str(name)).strip("._")
    return cleaned or fallback


def _safeCellName(name: str) -> str:
    return _safeName(name, "cell")


def _transformedPinPoint(pinPos, loc, angle: float, flip):
    """Instance pin position in scene coordinates (adapters.py semantics).

    reveda item transforms rotate by *angle* first, then post-multiply the
    flip scale: ``loc + rot(angle)·pin·flip``.
    """
    x, y = pinPos
    if angle:
        rad = math.radians(angle)
        cosA, sinA = math.cos(rad), math.sin(rad)
        x, y = x * cosA - y * sinA, x * sinA + y * cosA
    return loc[0] + x * flip[0], loc[1] + y * flip[1]


class edifImporter:
    """Import an EDIF file as schematic+symbol cellviews into a library."""

    def __init__(
        self,
        parent: QMainWindow,
        inputFile: pathlib.Path,
        importLibItem: libb.libraryItem,
    ):
        self._parent = parent
        self.inputFile = pathlib.Path(inputFile)
        self._edif = edifC(self.inputFile)
        self._libraryModel = (
            self._parent.libraryBrowser.designView.libraryModel)
        self._libItem = importLibItem
        self._libName = importLibItem.libraryName
        libraryDict = dict(
            getattr(self._libraryModel, "libraryDict", None) or {})
        libraryDict.setdefault(self._libName, self._libItem.libraryPath)
        self._libraryDict = libraryDict
        # cellName -> {pinName: (x, y)} for generated symbol views.
        self._generatedPinMaps: dict[str, dict[str, tuple]] = {}
        # cellName -> symbol bounding rect for generated symbols.
        self._generatedRects: dict[str, list[int]] = {}
        # referenced cell name -> {propName: firstValue} across instances.
        self._cellProperties: dict[str, dict[str, str]] = {}
        # unresolved cell name -> inferred stub ports from net portRefs.
        self._stubPorts: dict[str, dict[str, EdifPort]] = {}
        # EDIF cells imported as full cellviews, keyed by target cell name.
        self._cells: dict[str, EdifCell] = {}
        # EDIF external-library cells (stub-symbol sources), same keying.
        self._externalCells: dict[str, EdifCell] = {}
        self._instanceCounters: dict[str, int] = {}
        self._stubCells: set[str] = set()
        self.messages: list[str] = []

    # ------------------------------------------------------------------
    # public entry point
    # ------------------------------------------------------------------

    def importEDIF(self):
        """Write schematic and symbol views for every imported EDIF cell."""
        self._collectCells()
        self._collectCellMetadata()
        # Symbols first: schematic pin stubs need the generated pin maps.
        for cell in self._cells.values():
            self._writeSymbolView(cell)
        for cell in self._cells.values():
            self._writeSchematicView(cell)
        self._log(
            f"Imported {self.inputFile.name}: {len(self._cells)} cells, "
            f"top cell '{self._edif.topCellName or '?'}'")
        designView = self._parent.libraryBrowser.designView
        designView.reworkDesignLibrariesView(self._libraryModel.libraryDict)

    # ------------------------------------------------------------------
    # EDIF model -> import model
    # ------------------------------------------------------------------

    def _collectCells(self):
        """Map every EDIF library cell to a unique target cell name."""
        usedNames: set[str] = set()
        for edifLib in self._edif.libraries.values():
            for cellName, cell in edifLib.cells.items():
                target = _safeCellName(cellName)
                if target.casefold() in usedNames:
                    suffix = 2
                    while f"{target}_{suffix}".casefold() in usedNames:
                        suffix += 1
                    self._log(
                        f"Cell name collision: '{cellName}' renamed "
                        f"'{target}_{suffix}'", warning=True)
                    target = f"{target}_{suffix}"
                usedNames.add(target.casefold())
                cell.name = target  # display name -> filesystem-safe name
                if edifLib.external:
                    self._externalCells[target] = cell
                else:
                    self._cells[target] = cell

    def _collectCellMetadata(self):
        """Gather per-cell instance properties and stub port names."""
        for cell in self._cells.values():
            view = cell.bestView()
            if view is None:
                continue
            for inst in view.instances:
                props = self._cellProperties.setdefault(
                    _safeCellName(inst.cellName), {})
                for key, value in inst.properties.items():
                    props.setdefault(key, value)
            for net in view.nets:
                for ref in net.refs:
                    if ref.instance is None:
                        continue
                    inst = next(
                        (i for i in view.instances
                         if i.name == ref.instance), None)
                    if inst is None:
                        continue
                    targetCell = _safeCellName(inst.cellName)
                    if targetCell in self._cells:
                        continue  # real cell: interface ports are known
                    self._stubPorts.setdefault(targetCell, {})[
                        ref.port] = EdifPort(name=ref.port)

    # ------------------------------------------------------------------
    # reference resolution
    # ------------------------------------------------------------------

    def _resolveRef(self, inst: EdifInstance) -> tuple[str, str, str]:
        """Resolve an instance ref to (libName, cellName, viewName)."""
        cellName = _safeCellName(inst.cellName)
        if cellName in self._cells:
            return self._libName, cellName, "symbol"
        # External/unknown reference: prefer a loaded library carrying a
        # symbol view for this cell name (EDIF library name first).
        for libName in self._candidateLibraries(inst.libName):
            resolved = self._resolveInLibrary(libName, cellName)
            if resolved is not None:
                return resolved
        # Unresolved: generate a stub cell in the target library.
        self._writeStubCell(cellName)
        return self._libName, cellName, "symbol"

    def _candidateLibraries(self, edifLibName: str | None) -> Iterable[str]:
        """Libraries to search for a referenced cell, EDIF lib first."""
        seen = {self._libName}
        if edifLibName and edifLibName != self._libName:
            seen.add(edifLibName)
            yield edifLibName
        for libName in self._libraryDict:
            if libName not in seen:
                seen.add(libName)
                yield libName
        # Libraries present in the browser model but not in libraryDict.
        for libName in self._modelLibNames():
            if libName not in seen:
                seen.add(libName)
                yield libName

    def _modelLibNames(self) -> Iterable[str]:
        """Library names currently shown in the library browser model."""
        if not isinstance(self._libraryModel, QStandardItemModel):
            return
        root = self._libraryModel.invisibleRootItem()
        for row in range(root.rowCount()):
            item = root.child(row)
            if getattr(item, "libraryName", None):
                yield item.libraryName

    def _libPath(self, libName: str) -> pathlib.Path | None:
        """On-disk path for a candidate library (model first, then dict)."""
        if isinstance(self._libraryModel, QStandardItemModel):
            libItem = libm.getLibItem(self._libraryModel, libName)
            if libItem is not None:
                return libItem.libraryPath
        return self._libraryDict.get(libName)

    def _resolveInLibrary(
        self, libName: str, cellName: str
    ) -> tuple[str, str, str] | None:
        """Find a symbol view for *cellName* in *libName*.

        Cell lookup is case-insensitive; the returned names are the real
        on-disk names so the emitted ``sys`` record resolves correctly.
        """
        libPath = self._libPath(libName)
        if libPath is None or not libPath.is_dir():
            return None
        cellDir = libPath.joinpath(cellName)
        if not cellDir.is_dir():
            folded = cellName.casefold()
            cellDir = next(
                (entry for entry in libPath.iterdir()
                 if entry.is_dir() and entry.name.casefold() == folded),
                None)
            if cellDir is None:
                return None
        viewJson = self._symbolViewJson(cellDir)
        if viewJson is not None:
            return libName, cellDir.name, viewJson.stem
        return None

    @staticmethod
    def _symbolViewJson(cellDir: pathlib.Path) -> pathlib.Path | None:
        """First view file in *cellDir* with 'symbol' in its stem —
        the same convention as libBackEnd.viewItem.viewType."""
        for viewJson in sorted(cellDir.glob("*.json")):
            if "symbol" in viewJson.stem:
                return viewJson
        return None

    def _writeStubCell(self, cellName: str):
        """Create a generated stub cell+symbol for an unresolved ref."""
        if cellName in self._stubCells or cellName in self._cells:
            return
        self._stubCells.add(cellName)
        edifCell = self._externalCells.get(cellName)
        view = edifCell.bestView() if edifCell is not None else None
        ports = (view.ports if view is not None and view.ports
                 else list(self._stubPorts.get(cellName, {}).values()))
        cellItem = self._cellItemFor(cellName)
        self._writeSymbolRecords(
            cellItem, cellName, ports,
            self._cellProperties.get(cellName, {}), stub=True)
        self._generatedPinMaps[cellName] = self._pinMapFromFile(
            cellItem.cellPath.joinpath("symbol.json"))
        # A bare schematic keeps the cell openable in the schematic editor.
        self._writeViewJson(
            cellItem.cellPath.joinpath("schematic.json"),
            [sv.make_view_header("schematic"),
             {"snapGrid": (MAJOR_GRID, SNAP_GRID)}])
        cellItem.refreshCellViews()
        self._log(f"Generated stub symbol for unresolved cell "
                  f"'{cellName}'", warning=True)

    # ------------------------------------------------------------------
    # library items / file output
    # ------------------------------------------------------------------

    def _cellItemFor(self, cellName: str) -> libb.cellItem:
        existing = libm.getCellItem(self._libItem, cellName)
        if existing is not None:
            return existing
        return libb.createNewCellItem(
            self._libItem, self._libItem.libraryPath.joinpath(cellName))

    @staticmethod
    def _writeViewJson(viewPath: pathlib.Path, records: list):
        """Atomically write a cellview JSON array (tmp file + replace)."""
        tmpPath = viewPath.with_suffix(".tmp")
        with tmpPath.open("w", encoding="utf-8") as file:
            json.dump(records, file, indent=4)
            file.flush()
        tmpPath.replace(viewPath)

    # ------------------------------------------------------------------
    # symbol generation
    # ------------------------------------------------------------------

    def _writeSymbolView(self, cell: EdifCell):
        view = cell.bestView()
        ports = view.ports if view is not None else []
        cellItem = self._cellItemFor(cell.name)
        self._writeSymbolRecords(
            cellItem, cell.name, ports,
            self._cellProperties.get(cell.name, {}))
        self._generatedPinMaps[cell.name] = self._pinMapFromFile(
            cellItem.cellPath.joinpath("symbol.json"))
        cellItem.refreshCellViews()

    def _writeSymbolRecords(
        self,
        cellItem: libb.cellItem,
        cellName: str,
        ports: Iterable[EdifPort],
        props: dict[str, str],
        stub: bool = False,
    ):
        """Emit a drawBaseSymbol-style box symbol for the port list."""
        ports = list(ports)
        left = sorted((p for p in ports if p.direction == "Input"),
                      key=lambda p: p.name)
        right = sorted((p for p in ports if p.direction == "Output"),
                       key=lambda p: p.name)
        top = sorted((p for p in ports
                      if p.direction not in ("Input", "Output")),
                     key=lambda p: p.name)
        rectX = (max(len(top), 1) + 1) * PIN_DISTANCE
        rectY = (max(len(left), len(right), 1) + 1) * PIN_DISTANCE

        records = [
            sv.make_view_header("symbol"),
            {"snapGrid": (MAJOR_GRID, SNAP_GRID)},
            {"type": "rect", "rect": [0, 0, rectX, rectY], "loc": [0, 0],
             "ang": 0, "fl": [1, 1]},
            self._labelRecord(
                (int(0.25 * rectX), int(0.4 * rectY)),
                "@cellName", "[@cellName]"),
            self._labelRecord(
                (rectX, int(-0.1 * rectY)), "@instName", "[@instName]"),
        ]
        pinOrder: list[str] = []
        for index, port in enumerate(left):
            y = (index + 1) * PIN_DISTANCE
            records.append(self._lineRecord((-STUB_LENGTH, y), (0, y)))
            records.append(self._pinRecord((-STUB_LENGTH, y), port))
            pinOrder.append(port.name)
        for index, port in enumerate(right):
            y = (index + 1) * PIN_DISTANCE
            records.append(
                self._lineRecord((rectX + STUB_LENGTH, y), (rectX, y)))
            records.append(
                self._pinRecord((rectX + STUB_LENGTH, y), port))
            pinOrder.append(port.name)
        for index, port in enumerate(top):
            x = (index + 1) * PIN_DISTANCE
            records.append(self._lineRecord((x, -STUB_LENGTH), (x, 0)))
            records.append(self._pinRecord((x, -STUB_LENGTH), port))
            pinOrder.append(port.name)

        # NLP parameter labels stacked along the right edge; their label
        # names (@name) carry instance values via the schematic ``ld`` map.
        props = dict(props)
        for index, (name, default) in enumerate(sorted(props.items())):
            records.append(self._labelRecord(
                (rectX, int(index * 0.2 * rectY / max(len(props), 1))),
                f"@{name}",
                f"[@{name}:{name}=%:{name}={default}]",
                value=str(default)))

        records.append({"type": "attr", "nam": "pinOrder",
                        "def": ",".join(pinOrder)})
        if stub:
            records.append({"type": "attr", "nam": "edifStub", "def": "1"})
        paramDefs = self._paramDefsAttribute(props)
        if paramDefs is not None:
            records.append(paramDefs)
        self._generatedRects[cellName] = [0, 0, rectX, rectY]
        self._writeViewJson(
            cellItem.cellPath.joinpath("symbol.json"), records)

    @staticmethod
    def _paramDefsAttribute(props: dict[str, str]) -> dict | None:
        """``paramDefs`` attr record for the union of instance properties."""
        if not props:
            return None
        defs = [prm.ParamDef(name=str(key), type=prm.inferType(str(value)),
                             default=str(value))
                for key, value in props.items()]
        return {"type": "attr", "nam": prm.PARAMDEFS_ATTR,
                "def": prm.paramDefsToJson(defs)}

    @staticmethod
    def _labelRecord(st, name, definition, value=""):
        return {
            "type": "label", "st": [int(st[0]), int(st[1])], "nam": name,
            "def": definition, "txt": definition, "val": str(value),
            "vis": True, "lt": "NLPLabel", "ht": 12, "al": "Center",
            "or": "R0", "use": "Instance", "loc": [0, 0], "fl": [1, 1],
        }

    @staticmethod
    def _pinRecord(st, port: EdifPort):
        return {
            "type": "pin", "st": [int(st[0]), int(st[1])],
            "nam": port.name,
            "pd": port.direction,
            "pt": port.pinType if port.pinType in _PIN_TYPES else "Signal",
            "loc": [0, 0], "ang": 0, "fl": [1, 1],
        }

    @staticmethod
    def _lineRecord(p1, p2):
        return {"type": "line", "st": [int(p1[0]), int(p1[1])],
                "end": [int(p2[0]), int(p2[1])], "loc": [0, 0],
                "ang": 0, "fl": [1, 1]}

    # ------------------------------------------------------------------
    # schematic generation
    # ------------------------------------------------------------------

    def _writeSchematicView(self, cell: EdifCell):
        cellItem = self._cellItemFor(cell.name)
        view = cell.bestView()
        records = [
            sv.make_view_header("schematic"),
            {"snapGrid": (MAJOR_GRID, SNAP_GRID)},
        ]
        if view is not None:
            records.extend(self._schematicRecords(view))
        self._writeViewJson(
            cellItem.cellPath.joinpath("schematic.json"), records)
        cellItem.refreshCellViews()

    def _schematicRecords(self, view: EdifView) -> list[dict]:
        """Emit sys/scn/scp/txt records for one EDIF view."""
        transform = self._viewTransform(view)
        instPositions = self._placeInstances(view, transform)

        records: list[dict] = []
        for inst in view.instances:
            libName, refCell, viewName = self._resolveRef(inst)
            counter = self._instanceCounters.get(refCell, 0) + 1
            self._instanceCounters[refCell] = counter
            records.append({
                "type": "sys", "lib": libName, "cell": refCell,
                "view": viewName, "nam": inst.name or f"I{counter}",
                "ic": counter,
                "ld": {f"@{key}": [str(value), True]
                       for key, value in inst.properties.items()},
                "loc": list(instPositions[inst.name]), "ang": inst.angle,
                "ign": 0, "br": self._symbolBBox(libName, refCell),
                "fl": list(inst.flip),
            })

        # Nets: figure segments when present, else SET-named pin stubs.
        stubNets: list[EdifNet] = []
        for net in view.nets:
            wireName = self._wireName(net)
            segments = [
                [self._scenePoint(pt, transform, net.page) for pt in seg]
                for seg in net.segments]
            emitted = [
                (p1, p2) for seg in segments for p1, p2 in itertools.pairwise(seg)
                if p1 != p2]
            if emitted:
                for p1, p2 in emitted:
                    records.append(self._netRecord(
                        p1, p2, wireName, 3 if wireName else 1))
                self._attachFigureNetPins(
                    net, emitted, view, records, instPositions)
            else:
                stubNets.append(net)

        self._emitSheetPins(view, records, transform)
        stripY = self._emitStubNets(stubNets, view, records, instPositions)

        # Unreferenced interface ports get a pin+stub so nothing floats.
        referencedPorts = {ref.port for net in view.nets for ref in net.refs
                           if ref.instance is None}
        for index, port in enumerate(view.ports):
            if port.name in referencedPorts:
                continue
            anchor = (-2 * COL_SPACING, stripY + index * PIN_DISTANCE)
            records.append(self._pinSheetRecord(anchor, port))
            records.append(self._netRecord(
                anchor, (anchor[0] + PIN_STUB, anchor[1]), "", 1))

        for index, comment in enumerate(view.comments):
            records.append({
                "type": "txt",
                "st": [0, -MAJOR_GRID * (index + 2)],
                "tc": comment, "ff": "Arial", "fs": "Regular", "th": 10,
                "ta": "Left", "to": "R0",
            })
        return records

    # ------------------------------------------------------------------
    # schematic helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _wireName(net: EdifNet) -> str:
        """SET name for the net's wire records.

        A joined interface port becomes an ``scp`` sheet pin that asserts
        its own name — the wires must carry the same name or
        ``checkRecords`` reports a net-name conflict.
        """
        for ref in net.refs:
            if ref.instance is None:
                return ref.port
        return net.name or ""

    def _viewTransform(self, view: EdifView) -> dict:
        """Uniform scale + per-page band offsets, EDIF -> scene units.

        Returns ``{"scale": s, "offset": (minX, minY), "pages": {page:
        (pageMinX, cursorX)}}`` — each EDIF page gets its own horizontal
        band so multi-page schematics merge without overlap.
        """
        points = [inst.pos for inst in view.instances if inst.pos]
        points.extend(pt for net in view.nets for seg in net.segments
                      for pt in seg)
        if not points:
            return {"scale": 1.0, "offset": (0.0, 0.0), "pages": {}}
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        span = max(max(xs) - min(xs), max(ys) - min(ys))
        scale = TARGET_SPAN / span if span > 0 else 1.0
        offset = (min(xs), min(ys))

        pageXs: dict[int, list[float]] = {}
        for inst in view.instances:
            if inst.pos is not None:
                pageXs.setdefault(inst.page, []).append(inst.pos[0])
        for net in view.nets:
            for seg in net.segments:
                for pt in seg:
                    pageXs.setdefault(net.page, []).append(pt[0])
        pages: dict[int, tuple] = {}
        cursor = 0.0
        for page in sorted(pageXs):
            pageMin = min(pageXs[page])
            pageWidth = (max(pageXs[page]) - pageMin) * scale
            pages[page] = (pageMin, cursor)
            cursor += pageWidth + 2 * COL_SPACING
        return {"scale": scale, "offset": offset, "pages": pages}

    def _scenePoint(self, point, transform, page: int):
        scale = transform["scale"]
        offset = transform["offset"]
        pageMinX, bandX = transform["pages"].get(
            page, (offset[0], 0.0))
        return (
            _snap((point[0] - pageMinX) * scale + bandX),
            _snap((point[1] - offset[1]) * scale),
        )

    def _placeInstances(self, view: EdifView, transform) -> dict[str, tuple]:
        """Scene positions keyed by instance name.

        Positioned instances keep their normalised EDIF placement; the
        rest are column-auto-placed to the right of existing content.
        """
        positions: dict[str, tuple] = {}
        maxX = 0.0
        for inst in view.instances:
            if inst.pos is not None:
                pos = self._scenePoint(inst.pos, transform, inst.page)
                positions[inst.name] = pos
                maxX = max(maxX, pos[0])
        autoIndex = 0
        for inst in view.instances:
            if inst.name in positions:
                continue
            positions[inst.name] = (
                maxX + COL_SPACING * ((autoIndex // ROWS_PER_COL) + 1),
                (autoIndex % ROWS_PER_COL) * ROW_SPACING)
            autoIndex += 1
        return positions

    def _symbolBBox(self, libName: str, cellName: str) -> list:
        if libName == self._libName and cellName in self._generatedRects:
            return list(self._generatedRects[cellName])
        pins = self._symbolPinMap(libName, cellName)
        if pins:
            xs = [p[0] for p in pins.values()]
            ys = [p[1] for p in pins.values()]
            return [min(xs) - PIN_DISTANCE, min(ys) - PIN_DISTANCE,
                    max(xs) + PIN_DISTANCE, max(ys) + PIN_DISTANCE]
        return [0, 0, 2 * PIN_DISTANCE, 2 * PIN_DISTANCE]

    def _symbolPinMap(self, libName: str,
                      cellName: str) -> dict[str, tuple]:
        """Symbol-coordinate pin positions for a cell's symbol view."""
        if libName == self._libName and cellName in self._generatedPinMaps:
            return self._generatedPinMaps[cellName]
        libPath = self._libraryDict.get(libName)
        if libPath is None:
            return {}
        return self._pinMapFromFile(
            pathlib.Path(libPath).joinpath(cellName, "symbol.json"))

    @staticmethod
    def _pinMapFromFile(viewPath: pathlib.Path) -> dict[str, tuple]:
        try:
            records = json.loads(viewPath.read_text())
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(records, list):
            return {}
        pinMap = {}
        for record in records:
            if isinstance(record, dict) and record.get("type") == "pin":
                loc = record.get("loc", (0, 0))
                st = record.get("st", (0, 0))
                pinMap[record.get("nam", "")] = (
                    loc[0] + st[0], loc[1] + st[1])
        return pinMap

    def _emitSheetPins(self, view: EdifView, records, transform):
        """scp records for interface ports joined on figure-geometry nets.

        Each referenced port pins to a point on the net's first segment
        (later ports walk along the segment so pins do not overlap).
        """
        for net in view.nets:
            if not net.segments:
                continue
            portRefs = [ref for ref in net.refs if ref.instance is None]
            if not portRefs:
                continue
            anchorPts = [pt for seg in net.segments for pt in seg]
            for index, ref in enumerate(portRefs):
                anchor = self._scenePoint(
                    anchorPts[min(index, len(anchorPts) - 1)],
                    transform, net.page)
                port = next((p for p in view.ports if p.name == ref.port),
                            EdifPort(name=ref.port))
                records.append(self._pinSheetRecord(anchor, port))

    @staticmethod
    def _pointSegDist(p, a, b) -> float:
        dx, dy = b[0] - a[0], b[1] - a[1]
        lenSq = dx * dx + dy * dy
        if lenSq < 1e-9:
            return math.hypot(p[0] - a[0], p[1] - a[1])
        t = max(0.0, min(1.0,
                         ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / lenSq))
        return math.hypot(p[0] - (a[0] + t * dx),
                          p[1] - (a[1] + t * dy))

    def _attachFigureNetPins(self, net: EdifNet, emitted, view: EdifView,
                             records, instPositions):
        """Add SET-named stubs for net refs the figure geometry misses.

        EDIF figures do not always run exactly through pin connection
        points; any joined pin left untouched by the drawn segments gets a
        named stub so connect-by-name preserves the intended net.
        """
        for ref in net.refs:
            if ref.instance is None:
                continue
            inst = next(
                (i for i in view.instances if i.name == ref.instance), None)
            if inst is None:
                self._log(
                    f"Net '{net.name}': unknown instance ref "
                    f"'{ref.instance}'", warning=True)
                continue
            libName, refCell, _viewName = self._resolveRef(inst)
            pinPos = self._symbolPinMap(libName, refCell).get(ref.port)
            loc = instPositions.get(inst.name, (0, 0))
            if pinPos is None:
                self._log(
                    f"Net '{net.name}': pin '{ref.port}' not found on "
                    f"symbol '{refCell}' (instance '{inst.name}')",
                    warning=True)
                anchor = tuple(loc)
            else:
                anchor = _transformedPinPoint(
                    pinPos, loc, inst.angle, inst.flip)
            if any(self._pointSegDist(anchor, p1, p2) <= 10
                   for p1, p2 in emitted):
                continue
            if pinPos is None:
                end = (anchor[0] + PIN_STUB, anchor[1])
            else:
                _anchor, end = self._pinStub(
                    pinPos, loc, inst.angle, inst.flip,
                    self._symbolBBox(libName, refCell))
            wireName = self._wireName(net)
            records.append(
                self._netRecord(anchor, end, wireName,
                                3 if wireName else 1))

    def _emitStubNets(self, stubNets, view: EdifView, records,
                      instPositions) -> int:
        """Emit SET-named stub wires on every pin of geometry-less nets.

        Returns the Y cursor used so unplaced interface pins continue below.
        """
        stripY = 0
        for net in stubNets:
            netName = self._wireName(net)
            strength = 3 if netName else 1
            sheetPortDone = False
            for ref in net.refs:
                if ref.instance is None:
                    if sheetPortDone:
                        continue
                    sheetPortDone = True
                    port = next(
                        (p for p in view.ports if p.name == ref.port),
                        EdifPort(name=ref.port))
                    anchor = (-2 * COL_SPACING, stripY)
                    records.append(self._pinSheetRecord(anchor, port))
                    records.append(self._netRecord(
                        anchor, (anchor[0] + PIN_STUB, anchor[1]),
                        netName, strength))
                    stripY += PIN_DISTANCE
                    continue
                inst = next(
                    (i for i in view.instances if i.name == ref.instance),
                    None)
                if inst is None:
                    self._log(
                        f"Net '{net.name}': unknown instance ref "
                        f"'{ref.instance}'", warning=True)
                    continue
                libName, refCell, _viewName = self._resolveRef(inst)
                pinPos = self._symbolPinMap(libName, refCell).get(ref.port)
                loc = instPositions.get(inst.name, (0, 0))
                if pinPos is None:
                    self._log(
                        f"Net '{net.name}': pin '{ref.port}' not found on "
                        f"symbol '{refCell}' (instance '{inst.name}')",
                        warning=True)
                    anchor = tuple(loc)
                    end = (anchor[0] + PIN_STUB, anchor[1])
                else:
                    anchor, end = self._pinStub(
                        pinPos, loc, inst.angle, inst.flip,
                        self._symbolBBox(libName, refCell))
                records.append(
                    self._netRecord(anchor, end, netName, strength))
        return stripY

    @staticmethod
    def _pinStub(pinPos, loc, angle, flip, bbox) -> tuple[tuple, tuple]:
        """(anchor, end) of a stub wire at an instance pin.

        The stub direction is chosen in *symbol* space (away from the
        symbol bbox centre), then both endpoints go through the instance
        transform so rotations/flips are honoured.
        """
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        dx = pinPos[0] - cx
        dy = pinPos[1] - cy
        if abs(dx) >= abs(dy):
            step = (-PIN_STUB, 0) if dx < 0 else (PIN_STUB, 0)
        else:
            step = (0, -PIN_STUB) if dy < 0 else (0, PIN_STUB)
        anchor = _transformedPinPoint(pinPos, loc, angle, flip)
        endSym = (pinPos[0] + step[0], pinPos[1] + step[1])
        end = _transformedPinPoint(endSym, loc, angle, flip)
        return anchor, (_snap(end[0]), _snap(end[1]))

    @staticmethod
    def _netRecord(p1, p2, name, strength=3):
        return {
            "type": "scn", "st": [int(p1[0]), int(p1[1])],
            "end": [int(p2[0]), int(p2[1])],
            "nam": name, "ns": strength,
        }

    @staticmethod
    def _pinSheetRecord(point, port: EdifPort):
        return {
            "type": "scp", "st": [int(point[0]), int(point[1])],
            "pn": port.name, "pd": port.direction,
            "pt": port.pinType if port.pinType in _PIN_TYPES else "Signal",
            "ang": 0, "fl": [1, 1],
        }

    # ------------------------------------------------------------------

    def _log(self, message: str, warning: bool = False):
        self.messages.append(message)
        logger = getattr(self._parent, "logger", None)
        if logger is None:
            return
        (logger.warning if warning else logger.info)(message)
