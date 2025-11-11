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


import json
import os
import pathlib
from collections import Counter

from typing import Union, Set, Dict, Tuple, List
from PySide6.QtCore import (
    QPoint,
    QPointF,
    QRect,
    QRectF,
    Qt,
    QLineF,
    Signal,
    Slot,
    QRegularExpression,
)
from PySide6.QtGui import (
    QTextDocument,
    QFontDatabase,
    QFont,
    QGuiApplication,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QGraphicsRectItem,
    QGraphicsSceneMouseEvent,
    QGraphicsItem,
)
from numpy.ma import isin

import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.backend.libraryMethods as libm
import revedaEditor.backend.undoStack as us
import revedaEditor.common.labels as lbl
import revedaEditor.common.shapes as shp  # import the shapes
import revedaEditor.common.net as snet
import revedaEditor.fileio.loadJSON as lj
import revedaEditor.fileio.schematicEncoder as schenc
import revedaEditor.backend.editFunctions as edf
import revedaEditor.gui.fileDialogues as fd
import revedaEditor.gui.propertyDialogues as pdlg
from revedaEditor.backend.pdkPaths import importPDKModule
from revedaEditor.scenes.editorScene import editorScene
import revedaEditor.checks.schematic as schk

schlyr = importPDKModule("schLayers")


