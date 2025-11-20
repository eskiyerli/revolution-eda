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

# Load symbol and maybe later schematic from json file.
# import pathlib

import functools
import json
import orjson
import pathlib
from typing import Any, List

from PySide6.QtCore import QPoint, QLineF, QRect
from PySide6.QtGui import (
    QColor,
    QFont,
)
from PySide6.QtWidgets import (
    QGraphicsScene,
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsSimpleTextItem,
)
# from methodtools import lru_cache

import revedaEditor.common.labels as lbl
import revedaEditor.common.layoutShapes as lshp
import revedaEditor.common.net as net
import revedaEditor.common.shapes as shp
import revedaEditor.fileio.symbolEncoder as se
from revedaEditor.backend.pdkPaths import importPDKModule

laylyr = importPDKModule('layoutLayers')
pcells = importPDKModule('pcells')
fabproc = importPDKModule('process')

class symbolItems:
    def __init__(self, scene: QGraphicsScene):
        """
        Initializes the class instance.

        Args:
            scene (QGraphicsScene): The QGraphicsScene object.

        """
        self.scene = scene
        self.snapTuple = scene.snapTuple

    def create(self, item: dict):
        """
        Create symbol items from json file.
        """
        if isinstance(item, dict):
            match item.get("type"):
                case "rect":
                    return self.createRectItem(item)
                case "circle":
                    return self.createCircleItem(item)
                case "arc":
                    return self.createArcItem(item)
                case "line":
                    return self.createLineItem(item)
                case "pin":
                    return self.createPinItem(item)
                case "label":
                    return self.createLabelItem(item)
                case "text":
                    return self.createTextItem(item)
                case "polygon":
                    return self.createPolygonItem(item)
            


    @staticmethod
    def createRectItem(item: dict):
        """
        Create symbol items from json file.
        """
        start = QPoint(item["rect"][0], item["rect"][1])
        end = QPoint(item["rect"][2], item["rect"][3])
        rect = shp.symbolRectangle(start, end)
        rect.setPos(
            QPoint(item["loc"][0], item["loc"][1]),
        )
        rect.angle = item.get("ang",0)
        rect.flipTuple = item.get('fl',(1,1))
        return rect

    @staticmethod
    def createCircleItem(item: dict):
        centre = QPoint(item["cen"][0], item["cen"][1])
        end = QPoint(item["end"][0], item["end"][1])
        circle = shp.symbolCircle(centre, end)  # note that we are using grid
        # values for
        # scene
        circle.setPos(
            QPoint(item["loc"][0], item["loc"][1]),
        )
        circle.angle = item.get("ang",0)
        circle.flipTuple = item.get('fl',(1,1))
        return circle

    @staticmethod
    def createArcItem(item: dict):
        start = QPoint(item["st"][0], item["st"][1])
        end = QPoint(item["end"][0], item["end"][1])

        arc = shp.symbolArc(start, end)  # note that we are using grid values
        # for scene
        arc.setPos(QPoint(item["loc"][0], item["loc"][1]))
        arc.angle = item.get("ang", 0)
        arc.flipTuple = item.get('fl',(1,1))
        arc.arcType = shp.symbolArc.arcTypes[item["at"]]
        return arc

    @staticmethod
    def createLineItem(item: dict):
        start = QPoint(item["st"][0], item["st"][1])
        end = QPoint(item["end"][0], item["end"][1])

        line = shp.symbolLine(start, end)
        line.setPos(QPoint(item["loc"][0], item["loc"][1]))
        line.angle = item.get("ang",0)
        line.flipTuple = item.get('fl',(1,1))
        return line

    @staticmethod
    def createPinItem(item: dict):
        start = QPoint(item["st"][0], item["st"][1])
        pin = shp.symbolPin(start, item["nam"], item["pd"], item["pt"])
        pin.setPos(QPoint(item["loc"][0], item["loc"][1]))
        pin.angle = item["ang"]
        pin.flipTuple = item.get('fl',(1,1))
        return pin

    @staticmethod
    def createLabelItem(item: dict):
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
        return label

    @staticmethod
    def createTextItem(item: dict):
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
    def createPolygonItem(item: dict):
        pointsList = [QPoint(point[0], point[1]) for point in item["ps"]]
        polygon = shp.symbolPolygon(pointsList)
        polygon.flipTuple = item.get('fl',(1,1))
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

    def unknownItem(self):
        rectItem = QGraphicsRectItem(QRect(0, 0, *self.snapTuple))
        rectItem.setVisible(False)
        return rectItem


