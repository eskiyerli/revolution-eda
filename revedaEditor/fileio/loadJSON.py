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

import json
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
    QGraphicsTextItem,
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
                case _:
                    return self.unknownItem()

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
        text.flipTuple = item.get('fl', (1,1))

        return text

    def _createPin(self, item):
        start = QPoint(item["st"][0], item["st"][1])
        pinName = item["pn"]
        pinDir = item["pd"]
        pinType = item["pt"]
        pinItem = shp.schematicPin(
                        start,
                        pinName,
                        pinDir,
                        pinType,
                    )
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
        symbolInstance.labelDict = item["ld"]
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
                        assert jsonItems[0]["cellView"] == "symbol"
                        symbolSnapTuple = jsonItems[1]["snapGrid"]
                        # we snap to scene grid values. Need to test further.
                        symbolShape = symbolItems(self.scene)
                        symbolShape.snapTuple = symbolSnapTuple
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
                                    in symbolInstance.labelDict.keys()
                            ):
                                labelItem.labelValue = (
                                    symbolInstance.labelDict[
                                        labelItem.labelName
                                    ][0]
                                )
                                labelItem.labelVisible = (
                                    symbolInstance.labelDict[
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
   # @lru_cache(maxsize=100)
    def getPCellDef(cls, file_path: str) -> dict:
        try:
            with open(file_path, "r") as temp:
                return json.load(temp)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    @classmethod
    # @lru_cache(maxsize=100)
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
    def __init__(self, scene: QGraphicsScene):
        """
        Create layout items from json file.
        """
        self.scene = scene
        self.libraryDict = scene.libraryDict
        self.rulerFont = scene.rulerFont
        self.rulerTickLength = scene.rulerTickLength
        self.snapTuple = scene.snapTuple
        self.rulerWidth = scene.rulerWidth
        self.rulerTickGap = scene.rulerTickGap
        self.cache = PCellCache()

    def create(self, item: dict):
        if isinstance(item, dict):
            match item["type"]:
                case "Inst":
                    return self.createLayoutInstance(item)
                case "Pcell":
                    return self.createPcellInstance(item)
                case "Rect":
                    return self.createRectShape(item)
                case "Path":
                    return self.createPathShape(item)
                case "Label":
                    return self.createLabelShape(
                        item,
                    )
                case "Pin":
                    return self.createPinShape(item)
                case "Polygon":
                    return self.createPolygonShape(item)
                case "Via":
                    return self.createViaArrayShape(item)
                case "Ruler":
                    return self.createRulerShape(item)
                case _:
                    return self.unknownItem()

    def createPcellInstance(self, item):
        libraryPath = pathlib.Path(self.libraryDict.get(item["lib"], None))
        if not libraryPath:
            self.scene.logger.error(f'{item["lib"]} cannot be found.')
            return None

        cell = item["cell"]
        viewName = item["view"]
        filePath = libraryPath / cell / f"{viewName}.json"

        if not filePath.is_file():
            self.scene.logger.error(f"File {filePath} does not exist.")
            return None

        try:
            with filePath.open("r") as temp:
                pcellDef = json.load(temp)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            self.scene.logger.error(f"Error reading PCell file: {e}")
            return None

        if not pcellDef or pcellDef[0].get("cellView") != "pcell":
            self.scene.logger.error("Not a PCell cell")
            return None

        pcellClassName = pcellDef[1].get("reference")
        pcellClass = pcells.pcells.get(pcellClassName)
        if not pcellClass:
            self.scene.logger.error(f"Unknown PCell class: {pcellClassName}")
            return None

        try:
            pcellInstance = pcellClass()
            pcellInstance(**item.get("params", {}))
            pcellInstance.libraryName = item["lib"]
            pcellInstance.cellName = item["cell"]
            pcellInstance.viewName = item["view"]
            pcellInstance.counter = item["ic"]
            pcellInstance.instanceName = item["nam"]
            pcellInstance.setPos(QPoint(*item["loc"]))
            pcellInstance.angle = item.get("ang", 0)
            pcellInstance.flipTuple = item.get('fl', (1,1))
            return pcellInstance
        except Exception as e:
            self.scene.logger.error(f"Error creating PCell instance: {e}")
            return None

    def createLayoutInstance(self, item):
        libraryName = item.get("lib")
        libraryPath = pathlib.Path(self.libraryDict.get(libraryName))

        if not libraryPath.exists():
            self.scene.logger.error(f"{libraryName} cannot be found.")
            return None

        cell = item.get("cell")
        viewName = item.get("view")
        filePath = libraryPath / cell / f"{viewName}.json"

        if not filePath.is_file():
            self.scene.logger.error(f"File {filePath} does not exist.")
            return None

        # Try to get the cached file contents
        file_contents = self.cache.getLayoutFileContents(str(filePath))
        if file_contents is None:
            try:
                with filePath.open("r") as file:
                    file_contents = json.load(file)
                # Cache the file contents
                self.cache.setLayoutFileContents(str(filePath), file_contents)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                self.scene.logger.error(f"Error reading Layout file: {e}")
                return None

        itemShapes = []
        for shape in file_contents[2:]:
            try:
                itemShapes.append(layoutItems(self.scene).create(shape))
            except Exception as e:
                self.scene.logger.error(f"Error creating shape: {e}")

        layoutInstance = lshp.layoutInstance(itemShapes)
        layoutInstance.libraryName = libraryName
        layoutInstance.cellName = cell
        layoutInstance.counter = item.get("ic")
        layoutInstance.instanceName = item.get("nam", "")
        layoutInstance.setPos(item["loc"][0], item["loc"][1])
        layoutInstance.angle = item.get("ang", 0)
        layoutInstance.flipTuple = item.get('fl', (1,1))
        layoutInstance.viewName = viewName
        return layoutInstance

    def createRectShape(self, item):
        start = QPoint(item["tl"][0], item["tl"][1])
        end = QPoint(item["br"][0], item["br"][1])
        layoutLayer = laylyr.pdkAllLayers[item["ln"]]
        rect = lshp.layoutRect(start, end, layoutLayer)
        # rect.setPos(QPoint(item["loc"][0], item["loc"][1]))
        rect.angle = item.get("ang", 0)
        rect.flipTuple = item.get('fl', (1,1))
        return rect

    def createPathShape(self, item):
        path = lshp.layoutPath(
            QLineF(
                QPoint(item["dfl1"][0], item["dfl1"][1]),
                QPoint(item["dfl2"][0], item["dfl2"][1]),
            ),
            laylyr.pdkAllLayers[item["ln"]],
            item["w"],
            item["se"],
            item["ee"],
            item["md"],
        )
        path.name = item.get("nam", "")
        path.angle = item.get("ang", 0)
        path.flipTuple = item.get('fl', (1,1))
        return path

    def createRulerShape(self, item):
        ruler = lshp.layoutRuler(
            QLineF(
                QPoint(item["dfl1"][0], item["dfl1"][1]),
                QPoint(item["dfl2"][0], item["dfl2"][1]),
            ),
            self.rulerWidth,
            self.rulerTickGap,
            self.rulerTickLength,
            self.rulerFont,
            item["md"],
        )
        ruler.angle = item.get("ang", 0)
        return ruler

    def createLabelShape(self, item):
        layoutLayer = laylyr.pdkAllLayers[item["ln"]]
        label = lshp.layoutLabel(
            QPoint(item["st"][0], item["st"][1]),
            item["lt"],
            item["ff"],
            item["fs"],
            item["fh"],
            item["la"],
            item["lo"],
            layoutLayer,
        )
        label.angle = item.get("ang", 0)
        label.flipTuple = item.get('fl', (1,1))
        return label

    def createPinShape(self, item):
        layoutLayer = laylyr.pdkAllLayers[item["ln"]]
        pin = lshp.layoutPin(
            QPoint(item["tl"][0], item["tl"][1]),
            QPoint(item["br"][0], item["br"][1]),
            item["pn"],
            item["pd"],
            item["pt"],
            layoutLayer,
        )
        pin.angle = item.get("ang", 0)
        pin.flipTuple = item.get('fl', (1,1))
        return pin

    def createPolygonShape(self, item):
        layoutLayer = laylyr.pdkAllLayers[item["ln"]]
        pointsList = [QPoint(point[0], point[1]) for point in item["ps"]]
        polygon = lshp.layoutPolygon(pointsList, layoutLayer)
        polygon.angle = item.get("ang", 0)
        polygon.flipTuple = item.get('fl', (1,1))
        return polygon

    def createViaArrayShape(self, item):
        viaDefTuple = fabproc.processVias[
            fabproc.processViaNames.index(item["via"]["vdt"])
        ]
        via = lshp.layoutVia(
            QPoint(item["via"]["st"][0], item["via"]["st"][1]),
            viaDefTuple,
            item["via"]["w"],
            item["via"]["h"],
        )
        viaArray = lshp.layoutViaArray(
            QPoint(item["st"][0], item["st"][1]),
            via,
            item["xs"],
            item["ys"],
            item["xn"],
            item["yn"],
        )
        viaArray.angle = item.get("ang", 0)
        viaArray.flipTuple = item.get('fl', (1,1))
        return viaArray

    def unknownItem(self):
        rectItem = QGraphicsRectItem(QRect(0, 0, *self.snapTuple))
        rectItem.setVisible(False)
        return rectItem
