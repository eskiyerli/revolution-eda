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

from PySide6.QtCore import (QPoint, QRect, )
from PySide6.QtWidgets import (QMainWindow, )

import revedaEditor.backend.libBackEnd as scb
import revedaEditor.backend.libraryMethods as libm
import revedaEditor.backend.libraryModelView as lmview
import revedaEditor.common.labels as lbl
import revedaEditor.common.shapes as shp
import revedaEditor.fileio.symbolEncoder as symenc
import revedaEditor.gui.symbolEditor as symed
from revedaEditor.backend.pdkPaths import importPDKModule

cb = importPDKModule('callbacks')


class importXschemSym:
    """
    Imports a xschem sym file
    """

    def __init__(self, parent: QMainWindow, filePathObj: Path,
            libraryView: lmview.BaseDesignLibrariesView, libraryName: str, ):
        self.parent = parent
        self.filePathObj = filePathObj
        self.libraryView = libraryView
        self.libraryName = libraryName
        self._scaleFactor = 4.0
        self._labelHeight = 16
        self._labelXOffset = 40
        self._labelYOffset = 16
        self._labelList = []
        self._functions = []
        self._pins = []
        self._tclExpressLines = []
        self._expressionDict = {}
        self.cellName = self.filePathObj.stem
        libItem = libm.getLibItem(self.libraryView.libraryModel, self.libraryName)

        cellItem = scb.createCell(self.parent, libItem,
            self.cellName)
        symbolViewItem = scb.createCellView(self.parent, "symbol", cellItem)
        self.symbolWindow = symed.symbolEditor(symbolViewItem, self.parent.libraryDict,
            self.libraryView)
        self.symbolScene = self.symbolWindow.centralW.scene

    def importSymFile(self):
        with self.filePathObj.open("r") as file:
            for line in file.readlines():
                lineTokens = line.split()
                if line[0] == "L" and len(lineTokens) > 4:
                    self.symbolScene.lineDraw(
                        QPoint(self._scaleFactor * float(lineTokens[2]),
                               self._scaleFactor * float(lineTokens[3]), ),
                        QPoint(self._scaleFactor * float(lineTokens[4]),
                               self._scaleFactor * float(lineTokens[5]), ), )
                elif line[0] == "B" and len(lineTokens) > 4:
                    properties = self.findProperties(line)
                    if "name" in properties.keys():
                        pin = shp.symbolPin(QPoint(0, 0), properties.get("name", ""),
                            properties.get("dir", "input").capitalize(),
                            shp.symbolPin.pinTypes[0], )
                        pin.rect = QRect(QPoint(self._scaleFactor * float(lineTokens[2]),
                                                self._scaleFactor * float(lineTokens[3]), ),
                            QPoint(self._scaleFactor * float(lineTokens[4]),
                                   self._scaleFactor * float(lineTokens[5]), ), )
                        self.symbolScene.addItem(pin)
                        self._pins.append(pin)
                    else:
                        self.symbolScene.rectDraw(
                            QPoint(self._scaleFactor * float(lineTokens[2]),
                                   self._scaleFactor * float(lineTokens[3]), ),
                            QPoint(self._scaleFactor * float(lineTokens[4]),
                                   self._scaleFactor * float(lineTokens[5]), ), )
                elif line[0] == "P" and len(lineTokens) > 4:
                    numberPoints = int(float(lineTokens[2]))
                    points = []
                    for i in range(numberPoints):
                        points.append(
                            QPoint(self._scaleFactor * float(lineTokens[2 * i + 3]),
                                   self._scaleFactor * float(lineTokens[2 * i + 4]), ))
                    polygon = shp.symbolPolygon(points)
                    self.symbolScene.addItem(polygon)
                elif line[0] == "T" and len(lineTokens) > 4:
                    if "tcleval" in line:
                        # self._functions.append(line)  # just a reminder
                        self._tclExpressLines.append(line)

        with self.filePathObj.open("r") as file:
            fileContent = file.read()
            pattern = re.compile(r"K\s*{[^}]+}")
            formatStringMatch = pattern.search(fileContent)
            if formatStringMatch:
                formatString = formatStringMatch.group()
                formatDict = self.processFormatString(formatString)
                self.symbolScene.attributeList = list()
                templateDict = formatDict.get("template")
                textLocation = (self._labelXOffset, self._labelYOffset)
                if templateDict:
                    if templateDict.get("model"):
                        self.symbolScene.attributeList.append(
                            symenc.symbolAttribute("modelName", templateDict["model"]))
                        templateDict.pop("model")
                    if templateDict.get("spiceprefix"):
                        self.symbolScene.attributeList.append(
                            symenc.symbolAttribute("spiceprefix",
                                templateDict["spiceprefix"]))
                        templateDict.pop("spiceprefix")
                    if templateDict.get("name"):
                        templateDict.pop("name")
                    for key, value in templateDict.items():
                        label = lbl.symbolLabel(QPoint(textLocation[0], textLocation[1]),
                            f"[@{key}:{key.lower()}=%:{key.lower()}={value}]",
                            lbl.symbolLabel.labelTypes[1], self._labelHeight,
                            lbl.symbolLabel.labelAlignments[0],
                            lbl.symbolLabel.labelOrients[0], lbl.symbolLabel.labelUses[1], )
                        textLocation = (textLocation[0], textLocation[
                            1] - self._labelHeight - self._labelYOffset,)
                        label.labelDefs()
                        label.labelVisible = True
                        label.setOpacity(1)
                        self.symbolScene.addItem(label)
                        self._labelList.append(label.labelName)
                    label = lbl.symbolLabel(QPoint(textLocation[0], textLocation[1]),
                        "[@instName]", lbl.symbolLabel.labelTypes[1], self._labelHeight,
                        lbl.symbolLabel.labelAlignments[0], lbl.symbolLabel.labelOrients[0],
                        lbl.symbolLabel.labelUses[1], )
                    label.labelDefs()
                    label.labelVisible = True
                    label.setOpacity(1)
                    self.symbolScene.addItem(label)

                if formatDict.get("format"):
                    netlistLine = (
                        formatDict["format"].replace("@name", "@instName").replace("@model",
                                                                                   "%modelName").replace(
                            "@spiceprefix", "%spiceprefix").replace("@pinlist", "@pinList"))
                    self.symbolScene.attributeList.append(
                        symenc.symbolAttribute("XyceSymbolNetlistLine", netlistLine))
            pinNames = [pin.pinName for pin in self._pins]
            self.symbolScene.attributeList.append(
                symenc.symbolAttribute("pinOrder", ", ".join(pinNames)))
        self.processTclEval(self._tclExpressLines)
        self.symbolWindow.checkSaveCell()

    @property
    def scaleFactor(self) -> float:
        return self._scaleFactor

    @scaleFactor.setter
    def scaleFactor(self, value: float):
        self._scaleFactor = value

    @staticmethod
    def findProperties(line: str):
        properties = {}
        # Remove curly braces from the string
        propertiesStr = line.split("{")[1].split("}")[0]
        # Split the string by commas to separate key-value pairs
        pairs = propertiesStr.split()
        for pair in pairs:
            key, value = pair.split("=")
            key = key.strip()
            value = value.strip()
            properties[key] = value
        return properties

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

        textLocation = [self._scaleFactor * float(restList[0]),
                        self._scaleFactor * float(restList[1]), ]
        rotationAngle = float(restList[2])
        return text, textProperties, textLocation, rotationAngle

    @staticmethod
    def processFormatString(formatString: str):
        lines = " ".join([line.strip() for line in formatString.strip().split("\n")])
        # print(lines)
        joinedLines = lines.split("{")[1].split("}")[0]
        startIndex = 0
        indexes = []
        while True:
            startIndex = joinedLines.find('="', startIndex)
            if startIndex == -1:
                break
            startIndex += 2
            indexes.append(startIndex)
        startIndex = 0
        # print(f'Keys: {keys}')
        values = []
        for index in indexes:
            endIndex = joinedLines.find('"', index)
            values.append(joinedLines[index:endIndex])

        for valueItem in values:
            joinedLines = joinedLines.replace(valueItem, "")

        keys = [item.replace('=""', "") for item in joinedLines.split()[1:]]
        formatDict = {key: value for key, value in zip(keys, values)}
        templateDict = {item.split("=")[0]: item.split("=")[1] for item in
            formatDict["template"].split()}
        formatDict["template"] = templateDict
        return formatDict

    def processTclEval(self, inputLines: list[str]):
        tclEvalMatches = []
        parameterMatches = []
        tclPattern = r"\\{(.*?)\\}"
        parameterPattern = r"tcleval\((.*?)=\["
        for lineItem in inputLines:
            tclEvalMatches.append(re.findall(tclPattern, lineItem)[0])
            parameterMatches.append(re.findall(parameterPattern, lineItem)[0])

        for key, value in zip(parameterMatches, tclEvalMatches):
            self._expressionDict[key] = value

        clbPathObj = pathlib.Path(cb.__file__)
        with clbPathObj.open("a") as clbFile:
            clbFile.write("\n\n")
            clbFile.write(f"class {self.cellName}(baseInst):\n")
            clbFile.write(f"    def __init__(self, labels_dict:dict):\n")
            clbFile.write(f"        super().__init__(labels_dict)\n")
            for labelName in self._labelList:
                clbFile.write(f"        self.{labelName[1:]} = Quantity(self._labelsDict["
                              f"'{labelName}'].labelValue)\n")

            for key, value in self._expressionDict.items():
                for labelName in self._labelList:
                    value = value.replace(labelName, f"self.{labelName[1:]}")
                clbFile.write("\n")
                clbFile.write(f"    def {key}parm(self):\n")
                clbFile.write(f"       returnValue = {value}\n")
                clbFile.write(f"       return returnValue\n")
                label = lbl.symbolLabel(QPoint(0, 0), f"{key} = {key}parm()",
                    lbl.symbolLabel.labelTypes[2], self._labelHeight,
                    lbl.symbolLabel.labelAlignments[0], lbl.symbolLabel.labelOrients[0],
                    lbl.symbolLabel.labelUses[1], )
                label.labelDefs()
                label.labelVisible = True
                label.setOpacity(1)
                self.symbolScene.addItem(label)
            clbFile.write("\n")
