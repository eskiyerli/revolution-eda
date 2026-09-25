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

# Load symbol and maybe later schematic from json file.

import functools
import itertools
import pathlib
from typing import Any, Optional

import orjson
from PySide6.QtCore import QPoint, QPointF, QLineF, QRect, QRectF
from PySide6.QtGui import QTransform
from PySide6.QtWidgets import (
    QGraphicsScene,
    QGraphicsRectItem,
    QGraphicsSimpleTextItem,
)

import revedaEditor.common.labels as lbl
import revedaEditor.common.layoutShapes as lshp
import revedaEditor.common.net as net
import revedaEditor.common.params as prm
import revedaEditor.common.shapes as shp
import revedaEditor.fileio.symbolEncoder as se
import revedaEditor.fileio.schemaValidation as sv
from revedaEditor.backend.pdkLoader import lazyPDKModule

laylyr = lazyPDKModule('layoutLayers')
pcells = lazyPDKModule('pcells')
fabproc = lazyPDKModule('process')

def clear_symbol_cache():
    """Clear the symbol JSON loading cache."""
    schematicItems._load_sym_json.cache_clear()


def makeSymbolPinLocator(libraryDict):
    """Return a pinLocator for ``connectivity.checkRecords``.

    The callable maps (libName, cellName, viewName) to
    ``{pinName: (x, y), "directions": {pinName: dir}}`` with pin positions
    in symbol coordinates (``loc`` + ``st`` of the pin record), or None when
    the symbol file cannot be resolved.
    """
    def locator(libName: str, cellName: str, viewName: str):
        libraryPath = libraryDict.get(libName)
        if libraryPath is None:
            return None
        file = libraryPath.joinpath(cellName, f"{viewName}.json")
        if not file.exists():
            return None
        jsonItems = schematicItems._load_sym_json(str(file))
        if jsonItems is None:
            return None
        pinMap = {}
        directions = {}
        pinExprs = {}
        attrs = {}
        for jsonItem in itertools.islice(jsonItems, 2, None):
            if not isinstance(jsonItem, dict):
                continue
            if jsonItem.get("type") == "pin":
                pinName = jsonItem.get("nam", "")
                loc = jsonItem.get("loc", (0, 0))
                st = jsonItem.get("st", (0, 0))
                pinMap[pinName] = (loc[0] + st[0], loc[1] + st[1])
                directions[pinName] = jsonItem.get("pd", "")
                if jsonItem.get("nx"):
                    pinExprs[pinName] = jsonItem["nx"]
            elif jsonItem.get("type") == "attr":
                attrs[jsonItem.get("nam", "")] = jsonItem.get("def", "")
        pinMap["directions"] = directions
        # Typed parameter definitions (CDF-lite); empty list when the
        # symbol declares none. Diagnostics use it to validate ld values.
        pinMap["paramDefs"] = prm.paramDefsFromSymattrs(attrs)
        # Per-pin net expressions (inherited connections); empty when the
        # symbol declares none.
        pinMap["pinExprs"] = pinExprs
        return pinMap

    return locator


