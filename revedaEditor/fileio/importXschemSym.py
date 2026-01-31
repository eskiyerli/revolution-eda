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
import pathlib
import re
from pathlib import Path

from PySide6.QtCore import (
    QPoint,
    QRect,
)
from PySide6.QtWidgets import (
    QMainWindow,
)

import revedaEditor.backend.libBackEnd as scb
import revedaEditor.backend.libraryMethods as libm
import revedaEditor.backend.libraryModelView as lmview
import revedaEditor.common.labels as lbl
import revedaEditor.common.shapes as shp
import revedaEditor.fileio.symbolEncoder as symenc
import revedaEditor.gui.symbolEditor as symed
from revedaEditor.backend.pdkLoader import importPDKModule

cb = importPDKModule("callbacks")


class importXschemSym:
    """
    Imports a xschem sym file
    """

    def __init__(
            self,
            parent: QMainWindow,
            filePathObj: Path,
            libraryView: lmview.BaseDesignLibrariesView,
            libraryName: str,
    ):
        self.parent = parent
        self.filePathObj = filePathObj
        self.libraryView = libraryView
        self.libraryName = libraryName
        self._scaleFactor = 4.0
        self._labelHeight = 16
        self._labelXOffset = 40
        self._labelYOffset = 8
        self._labelList = []
        self._pins = []
        self._expressionDict = dict()

        self.cellName = self.filePathObj.stem
        libItem = libm.getLibItem(self.libraryView.libraryModel, self.libraryName)

        cellItem = scb.createCell(self.parent, libItem, self.cellName)
        symbolViewItem = scb.createCellView(self.parent, "symbol", cellItem)
        self.symbolWindow = symed.symbolEditor(
            symbolViewItem, self.parent.libraryDict, self.libraryView
        )
        self.symbolScene = self.symbolWindow.centralW.scene

        self.clbPathObj = pathlib.Path(cb.__file__)
        with self.clbPathObj.open("a") as clbFile:
            clbFile.write("\n\n")
            clbFile.write(f"class {self.cellName}(baseInst):\n")
            clbFile.write("    def __init__(self, labels_dict:dict):\n")
            clbFile.write("        super().__init__(labels_dict)\n")

    def _createScaledPoint(self, x_token, y_token):
        """Helper to create scaled QPoint from string tokens"""
        return QPoint(
            int(self._scaleFactor * float(x_token)), int(self._scaleFactor *
                                                         float(y_token))
        )

    def importSymFile(self):
        # Read file once and process both line-by-line and pattern matching
        with self.filePathObj.open("r") as file:
            fileContent = file.read()

        # Process lines
        lines = fileContent.splitlines()
        processed_lines = []

        for line in lines:
            if not line or len(line) < 1 or line.startswith("*"):
                continue
            if line.startswith("+") and processed_lines:
                processed_lines[-1] += line[1:]  # Append without the '+'
            else:
                if line[0] in "LBPTVGKSE" and line[1] == " ":
                    processed_lines.append(line)
                elif processed_lines:
                    processed_lines[-1] += " " + line

        for line in processed_lines:
            lineTokens = line.split()
            line_type = line[0]
            #
            if line_type == "L" and len(lineTokens) > 4:
                self.symbolScene.lineDraw(
                    self._createScaledPoint(lineTokens[2], lineTokens[3]),
                    self._createScaledPoint(lineTokens[4], lineTokens[5]),
                )

            elif line_type == "B" and len(lineTokens) > 4:
                properties = self.parseLineLine(line)
                point1 = self._createScaledPoint(lineTokens[2], lineTokens[3])
                point2 = self._createScaledPoint(lineTokens[4], lineTokens[5])

                if "name" in properties:
                    pin = shp.symbolPin(
                        QPoint(0, 0),
                        properties.get("name", ""),
                        properties.get("dir", "input").capitalize(),
                        shp.symbolPin.pinTypes[0],
                    )
                    pin.rect = QRect(point1, point2)
                    pin.start = pin.rect.center()
                    self.symbolScene.addItem(pin)
                    self._pins.append(pin)
                else:
                    self.symbolScene.rectDraw(point1, point2)

            elif line_type == "P" and len(lineTokens) > 4:
                numberPoints = int(float(lineTokens[2]))
                points = [
                    self._createScaledPoint(
                        lineTokens[2 * i + 3], lineTokens[2 * i + 4]
                    )
                    for i in range(numberPoints)
                ]
                self.symbolScene.addItem(shp.symbolPolygon(points))

            elif line_type == "K":
                self._expressionDict = self.processFormatString(line)

                if self._expressionDict.get("format"):
                    netlistLine = (
                        self._expressionDict["format"]
                        .replace("@name", "@instName")
                        .replace("@model", "%modelName")
                        .replace("@spiceprefix", "%spiceprefix")
                        .replace("@pinlist", "%pinOrder")
                    )

                    self.symbolScene.attributeList.append(
                        symenc.symbolAttribute("SpiceNetlistLine", netlistLine)
                    )

                templateString = self._expressionDict.get("template")
                textLocation = [self._labelXOffset, self._labelYOffset]
                if templateString:
                    pairs = re.findall(r"(\w+)=([^\s]+)", templateString)
                    templateDict = dict((k, v.strip()) for k, v in pairs)
                    if templateDict:
                        if templateDict.get("name"):
                            templateDict.pop("name")  # we don't use this
                        if templateDict.get("model"):
                            self.symbolScene.attributeList.append(
                                symenc.symbolAttribute(
                                    "modelName", templateDict.pop("model")
                                )
                            )
                        if templateDict.get("spiceprefix"):
                            self.symbolScene.attributeList.append(
                                symenc.symbolAttribute(
                                    "spiceprefix", templateDict.pop("spiceprefix")
                                )
                            )

                    # Add instance name label
                    self._createNLPLabel(textLocation, "[@instName]")

        # Add pin order attribute
        pinNames = [pin.pinName for pin in self._pins]
        self.symbolScene.attributeList.append(
            symenc.symbolAttribute("pinOrder", ", ".join(pinNames))
        )

        self.symbolWindow.checkSaveCell()

    @property
    def scaleFactor(self) -> float:
        return self._scaleFactor

    @scaleFactor.setter
    def scaleFactor(self, value: float):
        self._scaleFactor = value

    @staticmethod
    def parseLineLine(line: str):
        start = line.find("{")
        end = line.find("}", start)
        if start == -1 or end == -1:
            return {}
        return dict(
            pair.split("=", 1) for pair in line[start + 1: end].split() if "=" in pair
        )

    def parseTextLine(self, line: str):
        text = line.split("{")[1].split("}")[0]
        textPropertiesStr = line.split("{")[2].split("}")[0]
        pairs = textPropertiesStr.split()
        textProperties = {}
        for pair in pairs:
            key, value = pair.split("=")
            key = key.strip()
            value = value.strip()
            textProperties[key] = value
        restList = line.split("{")[1].split("}")[1].split()

        textLocation = [
            self._scaleFactor * float(restList[0]),
            self._scaleFactor * float(restList[1]),
        ]
        rotationAngle = float(restList[2])
        return text, textProperties, textLocation, rotationAngle

    @staticmethod
    def processFormatString(inputText: str) -> dict:
        # this is an adhoc list
        keys = {
            "format=": "format",
            "lvs_format=": "lvs",
            "template=": "template",
            "drc=": "drc",
        }
        text = inputText.replace('\\\\"', "").replace("'", "")

        result = {}
        for key_str, key in keys.items():
            pos = text.find(key_str)
            if pos != -1:
                start = pos + len(key_str)
                if start < len(text) and text[start] == '"':
                    start += 1
                    end = text.find('"', start)
                    if end != -1:
                        result[key] = text[start:end]
                else:
                    end = start
                    while end < len(text) and text[end] not in " \n":
                        end += 1
                    result[key] = text[start:end]

        return result

    def _createNLPLabel(self, location: list[int], text: str, add_to_scene=True):
        '''
        Helper method to create and configure NLPLabels with common settings.
        '''
        label = lbl.symbolLabel(QPoint(location[0], location[1]), text,
                                lbl.symbolLabel.labelTypes[1], self._labelHeight,
                                lbl.symbolLabel.labelAlignments[0],
                                lbl.symbolLabel.labelOrients[0],
                                lbl.symbolLabel.labelUses[0])
        label.labelDefs()
        label.labelVisible = True
        label.setOpacity(1)
        if add_to_scene:
            self.symbolScene.addItem(label)
        return label
