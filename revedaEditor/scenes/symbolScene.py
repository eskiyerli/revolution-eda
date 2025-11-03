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

# from hashlib import new
import json

# from hashlib import new
import pathlib
from copy import deepcopy


# import numpy as np
from PySide6.QtCore import (
    QLineF,
    QPoint,
    QPointF,
    QRectF,
    Qt,
)
from PySide6.QtGui import (
    QColor,
    QGuiApplication,
    QPen,
    QPainterPath,
)
from PySide6.QtWidgets import (
    QDialog,
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsSceneMouseEvent,
)

import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.backend.undoStack as us
import revedaEditor.common.labels as lbl
import revedaEditor.common.shapes as shp  # import the shapes
import revedaEditor.fileio.loadJSON as lj
import revedaEditor.fileio.symbolEncoder as symenc
import revedaEditor.gui.propertyDialogues as pdlg
from revedaEditor.backend.pdkPaths import importPDKModule
from revedaEditor.scenes.editorScene import editorScene
from typing import List, Dict

symlyr = importPDKModule('symLayers')

# noinspection PyUnresolvedReferences
class symbolScene(editorScene):
    """
    Scene for Symbol editor.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        # drawing modes
        self.editModes = ddef.symbolModes(
            selectItem=True,
            deleteItem=False,
            moveItem=False,
            copyItem=False,
            rotateItem=False,
            changeOrigin=False,
            panView=False,
            drawPin=False,
            drawArc=False,
            drawRect=False,
            drawLine=False,
            addLabel=False,
            drawCircle=False,
            drawPolygon=False,
            stretchItem=False,
        )

        self.symbolShapes = ["line", "arc", "rect", "circle", "pin", "label", "polygon"]
        self.attributeList = [] # list of symbol attributes
        self.origin = QPoint(0, 0)
        # some default attributes

        self.pinName = ""
        self.pinType = shp.symbolPin.pinTypes[0]
        self.pinDir = shp.symbolPin.pinDirs[0]
        self.labelDefinition = ""
        self.labelType = lbl.symbolLabel.labelTypes[0]
        self.labelOrient = lbl.symbolLabel.labelOrients[0]
        self.labelAlignment = lbl.symbolLabel.labelAlignments[0]
        self.labelUse = lbl.symbolLabel.labelUses[0]
        self.labelVisible = False
        self.labelHeight = "12"
        self.labelOpaque = True
        self._newPin = None
        self._newLine = None
        self._newRect = None
        self._newCircle = None
        self._newArc = None
        self._newLabel = None
        self._newPolygon = None
        self._polygonGuideLine = None

    @property
    def drawMode(self):
        return any(
            (
                self.editModes.drawPin,
                self.editModes.drawArc,
                self.editModes.drawLine,
                self.editModes.drawRect,
                self.editModes.drawCircle,
                self.editModes.drawPolygon,
            )
        )

    def mousePressEvent(self, mouse_event: QGraphicsSceneMouseEvent) -> None:
        """Handle mouse press events in the scene."""
        super().mousePressEvent(mouse_event)



    def mouseMoveEvent(self, mouse_event: QGraphicsSceneMouseEvent) -> None:
        super().mouseMoveEvent(mouse_event)
        self.mouseMoveLoc = self.snapToGrid(mouse_event.scenePos().toPoint(),
                                            self.snapTuple)

        # Update message only when needed
        message = None
        if self.editModes.drawLine and self._newLine:
            message = "Release mouse on the end point"
            self._newLine.end = self.mouseMoveLoc
        elif self.editModes.drawPin and self._newPin:
            message = "Place pin"
            self._newPin.setPos(self.mouseMoveLoc - self.mouseReleaseLoc)
        elif self.editModes.drawCircle and self._newCircle:
            message = "Extend Circle"
            # Optimize circle radius calculation
            dx = self.mouseMoveLoc.x() - self._newCircle.centre.x()
            dy = self.mouseMoveLoc.y() - self._newCircle.centre.y()
            self._newCircle.radius = (dx * dx + dy * dy) ** 0.5
        elif self.editModes.drawRect and self._newRect:
            message = "Click to finish the rectangle"
            self._newRect.end = self.mouseMoveLoc
        elif self.editModes.drawArc and self._newArc:
            message = "Extend Arc"
            self._newArc.end = self.mouseMoveLoc
        elif self.editModes.addLabel and self._newLabel:
            message = "Place Label"
            self._newLabel.setPos(self.mouseMoveLoc)
        elif (self.editModes.drawPolygon and
              self._newPolygon and
              self._polygonGuideLine):
            message = "Add another point to Polygon"
            self._polygonGuideLine.setLine(
                QLineF(self._newPolygon.points[-1], self.mouseMoveLoc)
            )

        if message:
            self.editorWindow.messageLine.setText(message)

        self.statusLine.showMessage(f"Cursor Position: {(self.mouseMoveLoc - self.origin).toTuple()}")

    def mouseReleaseEvent(self, mouse_event: QGraphicsSceneMouseEvent) -> None:
        super().mouseReleaseEvent(mouse_event)
        if mouse_event.button() == Qt.LeftButton:
            self.mouseReleaseLoc = mouse_event.scenePos().toPoint()
            modifiers = QGuiApplication.keyboardModifiers()
            if self.editModes.selectItem and self._selectionRectItem:
                self._handleSelectionRect(modifiers)
            else:
                self._handleMouseRelease(self.mouseReleaseLoc, mouse_event.button())

    def _handleMouseRelease(self, mousePos: QPoint, button: Qt.MouseButton) -> None:
        try:
            if self.editModes.changeOrigin:
                self.origin = mousePos
            elif self.editModes.drawLine:
                self.editorWindow.messageLine.setText("Click for the first of line")
                if self._newLine:
                    if self._newLine.length <= 1:
                        self.undoStack.removeLastCommand()
                    self._newLine = None
                self._newLine = self.lineDraw(mousePos, mousePos)
                self._newLine.setSelected(True)
            elif self.editModes.drawCircle:
                if self._newCircle:
                    if self._newCircle.radius <= 1:
                        self.undoStack.removeLastCommand()
                    self._newCircle = None
                self.editorWindow.messageLine.setText("Click for the centre of Circle")
                self._newCircle = self.circleDraw(mousePos, mousePos)
                self._newCircle.setSelected(True)
            elif self.editModes.drawPin:
                if self._newPin:
                    self._newPin = None
                self.editorWindow.messageLine.setText("Add a pin")
                self._newPin = self.pinDraw(mousePos)
                self._newPin.setSelected(True)
            elif self.editModes.drawRect:
                if self._newRect:
                    if self._newRect.width <= 1 or self._newRect.height <= 1:
                        self.undoStack.removeLastCommand()
                    self._newRect = None
                self.editorWindow.messageLine.setText("Click for the first point of Rectangle")
                self._newRect = self.rectDraw(mousePos, mousePos)
                self._newRect.setSelected(True)
            elif self.editModes.drawArc:
                if self._newArc:
                    if self._newArc.width <= 1 or self._newArc.height <= 1:
                        self.undoStack.removeLastCommand()
                    self._newArc = None
                self.editorWindow.messageLine.setText("Click for the first point of Arc")
                self._newArc = self.arcDraw(mousePos, mousePos)
                self._newArc.setSelected(True)
            elif self.editModes.addLabel:
                if self._newLabel:
                    self._newLabel = None
                self.editorWindow.messageLine.setText("Adding a label")
                self._newLabel = self.labelDraw(
                    mousePos,
                    self.labelDefinition,
                    self.labelType,
                    self.labelHeight,
                    self.labelAlignment,
                    self.labelOrient,
                    self.labelUse,
                )
                self._newLabel.setSelected(True)
            elif self.editModes.drawPolygon:
                if self._newPolygon:
                    self._newPolygon.addPoint(mousePos)
                else:
                    self._newPolygon, self._polygonGuideLine = self.startPolygon(mousePos)
                    self.editorWindow.messageLine.setText("Click for the first point of Polygon.")
            elif self.editModes.rotateItem:
                self.editorWindow.messageLine.setText("Rotate item")
                self.rotateSelectedItems(self.mousePressLoc)
        except Exception as e:
            self.logger.error(f"Error in Mouse Release Event: {e} ")


    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        super().mouseDoubleClickEvent(event)
        try:
            self.finishPolygon(event)
        except Exception as e:
            self.logger.error(f"Error in mouse Double Click Event: {e}")

    def lineDraw(self, start: QPoint, current: QPoint):
        line = shp.symbolLine(start, current)
        # self.addItem(line)
        undoCommand = us.addShapeUndo(self, line)
        self.undoStack.push(undoCommand)
        return line

    def rectDraw(self, start: QPoint, end: QPoint):
        """
        Draws a rectangle on the scene
        """
        rect = shp.symbolRectangle(start, end)
        # self.addItem(rect)
        undoCommand = us.addShapeUndo(self, rect)
        self.undoStack.push(undoCommand)
        return rect

    def circleDraw(self, start: QPoint, end: QPoint):
        """
        Draws a circle on the scene
        """
        circle = shp.symbolCircle(start, end)
        # self.addItem(circle)
        self.addUndoStack(circle)
        return circle

    def arcDraw(self, start: QPoint, end: QPoint):
        """
        Draws an arc inside the rectangle defined by start and end points.
        """
        arc = shp.symbolArc(start, end)
        # self.addItem(arc)
        self.addUndoStack(arc)
        return arc

    def pinDraw(self, current):
        pin = shp.symbolPin(current, self.pinName, self.pinDir, self.pinType)
        # self.addItem(pin)
        self.addUndoStack(pin)
        return pin

    def labelDraw(
            self,
            start,
            labelDefinition,
            labelType,
            labelHeight,
            labelAlignment,
            labelOrient,
            labelUse,
    ):
        label = lbl.symbolLabel(
            start,
            labelDefinition,
            labelType,
            labelHeight,
            labelAlignment,
            labelOrient,
            labelUse,
        )
        label.labelVisible = self.labelOpaque
        label.labelDefs()
        label.setOpacity(1)
        self.addUndoStack(label)
        return label

    def addProperty(self, labelDefinition: str):
        pass
        # Extract core expression between [@ and ]
        if labelDefinition.startswith("[@") and labelDefinition.endswith("]"):
            core = labelDefinition[2:-1]
            # Split into components
            parts = core.split(":")
            instProp = parts[0]

    def startPolygon(self, startLoc: QPoint ):
        newPolygon = shp.symbolPolygon([startLoc, startLoc])
        self.addUndoStack(newPolygon)
        # Create guide line
        guide_line = QLineF(newPolygon.points[-2], newPolygon.points[-1])
        polygonGuideLine = QGraphicsLineItem(guide_line)
        polygonGuideLine.setPen(QPen(QColor(255, 255, 0), 1, Qt.DashLine))
        self.addUndoStack(polygonGuideLine)
        return newPolygon,polygonGuideLine

    def finishPolygon(self, event):
        if hasattr(event, 'button') and event.button() == Qt.LeftButton and self.editModes.drawPolygon and self._newPolygon:
            self._newPolygon.polygon.remove(0)
            self._newPolygon.points.pop(0)
            self.editModes.setMode("selectItem")
            self._newPolygon = None
            self.removeItem(self._polygonGuideLine)
            self._polygonGuideLine = None
            self.editorWindow.messageLine.setText('Select Item.')

    def moveBySelectedItems(self):
        if self.selectedItems():
            dlg = pdlg.moveByDialogue(self.editorWindow)
            dlg.xEdit.setText("0")
            dlg.yEdit.setText("0")
            if dlg.exec() == QDialog.Accepted:
                for item in self.selectedItems():
                    item.moveBy(
                        self.snapToBase(float(dlg.xEdit.text()), self.snapTuple[0]),
                        self.snapToBase(float(dlg.yEdit.text()), self.snapTuple[1]),
                    )
            self.editorWindow.messageLine.setText(
                f"Moved items by {dlg.xEdit.text()} and {dlg.yEdit.text()}"
            )
            self.editModes.setMode("selectItem")

    def itemProperties(self):
        """
        When item properties is queried.
        """
        # Define the mapping of types to update methods
        UPDATE_METHODS = {
            shp.symbolRectangle: self.updateSymbolRectangle,
            shp.symbolCircle: self.updateSymbolCircle,
            shp.symbolArc: self.updateSymbolArc,
            shp.symbolLine: self.updateSymbolLine,
            shp.symbolPin: self.updateSymbolPin,
            lbl.symbolLabel: self.updateSymbolLabel,
            shp.symbolPolygon: self.updateSymbolPolygon
        }

        # Filter selected items and update them
        for item in (item for item in self.selectedItems() if item.parentItem() is None):
            updateMethod = UPDATE_METHODS.get(type(item))
            if updateMethod:
                updateMethod(item)


    def updateSymbolRectangle(self, item):
        queryDlg = pdlg.rectPropertyDialog(self.editorWindow)
        [left, top, width, height] = item.rect.getRect()
        sceneTopLeftPoint = item.mapToScene(QPoint(left, top))
        queryDlg.rectLeftLine.setText(str(sceneTopLeftPoint.x()))
        queryDlg.rectTopLine.setText(str(sceneTopLeftPoint.y()))
        queryDlg.rectWidthLine.setText(str(width))  # str(width))
        queryDlg.rectHeightLine.setText(str(height))  # str(height))
        if queryDlg.exec() == QDialog.Accepted:
            newRectItem = shp.symbolRectangle(QPoint(0, 0), QPoint(0, 0))
            newRectItem.left = self.snapToBase(
                float(queryDlg.rectLeftLine.text()), self.snapTuple[0]
            )
            newRectItem.top = self.snapToBase(
                float(queryDlg.rectTopLine.text()), self.snapTuple[1]
            )
            newRectItem.width = self.snapToBase(
                float(queryDlg.rectWidthLine.text()), self.snapTuple[0]
            )
            newRectItem.height = self.snapToBase(
                float(queryDlg.rectHeightLine.text()), self.snapTuple[1]
            )

            self.undoStack.push(us.addDeleteShapeUndo(self, newRectItem, item))

    def updateSymbolCircle(self, item):
        queryDlg = pdlg.circlePropertyDialog(self.editorWindow)
        centre = item.mapToScene(item.centre).toTuple()
        radius = item.radius
        queryDlg.centerXEdit.setText(str(centre[0]))
        queryDlg.centerYEdit.setText(str(centre[1]))
        queryDlg.radiusEdit.setText(str(radius))
        if queryDlg.exec() == QDialog.Accepted:
            newCircleItem = shp.symbolCircle(QPoint(0, 0), QPoint(0, 0))
            centerX = self.snapToBase(
                float(queryDlg.centerXEdit.text()), self.snapTuple[0]
            )
            centerY = self.snapToBase(
                float(queryDlg.centerYEdit.text()), self.snapTuple[1]
            )
            newCircleItem.centre = QPoint(centerX, centerY)
            radius = self.snapToBase(
                float(queryDlg.radiusEdit.text()), self.snapTuple[0]
            )
            newCircleItem.radius = radius
            self.undoStack.push(us.addDeleteShapeUndo(self, newCircleItem, item))

    def updateSymbolLine(self, item):
        queryDlg = pdlg.linePropertyDialog(self.editorWindow)
        sceneLineStartPoint = item.mapToScene(item.start).toPoint()
        sceneLineEndPoint = item.mapToScene(item.end).toPoint()
        queryDlg.startXLine.setText(str(sceneLineStartPoint.x()))
        queryDlg.startYLine.setText(str(sceneLineStartPoint.y()))
        queryDlg.endXLine.setText(str(sceneLineEndPoint.x()))
        queryDlg.endYLine.setText(str(sceneLineEndPoint.y()))
        if queryDlg.exec() == QDialog.Accepted:
            startX = self.snapToBase(
                float(queryDlg.startXLine.text()), self.snapTuple[0]
            )
            startY = self.snapToBase(
                float(queryDlg.startYLine.text()), self.snapTuple[1]
            )
            endX = self.snapToBase(
                float(queryDlg.endXLine.text()), self.snapTuple[0]
            )
            endY = self.snapToBase(
                float(queryDlg.endYLine.text()), self.snapTuple[1]
            )
            newLine = shp.symbolLine(QPoint(startX, startY), QPoint(endX, endY))
            self.undoStack.push(us.addDeleteShapeUndo(self, newLine, item))

    def updateSymbolArc(self, item):
        queryDlg = pdlg.arcPropertyDialog(self.editorWindow)
        sceneStartPoint = item.mapToScene(item.start).toPoint()
        queryDlg.startXEdit.setText(str(sceneStartPoint.x()))
        queryDlg.startYEdit.setText(str(sceneStartPoint.y()))
        queryDlg.widthEdit.setText(str(item.width))
        queryDlg.heightEdit.setText(str(item.height))
        arcType = item.arcType
        if queryDlg.exec() == QDialog.Accepted:
            startX = int(float(queryDlg.startXEdit.text()))
            startY = int(float(queryDlg.startYEdit.text()))
            start = self.snapToGrid(QPoint(startX, startY), self.snapTuple)
            width = int(float(queryDlg.widthEdit.text()))
            height = int(float(queryDlg.heightEdit.text()))
            end = start + QPoint(width, height)
            newArc = shp.symbolArc(start, end)
            newArc.arcType = arcType

            self.undoStack.push(us.addDeleteShapeUndo(self, newArc, item))
            newArc.height = height

    def updateSymbolLabel(self, item):
        queryDlg = pdlg.labelPropertyDialog(self.editorWindow)
        queryDlg.labelDefinition.setText(str(item.labelDefinition))
        queryDlg.labelHeightEdit.setText(str(item.labelHeight))
        queryDlg.labelAlignCombo.setCurrentText(item.labelAlign)
        queryDlg.labelOrientCombo.setCurrentText(item.labelOrient)
        queryDlg.labelUseCombo.setCurrentText(item.labelUse)
        if item.labelVisible:
            queryDlg.labelVisiCombo.setCurrentText("Yes")
        else:
            queryDlg.labelVisiCombo.setCurrentText("No")
        if item.labelType == "Normal":
            queryDlg.normalType.setChecked(True)
        elif item.labelType == "NLPLabel":
            queryDlg.NLPType.setChecked(True)
        elif item.labelType == "PyLabel":
            queryDlg.pyLType.setChecked(True)
        sceneStartPoint = item.pos()
        queryDlg.labelXLine.setText(str(sceneStartPoint.x()))
        queryDlg.labelYLine.setText(str(sceneStartPoint.y()))
        if queryDlg.exec() == QDialog.Accepted:
            startX = int(float(queryDlg.labelXLine.text()))
            startY = int(float(queryDlg.labelYLine.text()))
            start = self.snapToGrid(QPoint(startX, startY), self.snapTuple)
            labelDefinition = queryDlg.labelDefinition.text()
            labelHeight = int(float(queryDlg.labelHeightEdit.text()))
            labelAlign = queryDlg.labelAlignCombo.currentText()
            labelOrient = queryDlg.labelOrientCombo.currentText()
            labelUse = queryDlg.labelUseCombo.currentText()
            labelType = lbl.symbolLabel.labelTypes[0]
            if queryDlg.NLPType.isChecked():
                labelType = lbl.symbolLabel.labelTypes[1]
            elif queryDlg.pyLType.isChecked():
                labelType = lbl.symbolLabel.labelTypes[2]
            newLabel = lbl.symbolLabel(
                start,
                labelDefinition,
                labelType,
                labelHeight,
                labelAlign,
                labelOrient,
                labelUse,
            )
            newLabel.labelVisible = (
                    queryDlg.labelVisiCombo.currentText() == "Yes"
            )
            newLabel.labelDefs()
            newLabel.setOpacity(1)
            self.undoStack.push(us.addDeleteShapeUndo(self, newLabel, item))
        else:
            self.addItem(item)

    def updateSymbolPin(self, item):
        queryDlg = pdlg.pinPropertyDialog(self.editorWindow)
        queryDlg.pinName.setText(str(item.pinName))
        queryDlg.pinType.setCurrentText(item.pinType)
        queryDlg.pinDir.setCurrentText(item.pinDir)
        sceneStartPoint = item.mapToScene(item.start).toPoint()
        queryDlg.pinXLine.setText(str(sceneStartPoint.x()))
        queryDlg.pinYLine.setText(str(sceneStartPoint.y()))
        if queryDlg.exec() == QDialog.Accepted:
            sceneStartX = int(float(queryDlg.pinXLine.text()))
            sceneStartY = int(float(queryDlg.pinYLine.text()))
            start = self.snapToGrid(
                QPoint(sceneStartX, sceneStartY), self.snapTuple
            )
            pinName = queryDlg.pinName.text()
            pinType = queryDlg.pinType.currentText()
            pinDir = queryDlg.pinDir.currentText()
            newPin = shp.symbolPin(start, pinName, pinDir, pinType)
            self.undoStack.push(us.addDeleteShapeUndo(self, newPin, item))

    def updateSymbolPolygon(self, item):
        pointsTupleList = [(point.x(), point.y()) for point in item.points]
        queryDlg = pdlg.symbolPolygonProperties(
            self.editorWindow, pointsTupleList
        )
        if queryDlg.exec() == QDialog.Accepted:
            tempPoints = []
            for i in range(queryDlg.tableWidget.rowCount()):
                xcoor = queryDlg.tableWidget.item(i, 1).text()
                ycoor = queryDlg.tableWidget.item(i, 2).text()
                if xcoor != "" and ycoor != "":
                    tempPoints.append(QPointF(float(xcoor), float(ycoor)))
            newPolygon = shp.symbolPolygon(tempPoints)
            self.undoStack.push(us.addDeleteShapeUndo(self, newPolygon, item))

    def loadDesign(self, filePathObj: pathlib.Path) -> None:
        try:
            with filePathObj.open("r") as file:
                decodedData = json.load(file)
            self.blockSignals(True)
            with self.measureDuration():
                viewDict, gridSettings, *itemData = decodedData
                # if viewDict.get("viewType") != "symbol":
                #     self.logger.error("Not a symbol file!")
                #     return
                self.configureGridSettings(gridSettings)
                self.attributeList = []
                self.createSymbolItems(itemData)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            self.logger.error(f"File error while loading symbol: {e}")
            self.attributeList = []
            self.clear()
            return
        except KeyError as e:
            self.logger.error(f"Invalid symbol format - missing key: {e}")
            self.attributeList = []
            self.clear()
            return
        except Exception as e:
            self.logger.error(f"Unexpected error loading symbol: {e}")
            self.attributeList = []
            self.clear()
            return
        finally:
            self.blockSignals(False)
            self.update()


        # try:
        #     # Load file contents
        #     with open(self.editorWindow.file) as file:
        #         itemsList = json.load(file)
        #
        #     # Disable updates
        #     self.blockSignals(True)
        #
        #     # Fast grid setup
        #     if (len(itemsList) > 1) and (itemsList[1].get("snapGrid") is not None):
        #         self.snapGrid = itemsList[1].get("snapGrid")
        #         self.snapTuple = (self.snapGrid, self.snapGrid)
        #         self.snapDistance = self.snapGrid << 1
        #
        #
        #     # Create factory once
        #     factory = lj.symbolItems(self)
        #
        #     # Reset attribute list
        #     self.attributeList = []
        #
        #     # Process items directly
        #     for item in itemsList[2:]:
        #         if not item:
        #             continue
        #
        #         itemType = item.get("type")
        #
        #         if itemType in self.symbolShapes:
        #             shape = factory.create(item)
        #             if isinstance(shape, lbl.symbolLabel):
        #                 shape.setOpacity(1)
        #             self.addItem(shape)
        #         elif itemType == "attr":
        #             self.attributeList.append(
        #                 factory.createSymbolAttribute(item)
        #             )
        #
        # except Exception as e:
        #     self.logger.error(f"Load failed: {e}")
        #     # Optionally reset scene state
        #     self.clear()
        #     self.attributeList = []
        #     raise

        # finally:
        #     self.blockSignals(False)
        #     self.update()


    def createSymbolItems(self, itemsList: List[Dict]):
        factory = lj.symbolItems(self)
        for itemDict in itemsList:
            if itemDict:
                itemType = itemDict.get("type", None)
                if itemType in self.symbolShapes:
                    itemShape = factory.create(itemDict)
                    if itemType == "label":
                        itemShape.setOpacity(1)
                    self.addItem(itemShape)
                    continue
                if itemType == "attr":
                    self.attributeList.append(factory.createSymbolAttribute(itemDict))

    def saveSymbolCell(self, fileName: pathlib.Path) -> bool:
        """
        Save symbol cell to file.

        Args:
            fileName: Path to save the symbol cell

        Returns:
            bool: True if save successful, False otherwise
        """

        try:
            # Filter items and process labels in one pass
            sceneItems = [item for item in self.items() 
                         if isinstance(item, shp.symbolPolygon) or item.parentItem() is None]
            # Build save data
            save_data = [
                {"viewType": "symbol"},
                {"snapGrid": self.snapTuple},
                *sceneItems,
                *getattr(self, "attributeList", [])
            ]

            # Write to file
            with fileName.open("w") as f:
                json.dump(save_data, f, cls=symenc.symbolEncoder, indent=4)

            self.undoStack.clear()
            return True

        except Exception as e:
            self.logger.error(f"Symbol save error: {e}")
            return False

    def viewSymbolProperties(self):
        """
        View symbol properties dialog.
        """
        # copy symbol attribute list to another list by deepcopy to be safe
        attributeListCopy = deepcopy(self.attributeList)
        symbolPropDialogue = pdlg.symbolLabelsDialogue(
            self.editorWindow, self.items(), attributeListCopy
        )
        if symbolPropDialogue.exec() == QDialog.Accepted:
            for i, item in enumerate(symbolPropDialogue.labelItemList):
                # label name is not changed.
                item.labelHeight = int(
                    float(symbolPropDialogue.labelHeightList[i].text())
                )
                item.labelAlign = symbolPropDialogue.labelAlignmentList[i].currentText()
                item.labelOrient = symbolPropDialogue.labelOrientationList[
                    i
                ].currentText()
                item.labelUse = symbolPropDialogue.labelUseList[i].currentText()
                item.labelType = symbolPropDialogue.labelTypeList[i].currentText()
                item.update(item.boundingRect())
            # create an empty attribute list. If the dialog is OK, the local attribute list
            # will be copied to the symbol attribute list.
            localAttributeList = []
            for i, item in enumerate(symbolPropDialogue.attributeNameList):
                if item.text().strip() != "":
                    localAttributeList.append(
                        symenc.symbolAttribute(
                            item.text(), symbolPropDialogue.attributeDefList[i].text()
                        )
                    )
                self.attributeList = deepcopy(localAttributeList)

    def copySelectedItems(self):
        copyOffset = QPoint(2 * self.snapTuple[0], 2 * self.snapTuple[1])

        def apply_offset(point):
            return point + copyOffset

        def create_label(item: lbl.symbolLabel):
            newLabel = lbl.symbolLabel(
                apply_offset(item.start),
                item.labelDefinition,
                item.labelType,
                item.labelHeight,
                item.labelAlign,
                item.labelOrient,
                item.labelUse,
            )
            newLabel.setVisible(True)
            newLabel.setOpacity(1)
            if newLabel.labelType == lbl.symbolLabel.labelTypes[1]:
                newLabel.labelDefs()
            return newLabel

        def create_pin(item: shp.symbolPin):
            return shp.symbolPin(
                apply_offset(item.start),
                item.pinName,
                item.pinDir,
                item.pinType,
            )

        def create_line(item: shp.symbolLine):
            return shp.symbolLine(
                apply_offset(item.start),
                apply_offset(item.end),
            )

        def create_arc(item: shp.symbolArc):
            return shp.symbolArc(
                apply_offset(item.start),
                apply_offset(item.end),
            )

        def create_polygon(item: shp.symbolPolygon):
            return shp.symbolPolygon(
                [apply_offset(point) for point in item.points]
            )

        def create_circle(item: shp.symbolCircle):
            return shp.symbolCircle(
                apply_offset(item.centre),
                apply_offset(item.end),
            )

        # Dictionary mapping types to their creation functions
        creators = {
            lbl.symbolLabel: create_label,
            shp.symbolPin: create_pin,
            shp.symbolLine: create_line,
            shp.symbolArc: create_arc,
            shp.symbolPolygon: create_polygon,
            shp.symbolCircle: create_circle,
        }

        for item in self.selectedItems():
            itemType = type(item)
            if itemType in creators:
                new_item = creators[itemType](item)
                self.addUndoStack(new_item)