class symbolItems:
    def __init__(self, scene: QGraphicsScene):
        """
        Initializes the class instance.

        Args:
            scene (QGraphicsScene): The QGraphicsScene object.

        """
        self.scene = scene
        self.snapTuple = scene.snapTuple
        # Pre-create method mapping for faster dispatch
        self._creators = {
            "rect": self.createRectItem,
            "circle": self.createCircleItem,
            "arc": self.createArcItem,
            "line": self.createLineItem,
            "pin": self.createPinItem,
            "label": self.createLabelItem,
            "text": self.createTextItem,
            "polygon": self.createPolygonItem,
        }

    def create(self, item: dict) -> Optional[shp.symbolShape]:
        """
        Create symbol items from json file.
        """
        if not isinstance(item, dict):
            return None
        creator = self._creators.get(item.get("type"))
        if creator is not None:
            return creator(item)
        return None

    @staticmethod
    def createRectItem(item: dict) -> shp.symbolRectangle:
        """
        Create symbol items from json file.
        """
        start = QPoint(item["rect"][0], item["rect"][1])
        end = QPoint(item["rect"][2], item["rect"][3])
        rect = shp.symbolRectangle(start, end)
        rect.setPos(
            QPoint(item["loc"][0], item["loc"][1]),
        )
        rect.angle = item.get("ang", 0)
        rect.flipTuple = item.get('fl', (1, 1))
        return rect

    @staticmethod
    def createCircleItem(item: dict) -> shp.symbolCircle:
        centre = QPoint(item["cen"][0], item["cen"][1])
        end = QPoint(item["end"][0], item["end"][1])
        circle = shp.symbolCircle(centre, end)  # note that we are using grid
        # values for
        # scene
        circle.setPos(
            QPoint(item["loc"][0], item["loc"][1]),
        )
        circle.angle = item.get("ang", 0)
        circle.flipTuple = item.get('fl', (1, 1))
        return circle

    @staticmethod
    def createArcItem(item: dict) -> shp.symbolArc:
        start = QPoint(item["st"][0], item["st"][1])
        end = QPoint(item["end"][0], item["end"][1])

        arc = shp.symbolArc(start, end)  # note that we are using grid values
        # for scene
        arc.setPos(QPoint(item["loc"][0], item["loc"][1]))
        arc.angle = item.get("ang", 0)
        arc.flipTuple = item.get('fl', (1, 1))
        arc.arcType = shp.symbolArc.arcTypes[item["at"]]
        return arc

    @staticmethod
    def createLineItem(item: dict) -> shp.symbolLine:
        start = QPoint(item["st"][0], item["st"][1])
        end = QPoint(item["end"][0], item["end"][1])

        line = shp.symbolLine(start, end)
        line.setPos(QPoint(item["loc"][0], item["loc"][1]))
        line.angle = item.get("ang", 0)
        line.flipTuple = item.get('fl', (1, 1))
        return line

    @staticmethod
    def createPinItem(item: dict) -> shp.symbolPin:
        start = QPoint(item["st"][0], item["st"][1])
        pin = shp.symbolPin(start, item["nam"], item["pd"], item["pt"])
        pin.setPos(QPoint(item["loc"][0], item["loc"][1]))
        pin.angle = item["ang"]
        pin.flipTuple = item.get('fl', (1, 1))
        pin.netExpr = item.get("nx", "") or ""
        return pin

    @staticmethod
    def createLabelItem(item: dict) -> lbl.symbolLabel:
        start = QPoint(item["st"][0], item["st"][1])
        label = lbl.symbolLabel(
            start,
            item["def"],
            item["lt"],
            item["ht"],
            item["al"],
            item["or"],
            item["use"],
        )
        label.setPos(QPoint(item["loc"][0], item["loc"][1]))
        label.labelName = item["nam"]
        label.labelText = item["txt"]
        label.labelVisible = item["vis"]
        label.labelValue = item["val"]
        label._updateVisibility()  # Ensure visibility is set after all properties are loaded
        return label

    @staticmethod
    def createTextItem(item: dict) -> shp.text:
        start = QPoint(item["st"][0], item["st"][1])
        text = shp.text(
            start,
            item["tc"],
            item["ff"],
            item["fs"],
            item["th"],
            item["ta"],
            item["to"],
        )
        text.setPos(QPoint(item["loc"][0], item["loc"][1]))
        return text

    @staticmethod
    def createPolygonItem(item: dict) -> shp.symbolPolygon:
        pointsList = [QPoint(point[0], point[1]) for point in item["ps"]]
        polygon = shp.symbolPolygon(pointsList)
        polygon.flipTuple = item.get('fl', (1, 1))
        return polygon

    @staticmethod
    def createSymbolAttribute(item: dict):
        return se.symbolAttribute(item["nam"], item["def"])

    def createSimpleTextItem(self, item: dict):
        text = QGraphicsSimpleTextItem(item["text"])
        text.setPos(QPoint(item["pos"][0], item["pos"][1]))
        return text

    def createQRectItem(self, item: dict):
        rect = QGraphicsRectItem(QRect(*item["rect"]))
        rect.setPos(QPoint(item["pos"][0], item["pos"][1]))
        return rect

    def unknownItem(self) -> QGraphicsRectItem:
        rectItem = QGraphicsRectItem(QRect(0, 0, *self.snapTuple))
        rectItem.setVisible(False)
        return rectItem


