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
from PySide6.QtCore import QPoint, QPointF, QLineF, QRect
from PySide6.QtWidgets import (
    QGraphicsScene,
    QGraphicsRectItem,
    QGraphicsSimpleTextItem,
)

import revedaEditor.common.labels as lbl
import revedaEditor.common.layoutShapes as lshp
import revedaEditor.common.net as net
import revedaEditor.common.shapes as shp
import revedaEditor.fileio.symbolEncoder as se
from revedaEditor.backend.pdkLoader import importPDKModule

laylyr = importPDKModule('layoutLayers')
pcells = importPDKModule('pcells')
fabproc = importPDKModule('process')

def clear_symbol_cache():
    """Clear the symbol JSON loading cache."""
    schematicItems._load_sym_json.cache_clear()


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
        self.rulerTickLength = scene.rulerTickLength
        self.snapTuple = scene.snapTuple
        self.rulerWidth = scene.rulerWidth
        self.rulerTickGap = scene.rulerTickGap
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

    def createPcellInstance(self, item):
        library_path = self._get_library_path(item["lib"])
        if not library_path:
            return None

        file_path = library_path / item["cell"] / f"{item['view']}.json"
        pcell_def = PCellCache.getPCellDef(str(file_path))
        if not pcell_def or pcell_def[0].get("cellView") != "pcell":
            self.scene.logger.error("Not a PCell cell")
            return None

        pcell_class = PCellCache.getPCellClass(pcell_def[1].get("reference"))
        if not pcell_class:
            self.scene.logger.error(
                f"Unknown PCell class: {pcell_def[1].get('reference')}")
            return None

        try:
            instance = pcell_class()
            instance(**item.get("params", {}))
            instance.libraryName = item["lib"]
            instance.cellName = item["cell"]
            instance.viewName = item["view"]
            instance.counter = item["ic"]
            instance.instanceName = item["nam"]
            instance.setPos(QPointF(*item["loc"]))
            self._set_common_attrs(instance, item)
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

        file_path_key = str(file_path)
        if file_path_key in self._active_layout_paths:
            self.scene.logger.error(f"Recursive layout reference: {file_path}")
            return None

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
        self._set_common_attrs(instance, item)
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
        # Geometry is saved pos-folded (pos() + local); see createRectShape.
        ruler = lshp.layoutRuler(
            QLineF(QPointF(*item["dfl1"]), QPointF(*item["dfl2"])),
            self.rulerWidth, self.rulerTickGap, self.rulerTickLength,
            self.rulerFont, item["md"]
        )
        self._set_common_attrs(ruler, item)
        return ruler

    def createLabelShape(self, item):
        # Labels set their own rotation/flip from labelOrient in __init__;
        # generic ang/fl would override that.  Anchor is saved pos-folded.
        label = lshp.layoutLabel(
            QPointF(*item["st"]), item["lt"], item["ff"], item["fs"],
            item["fh"], item["la"], item["lo"], self._pdkLayers[item["ln"]]
        )
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
        points = [QPointF(x, y) for x, y in item["ps"]]
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

    def unknownItem(self, item=None):
        return None