class schematicItems:
    def __init__(self, scene: QGraphicsScene):
        self.scene = scene
        self.libraryDict = scene.libraryDict
        self.snapTuple = scene.snapTuple

    def create(self, item: dict):
        if isinstance(item, dict):
            match item["type"]:
                case "sys":
                    return self._createSymbolShape(item)
                case "scn":
                    return self._createNet(item)
                case "scp":
                    return self._createPin(item)
                case "txt":
                    return self._createText(item)
                case _:
                    pass
                    # return self.unknownItem()

    def _createText(self, item):
        start = QPoint(0,0)
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
        text.flipTuple = item.get('fl', (1,1))
        text.angle = item.get('ang', 0)

        return text

    def _createPin(self, item):
        start = QPoint(0,0)
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
        pinItem.flipTuple = item.get('fl', (1,1))
        return pinItem

    def _createNet(self, item):
        start = QPoint(item["st"][0], item["st"][1])
        end = QPoint(item["end"][0], item["end"][1])
        width = item.get('w',0)
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
        [
            labelItem.labelDefs()
            for labelItem in symbolInstance.labels.values()
        ]
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
                with file.open(mode="r", encoding="utf-8") as temp:
                    try:
                        jsonItems = json.load(temp)
                        symbolShape = symbolItems(self.scene)
                        for jsonItem in jsonItems[2:]:  # skip first two entries.
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
                            if (
                                    labelItem.labelName
                                    in labelDict.keys()
                            ):
                                labelItem.labelValue = (
                                    labelDict[
                                        labelItem.labelName
                                    ][0]
                                )
                                labelItem.labelVisible = (
                                    labelDict[
                                        labelItem.labelName
                                    ][1]
                                )
                        symbolInstance.symattrs = symbolAttributes
                        [
                            labelItem.labelDefs()
                            for labelItem in symbolInstance.labels.values()
                        ]
                        symbolInstance.angle = item.get("ang", 0)
                        symbolInstance.flipTuple = item.get('fl', (1,1))
                        return symbolInstance
                    except json.decoder.JSONDecodeError:
                        self.scene.logger.error(
                            "Error: Invalid Symbol file"
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
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PCellCache, cls).__new__(cls)
            cls._instance.layout_file_cache = {}
        return cls._instance

    @classmethod
    @functools.lru_cache(maxsize=100)
    def getPCellDef(cls, file_path: str) -> dict:
        try:
            with open(file_path, "r") as temp:
                return json.load(temp)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    @classmethod
    @functools.lru_cache(maxsize=100)
    def getPCellClass(cls, pcell_class_name: str) -> Any:
        return pcells.pcells.get(pcell_class_name)

    @classmethod
    def getLayoutFileContents(cls, file_path: str) -> List:
        return cls._instance.layout_file_cache.get(file_path)

    @classmethod
    def setLayoutFileContents(cls, file_path: str, contents: List):
        cls._instance.layout_file_cache[file_path] = contents

    @classmethod
    def clear_caches(cls):
        cls.getPCellDef.cache_clear()
        cls.getPCellClass.cache_clear()
        cls._instance.layout_file_cache.clear()