class schematicItems:
    def __init__(self, scene: QGraphicsScene):
        self.scene = scene
        self.libraryDict = scene.libraryDict
        self.snapTuple = scene.snapTuple
        self._snapToGrid = scene.snapToGrid
        self._symbolItems = symbolItems(scene)
        # Pre-create method mapping for faster dispatch
        self._creators = {
            "sys": self._createSymbolShape,
            "scn": self._createNet,
            "scp": self._createPin,
            "txt": self._createText,
            "Group": self._createGroup,
        }

    @staticmethod
    @functools.lru_cache(maxsize=256)
    def _load_sym_json(file_path_str: str):
        """Cache symbol file contents keyed by path to avoid repeated I/O for repeated cells."""
        try:
            with open(file_path_str, "rb") as f:
                return orjson.loads(f.read())
        except (orjson.JSONDecodeError, FileNotFoundError, OSError):
            return None

    def create(self, item: dict):
        if isinstance(item, dict):
            creator = self._creators.get(item.get("type"))
            if creator is not None:
                return creator(item)
        return None

    def _createGroup(self, item):
        """Rebuild a persisted symbols-only schematic mosaic."""
        members = []
        for record in item.get("items", []):
            if not isinstance(record, dict) or record.get("type") != "sys":
                continue
            symbol = self._createSymbolShape(record)
            if symbol is not None:
                members.append(symbol)
        group = shp.schematicGroup(members)
        group.setPos(QPoint(*item.get("loc", (0, 0))))
        return group

    def _createText(self, item):
        start = QPoint(0, 0)
        text = shp.text(
            start,
            item["tc"],
            item["ff"],
            item["fs"],
            item["th"],
            item["ta"],
            item["to"],
        )
        text.setPos(QPoint(item["st"][0], item["st"][1]))
        text.flipTuple = item.get('fl', (1, 1))
        text.angle = item.get('ang', 0)

        return text

    def _createPin(self, item):
        start = QPoint(0, 0)
        pinName = item["pn"]
        pinDir = item["pd"]
        pinType = item["pt"]
        pinItem = shp.schematicPin(
            start,
            pinName,
            pinDir,
            pinType,
        )
        pinItem.setPos(QPoint(item["st"][0], item["st"][1]))
        pinItem.angle = item.get('ang', 0)
        pinItem.flipTuple = item.get('fl', (1, 1))
        pinItem.netExpr = item.get("nx", "") or ""
        return pinItem

    def _createNet(self, item):
        start = QPoint(item["st"][0], item["st"][1])
        end = QPoint(item["end"][0], item["end"][1])
        width = item.get('w', 0)
        # Snap coordinates to grid to ensure nets are properly aligned
        start = self._snapToGrid(start)
        end = self._snapToGrid(end)
        netItem = net.schematicNet(start, end, width)
        netItem.name = item["nam"]
        netItem.netExpr = item.get("nx", "") or ""
        match item["ns"]:
            case 3:

                netItem.nameStrength = net.netNameStrengthEnum.SET
            case 2:

                netItem.nameStrength = net.netNameStrengthEnum.INHERIT
            case 1:

                netItem.nameStrength = net.netNameStrengthEnum.WEAK
            case _:
                netItem.nameStrength = net.netNameStrengthEnum.NONAME

        return netItem

    def _createSymbolShape(self, item):
        itemShapes = list()
        symbolAttributes = dict()
        symbolInstance = shp.schematicSymbol(itemShapes, symbolAttributes)
        symbolInstance.libraryName = item["lib"]
        symbolInstance.cellName = item["cell"]
        symbolInstance.viewName = item["view"]
        symbolInstance.counter = item["ic"]
        symbolInstance.instanceName = item["nam"]
        symbolInstance.netlistIgnore = bool(item.get("ign", 0))
        # Inherited-connection overrides (netSet): {exprName: localNet}.
        symbolInstance.netSet = item.get("nst", {})
        labelDict = item["ld"]
        symbolInstance.setPos(*item["loc"])
        for labelItem in symbolInstance.labels.values():
            labelItem.labelDefs()
        libraryPath = self.libraryDict.get(item["lib"])
        if libraryPath is None:
            self.createDraftSymbol(item, symbolInstance)
            self.scene.logger.warning(f"{item['lib']} cannot be found.")
            return symbolInstance
        else:
            # find the symbol file
            file = libraryPath.joinpath(
                item["cell"], f'{item["view"]}.json'
            )
            if not file.exists():
                self.createDraftSymbol(item, symbolInstance)
                self.scene.logger.warning(f"{item['lib']} cannot be found.")
                return symbolInstance
            else:
                # load json file and create shapes
                file_path_str = str(file)
                jsonItems = self._load_sym_json(file_path_str)
                if jsonItems is None:
                    self.scene.logger.error("Error: Invalid or missing Symbol file")
                    return None
                try:
                    jsonItems, compatibility = sv.prepare_design_data(
                        jsonItems, "symbol", file_path_str)
                except sv.DesignFileValidationError as error:
                    self.scene.logger.error(
                        f"Invalid symbol file {file_path_str}: "
                        f"{'; '.join(error.errors or [str(error)])}")
                    return None
                if compatibility.migrated:
                    self.scene.logger.info(
                        f"Migrated symbol schema "
                        f"{compatibility.sourceVersion} to "
                        f"{compatibility.targetVersion}: {file_path_str}")
                try:
                    symbolShape = self._symbolItems
                    for jsonItem in itertools.islice(jsonItems, 2, None):
                        if jsonItem["type"] == "attr":
                            symbolAttributes[jsonItem["nam"]] = (
                                jsonItem["def"]
                            )
                        else:
                            itemShapes.append(
                                symbolShape.create(jsonItem)
                            )
                    symbolInstance.shapes = itemShapes
                    for labelItem in symbolInstance.labels.values():
                        entry = labelDict.get(labelItem.labelName)
                        if entry is not None:
                            labelItem.labelValue = entry[0]
                            # Only override visibility if it's explicitly in the schematic's label dict
                            if len(entry) > 1:
                                labelItem.labelVisible = entry[1]
                    symbolInstance.symattrs = symbolAttributes
                    for labelItem in symbolInstance.labels.values():
                        labelItem.labelDefs()
                    # Validate persisted label values against the symbol's
                    # typed parameter definitions (CDF-lite); invalid values
                    # are kept but reported. Malformed paramDefs JSON on the
                    # symbol itself is reported too.
                    _defs, defErrs = prm.paramDefsFromJson(
                        symbolAttributes.get(prm.PARAMDEFS_ATTR, ""))
                    for paramErr in (*defErrs,
                                     *prm.validateInstanceValues(
                                         symbolInstance.paramDefs,
                                         labelDict,
                                         owner=symbolInstance.instanceName)):
                        self.scene.logger.warning(paramErr)
                    symbolInstance.angle = item.get("ang", 0)
                    symbolInstance.flipTuple = item.get('fl', (1, 1))
                    return symbolInstance
                except Exception as e:
                    self.scene.logger.error(
                        f"Error creating symbol instance: {e}"
                    )
                    return None

    def createDraftSymbol(self, item: dict, symbolInstance: shp.schematicSymbol):
        rectItem = shp.symbolRectangle(
            QPoint(item["br"][0], item["br"][1]), QPoint(item["br"][2], item["br"][3])
        )
        fixedFont = self.scene.fixedFont
        textItem = shp.text(
            rectItem.start,
            f'{item["lib"]}/{item["cell"]}/{item["view"]}',
            fixedFont.family(),
            fixedFont.styleName(),
            fixedFont.pointSize(),
            shp.text.textAlignments[0],
            shp.text.textOrients[0],
        )
        symbolInstance.shapes = [rectItem, textItem]
        symbolInstance.draft = True

    def unknownItem(self):
        rectItem = QGraphicsRectItem(QRect(0, 0, *self.snapTuple))
        rectItem.setVisible(False)
        return rectItem


