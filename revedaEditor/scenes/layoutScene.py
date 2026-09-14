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

import inspect
import json
import pathlib
# import time
from typing import Any, Dict, List, Union, Optional

import orjson
import shiboken6
from PySide6.QtCore import QLineF, QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QPen,
    QTransform,
)
from PySide6.QtWidgets import (
    QCompleter,
    QDialog,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsSceneMouseEvent,
)

import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.backend.libraryMethods as libm
import revedaEditor.backend.libraryModelView as lmview
import revedaEditor.backend.undoStack as us
import revedaEditor.common.layoutShapes as lshp  # import layout shapes
import revedaEditor.fileio.exportGDS as gdse
import revedaEditor.fileio.layoutEncoder as layenc
import revedaEditor.fileio.loadJSON as lj
import revedaEditor.fileio.schemaValidation as sv
import revedaEditor.gui.editFunctions as edf
import revedaEditor.gui.fileDialogues as fd
import revedaEditor.gui.layoutDialogues as ldlg
import revedaEditor.gui.propertyDialogues as pdlg
from revedaEditor.backend.pdkLoader import importPDKModule
from revedaEditor.gui.alignItems import alignItemsDialogue, alignToLine
from revedaEditor.scenes.editorScene import editorScene

fabproc = importPDKModule("process")
laylyr = importPDKModule("layoutLayers")
schlyr = importPDKModule("schLayers")
pcells = importPDKModule("pcells")