class layoutItems:
    def __init__(self, scene):
        self.scene = scene
        self.libraryDict = scene.libraryDict
        self.rulerFont = scene.rulerFont
        self.rulerTickLength = scene.rulerTickLength
        self.snapTuple = scene.snapTuple
        self.rulerWidth = scene.rulerWidth
        self.rulerTickGap = scene.rulerTickGap
        self.cache = PCellCache()

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
        """Common method to get and validate library path"""
        return self._get_library_path_cached(lib_name, tuple(self.libraryDict.items()))
    
    @functools.lru_cache(maxsize=32)
    def _get_library_path_cached(self, lib_name, library_dict_items):
        """Cached library path lookup"""
        library_dict = dict(library_dict_items)
        library_path = pathlib.Path(library_dict.get(lib_name, ""))
        if not library_path.exists():
            return None
        return library_path

    @staticmethod
    @functools.lru_cache(maxsize=128)
    def _load_json_file(file_path_str):
        """Cached JSON file loading with error handling"""
        try:
            with open(file_path_str, "rb") as f:
                return orjson.loads(f.read())
        except (orjson.JSONDecodeError, FileNotFoundError):
            return None

    def _set_common_attrs(self, obj, item):
        """Set common attributes for layout objects"""
        obj.angle = item.get("ang", 0)
        obj.flipTuple = item.get('fl', (1, 1))

    def createPcellInstance(self, item):
        library_path = self._get_library_path(item["lib"])
        if not library_path:
            return None

        file_path = library_path / item["cell"] / f"{item['view']}.json"
        pcell_def = self._load_json_file(str(file_path))
        if not pcell_def or pcell_def[0].get("cellView") != "pcell":
            self.scene.logger.error("Not a PCell cell")
            return None

        pcell_class = pcells.pcells.get(pcell_def[1].get("reference"))
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
            instance.setPos(QPoint(*item["loc"]))
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
        file_path_str = str(file_path)

        # Use cache
        file_contents = self.cache.getLayoutFileContents(file_path_str)
        if file_contents is None:
            file_contents = self._load_json_file(file_path_str)
            if file_contents is None:
                return None
            self.cache.setLayoutFileContents(file_path_str, file_contents)

        # Create shapes with cached factory and pre-allocated list
        shapes_data = file_contents[2:]
        item_shapes = []
        item_shapes_append = item_shapes.append  # Cache method
        
        for shape in shapes_data:
            try:
                created_shape = self.create(shape)  # Reuse self instead of creating new instance
                if created_shape:
                    item_shapes_append(created_shape)
            except Exception:
                pass  # Skip logging for performance

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
        rect = lshp.layoutRect(
            QPoint(tl[0], tl[1]),
            QPoint(br[0], br[1]),
            laylyr.pdkAllLayers[ln]
        )
        self._set_common_attrs(rect, item)
        return rect

    def createPathShape(self, item):
        dfl1, dfl2 = item["dfl1"], item["dfl2"]
        path = lshp.layoutPath(
            QLineF(QPoint(dfl1[0], dfl1[1]), QPoint(dfl2[0], dfl2[1])),
            laylyr.pdkAllLayers[item["ln"]],
            item["w"], item["se"], item["ee"], item["md"]
        )
        path.name = item.get("nam", "")
        self._set_common_attrs(path, item)
        return path

    def createRulerShape(self, item):
        ruler = lshp.layoutRuler(
            QLineF(QPoint(*item["dfl1"]), QPoint(*item["dfl2"])),
            self.rulerWidth, self.rulerTickGap, self.rulerTickLength,
            self.rulerFont, item["md"]
        )
        ruler.angle = item.get("ang", 0)
        return ruler

    def createLabelShape(self, item):
        label = lshp.layoutLabel(
            QPoint(*item["st"]), item["lt"], item["ff"], item["fs"],
            item["fh"], item["la"], item["lo"], laylyr.pdkAllLayers[item["ln"]]
        )
        self._set_common_attrs(label, item)
        return label

    def createPinShape(self, item):
        pin = lshp.layoutPin(
            QPoint(*item["tl"]), QPoint(*item["br"]), item["pn"],
            item["pd"], item["pt"], laylyr.pdkAllLayers[item["ln"]]
        )
        self._set_common_attrs(pin, item)
        return pin

    @functools.lru_cache(maxsize=64)
    def _create_polygon_points(self, points_tuple):
        """Cache polygon point creation for repeated patterns"""
        return [QPoint(p[0], p[1]) for p in points_tuple]

    def createPolygonShape(self, item):
        points = self._create_polygon_points(tuple(tuple(p) for p in item["ps"]))
        polygon = lshp.layoutPolygon(points, laylyr.pdkAllLayers[item["ln"]])
        self._set_common_attrs(polygon, item)
        return polygon

    @functools.lru_cache(maxsize=16)
    def _get_via_def(self, via_name):
        """Cache via definition lookup"""
        return fabproc.processVias[fabproc.processViaNames.index(via_name)]

    def createViaArrayShape(self, item):
        via_info = item["via"]
        via_def = self._get_via_def(via_info["vdt"])
        via_st = via_info["st"]
        via = lshp.layoutVia(
            QPoint(via_st[0], via_st[1]), via_def,
            via_info["w"], via_info["h"]
        )
        st = item["st"]
        via_array = lshp.layoutViaArray(
            QPoint(st[0], st[1]), via,
            item["xs"], item["ys"], item["xn"], item["yn"]
        )
        self._set_common_attrs(via_array, item)
        return via_array

    def unknownItem(self):
        rect_item = QGraphicsRectItem(QRect(0, 0, *self.snapTuple))
        rect_item.setVisible(False)
        return rect_item