class PCellCache:
    @classmethod
    @functools.lru_cache(maxsize=100)
    def getPCellDef(cls, file_path: str) -> dict:
        try:
            with open(file_path, "rb") as temp:
                return orjson.loads(temp.read())
        except (orjson.JSONDecodeError, FileNotFoundError, OSError):
            return {}

    @classmethod
    @functools.lru_cache(maxsize=100)
    def getPCellClass(cls, pcell_class_name: str) -> Any:
        return pcells.pcells.get(pcell_class_name)

    @classmethod
    def clear_caches(cls):
        cls.getPCellDef.cache_clear()
        cls.getPCellClass.cache_clear()


class layoutItems:
    def __init__(self, scene):
        self.scene = scene
        self.libraryDict = scene.libraryDict
        self.rulerFont = scene.rulerFont
        self.snapTuple = scene.snapTuple
        self.rulerWidth = scene.rulerWidth
        self._library_paths = {}
        self._active_layout_paths = set()
        for name, path in self.libraryDict.items():
            if path:
                library_path = pathlib.Path(path)
                if library_path.exists():
                    self._library_paths[name] = library_path
        self._pdkLayers = laylyr.pdkAllLayers

        # Pre-create method mapping for faster dispatch
        self._creators = {
            "Inst": self.createLayoutInstance,
            "Pcell": self.createPcellInstance,
            "Rect": self.createRectShape,
            "Path": self.createPathShape,
            "Label": self.createLabelShape,
            "Pin": self.createPinShape,
            "Polygon": self.createPolygonShape,
            "Via": self.createViaArrayShape,
            "Ruler": self.createRulerShape,
            "Multipart": self.createMultipartShape,
            "Group": self.createGroupShape,
        }

    def create(self, item):
        if not isinstance(item, dict):
            return self.unknownItem()
        return self._creators.get(item.get("type"), self.unknownItem)(item)

    def _get_library_path(self, lib_name):
        return self._library_paths.get(lib_name)

    @staticmethod
    @functools.lru_cache(maxsize=128)
    def _load_json_file(file_path_str):
        try:
            with open(file_path_str, "rb") as file:
                return orjson.loads(file.read())
        except (orjson.JSONDecodeError, FileNotFoundError, OSError):
            return None

    def _restoreSdlSource(self, obj, item):
        """Restore only canonical persisted SDL correspondence metadata."""
        if "sdl" not in item:
            return
        if sv.is_canonical_sdl_source(item["sdl"]):
            obj._sdlSource = item["sdl"]
        else:
            self.scene.logger.warning(
                "Ignoring noncanonical sdl metadata on layout instance")

    @staticmethod
    def _set_common_attrs(obj, item):
        # flipTuple replaces the item's custom transform. Set it before the
        # rotation property so a saved combined transform is restored intact.
        obj.flipTuple = tuple(item.get("fl", (1, 1)))
        ang = item.get("ang", 0)
        # Avoid the geometry-change/rotation overhead for the common case where
        # there is no saved rotation; the default _angle is already 0.
        if ang != 0:
            obj.angle = ang
        # Path and ruler angle setters reset their pivot to the first endpoint.
        # Restore the saved local pivot last so all shape types retain the
        # original rotation center.
        if "top" in item:
            obj.setTransformOriginPoint(QPointF(*item["top"]))

    # fl (flip) is bounds-invariant: it mirrors the item about its own
    # bounding-rect center, so it never changes the rect. Only ang (rotation
    # about top) and translation move bounds.
    _UNBOUNDABLE = object()
    _RULER_BOUNDS_MARGIN = 200.0
    _boundsCacheSize = 256
    _localBoundsCache = {}

    @classmethod
    def clear_caches(cls):
        """Clear file and derived-bounds caches after a layout changes."""
        cls._load_json_file.cache_clear()
        cls._localBoundsCache.clear()

    def _localBoundsCacheKey(self, filePathKey):
        """Stable local-bounds cache key, including nested-library context."""
        libraryContext = tuple(sorted(
            (name, str(path)) for name, path in self._library_paths.items()
        ))
        return filePathKey, libraryContext

    def _cachedLocalBounds(self, filePathKey, fileContents):
        """Cached local bounds for a referenced layout cellview.

        Bounds are derived in the cell's own coordinates, before an instance
        record applies its translation or transform.  Returning a copy keeps
        callers free to transform the result without mutating the cache.
        """
        cacheKey = self._localBoundsCacheKey(filePathKey)
        if cacheKey not in self._localBoundsCache:
            try:
                bounds = self._dictsBounds(fileContents[2:], {filePathKey})
            except (KeyError, IndexError, TypeError, ValueError):
                bounds = None
            if len(self._localBoundsCache) >= self._boundsCacheSize:
                self._localBoundsCache.pop(next(iter(self._localBoundsCache)))
            self._localBoundsCache[cacheKey] = (
                QRectF(bounds) if bounds is not None else None
            )
        bounds = self._localBoundsCache[cacheKey]
        return QRectF(bounds) if bounds is not None else None

    def _dictsBounds(self, records, activePaths):
        """Union of a cell's record bounds from the raw dicts, without
        constructing any QGraphicsItems. Returns None when a record cannot be
        bounded cheaply, signalling the caller to load eagerly."""
        bounds = None
        for rec in records:
            r = self._recordBounds(rec, activePaths)
            if r is self._UNBOUNDABLE:
                return None
            if r is None:
                continue
            bounds = r if bounds is None else bounds.united(r)
        # Each child's boundingRect carries its own margin; inflate so the
        # stored bounds never underestimate the realised childrenBoundingRect.
        if bounds is None:
            return QRectF()
        return bounds.adjusted(-2, -2, 2, 2)

    @staticmethod
    def _applyRecordTransform(bounds, rec, translate=None):
        """Apply a record's ang rotation (about its saved ``top`` pivot) and an
        optional extra translation to ``bounds``."""
        ang = rec.get("ang", 0)
        if not ang and translate is None:
            return bounds
        transform = QTransform()
        if translate is not None:
            transform.translate(translate[0], translate[1])
        if ang:
            top = rec.get("top", (0, 0))
            transform.translate(top[0], top[1])
            transform.rotate(ang)
            transform.translate(-top[0], -top[1])
        return transform.mapRect(bounds)

    def _recordBounds(self, rec, activePaths):
        """Bounds of one record in parent (cell-local) coordinates.

        Returns a QRectF, None to skip the record, or _UNBOUNDABLE when the
        record cannot be bounded without building its item."""
        if not isinstance(rec, dict):
            return None
        rtype = rec.get("type")
        if rtype in ("Rect", "Pin"):
            bounds = QRectF(
                QPointF(*rec["tl"]), QPointF(*rec["br"])
            ).normalized()
            return self._applyRecordTransform(bounds, rec)
        if rtype in ("Path", "Ruler"):
            bounds = QRectF(
                QPointF(*rec["dfl1"]), QPointF(*rec["dfl2"])
            ).normalized()
            if rtype == "Path":
                margin = rec.get("w", 0) / 2 + max(
                    rec.get("se", 0), rec.get("ee", 0)
                )
            else:
                # Ruler ticks/labels render screen-space; a fixed scene
                # margin covers them at typical zoom levels.
                margin = self._RULER_BOUNDS_MARGIN
            return self._applyRecordTransform(
                bounds.adjusted(-margin, -margin, margin, margin), rec
            )
        if rtype == "Polygon":
            bounds = None
            for x, y in rec["ps"]:
                point = QRectF(x, y, 0, 0)
                bounds = point if bounds is None else bounds.united(point)
            if bounds is None:
                return None
            return self._applyRecordTransform(bounds, rec)
        if rtype == "Via":
            viaInfo = rec["via"]
            # ``st`` anchors the first cut; xs/ys are *gaps* between cuts,
            # so the array spans (n-1)*(gap+cut)+cut in the local frame
            # before ang is applied.
            cutW = viaInfo.get("w", 0)
            cutH = viaInfo.get("h", 0)
            margin = (
                    max(cutW, cutH)
                    + max(viaInfo.get("be") or 0, viaInfo.get("te") or 0)
                    + 2
            )
            start = rec["st"]
            span = QRectF(
                QPointF(0, 0),
                QPointF((rec["xn"] - 1) * (rec["xs"] + cutW) + cutW,
                        (rec["yn"] - 1) * (rec["ys"] + cutH) + cutH),
            ).normalized()
            bounds = self._applyRecordTransform(
                span.adjusted(-margin, -margin, margin, margin),
                rec,
                translate=start,
            )
            return bounds
        if rtype == "Label":
            return self._labelDictBounds(rec)
        if rtype == "Inst":
            libraryPath = self._get_library_path(rec.get("lib", ""))
            if not libraryPath:
                return None
            filePath = (
                    libraryPath / rec["cell"] / f"{rec['view']}.json"
            )
            filePathKey = str(filePath)
            if filePathKey in activePaths:
                # Recursive reference: the item loader skips these too.
                return None
            childContents = self._load_json_file(filePathKey)
            if not childContents:
                return None
            bbox = rec.get("bbox")
            if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
                bounds = QRectF(*bbox)
            else:
                bounds = self._dictsBounds(
                    childContents[2:], activePaths | {filePathKey}
                )
            if bounds is None:
                return self._UNBOUNDABLE
            return self._applyRecordTransform(bounds, rec, translate=rec["loc"])
        if rtype == "Pcell":
            bbox = rec.get("bbox")
            if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
                return self._applyRecordTransform(
                    QRectF(*bbox), rec, translate=rec["loc"]
                )
            return self._UNBOUNDABLE
        if rtype == "Group":
            bounds = None
            for child in rec.get("items", []):
                r = self._recordBounds(child, activePaths)
                if r is self._UNBOUNDABLE:
                    return self._UNBOUNDABLE
                if r is None:
                    continue
                bounds = r if bounds is None else bounds.united(r)
            if bounds is None:
                return None
            return self._applyRecordTransform(
                bounds.adjusted(-2, -2, 2, 2), rec, translate=rec.get("loc")
            )
        # Unknown or unboundable record type: force eager loading.
        return self._UNBOUNDABLE

    @staticmethod
    def _labelDictBounds(rec):
        """Label bounds from font metrics, honouring labelOrient rotation."""
        fontMetrics = lshp.layoutLabel._fontEntry(rec["ff"], rec["fs"], rec["fh"])[1]
        textBounds = fontMetrics.boundingRect(rec["lt"])
        orients = lshp.layoutLabel.LABEL_ORIENTS
        try:
            orientIndex = orients.index(rec["lo"])
        except ValueError:
            orientIndex = 0
        # labelOrient angles with flips collapsed out (flips are
        # bounds-invariant). MY90 has no setOrient case, so it stays at 0.
        orientAngles = (0, 90, 180, 270, 0, 90, 90, 0)
        start = rec["st"]
        totalAngle = orientAngles[orientIndex] + rec.get("ang", 0)
        bounds = QRectF(
            start[0], start[1], textBounds.width(), textBounds.height()
        )
        if totalAngle:
            transform = QTransform()
            transform.translate(start[0], start[1])
            transform.rotate(totalAngle)
            transform.translate(-start[0], -start[1])
            bounds = transform.mapRect(bounds)
        return bounds.adjusted(-8, -8, 8, 8)

    def createPcellInstance(self, item):
        library_path = self._get_library_path(item["lib"])
        if not library_path:
            return None

        file_path = library_path / item["cell"] / f"{item['view']}.json"
        pcell_def = PCellCache.getPCellDef(str(file_path))
        try:
            pcell_def, compatibility = sv.prepare_pcell_definition(
                pcell_def, str(file_path))
        except sv.DesignFileValidationError as error:
            self.scene.logger.error(
                f"Invalid PCell definition {file_path}: "
                f"{'; '.join(error.errors or [str(error)])}")
            return None
        if compatibility.migrated:
            self.scene.logger.info(
                f"Migrated PCell schema {compatibility.sourceVersion} "
                f"to {compatibility.targetVersion}: {file_path}")

        pcell_class = PCellCache.getPCellClass(pcell_def[1]["reference"])
        if not pcell_class:
            self.scene.logger.error(
                f"Unknown PCell class: {pcell_def[1].get('reference')}")
            return None

        try:
            instance = pcell_class()
            # A saved "bbox" defers pcell evaluation until shapes are needed.
            bbox = item.get("bbox")
            deferParams = getattr(instance, "deferParams", None)
            if (
                    callable(deferParams)
                    and isinstance(bbox, (list, tuple))
                    and len(bbox) == 4
            ):
                deferParams(item.get("params", {}), QRectF(*bbox))
            else:
                instance(**item.get("params", {}))
            instance.libraryName = item["lib"]
            instance.cellName = item["cell"]
            instance.viewName = item["view"]
            instance.counter = item["ic"]
            instance.instanceName = item["nam"]
            instance.setPos(QPointF(*item["loc"]))
            instance.setArray(
                item.get("rows", 1), item.get("cols", 1),
                item.get("rpt", 0), item.get("cpt", 0),
            )
            self._set_common_attrs(instance, item)
            # Schematic<->layout correspondence (backend/correspondence).
            self._restoreSdlSource(instance, item)
            return instance
        except Exception as e:
            self.scene.logger.error(f"Error creating PCell instance: {e}")
            return None

    def createLayoutInstance(self, item):
        library_path = self._get_library_path(item["lib"])
        if not library_path:
            return None

        file_path = library_path / item["cell"] / f"{item['view']}.json"
        file_contents = self._load_json_file(str(file_path))
        if not file_contents:
            return None

        try:
            file_contents, compatibility = sv.prepare_design_data(
                file_contents, "layout", str(file_path))
        except sv.DesignFileValidationError as error:
            self.scene.logger.error(
                f"Invalid layout file {file_path}: "
                f"{'; '.join(error.errors or [str(error)])}")
            return None
        if compatibility.migrated:
            self.scene.logger.info(
                f"Migrated layout schema {compatibility.sourceVersion} "
                f"to {compatibility.targetVersion}: {file_path}")

        file_path_key = str(file_path)
        if file_path_key in self._active_layout_paths:
            self.scene.logger.error(f"Recursive layout reference: {file_path}")
            return None

        # Defer child construction until the shapes are actually needed (paint
        # at full LOD, hit tests, export). The bounds come from a saved "bbox"
        # when present, or a cheap dict-level walk for legacy files; cells
        # containing unboundable records (e.g. a Pcell without bbox) fall back
        # to eager construction.
        bbox = item.get("bbox")
        if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            bounds = QRectF(*bbox)
        else:
            bounds = self._cachedLocalBounds(file_path_key, file_contents)
        if bounds is not None:
            instance = lshp.layoutInstance([])
            instance.deferShapes(file_contents[2:], bounds, file_path_key)
        else:
            item_shapes = []
            append_shape = item_shapes.append
            self._active_layout_paths.add(file_path_key)
            try:
                for shape_data in itertools.islice(file_contents, 2, None):
                    try:
                        shape = self.create(shape_data)
                    except Exception:
                        continue
                    if shape:
                        append_shape(shape)
            finally:
                self._active_layout_paths.remove(file_path_key)

            instance = lshp.layoutInstance(item_shapes)
        loc = item["loc"]
        instance.libraryName = item["lib"]
        instance.cellName = item["cell"]
        instance.counter = item.get("ic")
        instance.instanceName = item.get("nam", "")
        instance.setPos(loc[0], loc[1])  # Cache loc lookup
        instance.viewName = item["view"]
        instance.setArray(
            item.get("rows", 1), item.get("cols", 1),
            item.get("rpt", 0), item.get("cpt", 0),
        )
        self._set_common_attrs(instance, item)
        # Schematic<->layout correspondence (backend/correspondence).
        self._restoreSdlSource(instance, item)
        return instance

    def createRectShape(self, item):
        tl, br, ln = item["tl"], item["br"], item["ln"]
        # Geometry is saved pos-folded (pos() + local).  pos() stays at the
        # origin; _set_common_attrs restores ang/fl around the saved top.
        rect = lshp.layoutRect(
            QPointF(tl[0], tl[1]),
            QPointF(br[0], br[1]),
            self._pdkLayers[ln]
        )
        self._set_common_attrs(rect, item)
        return rect

    def createPathShape(self, item):
        dfl1, dfl2 = item["dfl1"], item["dfl2"]
        # Geometry is saved pos-folded (pos() + local); see createRectShape.
        path = lshp.layoutPath(
            QLineF(QPointF(dfl1[0], dfl1[1]), QPointF(dfl2[0], dfl2[1])),
            self._pdkLayers[item["ln"]],
            item["w"], item["se"], item["ee"], item["md"]
        )
        path.name = item.get("nam", "")
        self._set_common_attrs(path, item)
        return path

    def createRulerShape(self, item):
        """Rebuild a ruler from its canonical record.

        ``dfl1``/``dfl2`` are stored as a horizontal segment; ``ang`` is the
        drawn direction and ``top`` its pivot (both emitted by
        ``_encodeLayoutRuler`` and by pre-rewrite files). Fold the stored
        transform — mirror about the segment bbox centre, then rotate
        ``-ang`` about ``top`` — into the true scene endpoints. New-format
        records (``ang`` matching dfl direction or 0) pass through unchanged.
        """
        p1 = QPointF(*item["dfl1"])
        p2 = QPointF(*item["dfl2"])
        top = item.get("top", item["dfl1"])
        ang = float(item.get("ang", 0) or 0)
        fl = tuple(item.get("fl", (1, 1)))
        if ang != 0 or fl != (1, 1):
            xf = QTransform()
            xf.translate(top[0], top[1])
            xf.rotate(-ang)
            xf.translate(-top[0], -top[1])
            if fl != (1, 1):
                center = QRectF(p1, p2).normalized().center()
                xf = xf * QTransform(
                    fl[0], 0, 0, fl[1],
                    center.x() - fl[0] * center.x(),
                    center.y() - fl[1] * center.y())
            p1 = xf.map(p1)
            p2 = xf.map(p2)
        return lshp.layoutRuler(
            QLineF(p1, p2), self.rulerWidth, self.rulerFont,
            int(item.get("md", 0)))

    def createLabelShape(self, item):
        # Labels set their own rotation/flip from labelOrient in __init__;
        # 'ang' is an *additional* rotation baked in by flattening (the same
        # convention _labelDictBounds uses), applied on top of the orient.
        # Anchor is saved pos-folded.
        label = lshp.layoutLabel(
            QPointF(*item["st"]), item["lt"], item["ff"], item["fs"],
            item["fh"], item["la"], item["lo"], self._pdkLayers[item["ln"]]
        )
        extraAngle = float(item.get("ang") or 0)
        if abs(extraAngle) > 1e-9:
            label.addExtraRotation(extraAngle)
        return label

    def createPinShape(self, item):
        # Geometry is saved pos-folded (pos() + local); see createRectShape.
        pin = lshp.layoutPin(
            QPointF(*item["tl"]), QPointF(*item["br"]), item["pn"],
            item["pd"], item["pt"], self._pdkLayers[item["ln"]]
        )
        self._set_common_attrs(pin, item)
        return pin

    def createPolygonShape(self, item):
        # layoutPolygon stretch logic expects integer QPoint vertices.
        points = [QPoint(round(x), round(y)) for x, y in item["ps"]]
        polygon = lshp.layoutPolygon(points, self._pdkLayers[item["ln"]])
        self._set_common_attrs(polygon, item)
        return polygon

    @staticmethod
    @functools.lru_cache(maxsize=16)
    def _get_via_def(via_name):
        return fabproc.processVias[fabproc.processViaNames.index(via_name)]

    def createViaArrayShape(self, item):
        via_info = item["via"]
        via_start = via_info.get("st", (0, 0))
        via_def = self._get_via_def(via_info["vdt"])
        via = lshp.layoutVia(
            QPointF(*via_start),
            via_def,
            via_info["w"],
            via_info["h"],
            via_info.get("be"),
            via_info.get("te"),
        )
        is_legacy = item.get("coordMode") != "parent"
        via_array = lshp.layoutViaArray(
            QPointF(*via_start) if is_legacy else QPoint(0, 0),
            via,
            item["xs"],
            item["ys"],
            item["xn"],
            item["yn"],
            legacyStart=is_legacy,
        )

        if is_legacy:
            self._set_common_attrs(via_array, item)
            return via_array

        anchor = QPointF(*item["st"])
        via_array.setPos(anchor)
        self._set_common_attrs(via_array, item)
        # st is the first-cut scene anchor. Rotation and flip can move the
        # item's local origin away from that cut, so correct the parent once.
        via_array.setPos(via_array.pos() + anchor - via_array.mapToScene(QPointF(0, 0)))
        return via_array

    def createMultipartShape(self, item):
        cls = lshp.MULTIPART_KINDS.get(item.get("kind", ""))
        if cls is None:
            self.scene.logger.error(
                f"Unknown multipart kind: {item.get('kind')!r}")
            return None
        shape = cls(item.get("params", {}))
        shape.setPos(QPointF(*item.get("loc", (0, 0))))
        self._set_common_attrs(shape, item)
        return shape

    def createGroupShape(self, item):
        # Member records are stored in group-local coordinates; the group's
        # loc/top/ang/fl carries whatever transform it accumulated while
        # grouped (same convention as instances).
        members = []
        for record in item.get("items", []):
            if not isinstance(record, dict):
                continue
            shape = self.create(record)
            if shape is not None:
                members.append(shape)
        group = lshp.layoutGroup(members)
        group.setPos(QPointF(*item.get("loc", (0, 0))))
        self._set_common_attrs(group, item)
        return group

    def unknownItem(self, item=None):
        return None