class layoutScene(editorScene):
    LAYOUT_SHAPES = (
        lshp.layoutRect,
        lshp.layoutPin,
        lshp.layoutLabel,
        lshp.layoutPath,
        lshp.layoutPolygon,
        lshp.layoutViaArray,
        lshp.layoutInstance,
        lshp.layoutPcell,
        lshp.layoutRuler,
    )
    # Object filter categories shown below the LSW, mapped to the layout
    # shape classes they control. Pin name labels are filtered with pins.
    objectFilterClasses = {
        "Instances": (lshp.layoutInstance,),
        "Pins": (lshp.layoutPin,),
        "Vias": (lshp.layoutVia, lshp.layoutViaArray),
        "Labels": (lshp.layoutLabel,),
        "Paths": (lshp.layoutPath,),
        "Shapes": (lshp.layoutRect, lshp.layoutPolygon),
    }
    alignLineFinished = Signal(lshp.alignLine)

    def __init__(self, parent):
        super().__init__(parent)
        self.selectEdLayer = laylyr.pdkAllLayers[0] if laylyr else None
        # draw modes
        self.editModes = ddef.layoutModes(
            selectItem=False,
            deleteItem=False,
            moveItem=False,
            constrainedMoveItem=False,
            copyItem=False,
            rotateItem=False,
            changeOrigin=False,
            panView=False,
            zoomView=False,
            drawPath=False,
            drawPin=False,
            drawArc=False,
            drawPolygon=False,
            addLabel=False,
            addVia=False,
            drawRect=False,
            drawLine=False,
            drawCircle=False,
            drawRuler=False,
            stretchItem=False,
            addInstance=False,
            cutShape=False,
            alignItems=False,
        )
        self.editModes.setMode("selectItem")
        self.selectModes = ddef.layoutSelectModes(
            selectAll=True,
            selectPath=False,
            selectInstance=False,
            selectVia=False,
            selectPin=False,
            selectLabel=False,
            selectText=False,
        )
        # Per-category object filter state, toggled from the objects panel.
        self.objectVisibility = {name: True for name in self.objectFilterClasses}
        self.objectSelectability = {name: True for name in self.objectFilterClasses}
        # Merge with parent's messages
        self.messages.update({
            "drawPath": "Draw Path",
            "drawPin": "Draw Pin",
            "drawArc": "Draw Arc",
            "drawPolygon": "Draw Polygon",
            "addLabel": "Add Label",
            "addVia": "Add Via",
            "drawRect": "Draw Rect",
            "drawLine": "Draw Line",
            "drawCircle": "Draw Circle",
            "drawRuler": "Draw Ruler",
            "addInstance": "Add Instance",
            "cutShape": "Cut Shape",
        })
        self.newInstance = None
        self.layoutInstanceTuple = None
        self._scale = fabproc.dbu if fabproc else 1000
        self.itemCounter = 0
        self.newPath = None
        self.stretchPathItem = None
        defaultPathDefTuple = fabproc.processPaths[0] if fabproc else None
        self.newPathTuple = ddef.layoutPathTuple(
            "",
            defaultPathDefTuple.layer,
            0,
            defaultPathDefTuple.minWidth,
            int(defaultPathDefTuple.minWidth / 2),
            int(defaultPathDefTuple.minWidth / 2),
        )
        self.draftLine = None
        self.m45Rotate = QTransform().rotate(-45)
        self._newPin = None
        self.newPinTuple = None
        self.newLabelTuple = None
        self.newLabel = None
        self._labelPlacementMarker = None
        self.newRect = None
        self.newPolygon = None
        self.arrayViaTuple = None
        self._singleVia = None
        self.arrayVia = None
        self.polygonGuideLine = None
        self._newRuler = None
        self._newCutLine = None
        self._selectionRectItem = None
        self.rulersSet = set()
        self.rulerFont = self.setRulerFont(12 * fabproc.dbu)
        self.rulerFont.setKerning(False)
        self.rulerTickGap = fabproc.dbu
        self.rulerTickLength = 10
        self.rulerWidth = 2
        self.setItemIndexMethod(QGraphicsScene.ItemIndexMethod.BspTreeIndex)
        self._draftPen = QPen(Qt.PenStyle.DashLine)
        self._draftPen.setColor(QColor(0, 150, 0))
        self._draftPen.setWidth(2)
        self._draftPen.setCosmetic(True)
        self.setMinimumRenderSize(0.2)
        self.newAlignLine = None
        self.alignLineFinished.connect(alignToLine)

    @property
    def drawMode(self):
        return any(
            (
                self.editModes.drawPath,
                self.editModes.drawPin,
                self.editModes.drawArc,
                self.editModes.drawPolygon,
                self.editModes.drawRect,
                self.editModes.drawCircle,
                self.editModes.drawRuler,
            )
        )

    # Order of drawing
    # 1. Rect
    # 2. Path
    # 3. Pin
    # 4. Label
    # 5. Via/Contact
    # 6. Polygon
    # 7. Add instance
    # 8. select item/s
    # 9. rotate item/s

    @staticmethod
    def toLayoutCoord(point: QPoint) -> QPointF:
        """
        Converts a point in scene coordinates to layout coordinates by dividing it to
        fabproc.dbu.
        """
        scale = fabproc.dbu if fabproc else 1000
        if isinstance(point, QPointF):
            returnPoint = point / scale
        elif isinstance(point, QPoint):
            returnPoint = point.toPointF() / scale
        else:
            returnPoint = QPointF(0.0, 0.0)
        return returnPoint

    @staticmethod
    def toLayoutDistance(distance: float) -> float:
        """
        Converts a scalar distance in scene units to layout units by dividing it
        by fabproc.dbu.
        """
        scale = fabproc.dbu if fabproc else 1000
        return distance / scale

    @staticmethod
    def toSceneCoord(point: Union[QPoint | QPointF]) -> QPoint:
        """
        Converts a point in layout coordinates to scene coordinates by multiplying it with
        fabproc.dbu.
        """
        point *= fabproc.dbu
        if isinstance(point, QPointF):
            return QPoint(round(point.x()), round(point.y()))
        return point

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:

        self.mousePressLoc = self.snapToGrid(event.scenePos().toPoint())
        if self.editModes.cutShape:
            self.startCutLine()
        super().mousePressEvent(event)

    def _updateLabelPlacementMarker(self, point: QPoint) -> None:
        if self._labelPlacementMarker is not None:
            if not all(shiboken6.isValid(line) for line in self._labelPlacementMarker):
                self._labelPlacementMarker = None
        scale = abs(self.views()[0].transform().m11()) if self.views() else 1.0
        halfSize = 6.0 / (scale or 1.0)
        if self._labelPlacementMarker is None:
            pen = QPen(QColor(255, 255, 0), 0)
            pen.setCosmetic(True)
            self._labelPlacementMarker = (QGraphicsLineItem(), QGraphicsLineItem())
            for markerLine in self._labelPlacementMarker:
                markerLine.setPen(pen)
                markerLine.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                markerLine.setZValue(1e9)
                self.addItem(markerLine)
        horizontal, vertical = self._labelPlacementMarker
        horizontal.setLine(QLineF(
            QPointF(point.x() - halfSize, point.y()),
            QPointF(point.x() + halfSize, point.y()),
        ))
        vertical.setLine(QLineF(
            QPointF(point.x(), point.y() - halfSize),
            QPointF(point.x(), point.y() + halfSize),
        ))

    def _removeLabelPlacementMarker(self) -> None:
        if self._labelPlacementMarker is not None:
            for markerLine in self._labelPlacementMarker:
                if shiboken6.isValid(markerLine):
                    self.removeItem(markerLine)
            self._labelPlacementMarker = None

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """
        Handle the mouse move event.

        Args:
            mouse_event (QGraphicsSceneMouseEvent): The mouse event object.

        Returns:
            None
        """
        # Get the current mouse position
        self.mouseMoveLoc = self.snapToGrid(event.scenePos().toPoint())
        # Call the parentW class's mouseMoveEvent method
        super().mouseMoveEvent(event)

        # Handle drawing path mode
        if self.editModes.drawPath and self.newPath is not None:
            self.newPath.draftLine = QLineF(
                self.newPath.draftLine.p1(), self.mouseMoveLoc
            )
        elif (self.editModes.drawRect or self.editModes.cutShape) and self.newRect:
            self.newRect.end = self.mouseMoveLoc
        # Handle drawing pin mode with no new pin
        elif self.editModes.drawPin:
            if self._newPin is not None:
                self._newPin.end = self.mouseMoveLoc
        elif self.editModes.addLabel:
            if self.newLabel is not None:
                self.newLabel.start = self.mouseMoveLoc
                self.newLabel.update()
            else:
                self._updateLabelPlacementMarker(self.mouseMoveLoc)
        elif self.editModes.addInstance and self.newInstance is not None:
            self.newInstance.setPos(
                self.snapToGrid(self.mouseMoveLoc - self.newInstance.start))
        # Handle drawing polygon mode
        elif self.editModes.drawPolygon and self.newPolygon is not None:
            self.polygonGuideLine.setLine(
                QLineF(self.newPolygon.points[-1], self.mouseMoveLoc)
            )
        elif self.editModes.drawRuler and self._newRuler is not None:
            self._newRuler.draftLine = QLineF(
                self._newRuler.draftLine.p1(), self.mouseMoveLoc
            )
        # Handle adding via mode with array via tuple
        elif self.editModes.addVia and self.arrayVia is not None:
            self.arrayVia.setPos(self.mouseMoveLoc - self.arrayVia.start)

        elif self.editModes.stretchItem and self.stretchPathItem is not None:
            self.stretchPathItem.draftLine = QLineF(
                self.stretchPathItem.draftLine.p1(), self.mouseMoveLoc
            )
        elif self.editModes.cutShape and self._newCutLine is not None:
            self._newCutLine.draftLine = QLineF(
                self._newCutLine.draftLine.p1(), self.mouseMoveLoc
            )
        elif self.newAlignLine and self.editModes.alignItems:
            self.newAlignLine.draftLine = QLineF(
                self.newAlignLine.draftLine.p1(), self.mouseMoveLoc
            )

        # Calculate the cursor position in layout units
        cursorPosition = self.toLayoutCoord(self.mouseMoveLoc - self.origin)

        # Show the cursor position in the status line
        self.statusLine.showMessage(
            f"Cursor Position: ({cursorPosition.x():.3f}u, {cursorPosition.y():.3f}u)"
        )
        self.messageLine.setText(self.messages.get(self.editModes.mode(), self.editModes.mode()))

    # def mouseReleaseEvent(self, mouse_event: QGraphicsSceneMouseEvent) -> None:
    #     super().mouseReleaseEvent(mouse_event)
    #     if mouse_event.button() == Qt.LeftButton:
    #         self.mouseReleaseLoc = mouse_event.scenePos().toPoint()
    #         self._handleMouseRelease(self.mouseReleaseLoc, mouse_event.button())

    def _handleMouseRelease(self, mousePos: QPoint, button: Qt.MouseButton) -> None:
        try:
            if self.editModes.drawPath:
                self.drawLayoutPath()
            elif self.editModes.drawRect:
                self.drawLayoutRect()
            elif self.editModes.drawPin:
                self.drawLayoutPin()
            elif self.editModes.addLabel:
                self.addLayoutLabel()
            elif self.editModes.addInstance:
                self.addLayoutInstance()
            elif self.editModes.drawPolygon:
                self.drawLayoutPolygon()
            elif self.editModes.drawRuler:
                self.drawLayoutRuler()
            elif self.editModes.cutShape:
                self.finishCutLine()
            elif self.editModes.addVia:
                self.addLayoutViaArray()
            elif self.editModes.changeOrigin:
                self.origin: QPoint = mousePos
            elif self.editModes.alignItems:
                self._handleAlignItemLine(mousePos)
            elif self.editModes.rotateItem:
                self.editorWindow.messageLine.setText("Rotate item")
                if self.selectedItems():
                    self.rotateSelectedItems(mousePos)
        except Exception as e:
            self.logger.error(f"mouse release error: {e}")

    def addLayoutViaArray(self):
        if self.arrayVia is not None:
            # self.arrayViaTuple = None
            self.arrayVia = None


        singleVia = lshp.layoutVia(
            QPoint(0, 0),
            *self.arrayViaTuple.singleViaTuple,
        )
        self.arrayVia = lshp.layoutViaArray(
            QPoint(0, 0),
            singleVia,
            self.arrayViaTuple.xs,
            self.arrayViaTuple.ys,
            self.arrayViaTuple.xnum,
            self.arrayViaTuple.ynum,
        )
        self.arrayVia.setPos(self.mouseReleaseLoc)
        self.addUndoStack(self.arrayVia)

    def snapToClosestEdge(
        self,
        point,
        ruler: Optional[lshp.layoutRuler] = None,
        snapScreenPx: float = 20.0,
    ) -> QPointF:
        pointF = QPointF(point)
        # Convert screen-pixel snap radius to scene units using current view scale
        views = self.views()
        if views:
            scale = views[0].transform().m11()
            if scale > 0:
                maxDistance = snapScreenPx / scale
            else:
                maxDistance = snapScreenPx
        else:
            maxDistance = snapScreenPx

        if ruler is not None:
            snapped = ruler.snapPointToClosestEdge(pointF, maxDistance)
            if snapped != pointF:
                return snapped
        searchRect = QRectF(
            pointF.x() - maxDistance,
            pointF.y() - maxDistance,
            2 * maxDistance,
            2 * maxDistance,
        )
        items = self.items(searchRect)
        bestDist = maxDistance
        closestPoint = pointF
        for item in items:
            if isinstance(item, lshp.layoutRuler) or item is ruler or getattr(item, "drcError", False):
                continue
            edges = lshp.layoutRuler._extractItemEdges(item)
            for p1, p2 in edges:
                ptOnEdge = lshp.layoutRuler._closestPointOnSegment(pointF, p1, p2)
                dist = QLineF(pointF, ptOnEdge).length()
                if dist < bestDist:
                    bestDist = dist
                    closestPoint = ptOnEdge
        return closestPoint

    def drawLayoutRuler(self):
        if self._newRuler:
            # Snap the endpoint before finalizing
            endPt = self.snapToClosestEdge(
                self.mouseReleaseLoc, ruler=self._newRuler
            )
            self._newRuler.draftLine = QLineF(
                self._newRuler.draftLine.p1(), endPt
            )
            if self._newRuler.draftLine.isNull():
                self.undoStack.removeLastCommand()
            self._newRuler = None
        else:
            startPt = self.snapToClosestEdge(self.mouseReleaseLoc)
            self._newRuler = lshp.layoutRuler(
                QLineF(startPt, startPt),
                width=self.rulerWidth,
                tickGap=self.rulerTickGap,
                tickLength=self.rulerTickLength,
                tickFont=self.rulerFont,
            )
            self.addUndoStack(self._newRuler)

    def finishCutLine(self):
        if self._newCutLine is None:
            return
        if self._newCutLine.draftLine.isNull():
            self.undoStack.removeLastCommand()
        else:
            if self.selectedItemsSet:
                line = QLineF(*self._newCutLine.sceneEndPoints)
                for item in self.selectedItemsSet:
                    if isinstance(item, lshp.layoutRect):
                        self._splitRect(item, line)
                    elif isinstance(item, lshp.layoutPath):
                        self._splitPath(item, line)
                    elif isinstance(item, lshp.layoutPolygon):
                        self._splitPolygon(item, line)
                self.removeItem(self._newCutLine)
        self._newCutLine = None

    def _splitPolygonalShape(self, item, line: QLineF):
        """Split a polygonal shape (rectangle or polygon) at intersections with the cut line."""
        # Get points based on item type
        if hasattr(item, 'rect'):  # Rectangle
            rect = item.rect
            points = [
                rect.topLeft(),
                rect.topRight(),
                rect.bottomRight(),
                rect.bottomLeft(),
            ]
            shape_name = "Rectangle"
        else:  # Polygon
            points = item.points
            shape_name = "Polygon"

        intersections = []

        # Find all intersection points with shape edges
        for i in range(len(points)):
            edge = QLineF(points[i], points[(i + 1) % len(points)])
            result = line.intersects(edge)
            if result[0] == QLineF.IntersectionType.BoundedIntersection:
                intersections.append((i, result[1]))

        # Split shape if we have exactly 2 intersections
        if len(intersections) == 2:
            idx1, p1 = intersections[0]
            idx2, p2 = intersections[1]

            # Create two new polygons using list slicing
            poly1_points = [p1] + points[idx1 + 1:idx2 + 1] + [p2]
            poly2_points = [p2] + points[idx2 + 1:] + points[:idx1 + 1] + [p1]

            poly1 = lshp.layoutPolygon(poly1_points, item.layer)
            poly2 = lshp.layoutPolygon(poly2_points, item.layer)

            self.undoStack.beginMacro(f"Split {shape_name}")
            self.deleteUndoStack(item)
            self.addUndoStack(poly1)
            self.addUndoStack(poly2)
            self.undoStack.endMacro()

    def _splitRect(self, item, line: QLineF):
        """Split a rectangle - delegates to unified polygonal shape splitter."""
        self._splitPolygonalShape(item, line)

    def _splitPolygon(self, item, line):
        """Split a polygon - delegates to unified polygonal shape splitter."""
        self._splitPolygonalShape(item, line)

    def startCutLine(self):
        if self.selectedItemsSet:
            self._newCutLine = lshp.layoutLine(
                QLineF(self.mousePressLoc, self.mousePressLoc), self.snapGrid, 1
            )
            self.addUndoStack(self._newCutLine)
        else:
            self.editorWindow.messageLine.setText("No selected items")

    def _handleAlignItemLine(self, eventLoc: QPoint) -> None:
        if self.newAlignLine is None:
            from PySide6.QtWidgets import (
                QApplication,
            )

            alignDlg = [
                w
                for w in QApplication.topLevelWidgets()
                if isinstance(w, alignItemsDialogue)
                   and w.isVisible()
                   and w.scene == self
            ][0]
            if alignDlg.horizontalAlignButton.isChecked():
                self.newAlignLine = lshp.alignLine(
                    QLineF(eventLoc, eventLoc), 1, 0
                )  # horizontal
            else:
                self.newAlignLine = lshp.alignLine(QLineF(eventLoc, eventLoc), 1, 1)
            self.addUndoStack(self.newAlignLine)
        else:
            self.newAlignLine.draftLine = QLineF(
                self.newAlignLine.draftLine.p1(), eventLoc
            )
            self.alignLineFinished.emit(self.newAlignLine)
            # self.newAlignLine = None
            self.editModes.setMode("selectItem")

    def drawLayoutPolygon(self):
        if self.newPolygon is None:
            # Create a new polygon
            self.newPolygon = lshp.layoutPolygon(
                [self.mouseReleaseLoc, self.mouseReleaseLoc],
                self.selectEdLayer,
            )
            self.addUndoStack(self.newPolygon)
            # Create a guide line for the polygon
            self.polygonGuideLine = QGraphicsLineItem(
                QLineF(self.newPolygon.points[-2], self.newPolygon.points[-1])
            )
            self.polygonGuideLine.setPen(
                QPen(QColor(255, 255, 0), 0.1 * fabproc.dbu, Qt.PenStyle.DashLine)
            )
            self.polygonGuideLine.pen().setCosmetic(False)
            self.addUndoStack(self.polygonGuideLine)
        else:
            self.newPolygon.addPoint(self.mouseReleaseLoc)

    def addLayoutInstance(self):
        if self.newInstance is not None:
            self.newInstance = None
        if self.layoutInstanceTuple:
            self.newInstance = self.addNewInstance()
            self.addUndoStack(self.newInstance)
            self.newInstance.setPos(
                self.snapToGrid(self.mouseReleaseLoc - self.newInstance.start))

    def addLayoutLabel(self):
        if self.newLabel is not None:
            self.newLabelTuple = None
            self.newLabel.setPlacementMarkerVisible(False)
            self.newLabel = None
        if self.newLabelTuple is not None:
            self._removeLabelPlacementMarker()
            self.newLabel = lshp.layoutLabel(self.mouseReleaseLoc, *self.newLabelTuple)
            self.newLabel.setPlacementMarkerVisible(True)
            self.addUndoStack(self.newLabel)

    def drawLayoutPin(self):
        self.editorWindow.messageLine.setText("Pin mode.")
        # Create a new pin
        if self._newPin:
            if self._newPin.rect.isNull():
                self.undoStack.removeLastCommand()
            else:
                self.editModes.setMode("addLabel")
                self._removeLabelPlacementMarker()
                self.newLabel = lshp.layoutLabel(
                    self.mouseReleaseLoc, *self.newLabelTuple
                )
                self.newLabel.setPlacementMarkerVisible(True)
                self._newPin.label = self.newLabel
                self.addUndoStack(self.newLabel)
            self._newPin = None
        self._newPin = lshp.layoutPin(
            self.mouseReleaseLoc, self.mouseReleaseLoc, *self.newPinTuple
        )
        self.addUndoStack(self._newPin)

    def drawLayoutRect(self):
        self.editorWindow.messageLine.setText("Rectangle mode.")
        # Create a new rectangle
        if self.newRect:
            if self.newRect.rect.isNull():
                self.removeItem(self.newRect)
                self.undoStack.removeLastCommand()
            self.newRect = None
        self.newRect = lshp.layoutRect(
            self.mouseReleaseLoc,
            self.mouseReleaseLoc,
            self.selectEdLayer,
        )
        self.addUndoStack(self.newRect)

    def drawLayoutPath(self):
        self.editorWindow.messageLine.setText("Path mode")
        startPoint = self.mousePressLoc
        if self.newPath:
            # Commit the segment end at the snapped release point so the path
            # end lands on the snap grid, then chain the next segment from it.
            self.newPath.draftLine = QLineF(
                self.newPath.draftLine.p1(), self.mouseReleaseLoc
            )
            if self.newPath.draftLine.isNull():
                self.undoStack.removeLastCommand()
            else:
                startPoint = self.newPath.sceneEndPoints[1]
            self.newPath = None

            # Create a new path
        self.newPath = lshp.layoutPath(
            QLineF(startPoint, startPoint),
            self.newPathTuple.layer,
            self.newPathTuple.width,
            int(self.newPathTuple.startExtend),
            int(self.newPathTuple.endExtend),
            self.newPathTuple.pathMode,
        )
        self.newPath.name = self.newPathTuple.name
        self.addUndoStack(self.newPath)

    def addNewInstance(self) -> Union[lshp.layoutInstance, lshp.layoutPcell]:
        newInstance = self.instLayout(self.layoutInstanceTuple)
        if isinstance(newInstance, pcells.baseCell):
            dlg = ldlg.layoutInstanceDialogue(self.editorWindow)
            dlg.instanceLibName.setText(newInstance.libraryName)
            dlg.instanceCellName.setText(newInstance.cellName)
            dlg.instanceViewName.setText(newInstance.viewName)
            lineEditDict = self.extractPcellInstanceParameters(newInstance)
            if lineEditDict:
                dlg.pcellParamsGroup.show()
                for key, value in lineEditDict.items():
                    dlg.pcellParamsLayout.addRow(key, value)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                instanceValuesDict = {}
                for key, value in lineEditDict.items():
                    instanceValuesDict[key] = value.text()
                if instanceValuesDict:
                    newInstance(*instanceValuesDict.values())
        self.layoutInstanceTuple = None
        return newInstance

    def instLayout(
            self, layoutInstanceTuple: ddef.viewItemTuple
    ) -> Union[lshp.layoutInstance, lshp.layoutPcell]:
        """Read a layout file and create layoutShape objects from it."""
        try:
            with layoutInstanceTuple.viewItem.viewPath.open("rb") as temp:
                decodedData = orjson.loads(temp.read())

            # Common instance setup
            def setup_instance(instance):
                instance.libraryName = layoutInstanceTuple.libraryItem.libraryName
                instance.cellName = layoutInstanceTuple.cellItem.cellName
                instance.viewName = layoutInstanceTuple.viewItem.viewName
                self.itemCounter += 1
                instance.counter = self.itemCounter
                instance.instanceName = f"I{self.itemCounter}"
                return instance

            viewType = layoutInstanceTuple.viewItem.viewType

            if (
                    viewType == "layout"
                    and decodedData
                    and decodedData[0].get("viewType") == "layout"
            ):
                factory_create = lj.layoutItems(self).create
                # valid_items = filter(
                #     lambda item: isinstance(item, dict) and item.get(
                #         "type") in self.LAYOUT_SHAPES, decodedData[2:])
                instanceShapes = [
                    shape
                    for item in decodedData[2:]
                    if (shape := factory_create(item)) is not None
                ]
                return setup_instance(lshp.layoutInstance(instanceShapes))

            elif (
                    viewType == "pcell"
                    and len(decodedData) > 1
                    and decodedData[0].get("cellView") == "pcell"
            ):
                ref_name = decodedData[1]['reference']
                if not isinstance(ref_name, str) or not ref_name.isidentifier():
                    self.logger.error(f"Invalid pcell reference name: {ref_name!r}")
                    return None
                pcell_cls = getattr(pcells, ref_name, None)
                if pcell_cls is None or not (
                    isinstance(pcell_cls, type) and issubclass(pcell_cls, pcells.baseCell)
                ):
                    self.logger.error(f"Unknown or invalid pcell reference: {ref_name!r}")
                    return None
                pcellInstance = pcell_cls()
                return setup_instance(pcellInstance)
            else:
                self.logger.error(
                    f"Invalid file type for instance. Expected viewType '{viewType}' "
                    f"but got {decodedData[0].get('viewType') if decodedData else 'empty file'} "
                    f"from {layoutInstanceTuple.viewItem.viewPath}"
                )
                return None

        except orjson.JSONDecodeError:
            self.logger.error(f"Invalid file format for instance: {layoutInstanceTuple.viewItem.viewPath}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error loading instance from {layoutInstanceTuple.viewItem.viewPath}: {e}")
            return None

    def findScenelayoutCellSet(self) -> set[lshp.layoutInstance]:
        """
        Find all the symbols on the scene as a set.
        """
        return {item for item in self.items() if isinstance(item, lshp.layoutInstance)}

    def _filterBySelectModes(self, items: set) -> set:
        """Filter rubber-band selected items by the active selection filter."""
        return {
            item
            for item in items
            if item.isEnabled()
               and not getattr(item, "drcError", False)
               and (self.selectModes.selectAll or self._itemPassesFilter(item))
        }

    def _itemPassesFilter(self, item) -> bool:
        """Check if an item passes the current selection filter."""
        if self.selectModes.selectInstance and isinstance(item, lshp.layoutInstance):
            return True
        if self.selectModes.selectPath and isinstance(item, lshp.layoutPath):
            return True
        if self.selectModes.selectVia and isinstance(item, lshp.layoutViaArray):
            return True
        if self.selectModes.selectPin and isinstance(item, lshp.layoutPin):
            return True
        if self.selectModes.selectLabel and isinstance(item, lshp.layoutLabel):
            return True
        return False

    def pinLabelItems(self) -> set:
        """Labels attached to pins are filtered with the Pins category."""
        return {
            item.label
            for item in self.items()
            if isinstance(item, lshp.layoutPin) and item.label is not None
        }

    def objectCategory(
        self, item: QGraphicsItem, pinLabels: Optional[set] = None
    ) -> Optional[str]:
        """Object filter category for a top-level scene item, or None."""
        if isinstance(item, lshp.layoutLabel):
            if pinLabels is None:
                pinLabels = self.pinLabelItems()
            return "Pins" if item in pinLabels else "Labels"
        for category, classes in self.objectFilterClasses.items():
            if isinstance(item, classes):
                return category
        return None

    def objectVisible(
        self, item: QGraphicsItem, pinLabels: Optional[set] = None
    ) -> bool:
        """Object-filter visibility for an item. Only top-level items are
        filtered; instance/via children follow their parent item."""
        if item.parentItem() is not None:
            return True
        return self.objectVisibility.get(self.objectCategory(item, pinLabels), True)

    def objectSelectable(
        self, item: QGraphicsItem, pinLabels: Optional[set] = None
    ) -> bool:
        """Object-filter selectability for an item (top-level items only)."""
        if item.parentItem() is not None:
            return True
        return self.objectSelectability.get(self.objectCategory(item, pinLabels), True)

    def setObjectClassVisible(self, category: str, visible: bool) -> None:
        if category not in self.objectVisibility:
            return
        self.objectVisibility[category] = visible
        pinLabels = self.pinLabelItems()
        for item in self.items():
            if (
                item.parentItem() is None
                and self.objectCategory(item, pinLabels) == category
            ):
                self._applyItemObjectState(item, category)

    def setObjectClassSelectable(self, category: str, selectable: bool) -> None:
        if category not in self.objectSelectability:
            return
        self.objectSelectability[category] = selectable
        pinLabels = self.pinLabelItems()
        for item in self.items():
            if (
                item.parentItem() is None
                and self.objectCategory(item, pinLabels) == category
            ):
                self._applyItemObjectState(item, category)

    def _applyItemObjectState(self, item: QGraphicsItem, category: str) -> None:
        """Combine object-filter state with the item's layer state and apply
        the result to the item."""
        visible = self.objectVisibility[category]
        layer = getattr(item, "layer", None)
        if hasattr(item, "usesLayer"):
            # Composite items (vias) honour per-layer visibility inside paint;
            # the object filter hides the whole item instead.
            item.setVisible(visible)
        else:
            item.setVisible(visible and getattr(layer, "visible", True))
        item.setEnabled(
            self.objectSelectability[category] and getattr(layer, "selectable", True)
        )
        if not (visible and self.objectSelectability[category]):
            item.setSelected(False)
            self.selectedItemsSet.discard(item)

    def _applyObjectFilter(self, item: QGraphicsItem) -> None:
        """Apply active object filters to a newly added scene item."""
        if all(self.objectVisibility.values()) and all(
            self.objectSelectability.values()
        ):
            return
        if item.parentItem() is not None:
            return
        category = self.objectCategory(item)
        if category is not None:
            self._applyItemObjectState(item, category)

    def _applyObjectFilters(self) -> None:
        """Re-apply object filters to all top-level items in the scene."""
        if all(self.objectVisibility.values()) and all(
            self.objectSelectability.values()
        ):
            return
        pinLabels = self.pinLabelItems()
        for item in self.items():
            if item.parentItem() is not None:
                continue
            category = self.objectCategory(item, pinLabels)
            if category is not None:
                self._applyItemObjectState(item, category)

    def addUndoStack(self, item: QGraphicsItem):
        super().addUndoStack(item)
        self._applyObjectFilter(item)

    def addListUndoStack(self, itemList: List[QGraphicsItem]) -> None:
        super().addListUndoStack(itemList)
        for item in itemList:
            self._applyObjectFilter(item)

    def loadSchematicInstances(self, schematicTuple: ddef.viewItemTuple) -> None:
        """Load schematic and create corresponding layout instances.

        Args:
            schematicTuple: Tuple containing library/cell/view for the schematic
        """
        from PySide6.QtWidgets import QMessageBox

        # Check for existing layout instances
        existingInstances = self.findScenelayoutCellSet()
        if existingInstances:
            reply = QMessageBox.question(
                self.editorWindow,
                "Existing Layout Instances",
                f"There are {len(existingInstances)} layout instances on the scene.\n\n"
                "Continuing will remove all existing instances and place new ones from the schematic.\n\n"
                "Do you want to proceed?",
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel
            )
            if reply != QMessageBox.StandardButton.Ok:
                self.logger.info("Schematic-driven layout cancelled by user")
                return

            # Remove existing instances
            for inst in existingInstances:
                self.deleteUndoStack(inst)

        schematicPath = schematicTuple.viewItem.viewPath
        try:
            with schematicPath.open("rb") as f:
                data = orjson.loads(f.read())
        except Exception as e:
            self.logger.error(f"Failed to load schematic: {e}")
            return

        # Parse schematic instances (type "sys")
        schInstances = [
            {
                "lib": item.get("lib", ""),
                "cell": item.get("cell", ""),
                "view": item.get("view", ""),
                "name": item.get("nam", ""),
                "counter": item.get("ic", 0),
                "loc": item.get("loc", (0, 0)),
                "ang": item.get("ang", 0),
                "fl": item.get("fl", (1, 1)),
                "labels": item.get("ld", {}),
            }
            for item in (data[2:] if len(data) > 2 else [])
            if isinstance(item, dict) and item.get("type") == "sys"
        ]

        if not schInstances:
            self.logger.info("No schematic instances found to place")
            return

        # Create layout instances for each schematic instance
        createdCount = 0
        for sch_inst in schInstances:
            # Resolve layout view (try "layout" or "pcell" with same cell name)
            layoutTuple = self._resolveLayoutView(sch_inst["lib"], sch_inst["cell"])
            if layoutTuple:
                if self._createLayoutInstanceFromSch(layoutTuple, sch_inst):
                    createdCount += 1
            else:
                self.logger.warning(
                    f"No layout/pcell view found for {sch_inst['lib']}/{sch_inst['cell']}"
                )

        self.logger.info(f"Created {createdCount} layout instances from schematic")

    def _resolveLayoutView(self, lib_name: str, cell_name: str) -> Union[ddef.viewItemTuple, None]:
        """Find layout or pcell view for a given schematic cell.

        Args:
            lib_name: Library name
            cell_name: Cell name

        Returns:
            viewItemTuple if found, None otherwise
        """
        import revedaEditor.backend.libBackEnd as libb

        lib_path = self.libraryDict.get(lib_name)
        if not lib_path:
            return None

        cell_path = lib_path / cell_name
        if not cell_path.exists():
            return None

        # Try layout view first, then pcell
        for view_name in ["layout", "pcell"]:
            view_path = cell_path / f"{view_name}.json"
            if view_path.exists():
                lib_item = libb.libraryItem(lib_path)
                cell_item = libb.cellItem(cell_path)
                view_item = libb.viewItem(view_path)
                return ddef.viewItemTuple(lib_item, cell_item, view_item)

        return None

    def _getPcellParameterMap(self, cellName: str) -> dict:
        mapPath = pathlib.Path(fabproc.__file__).parent / "pcellParameterMap.json"
        try:
            with mapPath.open("rb") as mapFile:
                parameterMap = orjson.loads(mapFile.read())
        except (OSError, orjson.JSONDecodeError) as error:
            self.logger.error(f"Failed to load PCell parameter map: {error}")
            return {}
        return parameterMap.get("mappings", {}).get(cellName, {})

    def _createLayoutInstanceFromSch(self, viewTuple: ddef.viewItemTuple, sch_inst: dict) -> bool:
        """Create a layout instance from schematic instance data.

        Args:
            viewTuple: Library/cell/view tuple for layout/pcell
            sch_inst: Schematic instance data dict

        Returns:
            True if instance created successfully, False otherwise
        """
        # Store current tuple and set the new one
        oldTuple = self.layoutInstanceTuple
        self.layoutInstanceTuple = viewTuple

        try:
            new_inst = self.instLayout(viewTuple)
            if new_inst is None:
                return False

            # For PCells, apply matching schematic instance labels.
            if isinstance(new_inst, pcells.baseCell):
                labels = sch_inst.get("labels", {})
                callParameters = inspect.signature(new_inst.__call__).parameters
                parameterMap = self._getPcellParameterMap(sch_inst["cell"])
                if not parameterMap:
                    # No schematic->PCell parameter mapping: fall back to the
                    # PCell's default parameter values rather than failing.
                    lineEditDict = self.extractPcellInstanceParameters(new_inst)
                    if lineEditDict:
                        instanceValuesDict = {
                            key: value.text()
                            for key, value in lineEditDict.items()
                        }
                        if instanceValuesDict:
                            new_inst(*instanceValuesDict.values())
                else:
                    instanceParameters = {
                        name: labels[labelName][0]
                        for name, parameter in callParameters.items()
                        if parameter.kind in (
                            inspect.Parameter.POSITIONAL_OR_KEYWORD,
                            inspect.Parameter.KEYWORD_ONLY,
                        )
                        and (labelName := parameterMap.get(name)) in labels
                    }
                    missingParameters = [
                        name
                        for name, parameter in callParameters.items()
                        if parameter.kind in (
                            inspect.Parameter.POSITIONAL_OR_KEYWORD,
                            inspect.Parameter.KEYWORD_ONLY,
                        )
                        and parameter.default is inspect.Parameter.empty
                        and name not in instanceParameters
                    ]
                    if missingParameters:
                        self.logger.error(
                            f"Missing PCell parameters for {sch_inst['name']}: "
                            f"{', '.join(missingParameters)}"
                        )
                        return False
                    new_inst(**instanceParameters)

            # Inherit properties from schematic
            new_inst.instanceName = sch_inst["name"]
            new_inst.counter = sch_inst["counter"]
            new_inst.angle = sch_inst["ang"]
            new_inst.flipTuple = tuple(sch_inst["fl"])

            # Convert the schematic grid location to layout scene coordinates.
            loc: tuple[int, int] = (
                sch_inst["loc"][0] * 10,
                sch_inst["loc"][1] * 10,
            )

            if isinstance(loc, (list, tuple)) and len(loc) >= 2:
                new_inst.setPos(loc[0], loc[1])


            # Store SDL metadata for tracking
            new_inst._sdlSource = {
                "schematicLib": sch_inst["lib"],
                "schematicCell": sch_inst["cell"],
                "schematicInstance": sch_inst["name"],
                "labels": sch_inst.get("labels", {}),
            }

            # Add to scene via undo stack
            self.addUndoStack(new_inst)
            return True

        except Exception as e:
            self.logger.error(f"Error creating layout instance from schematic: {e}")
            return False
        finally:
            # Restore original tuple
            self.layoutInstanceTuple = oldTuple

    def saveLayoutCell(self, filePathObj: pathlib.Path) -> None:
        """Save the layout cell to a JSON file.

        Args:
            filePathObj (pathlib.Path): Path object for the output file

        Raises:
            IOError: If there are issues writing to the file
            ValueError: If the layout data is invalid
        """

        def safeJsonWrite(file_obj, data: list) -> None:
            """Write JSON data with optimized settings.

            Args:
                file_obj: File object to write to
                data: Data to be written

            Raises:
                JSONEncodeError: If JSON encoding fails
            """
            json.dump(
                data,
                file_obj,
                cls=layenc.layoutEncoder,
                separators=(",", ":"),  # Minimize JSON size
                check_circular=False,  # Optimize for non-circular references
            )

        try:
            # Create parentW directory if it doesn't exist
            filePathObj.parent.mkdir(parents=True, exist_ok=True)

            # A live selection group (e.g. right after copy) parents its
            # members to the group item; the top-level filter below would
            # otherwise silently drop them from the saved cell.
            if self.selectedItemGroup is not None:
                self.destroyItemGroup(self.selectedItemGroup)
                self.selectedItemGroup = None

            # Prepare data before file operation
            self.itemsRefSet = set(self.items())
            topLevelItems = [
                item
                for item in self.itemsRefSet
                if item.parentItem() is None
                   and isinstance(item, tuple(self.LAYOUT_SHAPES))
            ]
            layoutData = [
                {"viewType": "layout", "schemaVersion": "1.0"},
                # Grid values are stored in layout units (e.g. µm); the scene
                # converts them to dbu-scaled integers on load.
                {"snapGrid": (self.majorGrid / fabproc.dbu, self.snapGrid / fabproc.dbu),
                 "snapConnectDistance": self.editorWindow.snapConnectDistance / fabproc.dbu,
                 "lodThreshold": self.editorWindow.lodThreshold},
                *topLevelItems,
            ]

            # Use temporary file for atomic write
            temp_path = filePathObj.with_suffix(".tmp")
            try:
                with temp_path.open(mode="w", buffering=65536) as f:  # 64KB buffer
                    safeJsonWrite(f, layoutData)

                # Atomic rename for safer file writing
                temp_path.replace(filePathObj)

            finally:
                # Clean up temp file if it still exists
                if temp_path.exists():
                    temp_path.unlink()

            self.logger.info(
                f"Saved layout to {self.editorWindow.cellName}:{self.editorWindow.viewName}"
            )
            lj.PCellCache.clear_caches()
            lj.layoutItems._load_json_file.cache_clear()

        except ValueError as e:
            self.logger.error(f"Invalid layout data: {str(e)}")
            raise

        except (IOError, TypeError) as e:
            self.logger.error(f"Failed to save layout to {filePathObj}: {str(e)}")
            raise

        except Exception as e:
            self.logger.error(f"Unexpected error while saving layout: {str(e)}")
            raise

    def _exportCell(
            self, export_dir: pathlib.Path, unit: float, precision: float, dbu: int, format_type: str = "GDS"
    ):
        """Export cell in the specified format (GDS or OAS)."""
        format_upper = format_type.upper()
        file_extension = ".gds" if format_upper == "GDS" else ".oas"
        export_path = export_dir / f"{self.cellName}{file_extension}"

        try:
            # Ungroup a live selection group so its members are exported,
            # and take self.items() (the scene is the source of truth):
            # itemsRefSet can drift when items are added/removed outside
            # undo commands.
            if self.selectedItemGroup is not None:
                self.destroyItemGroup(self.selectedItemGroup)
                self.selectedItemGroup = None
            topLevelItems = [
                item
                for item in self.items()
                if item.parentItem() is None
                   and isinstance(item, tuple(self.LAYOUT_SHAPES))
            ]

            exportObj = gdse.gdsExporter(self.cellName, topLevelItems, export_path)
            exportObj.unit = unit
            exportObj.precision = precision
            exportObj.dbu = dbu

            self.logger.info(f"{format_upper} Export started.")
            with self.measureDuration():
                if format_upper == "OAS":
                    exportObj.oasExportThreaded(self.appMainW.threadPool)
                else:
                    exportObj.gdsExportThreaded(self.appMainW.threadPool)
            self.logger.info(f"{format_upper} Export finished.")

        except ValueError as e:
            self.logger.error(f"Invalid layout data: {str(e)}")
            raise

        except (IOError, TypeError) as e:
            self.logger.error(f"Failed to export layout to {export_path}: {str(e)}")
            raise

        except Exception as e:
            self.logger.error(f"Unexpected error while exporting layout: {str(e)}")
            raise

    def exportCellGDS(
            self, gdsExportDir: pathlib.Path, gdsUnit: float, gdsPrecision: float, dbu: int
    ):
        """Export cell as GDS format."""
        self._exportCell(gdsExportDir, gdsUnit, gdsPrecision, dbu, "GDS")

    def exportCellOAS(
            self, oasExportDir: pathlib.Path, gdsUnit: float, gdsPrecision: float, dbu: int
    ):
        """Export cell as OAS format."""
        self._exportCell(oasExportDir, gdsUnit, gdsPrecision, dbu, "OAS")

    def loadDesign(self, filePathObj: pathlib.Path) -> bool:
        """Load the layout cell from the given JSON file."""
        try:
            with filePathObj.open("rb") as file:
                decodedData = orjson.loads(file.read())
            # Validate file structure before processing
            is_valid, errors = sv.validate_design_file(
                decodedData, "layout", str(filePathObj)
            )
            if not is_valid:
                for err in errors:
                    self.logger.error(
                        f"Layout validation error in "
                        f"'{filePathObj.name}': {err}"
                    )
                return False
            with self.measureDuration():
                snapGridTuple = decodedData[1].get(
                    "snapGrid", (self.majorGrid / fabproc.dbu, self.snapGrid / fabproc.dbu)
                )
                # Snap grid is stored in layout units (floats); older files may
                # still have scene-unit ints. Convert layout-unit values back to
                # scene (dbu) values.
                if any(isinstance(v, float) for v in snapGridTuple):
                    snapGridTuple = (
                        round(float(snapGridTuple[0]) * fabproc.dbu),
                        round(float(snapGridTuple[1]) * fabproc.dbu),
                    )
                self.editorWindow.configureGridSettings(snapGridTuple)
                snapConnectDistance = decodedData[1].get("snapConnectDistance")
                if snapConnectDistance is not None:
                    # Floats are layout units (µm); ints are legacy scene-unit
                    # values stored by older versions.
                    if isinstance(snapConnectDistance, float):
                        snapConnectDistance = round(snapConnectDistance * fabproc.dbu)
                    self.editorWindow.snapConnectDistance = snapConnectDistance
                    self.snapConnectDistance = snapConnectDistance
                # Restore LOD threshold if saved
                lodThreshold = decodedData[1].get("lodThreshold", None)
                if lodThreshold is not None:
                    try:
                        lodThreshold = float(lodThreshold)
                        if lodThreshold > 0:
                            self.editorWindow.lodThreshold = lodThreshold
                            from revedaEditor.common.layoutShapes import layoutInstance
                            layoutInstance._lodThreshold = lodThreshold
                    except (ValueError, TypeError):
                        pass
                if len(decodedData) > 2:
                    self.createLayoutItems(decodedData[2:])
            self.itemsRefSet = set(self.items())
            return True
        except orjson.JSONDecodeError:
            self.logger.error("Invalid file format.")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error loading layout: {e}")
            return False

    def createLayoutItems(self, decoded_data: List[Dict[str, Any]]) -> None:
        if not decoded_data:
            return

        factory_create = lj.layoutItems(self).create
        index_method = self.itemIndexMethod()
        self.setItemIndexMethod(QGraphicsScene.ItemIndexMethod.NoIndex)
        try:
            for item in decoded_data:
                if isinstance(item, dict):
                    try:
                        shape = factory_create(item)
                        if shape is not None:
                            self.addItem(shape)
                    except Exception:
                        pass
        finally:
            self.setItemIndexMethod(index_method)
        if hasattr(self, "_applyObjectFilters"):
            self._applyObjectFilters()

    def deleteSelectedItems(self):
        for item in self.selectedItems():
            # if pin is to be deleted, the associated label should be also deleted.
            if isinstance(item, lshp.layoutPin) and item.label is not None:
                undoCommand = us.deleteShapeUndo(self, item.label)
                self.undoStack.push(undoCommand)
        super().deleteSelectedItems()

    def viewObjProperties(self):
        """
        Display the properties of the selected object.
        """
        try:
            selectedItems = [
                item for item in self.selectedItems() if item.parentItem() is None
            ]
            if selectedItems is not None:
                for item in selectedItems:
                    match type(item):
                        case lshp.layoutRect:
                            self.layoutRectProperties(item)
                        case lshp.layoutPin:
                            self.layoutPinProperties(item)
                        case lshp.layoutLabel:
                            self.layoutLabelProperties(item)
                        case lshp.layoutPath:
                            self.layoutPathProperties(item)
                        case lshp.layoutViaArray:
                            self.layoutViaProperties(item)
                        case lshp.layoutPolygon:
                            self.layoutPolygonProperties(item)
                        case lshp.layoutInstance:
                            self.layoutInstanceProperties(item, False)
                        # case _:
                        # if item.__class__.__bases__[0] == pcells.baseCell:
                        #     self.layoutInstanceProperties(item, True)
                        case _:
                            if isinstance(item, pcells.baseCell):
                                self.layoutInstanceProperties(item, True)

        except Exception as e:
            self.logger.error(f"{type(item)} property editor error: {e}")

    def layoutPolygonProperties(self, item):
        # points are stored in item-local coordinates; fold in pos() so the
        # dialog shows the polygon's actual scene position after moves.
        pointsTupleList = [
            self.toLayoutCoord(item.pos() + point).toTuple()
            for point in item.points
        ]

        dlg = ldlg.layoutPolygonProperties(self.editorWindow, pointsTupleList)
        dlg.polygonLayerCB.addItems(
            [f"{item.name} [{item.purpose}]" for item in laylyr.pdkAllLayers]
        )
        dlg.polygonLayerCB.setCurrentText(f"{item.layer.name} [{item.layer.purpose}]")

        if dlg.exec() == QDialog.DialogCode.Accepted:
            newLayer = laylyr.pdkAllLayers[dlg.polygonLayerCB.currentIndex()]
            tempPoints = []
            for i in range(dlg.tableWidget.rowCount()):
                xcoor = dlg.tableWidget.item(i, 1).text()
                ycoor = dlg.tableWidget.item(i, 2).text()
                if xcoor != "" and ycoor != "":
                    tempPoints.append(
                        self.toSceneCoord(QPointF(float(xcoor), float(ycoor)))
                    )
            newPoints = tempPoints
            newPolygon = lshp.layoutPolygon(newPoints, newLayer)
            self.undoStack.push(us.addDeleteShapeUndo(self, newPolygon, item))

    def layoutRectProperties(self, item):
        dlg = ldlg.layoutRectProperties(self.editorWindow)
        dlg.rectLayerCB.addItems(
            [f"{item.name} [{item.purpose}]" for item in laylyr.pdkAllLayers]
        )
        dlg.rectLayerCB.setCurrentText(f"{item.layer.name} [{item.layer.purpose}]")
        dlg.rectWidthEdit.setText(str(item.width / fabproc.dbu))
        dlg.rectHeightEdit.setText(str(item.height / fabproc.dbu))
        # rect is stored in item-local coordinates; fold in pos() so the
        # dialog shows the rect's actual scene position after moves.
        topLeft = item.pos() + item.rect.topLeft()
        dlg.topLeftEditX.setText(str(topLeft.x() / fabproc.dbu))
        dlg.topLeftEditY.setText(str(topLeft.y() / fabproc.dbu))
        if dlg.exec() == QDialog.DialogCode.Accepted:
            layer = laylyr.pdkAllLayers[dlg.rectLayerCB.currentIndex()]
            topLeft = self.snapToGrid(
                self.toSceneCoord(
                    QPointF(
                        float(dlg.topLeftEditX.text()),
                        float(dlg.topLeftEditY.text()),
                    )
                )
            )
            bottomRight = self.snapToGrid(
                topLeft
                + self.toSceneCoord(
                    QPointF(
                        float(dlg.rectWidthEdit.text()),
                        float(dlg.rectHeightEdit.text()),
                    )
                )
            )
            newRect = lshp.layoutRect(QPoint(0, 0), QPoint(0, 0), layer)
            newRect.rect = QRectF(topLeft, bottomRight).toRect()
            self.undoStack.push(us.addDeleteShapeUndo(self, newRect, item))

    def layoutViaProperties(self, item):
        dlg = ldlg.layoutViaProperties(self.editorWindow)
        if item.xnum == 1 and item.ynum == 1:
            dlg.singleViaRB.setChecked(True)
            dlg.singleViaClicked()
            dlg.singleViaNamesCB.addItems(fabproc.processViaNames)
            dlg.singleViaNamesCB.setCurrentText(item.via.viaDefTuple.name)
            dlg.singleViaWidthEdit.setText(str(item.width / fabproc.dbu))
            dlg.singleViaHeightEdit.setText(str(item.via.height / fabproc.dbu))
            dlg.singleBottomEncEdit.setText(str(item.via.bottomEnclosure))
            dlg.singleTopEncEdit.setText(str(item.via.topEnclosure))
        else:
            dlg.arrayViaRB.setChecked(True)
            dlg.arrayViaClicked()
            dlg.arrayViaNamesCB.addItems(fabproc.processViaNames)
            dlg.arrayViaNamesCB.setCurrentText(item.via.viaDefTuple.name)
            dlg.arrayViaWidthEdit.setText(str(item.via.width / fabproc.dbu))
            dlg.arrayViaHeightEdit.setText(str(item.via.height / fabproc.dbu))
            dlg.arrayXspacingEdit.setText(str(item.xs / fabproc.dbu))
            dlg.arrayYspacingEdit.setText(str(item.ys / fabproc.dbu))
            dlg.arrayXNumEdit.setText(str(item.xnum))
            dlg.arrayYNumEdit.setText(str(item.ynum))
            dlg.arrayBottomEncEdit.setText(str(item.via.bottomEnclosure))
            dlg.arrayTopEncEdit.setText(str(item.via.topEnclosure))
        dlg.startXEdit.setText(str(self.toLayoutCoord(item.mapToScene(item.start)).x()))
        dlg.startYEdit.setText(str(self.toLayoutCoord(item.mapToScene(item.start)).y()))
        if dlg.exec() == QDialog.DialogCode.Accepted:
            start = self.toSceneCoord(
                QPointF(
                    float(dlg.startXEdit.text()),
                    float(dlg.startYEdit.text()),
                )
            )
            if dlg.singleViaRB.isChecked():
                selViaDefTuple = fabproc.processVias[
                    fabproc.processViaNames.index(dlg.singleViaNamesCB.currentText())
                ]
                singleViaTuple = ddef.singleViaTuple(
                    selViaDefTuple,
                    float(dlg.singleViaWidthEdit.text().strip()) * fabproc.dbu,
                    float(dlg.singleViaHeightEdit.text().strip()) * fabproc.dbu,
                    float(dlg.singleBottomEncEdit.text().strip()),
                    float(dlg.singleTopEncEdit.text().strip()),
                )
                arrayViaTuple = ddef.arrayViaTuple(
                    singleViaTuple,
                    float(selViaDefTuple.minSpacing) * fabproc.dbu,
                    float(selViaDefTuple.minSpacing) * fabproc.dbu,
                    1,
                    1,
                )
            else:
                selViaDefTuple = [
                    viaDefTuple
                    for viaDefTuple in fabproc.processVias
                    if viaDefTuple.name == dlg.arrayViaNamesCB.currentText()
                ][0]

                singleViaTuple = ddef.singleViaTuple(
                    selViaDefTuple,
                    float(dlg.arrayViaWidthEdit.text().strip()) * fabproc.dbu,
                    float(dlg.arrayViaHeightEdit.text().strip()) * fabproc.dbu,
                    float(dlg.arrayBottomEncEdit.text().strip()),
                    float(dlg.arrayTopEncEdit.text().strip()),
                )
                arrayViaTuple = ddef.arrayViaTuple(
                    singleViaTuple,
                    float(dlg.arrayXspacingEdit.text().strip()) * fabproc.dbu,
                    float(dlg.arrayYspacingEdit.text().strip()) * fabproc.dbu,
                    int(float(dlg.arrayXNumEdit.text().strip())),
                    int(float(dlg.arrayYNumEdit.text().strip())),
                )
            singleVia = lshp.layoutVia(
                QPoint(0, 0),
                *arrayViaTuple.singleViaTuple,
            )
            arrayVia = lshp.layoutViaArray(
                QPoint(0, 0),
                singleVia,
                arrayViaTuple.xs,
                arrayViaTuple.ys,
                arrayViaTuple.xnum,
                arrayViaTuple.ynum,
            )
            arrayVia.setPos(start)
            self.undoStack.push(us.addDeleteShapeUndo(self, arrayVia, item))

    def layoutPathProperties(self, item):
        dlg = ldlg.layoutPathPropertiesDialog(self.editorWindow)
        match item.mode:
            case 0:
                dlg.manhattanButton.setChecked(True)
            case 1:
                dlg.diagonalButton.setChecked(True)
            case 2:
                dlg.anyButton.setChecked(True)
            case 3:
                dlg.horizontalButton.setChecked(True)
            case 4:
                dlg.verticalButton.setChecked(True)

        dlg.pathLayerCB.addItems(fabproc.processPathNames)

        currentIndex = next(
            (
                i
                for i, pathDefTuple in enumerate(fabproc.processPaths)
                if pathDefTuple.layer.name == item.layer.name
            ),
            0,
        )
        dlg.pathLayerCB.setCurrentIndex(currentIndex)

        dlg.pathWidth.setText(str(item.width / fabproc.dbu))
        dlg.pathNameEdit.setText(item.name)
        roundingFactor = len(str(fabproc.dbu)) - 1
        dlg.startExtendEdit.setText(
            str(round(item.startExtend / fabproc.dbu, roundingFactor))
        )
        dlg.endExtendEdit.setText(
            str(round(item.endExtend / fabproc.dbu, roundingFactor))
        )
        scenePoints = item.sceneEndPoints
        p1Layout = self.toLayoutCoord(scenePoints[0])
        p2Layout = self.toLayoutCoord(scenePoints[1])
        dlg.p1PointEditX.setText(
            str(round(p1Layout.x(), roundingFactor))
        )
        dlg.p1PointEditY.setText(
            str(round(p1Layout.y(), roundingFactor))
        )
        dlg.p2PointEditX.setText(
            str(round(p2Layout.x(), roundingFactor))
        )
        dlg.p2PointEditY.setText(
            str(round(p2Layout.y(), roundingFactor))
        )
        dlg.angleEdit.setText(str(item.angle))
        if dlg.exec() == QDialog.DialogCode.Accepted:
            item.name = dlg.pathNameEdit.text()
            pathDefTuple = fabproc.processPaths[dlg.pathLayerCB.currentIndex()]
            width = fabproc.dbu * float(dlg.pathWidth.text())
            startExtend = fabproc.dbu * float(dlg.startExtendEdit.text())
            endExtend = fabproc.dbu * float(dlg.endExtendEdit.text())
            p1 = self.toSceneCoord(
                QPointF(
                    float(dlg.p1PointEditX.text()),
                    float(dlg.p1PointEditY.text()),
                )
            )
            p2 = self.toSceneCoord(
                QPointF(
                    float(dlg.p2PointEditX.text()),
                    float(dlg.p2PointEditY.text()),
                )
            )
            draftLine = QLineF(p1, p2)
            newPath = lshp.layoutPath(
                draftLine, pathDefTuple.layer, width, startExtend, endExtend
            )
            newPath.angle = int(float(dlg.angleEdit.text()))
            self.undoStack.push(us.addDeleteShapeUndo(self, newPath, item))

    def layoutLabelProperties(self, item):
        dlg = ldlg.layoutLabelProperties(self.editorWindow)
        dlg.labelName.setText(item.labelText)
        labelLayers = getattr(laylyr, "pdkLabelLayers", laylyr.pdkTextLayers)
        dlg.labelLayerCB.addItems(
            [f"{layer.name} [{layer.purpose}]" for layer in labelLayers]
        )
        dlg.labelLayerCB.setCurrentText(f"{item.layer.name} [{item.layer.purpose}]")
        dlg.familyCB.setCurrentText(item.fontFamily)
        dlg.fontStyleCB.setCurrentText(item.fontStyle)
        dlg.labelHeightCB.setCurrentText(str(int(float(item.fontHeight))))
        dlg.labelAlignCB.setCurrentText(item.labelAlign)
        dlg.labelOrientCB.setCurrentText(item.labelOrient)
        start = item.mapToScene(item.start)
        dlg.labelTopLeftX.setText(str(self.toLayoutCoord(start).x()))
        dlg.labelTopLeftY.setText(str(self.toLayoutCoord(start).y()))

        if dlg.exec() == QDialog.DialogCode.Accepted:
            labelName = dlg.labelName.text()
            labelStartX = float(dlg.labelTopLeftX.text())
            labelStartY = float(dlg.labelTopLeftY.text())

            labelStart = self.toSceneCoord(QPointF(labelStartX, labelStartY))
            labelLayerName = dlg.labelLayerCB.currentText().split()[0]
            labelPurpose = dlg.labelLayerCB.currentText().split()[1].strip("[]")
            labelLayer = [
                item for item in labelLayers if item.name == labelLayerName and item.purpose == labelPurpose
            ][0]
            fontFamily = dlg.familyCB.currentText()
            fontStyle = dlg.fontStyleCB.currentText()
            fontHeight = dlg.labelHeightCB.currentText()
            labelAlign = dlg.labelAlignCB.currentText()
            labelOrient = dlg.labelOrientCB.currentText()
            newLabelTuple = ddef.layoutLabelTuple(
                labelName,
                fontFamily,
                fontStyle,
                fontHeight,
                labelAlign,
                labelOrient,
                labelLayer,
            )
            newLabel = lshp.layoutLabel(labelStart, *newLabelTuple)
            self.undoStack.push(us.addDeleteShapeUndo(self, newLabel, item))

    def layoutPinProperties(self, item):
        dlg = ldlg.layoutPinProperties(self.editorWindow)
        dlg.pinName.setText(item.pinName)
        dlg.pinDir.setCurrentText(item.pinDir)
        dlg.pinType.setCurrentText(item.pinType)

        dlg.pinLayerCB.addItems(
            [
                f"{pinLayer.name} [{pinLayer.purpose}]"
                for pinLayer in laylyr.pdkPinLayers
            ]
        )
        dlg.pinLayerCB.setCurrentText(f"{item.layer.name} [{item.layer.purpose}]")
        dlg.pinBottomLeftX.setText(str(item.mapToScene(item.start).x() / fabproc.dbu))
        dlg.pinBottomLeftY.setText(str(item.mapToScene(item.start).y() / fabproc.dbu))
        dlg.pinTopRightX.setText(str(item.mapToScene(item.end).x() / fabproc.dbu))
        dlg.pinTopRightY.setText(str(item.mapToScene(item.end).y() / fabproc.dbu))
        if dlg.exec() == QDialog.DialogCode.Accepted:
            pinName = dlg.pinName.text()
            pinDir = dlg.pinDir.currentText()
            pinType = dlg.pinType.currentText()
            labelText = dlg.pinName.text()
            start = self.snapToGrid(
                self.toSceneCoord(
                    QPointF(
                        float(dlg.pinBottomLeftX.text()),
                        float(dlg.pinBottomLeftY.text()),
                    )
                )
            )
            end = self.snapToGrid(
                self.toSceneCoord(
                    QPointF(
                        float(dlg.pinTopRightX.text()),
                        float(dlg.pinTopRightY.text()),
                    )
                )
            )
            pinLayer = laylyr.pdkPinLayers[dlg.pinLayerCB.currentIndex()]
            newPin = lshp.layoutPin(start, end, pinName, pinDir, pinType, pinLayer)
            newLabel = lshp.layoutLabel(
                item.label.start,
                labelText,
                item.label.fontFamily,
                item.label.fontStyle,
                item.label.fontHeight,
                item.label.labelAlign,
                item.label.labelOrient,
                item.label.layer,
            )
            newPin.label = newLabel

            undoCommandsList = [
                us.addDeleteShapeUndo(self, newPin, item),
                us.addDeleteShapeUndo(self, newLabel, item.label),
            ]
            self.addUndoMacroStack(undoCommandsList, "pin/label edit")
            # self.undoStack.beginMacro('pin/label edit')
            # self.undoStack.push(us.addDeleteShapeUndo(self, newPin, item))
            # self.undoStack.push(us.addDeleteShapeUndo(self, newLabel, item.label))
            # self.undoStack.endMacro()

    def layoutInstanceProperties(
            self, item: Union[lshp.layoutInstance, lshp.layoutPcell], pcell: bool = False
    ):
        libraryModel = lmview.layoutViewsModel(
            self.editorWindow.libraryDict, self.editorWindow.layoutViews
        )
        dlg = ldlg.layoutInstancePropertiesDialogue(self.editorWindow)
        if pcell:
            dlg.pcellParamsGroup.show()
            lineEditDict = self.extractPcellInstanceParameters(item)
            if lineEditDict:
                dlg.pcellParamsGroup.show()
                for key, value in lineEditDict.items():
                    dlg.pcellParamsLayout.addRow(key, value)
        libItem = libm.getLibItem(libraryModel, item.libraryName)
        cellItem = libm.getCellItem(libItem, item.cellName)
        viewItem = libm.getViewItem(cellItem, item.viewName)
        instanceTuple = ddef.viewItemTuple(libItem, cellItem, viewItem)
        dlg.instanceLibName.setText(item.libraryName)
        libNameCompleter = QCompleter(libraryModel.listLibraries())
        libNameCompleter.setCaseSensitivity(Qt.CaseInsensitive)
        dlg.instanceLibName.setCompleter(libNameCompleter)
        # create cell name completer list.
        dlg.instanceLibName.editingFinished.connect(
            lambda: self.cellNameComplete(
                dlg, libraryModel.listLibraryCells(dlg.instanceLibName.text())
            )
        )
        dlg.instanceCellName.setText(item.cellName)
        # create view name completer list
        dlg.instanceCellName.editingFinished.connect(
            lambda: self.viewNameComplete(
                dlg,
                libraryModel.listCellViews(
                    dlg.instanceLibName.text(),
                    dlg.instanceCellName.text(),
                    ["layout", "pcell"],
                ),
            )
        )
        dlg.instanceViewName.setText(item.viewName)
        dlg.instanceViewName.editingFinished.connect(
            lambda: self.changePcellParameterFields(dlg, libraryModel, instanceTuple)
        )
        dlg.instanceNameEdit.setText(item.instanceName)

        # Use pos() (parent-coordinate translation), not scenePos(). scenePos()
        # bakes in this item's rotation/flip about its origin; writing it back
        # through setPos() (which sets pos()) would apply that transform a
        # second time and shift a flipped/rotated instance. pos() round-trips
        # cleanly with setPos() and matches the frame the layout loader uses.
        dlg.xEdit.setText(str(item.pos().x() / fabproc.dbu))
        dlg.yEdit.setText(str(item.pos().y() / fabproc.dbu))

        if dlg.exec() == QDialog.DialogCode.Accepted:
            libraryName = dlg.instanceLibName.text().strip()
            cellName = dlg.instanceCellName.text().strip()
            viewName = dlg.instanceViewName.text().strip()
            instanceName = dlg.instanceNameEdit.text().strip()
            libItem = libm.getLibItem(libraryModel, libraryName)
            cellItem = libm.getCellItem(libItem, cellName)
            viewItem = libm.getViewItem(cellItem, viewName)

            layoutInstanceTuple = ddef.viewItemTuple(libItem, cellItem, viewItem)
            newLayoutInstance = self.instLayout(layoutInstanceTuple)
            newLayoutInstance.instanceName = instanceName
            lineEditDict = ldlg.formDictionary(
                dlg.pcellParamsLayout
            ).extractDictFormLayout()
            instanceValuesDict = {}
            if lineEditDict:
                for key, value in lineEditDict.items():
                    instanceValuesDict[key] = value.text()
            if instanceValuesDict:
                newLayoutInstance(**instanceValuesDict)
            # Preserve the original instance orientation. Rebuilding the
            # instance (needed to apply changed PCell parameters) starts from
            # the default transform, so the rotation and flip state must be
            # carried over or the instance silently reverts to unrotated /
            # unflipped. flipTuple is applied after angle because its transform
            # is derived from the item's (post-rotation) bounding rect.
            newLayoutInstance.angle = item.angle
            newLayoutInstance.flipTuple = item.flipTuple
            newLayoutInstance.setPos(
                QPoint(
                    self.snapToBase(
                        float(dlg.xEdit.text()) * fabproc.dbu, self.snapTuple[0]
                    ),
                    self.snapToBase(
                        float(dlg.yEdit.text()) * fabproc.dbu, self.snapTuple[1]
                    ),
                )
            )
            self.undoStack.push(us.addDeleteShapeUndo(self, newLayoutInstance, item))

    def changePcellParameterFields(
            self,
            dlg: ldlg.layoutInstancePropertiesDialogue,
            libraryModel: lmview.layoutViewsModel,
            instanceTuple: ddef.viewItemTuple,
    ):
        """Update the PCell parameter fields based on the selected instance tuple."""
        # Get the new item tuple
        lib_item = libm.getLibItem(libraryModel, dlg.instanceLibName.text().strip())
        cell_item = libm.getCellItem(lib_item, dlg.instanceCellName.text().strip())
        view_item = libm.getViewItem(cell_item, dlg.instanceViewName.text().strip())
        new_item_tuple = ddef.viewItemTuple(lib_item, cell_item, view_item)

        # Check if the view item has a 'viewType' key
        if hasattr(new_item_tuple.viewItem, "viewType"):
            # Clear the pcell parameters layout
            self.clearLayout(dlg.pcellParamsLayout)

            newInstance = self.instLayout(new_item_tuple)

            # Check the view type
            if new_item_tuple.viewItem.viewType == "pcell":
                # Extract PCell instance parameters
                line_edit_dict = self.extractPcellInstanceParameters(newInstance)

                # Add PCell parameters to the layout
                if line_edit_dict:
                    dlg.pcellParamsGroup.show()
                    for key, value in line_edit_dict.items():
                        dlg.pcellParamsLayout.addRow(key, value)
            elif new_item_tuple.viewItem.viewType == "layout":
                # Hide the PCell parameters group
                dlg.pcellParamsGroup.hide()

    def extractPcellInstanceParameters(self, instance: lshp.layoutPcell) -> dict:
        initArgs = inspect.signature(instance.__class__.__init__).parameters
        argsUsed = [param for param in initArgs if (param != "self")]
        argDict = {arg: getattr(instance, arg) for arg in argsUsed}
        lineEditDict = {key: edf.shortLineEdit(value) for key, value in argDict.items()}
        return lineEditDict

    def clearLayout(self, layout):
        """Clear the layout by deleting all its children."""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self.clearLayout(child.layout())

    def moveBySelectedItems(self):
        if self.selectedItems():
            dlg = pdlg.moveByDialogue(self.editorWindow)
            dlg.xEdit.setText("0.0")
            dlg.yEdit.setText("0.0")
            if dlg.exec() == QDialog.DialogCode.Accepted:
                for item in self.selectedItems():
                    item.moveBy(
                        self.snapToBase(
                            float(dlg.xEdit.text()) * fabproc.dbu, self.snapTuple[0]
                        ),
                        self.snapToBase(
                            float(dlg.yEdit.text()) * fabproc.dbu, self.snapTuple[1]
                        ),
                    )
                self.editorWindow.messageLine.setText(
                    f"Moved items by {dlg.xEdit.text()} and {dlg.yEdit.text()}"
                )
                self.editModes.setMode("selectItem")

    def copySelectedItems(self):
        selectedItems = [
            item for item in self.selectedItems() if item.parentItem() is None
        ]
        copyShapesList = []
        if selectedItems:
            for item in selectedItems:
                selectedItemJson = json.dumps(item, cls=layenc.layoutEncoder)
                itemCopyDict = json.loads(selectedItemJson)
                shape = lj.layoutItems(self).create(itemCopyDict)
                if shape is not None:
                    if isinstance(shape, (lshp.layoutInstance, lshp.layoutPcell)):
                        self.itemCounter += 1
                        shape.instanceName = f"I{self.itemCounter}"
                        shape.counter = int(self.itemCounter)
                    copyShapesList.append(shape)

            self.addListUndoStack(copyShapesList)
            # Record each copy's pre-group pos()/transform() so the base class
            # mouseReleaseEvent can restore them after destroyItemGroup().
            for shape in copyShapesList:
                shape._groupInitialState = (shape.pos(), shape.transform())
            self.selectedItemGroup = self.createItemGroup(copyShapesList)
            self._initialGroupPos = self.selectedItemGroup.pos()
            self.selectedItemGroup.setSelected(True)

    def deleteAllRulers(self):
        # A ruler is added on its first click and finalized on the second. Do
        # not keep a reference to it after the bulk-delete command removes it.
        self._newRuler = None
        sceneRulerSet = {
            item for item in self.items() if isinstance(item, lshp.layoutRuler)
        }
        if sceneRulerSet:
            self.deleteListUndoStack(list(sceneRulerSet))
        # for ruler in self.rulersSet:
        #     undoCommand = us.deleteShapeUndo(self, ruler)
        #     self.undoStack.push(undoCommand)

    def goDownHier(self):
        if self.selectedItems():
            for item in self.selectedItems():
                if isinstance(item, lshp.layoutInstance):
                    dlg = fd.goDownHierDialogue(self.editorWindow)
                    libItem = libm.getLibItem(
                        self.editorWindow.libraryView.libraryModel, item.libraryName
                    )
                    cellItem = libm.getCellItem(libItem, item.cellName)
                    viewNames = [
                        cellItem.child(i).text()
                        for i in range(cellItem.rowCount())
                        # if cellItem.child(i).text() != item.viewName
                        if "layout" in cellItem.child(i).text()
                    ]
                    dlg.viewListCB.addItems(viewNames)
                    if dlg.exec() == QDialog.DialogCode.Accepted:
                        libItem = libm.getLibItem(
                            self.editorWindow.libraryView.libraryModel, item.libraryName
                        )
                        cellItem = libm.getCellItem(libItem, item.cellName)
                        viewItem = libm.getViewItem(
                            cellItem, dlg.viewListCB.currentText()
                        )
                        viewItemT = ddef.viewItemTuple(libItem, cellItem, viewItem)
                        openViewNameT = (
                            self.editorWindow.libraryView.openCellView(
                                viewItemT
                            )
                        )
                        if self.editorWindow.appMainW.openViews[openViewNameT]:
                            childWindow = self.editorWindow.appMainW.openViews[
                                openViewNameT
                            ]
                            childWindow.parentEditor = self.editorWindow
                            childWindow.parentObj = item
                            childWindow.layoutToolbar.addAction(childWindow.goUpAction)
                            if dlg.buttonId == 2:
                                childWindow.centralW.scene.readOnly = True

    def stretchPath(self, pathItem: lshp.layoutPath, stretchEnd: str):
        match stretchEnd:
            case "p2":
                self.stretchPathItem = lshp.layoutPath(
                    QLineF(pathItem.sceneEndPoints[0], pathItem.sceneEndPoints[1]),
                    pathItem.layer,
                    pathItem.width,
                    pathItem.startExtend,
                    pathItem.endExtend,
                    pathItem.mode,
                )
            case "p1":
                self.stretchPathItem = lshp.layoutPath(
                    QLineF(pathItem.sceneEndPoints[1], pathItem.sceneEndPoints[0]),
                    pathItem.layer,
                    pathItem.width,
                    pathItem.startExtend,
                    pathItem.endExtend,
                    pathItem.mode,
                )
        self.stretchPathItem.stretch = True
        self.stretchPathItem.name = pathItem.name

        addDeleteStretchNetCommand = us.addDeleteShapeUndo(
            self, self.stretchPathItem, pathItem
        )
        self.undoStack.push(addDeleteStretchNetCommand)

    def findClosestFontSize(self, sizes: List[int], target: int = 16) -> int:
        return min(sizes, key=lambda x: abs(x - target))

    def setRulerFont(self, target_size: int = 16) -> QFont:
        fontDatabase = QFontDatabase()
        fixedFamilies = None
        if fontDatabase:
            fixedFamilies = [
                family
                for family in fontDatabase.families(QFontDatabase.Latin)
                if fontDatabase.isFixedPitch(family)
            ]

        if not fixedFamilies:
            self.logger.warning("No fixed-pitch fonts found. Using default font.")
            return QFont()
        else:
            for family in fixedFamilies:
                styles = fontDatabase.styles(family)
                if not styles:
                    continue

                style = styles[0]  # Use the first available style
                sizes = fontDatabase.pointSizes(family, style)

                if sizes:
                    closest_size = self.findClosestFontSize(sizes, target_size)
                    font = QFont(family)
                    font.setStyleName(style)
                    font.setPointSize(closest_size)
                    font.setKerning(False)
                    return font

        self.logger.warning("No suitable font found. Using default font.")
        return QFont()

    def updateItem(self, item: QGraphicsItem):
        # update the item to the latest version of the layout cell if it is edited in another editor window
        if isinstance(item, lshp.layoutInstance):
            libItem = libm.getLibItem(
                self.editorWindow.libraryView.libraryModel, item.libraryName
            )
            cellItem = libm.getCellItem(libItem, item.cellName)
            viewItem = libm.getViewItem(cellItem, item.viewName)
            viewItemTuple = ddef.viewItemTuple(libItem, cellItem, viewItem)
            if viewItem:
                newItem = self.instLayout(viewItemTuple)
                newItem.instanceName = item.instanceName
                newItem.setPos(item.pos())
                newItem.setRotation(item.rotation())
                newItem.setScale(item.scale())
                newItem.setTransform(item.transform())
                updateRect = item.boundingRect()
                self.removeItem(item)
                self.itemsRefSet.discard(item)
                self.addItem(newItem)
                self.itemsRefSet.add(newItem)
                self.update(updateRect)

    def renumberInstances(self):
        self.messageLine.setText("Renumbering instances. Cannot be undone.")
        instanceList = [
            item
            for item in self.items()
            if isinstance(item, (lshp.layoutInstance, lshp.layoutPcell))
        ]

        for index, layoutInstance in enumerate(instanceList):
            layoutInstance.counter = index
            if layoutInstance.instanceName.startswith("I"):
                # Preserve array notation like I2<0:5>
                if (
                        "<" in layoutInstance.instanceName
                        and ">" in layoutInstance.instanceName
                ):
                    array_part = layoutInstance.instanceName[
                        layoutInstance.instanceName.find("<"):
                    ]
                    layoutInstance.instanceName = f"I{index}{array_part}"
                else:
                    layoutInstance.instanceName = f"I{index}"
        self.instanceCounter = index + 1
        self.saveLayoutCell(self.editorWindow.file)
        self.reloadScene()