class schematicScene(editorScene):

    wireEditFinished = Signal(snet.schematicNet)
    stretchNet = Signal(snet.schematicNet, str)
    SCHEMATIC_SHAPES = (snet.schematicNet, shp.schematicPin, shp.text, shp.schematicSymbol)

    def __init__(self, parent):
        super().__init__(parent)

        # Initialize counters
        self.instCounter = 0
        self.instanceCounter = 0
        self.netCounter = 0

        # Initialize modes with default values
        self.editModes = ddef.schematicModes(
            selectItem=True,
            deleteItem=False,
            moveItem=False,
            copyItem=False,
            rotateItem=False,
            changeOrigin=False,
            panView=False,
            drawPin=False,
            drawWire=False,
            drawBus=False,
            drawText=False,
            addInstance=False,
            stretchItem=False,
            nameNet=False,
        )
        self.messages = {'selectItem': 'Select Item',
                         'deleteItem': 'Delete Item',
                         'moveItem': 'Move Item',
                         'copyItem': 'Copy Item',
                         'rotateItem': 'Rotate Item',
                         'changeOrigin': 'Change Origin',
                         'panView': 'Pan View at mouse Press Position',
                         'stretchItem': 'Stretch Item',
                         'drawPin': 'Draw Pin',
                         'drawWire': 'Draw Wire',
                         'drawBus': 'Draw Bus',
                         'drawText': 'Draw Text',
                         'addInstance': 'Add Instance',
                         'nameNet': 'Name Net',
                         'drawSymbol': 'Draw Symbol'
                        }

        self.selectModes = ddef.schematicSelectModes(
            selectAll=True, selectDevice=False, selectNet=False, selectPin=False
        )

        # Initialize selection trackers
        self.selectedNet = None
        self.selectedPin = None
        self.selectedSymbol = None
        self.selectedSymbolPin = None

        # Initialize pin defaults
        self.pinName = ""
        self.pinType = "Signal"
        self.pinDir = "Input"

        # Initialize internal state trackers
        self._newNet = None
        self._stretchNet = None
        self._newInstance = None
        self._newPin = None
        self._newText = None
        self._newNetNameObj = None
        self.textTuple = None
        self.netNameString = None
        self.newInstanceTuple = None
        self._snapPointRect = self.defineSnapRect()

        # error shapes
        self.overlapRectSet = set()

        # Initialize view properties
        self.highlightNets = False
        self.hierarchyTrail = ""
        self.parentEditor = None
        self.parentObj = None

        # Font initialization
        self._initializeFont()

        # Connect signals
        self.wireEditFinished.connect(self._handleWireFinished)
        self.stretchNet.connect(self._handleStretchNet)

        # Initialize cache
        self._symbolCache = {}

    def _initializeFont(self):
        """Initialize fixed-width font settings."""
        fontFamilies = QFontDatabase.families(QFontDatabase.Latin)

        # Find first fixed-pitch font family
        fixedFamily = next(
            family for family in fontFamilies if QFontDatabase.isFixedPitch(family)
        )

        # Get font style and create font
        fontStyle = QFontDatabase.styles(fixedFamily)[1]
        self.fixedFont = QFont(fixedFamily)
        self.fixedFont.setStyleName(fontStyle)

        # Set font size
        fontSize = QFontDatabase.pointSizes(fixedFamily, fontStyle)[3]
        self.fixedFont.setPointSize(fontSize)
        self.fixedFont.setKerning(False)

    def defineSnapRect(self):
        snapPointRect = QGraphicsRectItem()
        snapPointRect.setRect(QRect(-2, -2, 4, 4))
        snapPointRect.setZValue(100)
        snapPointRect.setVisible(False)
        snapPointRect.setPen(schlyr.guideLinePen)

        return snapPointRect

    @property
    def drawMode(self):
        return any(
            (self.editModes.drawPin, self.editModes.drawWire, self.editModes.drawText)
        )

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if self._selectedItemGroup and self.editModes.moveItem:
            for item in self._selectedItemGroup.childItems():
                if isinstance(item, shp.schematicSymbol) or isinstance(item, shp.schematicPin):
                    item.generatePinNetDict()
                    item.initializeSnapLines(self)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Handle mouse move event."""
        super().mouseMoveEvent(event)
        self.mouseMoveLoc = event.scenePos().toPoint()
        
        if self._newInstance and self.editModes.addInstance:
            self._newInstance.setPos(self.mouseMoveLoc)
        elif self._newPin and self.editModes.drawPin:

            self._newPin.setPos(self.mouseMoveLoc - self._newPin.start)
        elif self._newNet and (self.editModes.drawWire or self.editModes.drawBus):
            netEndPoint = self.findSnapPoint(self.mouseMoveLoc, set())
            self._snapPointRect.setPos(netEndPoint)
            self._newNet.draftLine = QLineF(self._newNet.draftLine.p1(), netEndPoint)
        elif self._stretchNet and self.editModes.stretchItem:

            netEndPoint = self.findSnapPoint(self.mouseMoveLoc, set())
            self._snapPointRect.setVisible(True)
            self._snapPointRect.setPos(netEndPoint)
            self._stretchNet.draftLine = QLineF(self._stretchNet.draftLine.p1(), netEndPoint)
        elif self._newText and self.editModes.drawText:

            self._newText.start = self.mouseMoveLoc
        elif self.editModes.nameNet and self._newNetNameObj:
            self._newNetNameObj.setPos(self.mouseMoveLoc)
        elif self.editModes.moveItem and self._selectedItemGroup:
            for item in self._selectedItemGroup.childItems():
                if isinstance(item,shp.schematicSymbol) or isinstance(item, shp.schematicPin):
                    item.updateSnapLines()
        
        cursorPosition = self.snapToGrid(self.mouseMoveLoc - self.origin, self.snapTuple)
        self.statusLine.showMessage(
            f"Cursor Position: ({cursorPosition.x()}, {cursorPosition.y()})"
        )
        self.messageLine.setText(self.messages[self.editModes.mode()])

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):

        return super().mouseReleaseEvent(event)
    
    def _handleMouseRelease(
        self, mousePos: QPoint, button: Qt.MouseButton
    ) -> None:
        """
        Handle mouse release logic.

        :param mouseReleaseLoc: QPoint instance
        :param button: Qt.MouseButton instance
        """

        if button == Qt.LeftButton:
            modifiers = QGuiApplication.keyboardModifiers()
            if self.editModes.addInstance:
                self._handleAddInstance(mousePos)
            elif self.editModes.drawPin:
                self._handleDrawPin(mousePos)
            elif self.editModes.drawWire:
                self._handleDrawWire(mousePos)
            elif self.editModes.drawBus:
                self._handleDrawBus(mousePos)
            elif self.editModes.drawText:
                self._handleDrawText(mousePos)
            elif self.editModes.rotateItem:
                self.rotateSelectedItems(mousePos)
            elif self.editModes.stretchItem:
                self._handleStretchItem()
            elif self.editModes.nameNet:
                self._handleNameNet(mousePos)


    def _handleSelectionRect(self, modifiers):
        self.clearSelection()
        selectionMode = (
            Qt.ItemSelectionMode.IntersectsItemShape
            if self.partialSelection
            else Qt.ItemSelectionMode.ContainsItemShape
        )
        selectionPath = QPainterPath()
        selectionPath.addRect(self._selectionRectItem.sceneBoundingRect())
        match modifiers:
            case Qt.KeyboardModifier.ShiftModifier:
                self._handleShiftSelection(selectionMode, selectionPath)
            case Qt.KeyboardModifier.ControlModifier:
                for item in self.items(selectionPath, mode=selectionMode):
                    item.setSelected(not item.isSelected())
            case _:
                for item in self.items(selectionPath, mode=selectionMode):
                    item.setSelected(True)
        self.removeItem(self._selectionRectItem)
        self._selectionRectItem = None

    def _handleShiftSelection(self, selectionMode, selectionPath):
        selectedItems = self.items(selectionPath, mode=selectionMode)

        type_map = {
            'selectNet': (snet.schematicNet, self.selectModes.selectNet),
            'selectDevice': (shp.schematicSymbol, self.selectModes.selectDevice),
            'selectPin': (shp.schematicPin, self.selectModes.selectPin)
        }

        for mode_name, (item_type, is_active) in type_map.items():
            if is_active:
                for item in selectedItems:
                    if isinstance(item, item_type):
                        item.setSelected(True)
                return

        # Default case - select all items
        self.setSelectionArea(selectionPath, mode=selectionMode)


    def _handleAddInstance(self, eventLoc: QPoint) -> None:
        """
        Handle add instance logic.

        :param eventLoc: QPoint instance
        """
        if self._newInstance:
            self._newInstance = None
        self._newInstance = self.drawInstance(self.newInstanceTuple, eventLoc)
        self._newInstance.setSelected(True)

    def _handleDrawPin(self, mouseReleaseLoc: QPoint) -> None:
        """
        Handle draw pin logic.

        :param mouseReleaseLoc: QPoint instance
        """
        # if self._newPin:
        #     self._newPin = None
        self._newPin = self.addPin(mouseReleaseLoc)
        self._newPin.setSelected(True)

    def _handleDrawWire(self, eventLoc: QPoint) -> None:
        """
        Handle draw wire logic.
        """
        if self._newNet:  # finish net drawing
            self._newNet.draftLine = QLineF(
                self._newNet.draftLine.p1(), self.snapToGrid(eventLoc, self.snapTuple)
            )
            self.wireEditFinished.emit(self._newNet)
            self._newNet = None

        startSnapPoint = self.snapToGrid(
            self.findSnapPoint(eventLoc, set()), self.snapTuple
        )

        self._snapPointRect.setPos(startSnapPoint)
        self._newNet = snet.schematicNet(startSnapPoint, startSnapPoint, 0)
        self.addUndoStack(self._newNet)

    def _handleDrawBus(self, eventLoc: QPoint):
        if self._newNet:
            self._newNet.draftLine = QLineF(
                self._newNet.draftLine.p1(), self.snapToGrid(eventLoc, self.snapTuple)
            )
            self.wireEditFinished.emit(self._newNet)
            self._newNet = None
        startSnapPoint = self.snapToGrid(
            self.findSnapPoint(eventLoc, set()), self.snapTuple
        )
        self._newNet = snet.schematicNet(startSnapPoint, startSnapPoint, 1)
        self.addUndoStack(self._newNet)

    def _handleDrawText(self, mouseReleaseLoc: QPoint) -> None:
        """
        Handle draw text logic.

        :param mouseReleaseLoc: QPoint instance
        """
        if self._newText:
            self._newText = None
            self.textTuple = None
        if self.textTuple:
            self._newText = self.addNote(mouseReleaseLoc, self.textTuple)

    def _handleStretchItem(self):
        if self._stretchNet:
            self._stretchNet.stretch = False
            self._stretchNet = None
            self._snapPointRect.setVisible(False)
            self.editModes.stretchItem = False

    def _handleNameNet(self, mouseReleaseLoc):
        if self.netNameString:
            self._newNetNameObj = snet.netName(self.netNameString)
            self._newNetNameObj.setPos(mouseReleaseLoc)
            self.addUndoStack(self._newNetNameObj)
            self.netNameString = None
        elif self._newNetNameObj and self.selectedNet:
            self.selectedNet.name = self._newNetNameObj.name
            self.undoStack.undo()
            # self.undoStack.removeLastCommand()
            self.selectedNet.nameStrength = snet.netNameStrengthEnum.SET
            self.selectedNet.setSelected(False)
            self.selectedNet = None

    def updateStretchNet(self):
        self._stretchNet.draftLine = QLineF(
            self._stretchNet.draftLine.p1(), self.mouseMoveLoc
        )

    @Slot(snet.schematicNet)
    def _handleWireFinished(self, newNet: snet.schematicNet):
        """
        check if the new net is valid. If it has zero length, remove it. Otherwise process it.

        """

        if newNet.draftLine.length() < self.snapDistance * 0.5:
            self.removeItem(newNet)
            self.undoStack.removeLastCommand()
        else:
            self.mergeSplitNets(newNet)

    def _updateNets(self, nets_to_remove: set, nets_to_add: set, name_source_net):
        """Helper to update nets in scene"""
        for net in nets_to_remove:
            self.removeItem(net)
        for net in nets_to_add:
            self.addItem(net)
            net.mergeNetName(name_source_net)

    def mergeSplitNets(self, inputNet: snet.schematicNet):
        merged, outputNet, processedNets = self.mergeNets(inputNet)

        if merged:
            splitDone, splitOutputNets = self.splitInputNet(outputNet)
            if splitDone:
                self._updateNets(processedNets - splitOutputNets,
                                 splitOutputNets - processedNets, outputNet)
            else:
                for net in processedNets:
                    self.removeItem(net)
                self.addItem(outputNet)
        else:
            splitDone, splitOutputNets = self.splitInputNet(inputNet)
            if splitDone:
                self._updateNets({inputNet} - splitOutputNets,
                                 splitOutputNets - {inputNet}, inputNet)

    def mergeNets(
            self, inputNet: snet.schematicNet
    ) -> Tuple[bool, snet.schematicNet, Set[snet.schematicNet]]:
        """
        Merges overlapping nets and returns the merged net.
        """
        otherNets = inputNet.findOverlapNets()
        if not otherNets:
            return False, inputNet, set()

        parallelNets = {net for net in otherNets if inputNet.isParallel(net)}
        if not parallelNets:
            return False, inputNet, set()

        points = list(inputNet.sceneEndPoints)  # Create a copy
        busExists = int(any(net.width for net in parallelNets) or inputNet.width)

        for net in parallelNets:
            points.extend(net.sceneEndPoints)

        furthestPoints = self.findFurthestPoints(points)
        mergedNet = snet.schematicNet(*furthestPoints, busExists)

        processedNets = parallelNets | {inputNet}
        for net in processedNets:
            mergedNet.mergeNetName(net)

        return True, mergedNet, processedNets

    def splitInputNet(self, inputNet) -> tuple[bool, Set[snet.schematicNet]]:
        sceneShapeRect = inputNet.sceneShapeRect
        sceneItems = self.items(sceneShapeRect)

        splitPointsSet = set()

        # Single iteration to collect all relevant points
        for item in sceneItems:
            if isinstance(item, snet.schematicNet) and inputNet.isOrthogonal(item):
                for point in item.sceneEndPoints:
                    if sceneShapeRect.contains(point):
                        splitPointsSet.add(point)
            elif isinstance(item, (shp.symbolPin, shp.schematicPin)):
                splitPointsSet.add(item.mapToScene(item.start).toPoint())

        if not splitPointsSet:
            return False, set()

        # Create ordered points list
        splitPointsList = [
            inputNet.sceneEndPoints[0],
            *splitPointsSet,
            inputNet.sceneEndPoints[1],
        ]
        orderedPoints = list(dict.fromkeys(self.orderPoints(splitPointsList)))

        # Create split nets
        splitNetSet = set()
        is_selected = inputNet.isSelected()

        for i in range(len(orderedPoints) - 1):
            splitNet = snet.schematicNet(
                orderedPoints[i], orderedPoints[i + 1], inputNet.width
            )
            if not splitNet.draftLine.isNull():
                if is_selected:
                    splitNet.setSelected(True)
                splitNetSet.add(splitNet)

        return True, splitNetSet

    def findSnapPoint(
        self, eventLoc: QPoint, ignoredSet: set[snet.schematicNet]
    ) -> QPoint:
        snapRect = QRect(
            eventLoc.x() - self.snapTuple[0],
            eventLoc.y() - self.snapTuple[1],
            2 * self.snapTuple[0],
            2 * self.snapTuple[1],
        )
        snapPoints = self.findConnectPoints(snapRect, ignoredSet)

        if self._newNet:
            snapPoints.update(self.findNetInterSect(self._newNet, snapRect))
        if snapPoints:
            lengths = [
                (snapPoint - eventLoc).manhattanLength() for snapPoint in snapPoints
            ]
            closestPoint = list(snapPoints)[lengths.index(min(lengths))]
            return closestPoint
        else:
            return eventLoc

    def findConnectPoints(
        self, sceneRect: QRect, ignoredSet: set[QGraphicsItem]
    ) -> set[QPoint]:
        snapPoints = set()
        rectItems = set(self.items(sceneRect)) - ignoredSet
        for item in rectItems:
            if isinstance(item, snet.schematicNet) and any(
                list(map(sceneRect.contains, item.sceneEndPoints))
            ):
                snapPoints.add(
                    item.sceneEndPoints[
                        list(map(sceneRect.contains, item.sceneEndPoints)).index(True)
                    ]
                )
            elif isinstance(item, shp.symbolPin):
                snapPoints.add(item.mapToScene(item.start).toPoint())
            elif isinstance(item, shp.schematicPin):
                snapPoints.add(item.mapToScene(item.start).toPoint())
        return snapPoints

    def findNetInterSect(self, inputNet: snet.schematicNet, rect: QRect) -> set[QPoint]:
        # Find all nets in the rectangle except the input net
        netsInSnapRectSet = {
            netItem
            for netItem in self.items(rect)
            if isinstance(netItem, snet.schematicNet) and netItem.isOrthogonal(inputNet)
        }
        snapPointsSet = set()
        l1 = QLineF(inputNet.sceneEndPoints[0], inputNet.sceneEndPoints[1])
        unitVector = l1.unitVector()
        dx = unitVector.dx() if unitVector.dx() else 0
        dy = unitVector.dy() if unitVector.dy() else 0
        newEndX = l1.x2() + rect.width() * dx
        newEndY = l1.y2() + rect.height() * dy
        extendedL1 = QLineF(l1.p1(), QPointF(newEndX, newEndY))
        for netItem in netsInSnapRectSet:
            l2 = QLineF(netItem.sceneEndPoints[0], netItem.sceneEndPoints[1])
            (_, intersectPoint) = extendedL1.intersects(l2)
            if intersectPoint:
                snapPointsSet.add(intersectPoint.toPoint())
        return snapPointsSet

    def findNetStretchPoints(
        self, netItem: snet.schematicNet, snapDistance: int
    ) -> dict[int, QPoint]:
        netEndPointsDict: dict[int, QPoint] = {}
        sceneEndPoints = netItem.sceneEndPoints
        for netEnd in sceneEndPoints:
            snapRect: QRect = QRect(
                netEnd.x() - snapDistance,
                netEnd.y() - snapDistance,
                2 * snapDistance,
                2 * snapDistance,
            )
            snapRectItems = set(self.items(snapRect)) - {netItem}

            for item in snapRectItems:
                if isinstance(item, snet.schematicNet) and any(
                    list(map(snapRect.contains, item.sceneEndPoints))
                ):
                    netEndPointsDict[sceneEndPoints.index(netEnd)] = netEnd
                elif (
                    isinstance(item, shp.symbolPin | shp.schematicPin)
                ) and snapRect.contains(item.mapToScene(item.start).toPoint()):
                    netEndPointsDict[sceneEndPoints.index(netEnd)] = item.mapToScene(
                        item.start
                    ).toPoint()
                if netEndPointsDict.get(
                    sceneEndPoints.index(netEnd)
                ):  # after finding one point, no need to iterate.
                    break
        return netEndPointsDict

    @staticmethod
    def orderPoints(points: list[QPoint]) -> list[QPoint]:
        currentPoint = points.pop(0)
        orderedPoints = [currentPoint]

        while points:
            distances = [(point - currentPoint).manhattanLength() for point in points]
            nearest_point_index = distances.index(min(distances))
            nearestPoint = points[nearest_point_index]
            orderedPoints.append(nearestPoint)
            currentPoint = points.pop(nearest_point_index)

        return orderedPoints

    @staticmethod
    def findFurthestPoints(points: list[QPoint]) -> tuple[QPoint, QPoint]:
        """
        Find the two points with the maximum distance between them.
        """
        max_distance = 0
        furthest_points = None

        for i in range(len(points)):
            for j in range(i + 1, len(points)):
                distance = (points[i] - points[j]).manhattanLength()
                if distance > max_distance:
                    max_distance = distance
                    furthest_points = (points[i], points[j])

        return furthest_points[0], furthest_points[1]

    def _handleStretchNet(self, netItem: snet.schematicNet, stretchEnd: str):
        match stretchEnd:
            case "p2":
                self._stretchNet = snet.schematicNet(
                    netItem.sceneEndPoints[0], netItem.sceneEndPoints[1]
                )
            case "p1":
                self._stretchNet = snet.schematicNet(
                    netItem.sceneEndPoints[1], netItem.sceneEndPoints[0]
                )
        self._stretchNet.stretch = True
        self._stretchNet.mergeNetName(netItem)
        addDeleteStretchNetCommand = us.addDeleteShapeUndo(
            self, self._stretchNet, netItem
        )
        self.undoStack.push(addDeleteStretchNetCommand)

    def generatePinNetMap(self, sceneSymbolSet: set[shp.schematicSymbol]):
        """
        For symbols in sceneSymbolSet, find which pin is connected to which net.
        Handles both single pins and bus connections.
        """
        for symbolItem in sceneSymbolSet:
            self.genSymbolPinNetMap(symbolItem)

    def genSymbolPinNetMap(self, symbolItem: shp.schematicSymbol):
        # Process connected pins and collect unconnected ones in single pass
        unconnectedPins = []
        for pinName, pinItem in symbolItem.pins.items():
            netsConnectedToPin = [
                netItem for netItem in pinItem.collidingItems(Qt.IntersectsItemBoundingRect)
                if isinstance(netItem, snet.schematicNet)
            ]
            if netsConnectedToPin:
                netName = netsConnectedToPin[0].name
                symbolItem.pinNetMap[pinName] = netName
                pinItem.connected = True
            else:
                pinItem.connected = False
                unconnectedPins.append(pinName)

        # Assign nets to unconnected pins
        for pin in unconnectedPins:
            symbolItem.pinNetMap[pin] = f"dnet{self.netCounter}"
            self.netCounter += 1

        # Handle pin ordering
        pinOrder = symbolItem.symattrs.get("pinOrder")
        if pinOrder:
            ordered_map = {}
            pinNames = (item.strip() for item in pinOrder.split(","))
            for pinName in pinNames:
                ordered_map[pinName] = symbolItem.pinNetMap[pinName]
            symbolItem.pinNetMap = ordered_map

    def findSceneSymbolSet(self) -> set[shp.schematicSymbol]:
        """
        Find all the symbols on the scene as a set.
        """
        return {item for item in self.items() if isinstance(item, shp.schematicSymbol)}

    def findSceneNetsSet(self) -> set[snet.schematicNet]:
        return {item for item in self.items() if isinstance(item, snet.schematicNet)}

    def findRectSymbolPin(self, rect: Union[QRect, QRectF]) -> set[shp.symbolPin]:
        pinsRectSet = {
            item for item in self.items(rect) if isinstance(item, shp.symbolPin)
        }
        return pinsRectSet

    def findRectSchemPins(self, rect: Union[QRect, QRectF]) -> set[shp.schematicPin]:
        pinsRectSet = {
            item for item in self.items(rect) if isinstance(item, shp.schematicPin)
        }
        return pinsRectSet

    def findSceneSchemPinsSet(self) -> set[shp.schematicPin]:
        pinsSceneSet = {
            item for item in self.items() if isinstance(item, shp.schematicPin)
        }
        if pinsSceneSet:  # check pinsSceneSet is empty
            return pinsSceneSet
        else:
            return set()

    def findSceneTextSet(self) -> set[shp.text]:
        if textSceneSet := {
            item for item in self.items() if isinstance(item, shp.text)
        }:
            return textSceneSet
        else:
            return set()

    def addStretchWires(self, start: QPoint, end: QPoint) -> List["snet.schematicNet"]:
        """
        Add a trio of wires between two points.

        Args:
            start (QPoint): The starting point of the wire.
            end (QPoint): The ending point of the wire.

        Returns:
            List[snet.schematicNet]: A list of schematic net objects representing the wires.
        """
        try:
            if start == end:
                self.logger.warning("Start and end points are the same. No wire added.")
                return []

            if start.y() == end.y() or start.x() == end.x():
                # Horizontal or vertical line
                return [snet.schematicNet(start, end)]

            # Calculate intermediate points
            firstPointX = self.snapToBase(
                (end.x() - start.x()) / 3 + start.x(), self.snapTuple[0]
            )
            firstPoint = QPoint(firstPointX, start.y())
            secondPoint = QPoint(firstPointX, end.y())

            # Create wire segments
            lines = []
            segments = [
                (start, firstPoint),
                (firstPoint, secondPoint),
                (secondPoint, end),
            ]
            for seg_start, seg_end in segments:
                if seg_start != seg_end:
                    lines.append(snet.schematicNet(seg_start, seg_end))

            return lines

        except Exception as e:
            self.logger.error(f"Error in addStretchWires: {e}", exc_info=True)
            return []

    def addPin(self, pos: QPoint) -> shp.schematicPin|None:
        try:
            pin = shp.schematicPin(pos, self.pinName, self.pinDir, self.pinType)
            self.addUndoStack(pin)
            return pin
        except Exception as e:
            self.logger.error(f"Pin add error: {e}")

    def addNote(self, pos: QPoint, textTuple: Tuple) -> shp.text:
        """
        Changed the method name not to clash with qgraphicsscene addText method.
        """
        text = shp.text(pos, *textTuple)
        self.addUndoStack(text)
        return text

    def drawInstance(self, instanceTuple: ddef.viewTuple, pos: QPoint):
        """
        Add an instance of a symbol to the scene.
        """
        instance = self.instSymbol(instanceTuple, pos)
        if instance:  # Add check for None
            self.instanceCounter += 1
            self.addUndoStack(instance)
            return instance
        else:
            return None

    def instSymbol(self, instanceTuple: ddef.viewTuple, pos: QPoint):
        viewItem = libm.findViewItem(
            self.editorWindow.libraryView.libraryModel,
            instanceTuple.libraryName,
            instanceTuple.cellName,
            instanceTuple.viewName,
        )
        viewPath = viewItem.viewPath
        try:
            # Try to get items from cache first
            items = self._symbolCache.get(viewPath)
            if items is None:
                with open(viewPath, "r") as temp:
                    items = json.load(temp)
                    self._symbolCache[viewPath] = items

            # if (items[0].get("viewType", "") != "symbol" or items[0].get("cellView", "") != "symbol"):
            #     self.logger.error("Not a symbol!")
            #     return None

            # Use comprehensions for better performance
            itemAttributes = {
                item["nam"]: item["def"] for item in items[2:] if item["type"] == "attr"
            }

            itemShapes = [
                lj.symbolItems(self).create(item)
                for item in items[2:]
                if item["type"] != "attr"
            ]
            symbolInstance = shp.schematicSymbol(itemShapes, itemAttributes)
            cellItem = viewItem.parent()
            libItem = cellItem.parent()
            # Batch property assignments
            instanceProperties = {
                "pos": pos,
                "counter": self.instanceCounter,
                "instanceName": f"I{self.instanceCounter}",
                "libraryName": libItem.libraryName,
                "cellName": cellItem.cellName,
                "viewName": viewItem.viewName,
            }

            for prop, value in instanceProperties.items():
                setattr(symbolInstance, prop, value)
            # as pylabels can depend on NLPLabel results, process first
            # NLP Labels.
            for labelItem in symbolInstance.labels.values():
                if labelItem.labelType==lbl.symbolLabel.labelTypes[1]:
                    labelItem.labelDefs()
            for labelItem in symbolInstance.labels.values():
                if labelItem.labelType==lbl.symbolLabel.labelTypes[2]:
                    labelItem.labelDefs()

            return symbolInstance

        except FileNotFoundError:
            self.logger.error(f"Symbol file not found: {viewPath}")
            return None
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON in symbol file: {viewPath}")
            return None
        except Exception as e:
            self.logger.warning(f"instantiation error: {e}")
            return None

    def copySelectedItems(self):
        selectedItems = [
            item for item in self.selectedItems() if item.parentItem() is None
        ]
        if selectedItems:
            for item in selectedItems:
                selectedItemJson = json.dumps(item, cls=schenc.schematicEncoder)
                itemCopyDict = json.loads(selectedItemJson)
                shape = lj.schematicItems(self).create(itemCopyDict)
                if shape is not None:
                    item.setSelected(False)
                    self.addUndoStack(shape)
                    shape.setSelected(True)
                    # shift position by four grid units to right and down
                    shape.setPos(
                        QPoint(
                            int(item.x() + 4 * self.snapTuple[0]),
                            int(item.y() + 4 * self.snapTuple[1]),
                        )
                    )
                    if isinstance(shape, shp.schematicSymbol):
                        self.instanceCounter += 1
                        shape.instanceName = f"I{self.instanceCounter}"
                        shape.counter = int(self.instanceCounter)
                        [label.labelDefs() for label in shape.labels.values()]

    def saveSchematic(self, file: pathlib.Path):
        """
        Save the schematic to a file with optimized memory usage and error handling.

        Args:
            file (pathlib.Path): The file path to save the schematic to.

        Raises:
            IOError: If there are file operation errors
            JSONEncodeError: If there are JSON serialization errors
        """
        try:
            # Ensure parent directory exists
            file.parent.mkdir(parents=True, exist_ok=True)

            # Create temporary file in the same directory
            tempFile = file.with_suffix(".tmp")
            # Write to temporary file first
            with self.measureDuration():
                with tempFile.open(mode="w", buffering=8192) as f:
                    # Start array
                    f.write("[\n")

                    header_items = [
                        {"viewType": "schematic"},
                        {"snapGrid": self.snapTuple},
                    ]
                    json.dump(header_items[0], f)
                    f.write(",\n")
                    json.dump(header_items[1], f)
                    # Get top-level items more efficiently
                    # topLevelItems = {
                    #     item for item in self.items() if item.parentItem() is None
                    # }
                    topLevelItems = filter(lambda item: isinstance(item, self.SCHEMATIC_SHAPES), self.items())
                    # Stream items
                    for item in list(topLevelItems):
                        f.write(",\n")
                        try:
                            json.dump(item, f, cls=schenc.schematicEncoder)
                        except Exception as json_err:
                            self.logger.error(
                                f"Failed to serialize item: {str(json_err)}"
                            )
                            return

                    # Close array
                    f.write("\n]")

                    # Ensure all data is written to disk
                    f.flush()
                    os.fsync(f.fileno())

                # Atomic file replacement
                tempFile.replace(file)

                self.logger.info(
                    f"Saved schematic to {self.editorWindow.cellName}:"
                    f"{self.editorWindow.viewName}"
                )

        except IOError as io_err:
            self.logger.error(f"IO Error while saving schematic: {str(io_err)}")
            return
        except Exception as e:
            self.logger.error(f"Unexpected error while saving schematic: {str(e)}")
            # Clean up temporary file if it exists
            if tempFile.exists():
                tempFile.unlink()
            return

    @staticmethod
    def findEditorTypeString(editorWindow):
        """
        This function returns the type of the parent editor as a string.
        The type of the parent editor is determined by finding the last dot in the
        string representation of the type of the parent editor and returning the
        string after the last dot. If there is no dot in the string representation
        of the type of the parent editor, the entire string is returned.
        """
        index: int = str(type(editorWindow)).rfind(".")
        if index == -1:
            return str(type(editorWindow))
        else:
            return str(type(editorWindow))[index + 1 : -2]

    def loadDesign(self, filePathObj: pathlib.Path) -> None:
        """
        Load schematic from a JSON file and initialize grid settings.

        Args:
            filePathObj (pathlib.Path): Path to the schematic JSON file

        Raises:
            JSONDecodeError: If the file contains invalid JSON
            FileNotFoundError: If the specified file doesn't exist
            KeyError: If required grid settings are missing
        """
        try:
            with filePathObj.open("r") as file:
                decodedData = json.load(file)
            with self.measureDuration():
                if len(decodedData) < 2:
                    viewDict = decodedData[0] if decodedData else {}
                    gridSettings = None
                    itemData = []
                else:
                    viewDict, gridSettings, *itemData = decodedData
                
                if viewDict.get("viewType") != "schematic":
                    self.logger.error("Not a schematic file!")
                    return
                
                if gridSettings and gridSettings.get("snapGrid"):
                    self.configureGridSettings(gridSettings)
                else:
                    self.configureGridSettings({'snapGrid': [self.editorWindow.MAJOR_GRID_DEFAULT, self.editorWindow.SNAP_GRID_DEFAULT]})
                self.createSchematicItems(itemData)
                # self._snapPointRect = self.defineSnapRect()
                # self.addItem(self._snapPointRect)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            self.logger.error(f"File error while loading schematic: {e}")
            return
        except KeyError as e:
            self.logger.error(f"Invalid schematic format - missing key: {e}")
            return
        except Exception as e:
            self.logger.error(f"Unexpected error loading schematic: {e}")
            return

    def createSchematicItems(self, itemsList: List[Dict]):
        for itemDict in itemsList:
            itemShape = lj.schematicItems(self).create(itemDict)
            if (
                isinstance(itemShape, shp.schematicSymbol)
                and itemShape.counter > self.instanceCounter
            ):
                self.instanceCounter = itemShape.counter + 1

            if itemShape is not None:
                self.addItem(itemShape)

    def reloadScene(self):
        super().reloadScene()


    def viewObjProperties(self):
        """
        Display the properties of the selected object.
        """
        try:
            selectedItems = [
                item for item in self.selectedItems() if item.parentItem() is None
            ]
            if selectedItems:
                for item in selectedItems:
                    item.prepareGeometryChange()
                    if isinstance(item, shp.schematicSymbol):
                        self.setInstanceProperties(item)
                    elif isinstance(item, snet.schematicNet):
                        self.setNetProperties(item)
                    elif isinstance(item, shp.text):
                        self.setTextProperties(item)
                    elif isinstance(item, shp.schematicPin):
                        self.setSchematicPinProperties(item)
                    elif isinstance(item, snet.netName):
                        self.setNetProperties(item.parentItem())
        except Exception as e:
            self.logger.error(e)

    def setInstanceProperties(self, item: shp.schematicSymbol):
        dlg = pdlg.instanceProperties(self.editorWindow)
        dlg.libNameEdit.setText(item.libraryName)
        dlg.cellNameEdit.setText(item.cellName)
        dlg.viewNameEdit.setText(item.viewName)
        dlg.instNameEdit.setText(item.instanceName)
        location = (item.scenePos() - self.origin).toTuple()
        dlg.xLocationEdit.setText(str(location[0]))
        dlg.yLocationEdit.setText(str(location[1]))
        dlg.angleEdit.setText(str(item.angle))
        row_index = 0
        # iterate through the item labels.
        for label in item.labels.values():
            if label.labelDefinition not in lbl.symbolLabel.predefinedLabels:
                dlg.instanceLabelsLayout.addWidget(
                    edf.boldLabel(label.labelName[1:], dlg), row_index, 0
                )
                labelValueEdit = edf.longLineEdit()
                labelValueEdit.setText(str(label.labelValue))
                dlg.instanceLabelsLayout.addWidget(labelValueEdit, row_index, 1)
                visibleCombo = QComboBox(dlg)
                visibleCombo.setInsertPolicy(QComboBox.NoInsert)
                visibleCombo.addItems(["True", "False"])
                if label.labelVisible:
                    visibleCombo.setCurrentIndex(0)
                else:
                    visibleCombo.setCurrentIndex(1)
                dlg.instanceLabelsLayout.addWidget(visibleCombo, row_index, 2)
                row_index += 1
        # now list instance attributes
        for counter, name in enumerate(item.symattrs.keys()):
            dlg.instanceAttributesLayout.addWidget(edf.boldLabel(name, dlg), counter, 0)
            labelNameEdit = edf.longLineEdit()
            labelNameEdit.setText(item.symattrs.get(name))
            labelNameEdit.setReadOnly(True)
            labelNameEdit.setToolTip(f"{name} attribute (Read Only)")
            dlg.instanceAttributesLayout.addWidget(labelNameEdit, counter, 1)
        if dlg.exec() == QDialog.Accepted:
            libraryName = dlg.libNameEdit.text().strip()
            cellName = dlg.cellNameEdit.text().strip()
            viewName = dlg.viewNameEdit.text().strip()
            instanceTuple = ddef.viewTuple(libraryName, cellName, viewName)
            location = QPoint(
                int(float(dlg.xLocationEdit.text().strip())),
                int(float(dlg.yLocationEdit.text().strip())),
            )
            newInstance = self.instSymbol(instanceTuple, location + self.origin)

            if newInstance:
                newInstance.instanceName = dlg.instNameEdit.text().strip()
                newInstance.angle = float(dlg.angleEdit.text().strip())
                newInstance.counter = item.counter

                tempDoc = QTextDocument()
                for i in range(dlg.instanceLabelsLayout.rowCount()):
                    labelNameItem = dlg.instanceLabelsLayout.itemAtPosition(i, 0)
                    labelValueItem = dlg.instanceLabelsLayout.itemAtPosition(i, 1)
                    labelVisibleItem = dlg.instanceLabelsLayout.itemAtPosition(i, 2)
                    
                    if not (labelNameItem and labelValueItem and labelVisibleItem):
                        continue
                    
                    # first create label name document with HTML annotations
                    tempDoc.setHtml(labelNameItem.widget().text())
                    # now strip html annotations
                    tempLabelName = f"@{tempDoc.toPlainText().strip()}"
                    # check if label name is in label dictionary of item.
                    if newInstance.labels.get(tempLabelName):
                        # this is where the label value is set.
                        newInstance.labels[tempLabelName].labelValue = labelValueItem.widget().text()
                        visible = labelVisibleItem.widget().currentText()
                        newInstance.labels[tempLabelName].labelVisible = (visible == "True")
                [labelItem.labelDefs() for labelItem in newInstance.labels.values()]
                newInstance.setPos(
                    self.snapToGrid(location, self.snapTuple) + self.origin
                )
                newInstance.flipTuple = item.flipTuple
                self.undoStack.push(us.addDeleteShapeUndo(self, newInstance, item))

    def setNetProperties(self, netItem: snet.schematicNet):
        dlg = pdlg.netProperties(self.editorWindow)
        dlg.netStartPointEditX.setText(
            str(round(netItem.mapToScene(netItem.draftLine.p1()).x()))
        )
        dlg.netStartPointEditY.setText(
            str(round(netItem.mapToScene(netItem.draftLine.p1()).y()))
        )
        dlg.netEndPointEditX.setText(
            str(round(netItem.mapToScene(netItem.draftLine.p2()).x()))
        )
        dlg.netEndPointEditY.setText(
            str(round(netItem.mapToScene(netItem.draftLine.p2()).y()))
        )
        dlg.netNameEdit.setText(netItem.name)
        dlg.widthButtonGroup.button(netItem.width).setChecked(True)
        if dlg.exec() == QDialog.Accepted:
            netName = dlg.netNameEdit.text().strip()
            netStartX = float(dlg.netStartPointEditX.text())
            netStartY = float(dlg.netStartPointEditY.text())
            netStart = self.snapToGrid(QPoint(netStartX, netStartY), self.snapTuple)
            netEndX = float(dlg.netEndPointEditX.text())
            netEndY = float(dlg.netEndPointEditY.text())
            netEnd = self.snapToGrid(QPoint(netEndX, netEndY), self.snapTuple)
            newNet = snet.schematicNet(netStart, netEnd, netItem.mode)
            newNet.nameStrength = snet.netNameStrengthEnum.SET
            if self.isValidNetName(netName):
                newNet.name = netName
            else:
                self.logger.warning(f"{netName} is malformed, please correct.")
                newNet.name = netItem.name
            newNet.width = dlg.widthButtonGroup.checkedId()
            self.undoStack.push(us.addDeleteShapeUndo(self, newNet, netItem))

    def setTextProperties(self, item):
        dlg = pdlg.noteTextEdit(self.editorWindow)
        dlg.plainTextEdit.setText(item.textContent)
        dlg.familyCB.setCurrentText(item.fontFamily)
        dlg.fontStyleCB.setCurrentText(item.fontStyle)
        dlg.fontsizeCB.setCurrentText(item.textHeight)
        dlg.textAlignmCB.setCurrentText(item.textAlignment)
        dlg.textOrientCB.setCurrentText(item.textOrient)
        if dlg.exec() == QDialog.Accepted:
            # item.prepareGeometryChange()
            start = item.mapToScene(item.start)
            newText = shp.text(
                start,
                dlg.plainTextEdit.toPlainText(),
                dlg.familyCB.currentText(),
                dlg.fontStyleCB.currentText(),
                dlg.fontsizeCB.currentText(),
                dlg.textAlignmCB.currentText(),
                dlg.textOrientCB.currentText(),
            )
            self.rotateAnItem(start, newText, int(float(item.textOrient[1:])))
            self.undoStack.push(us.addDeleteShapeUndo(self, newText, item))
        return item

    def setSchematicPinProperties(self, item: shp.schematicPin):
        dlg = pdlg.schematicPinPropertiesDialog(self.editorWindow)
        dlg.pinName.setText(item.pinName)
        dlg.pinDir.setCurrentText(item.pinDir)
        dlg.pinType.setCurrentText(item.pinType)
        dlg.angleEdit.setText(str(item.angle))
        dlg.xlocationEdit.setText(str(item.mapToScene(item.start).x()))
        dlg.ylocationEdit.setText(str(item.mapToScene(item.start).y()))
        if dlg.exec() == QDialog.Accepted:
            pinName = dlg.pinName.text().strip()
            pinDir = dlg.pinDir.currentText()
            pinType = dlg.pinType.currentText()
            itemStartPos = QPoint(
                int(float(dlg.xlocationEdit.text().strip())),
                int(float(dlg.ylocationEdit.text().strip())),
            )
            start = self.snapToGrid(itemStartPos - self.origin, self.snapTuple)
            angle = float(dlg.angleEdit.text().strip())
            newPin = shp.schematicPin(QPoint(0,0), pinName, pinDir, pinType)
            newPin.setPos(start)
            newPin.angle = angle
            self.undoStack.push(us.addDeleteShapeUndo(self, newPin, item))

    def hilightNets(self):
        """
        Show the connections the selected items.
        """
        try:
            self.highlightNets = bool(self.editorWindow.hilightNetAction.isChecked())
        except Exception as e:
            self.logger.error(e)

    def goDownHier(self):
        """
        Go down the hierarchy, opening the selected view.
        """
        try:
            selectedSymbol = [
                item
                for item in self.selectedItems()
                if isinstance(item, shp.schematicSymbol)
            ][0]

            if isinstance(selectedSymbol, shp.schematicSymbol):
                dlg = fd.goDownHierDialogue(self.editorWindow)
                libItem = libm.getLibItem(
                    self.editorWindow.libraryView.libraryModel,
                    selectedSymbol.libraryName,
                )
                cellItem = libm.getCellItem(libItem, selectedSymbol.cellName)
                viewNames = [
                    cellItem.child(i).text()
                    for i in range(cellItem.rowCount())
                    if "schematic" in cellItem.child(i).text()
                    or "symbol" in cellItem.child(i).text()
                ]
                dlg.viewListCB.addItems(viewNames)
                if dlg.exec() == QDialog.Accepted:
                    selectedSymbol.setSelected(False)
                    self.saveSchematic(self.editorWindow.file)
                    libItem = libm.getLibItem(
                        self.editorWindow.libraryView.libraryModel,
                        selectedSymbol.libraryName,
                    )
                    cellItem = libm.getCellItem(libItem, selectedSymbol.cellName)
                    viewItem = libm.getViewItem(cellItem, dlg.viewListCB.currentText())

                    openViewTuple = self.editorWindow.libraryView.libBrowsW.openCellView(
                        viewItem, cellItem, libItem
                    )
                    if viewItem.viewType == "schematic":
                        parentInstanceName = [
                            labelItem.labelValue
                            for labelItem in selectedSymbol.labels.values()
                            if labelItem.labelType == "NLPLabel"
                            and labelItem.labelDefinition == "[@instName]"
                        ][0]
                        self.editorWindow.appMainW.openViews[
                            openViewTuple
                        ].centralW.scene.hierarchyTrail = (
                            f"{self.hierarchyTrail}{parentInstanceName}."
                        )
                    if self.editorWindow.appMainW.openViews[openViewTuple]:
                        childWindow = self.editorWindow.appMainW.openViews[openViewTuple]
                        childWindow.parentEditor = self.editorWindow
                        childWindow.parentObj = selectedSymbol
                        childWindowType = self.findEditorTypeString(childWindow)

                        if childWindowType == "symbolEditor":
                            childWindow.symbolToolbar.addAction(childWindow.goUpAction)
                        elif childWindowType == "schematicEditor":
                            childWindow.schematicToolbar.addAction(childWindow.goUpAction)
                        if dlg.buttonId == 2:
                            childWindow.centralW.scene.readOnly = True
        except IndexError:
            pass

    def ignoreSymbol(self):
        if self.selectedItems() is not None:
            for item in self.selectedItems():
                if isinstance(item, shp.schematicSymbol):
                    item.netlistIgnore = not item.netlistIgnore
        else:
            self.logger.warning("No symbol selected")

    def selectInRectItems(self, selectionRect: QRect, partialSelection=False):
        """
        Select items in the scene.
        """

        mode = Qt.IntersectsItemShape if partialSelection else Qt.ContainsItemShape
        if self.selectModes.selectAll:
            [item.setSelected(True) for item in self.items(selectionRect, mode=mode)]
        elif self.selectModes.selectDevice:
            [
                item.setSelected(True)
                for item in self.items(selectionRect, mode=mode)
                if isinstance(item, shp.schematicSymbol)
            ]
        elif self.selectModes.selectNet:
            [
                item.setSelected(True)
                for item in self.items(selectionRect, mode=mode)
                if isinstance(item, snet.schematicNet)
            ]
        elif self.selectModes.selectPin:
            [
                item.setSelected(True)
                for item in self.items(selectionRect, mode=mode)
                if isinstance(item, shp.schematicPin)
            ]

    def renumberInstances(self):
        symbolList = [
            item for item in self.items() if isinstance(item, shp.schematicSymbol)
        ]

        for index, symbolInstance in enumerate(symbolList):
            symbolInstance.counter = index
            if symbolInstance.instanceName.startswith("I"):
                symbolInstance.instanceName = f"I{index}"
                for label in symbolInstance.labels.values():
                    label.labelDefs()
        self.instanceCounter = index + 1
        self.saveSchematic(self.editorWindow.file)
        self.reloadScene()

    # def findConnectedNetSet(
    #     self, netItem: snet.schematicNet, otherNets: set[snet.schematicNet]
    # ) -> set[snet.schematicNet]:
    #     """
    #     Find all nets connected to a net.
    #     """

    #     return {
    #         otherNetItem
    #         for otherNetItem in otherNets
    #         if otherNetItem.name == netItem.name
    #     }

    def _processNetGroup(
        self, namedNets: Set[snet.schematicNet], remainingNets: Set[snet.schematicNet]
    ):
        """Process a group of named nets and their connections."""
        while namedNets:
            net = namedNets.pop()
            connectedNets = self.findConnectedNets(net, remainingNets)
            for connectedNet in connectedNets:
                connectedNet.mergeNetName(net)
            remainingNets -= connectedNets

    def findConnectedNets(
        self, startNet: snet.schematicNet, candidateNets: Set[snet.schematicNet]
    ) -> Set[snet.schematicNet]:
        """Find all nets connected to startNet using DFS without mutating input."""
        connected = set()
        stack = [startNet]
        visited = {startNet}

        while stack:
            currentNet = stack.pop()
            for candidateNet in candidateNets:
                if candidateNet not in visited and self.checkNetConnect(
                    currentNet, candidateNet
                ):
                    connected.add(candidateNet)
                    stack.append(candidateNet)
                    visited.add(candidateNet)

        return connected

    def nameSceneNets(self):
        """
        Name all nets in the scene.
        """
        netCounter = 0
        schematicSymbolSet = self.findSceneSymbolSet()
        sceneNetsSet: Set[snet.schematicNet] = self.findSceneNetsSet()

        # Clear existing names
        for netItem in sceneNetsSet:
            netItem.clearName()

        # Process in priority order
        globalNetsSet = self.findGlobalNets(schematicSymbolSet)
        sceneNetsSet -= globalNetsSet
        self._processNetGroup(globalNetsSet, sceneNetsSet)

        schemPinConNetsSet = self.findSchPinNets()
        sceneNetsSet -= schemPinConNetsSet
        self._processNetGroup(schemPinConNetsSet, sceneNetsSet)

        namedNetsSet = {net for net in sceneNetsSet if net.nameStrength.value == 3}
        sceneNetsSet -= namedNetsSet
        self._processNetGroup(namedNetsSet, sceneNetsSet)

        # Auto-name remaining nets
        while sceneNetsSet:
            net = sceneNetsSet.pop()
            net.name = f"net{netCounter}"
            net.nameStrength = snet.netNameStrengthEnum.WEAK
            connectedNets = self.findConnectedNets(net, sceneNetsSet)
            for connectedNet in connectedNets:
                connectedNet.mergeNetName(net)
            sceneNetsSet -= connectedNets
            netCounter += 1

        self.netCounter = netCounter

    # Net finding methods
    def findGlobalNets(
        self, symbolSet: set[shp.schematicSymbol]
    ) -> set[snet.schematicNet]:
        """
        This method finds all nets connected to global pins.
        """
        globalNetsSet = set()

        # Find all global pins in one pass
        globalPins = (
            pinItem
            for symbol in symbolSet
            for pinName, pinItem in symbol.pins.items()
            if pinName.endswith("!")
        )

        for pinItem in globalPins:
            try:
                # Get nets connected to this global pin
                connectedNets = (
                    netItem
                    for netItem in pinItem.collidingItems(Qt.IntersectsItemShape)
                    if isinstance(netItem, snet.schematicNet)
                )

                for netItem in connectedNets:
                    if netItem.nameStrength.value == 3:  # Strong name
                        if netItem.name != pinItem.pinName:
                            netItem.nameConflict = True
                            self.logger.error(
                                f"Net name conflict at {pinItem.pinName} of "
                                f"{pinItem.parent.instanceName}."
                            )
                        else:
                            globalNetsSet.add(netItem)
                    else:
                        globalNetsSet.add(netItem)
                        netItem.name = pinItem.pinName
                        netItem.nameStrength = snet.netNameStrengthEnum.SET

            except AttributeError as e:
                self.logger.error(f"Error processing global pin {pinItem}: {e}")

        return globalNetsSet

    def _processNetPinConnection(
        self, net: snet.schematicNet, pinName: str, resultSet: set
    ) -> None:
        """Common logic for processing net-pin connections."""
        if net.nameStrength.value == 3:  # Strong name
            if net.name != pinName:
                net.nameConflict = True
                self.logger.error(
                    f"Net name conflict: net '{net.name}' vs pin '{pinName}'"
                )
            else:
                resultSet.add(net)
        else:
            resultSet.add(net)
            net.name = pinName
            net.nameStrength = snet.netNameStrengthEnum.SET


    def findSchPins(self, net:snet.schematicNet) -> set[shp.schematicPin]:
        return {pinItem for pinItem in net.collidingItems(
            Qt.IntersectsItemShape) if isinstance(pinItem, shp.schematicPin)}

    def findSchPinNets(self) -> set[snet.schematicNet]:
        """Find nets connected to schematic pins."""
        schemPinConNetsSet = set()

        for sceneSchemPin in self.findSceneSchemPinsSet():
            try:
                # Use collision detection for better performance
                connectedNets = (
                    netItem
                    for netItem in sceneSchemPin.collidingItems(Qt.IntersectsItemShape)
                    if isinstance(netItem, snet.schematicNet)
                )
                for netItem in connectedNets:
                    self._processNetPinConnection(netItem, sceneSchemPin.pinName, schemPinConNetsSet)


            except (AttributeError, ValueError) as e:
                self.logger.error(
                    f"Error processing schematic pin {sceneSchemPin.pinName}: {e}"
                )

        return schemPinConNetsSet

    def checkErrors(self):
        """
        Check for errors in the schematic.
        """
        self.logger.info("Checking for errors...")
        symbolSet = self.findSceneSymbolSet()
        overlapExists, overlapRects = schk.checkSymbolOverlaps(symbolSet)
        if overlapExists:
            errorPen = QPen(Qt.red, 1, Qt.DashDotLine)
            for rect in overlapRects:
                self.overlapRectSet.add(self.addRect(rect, errorPen))

    def deleteErrors(self):
        self.logger.info("Deleting errors...")
        for rectItem in self.overlapRectSet:
            self.removeItem(rectItem)

    @staticmethod
    def checkNetConnect(netItem, otherNetItem):
        """
        Determine if a net is connected to another one. One net should end on the other net.
        """
        if netItem is otherNetItem:
            return False

        # Check if any endpoint pairs are within connection tolerance
        return any(
            (netEnd - otherEnd).manhattanLength() <= 1
            for netEnd in netItem.sceneEndPoints
            for otherEnd in otherNetItem.sceneEndPoints
        )

    @staticmethod
    def isValidNetName(text: str) -> bool:
        """
        Validates if the string is either:
        1. A string without any < or > characters
        2. A string ending with <int> where int is a positive integer
        3. A string ending with <int:int> where int is a positive integer

        Returns True if valid, False otherwise
        """
        # Pattern for string ending with <int> or <int:int>
        bus_pattern = QRegularExpression(r"^.*<(\d+)(?::(\d+))?>$")

        # Pattern to detect any partial bus notation
        partial_pattern = QRegularExpression(r"[<>:]")

        # If there are no <, >, or : characters, it's a valid simple string
        if not partial_pattern.match(text).hasMatch():
            return True

        # If it contains any of <, >, or :, check if it ends with complete pattern
        match = bus_pattern.match(text)
        if match.hasMatch() and text.count("<") == 1 and text.count(">") == 1:
            return True
        return False

