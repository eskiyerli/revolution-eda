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
import revedaEditor.common.net as net
import revedaEditor.backend.undoStack as us
from collections import Counter

# import numpy as np
from PySide6.QtCore import (QPoint, QRect, Qt, Signal, QLine,)
from PySide6.QtGui import (QColor, QKeyEvent, QPainter, QWheelEvent, QPolygon, )
from PySide6.QtWidgets import (QGraphicsView, )
from PySide6.QtPrintSupport import (QPrinter,)
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from revedaEditor.backend.pdkPaths import importPDKModule

schlyr = importPDKModule('schLayers')



class editorView(QGraphicsView):
    """
    The qgraphicsview for qgraphicsscene. It is used for both schematic and layout editors.
    """
    keyPressedSignal = Signal(int)

    # zoomFactorChanged = Signal(float)
    def __init__(self, scene, parent):
        super().__init__(scene, parent)
        
        # Cache parent references
        self.parent = parent
        self.editor = parent.parent
        self.scene = scene
        self.logger = scene.logger
        
        # Cache editor properties
        editor = self.editor
        self.majorGrid = editor.majorGrid
        self.snapGrid = editor.snapGrid
        self.snapTuple = editor.snapTuple
        
        # Direct attribute initialization
        self.gridbackg = True
        self.linebackg = self._transparent = False
        self.zoomFactor = 1.0
        
        # Initialize coordinate cache as integers (faster than QPoint)
        self._left = self._right = self._top = self._bottom = 0
        
        # Defer expensive operations
        self.viewRect = None
        self.init_UI()

    def init_UI(self):
        """
        Initializes the user interface.
        """
        # Cache constants
        anchor = QGraphicsView.AnchorUnderMouse
        render_hints = QPainter.Antialiasing | QPainter.TextAntialiasing
        
        # Batch all settings in sequence to minimize Qt overhead
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        # self.setCacheMode(QGraphicsView.CacheBackground)
        self.setMouseTracking(True)
        self.setTransformationAnchor(anchor)
        self.setResizeAnchor(anchor)
        self.setInteractive(True)
        self.setCursor(Qt.CrossCursor)
        self.setRenderHints(render_hints)
        
        # Single flag for deferred calculation
        self._viewRect_cached = False

    def wheelEvent(self, event: QWheelEvent) -> None:
        """
        Handle the wheel event for zooming in and out of the view.

        Args:
            event (QWheelEvent): The wheel event to handle.
        """
        # Get the current center point of the view
        oldPos = self.mapToScene(self.viewport().rect().center())

        # Perform the zoom
        self.zoomFactor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
        self.scale(self.zoomFactor, self.zoomFactor)

        # Get the new center point of the view
        newPos = self.mapToScene(self.viewport().rect().center())

        # Calculate the delta and adjust the scene position
        delta = newPos - oldPos
        self.translate(delta.x(), delta.y())
        if not self._viewRect_cached:
            self.viewRect = self.mapToScene(self.rect()).boundingRect().toRect()
            self._viewRect_cached = True



    def drawBackground(self, painter, rect):
        """
        Draws the background of the painter within the given rectangle.

        Args:
            painter (QPainter): The painter object to draw on.
            rect (QRect): The rectangle to draw the background within.
        """
        # Cache rect values to avoid multiple calls
        left = int(rect.left())
        top = int(rect.top())

        # Calculate coordinates once
        self._left = left - (left % self.majorGrid)
        self._top = top - (top % self.majorGrid)
        self._bottom = int(rect.bottom())
        self._right = int(rect.right())

        if self.gridbackg or self.linebackg:
            # Fill rectangle with black color
            painter.fillRect(rect, QColor("black"))
            x_coords, y_coords = self.findCoords()

            if self.gridbackg:
                painter.setPen(QColor("white"))

                # Pre-allocate the polygon for better performance
                points = QPolygon()
                num_points = len(x_coords) * len(y_coords)
                points.reserve(num_points)

                # Fill the polygon with points
                for x in x_coords:
                    for y in y_coords:
                        points.append(QPoint(int(x), int(y)))

                # Draw all points in a single call
                painter.drawPoints(points)

            else:  # self.linebackg

                painter.setPen(QColor("gray"))

                # Create vertical and horizontal lines
                vertical_lines = [
                    QLine(int(x), self._top, int(x), self._bottom)
                    for x in x_coords
                ]

                horizontal_lines = [
                    QLine(self._left, int(y), self._right, int(y))
                    for y in y_coords
                ]

                # Draw all lines with minimal calls
                painter.drawLines(vertical_lines)
                painter.drawLines(horizontal_lines)
        elif self._transparent:
            self.viewport().setAttribute(Qt.WA_TranslucentBackground)
        else:
            painter.fillRect(rect, QColor("black"))
            super().drawBackground(painter, rect)

    def findCoords(self):
        """
        Calculate the coordinates for drawing lines or points on a grid.

        Returns:
            tuple: A tuple containing the x and y coordinates for drawing the lines or points.
        """
        x_coords = range(self._left, self._right, self.majorGrid)
        y_coords = range(self._top, self._bottom, self.majorGrid)

        if 160 <= len(x_coords) < 320:
            # Create a range of x and y coordinates for drawing the lines
            x_coords = range(self._left, self._right, self.majorGrid * 2)
            y_coords = range(self._top, self._bottom, self.majorGrid * 2)
        elif 320 <= len(x_coords) < 640:
            x_coords = range(self._left, self._right, self.majorGrid * 4)
            y_coords = range(self._top, self._bottom, self.majorGrid * 4)
        elif 640 <= len(x_coords) < 1280:
            x_coords = range(self._left, self._right, self.majorGrid * 8)
            y_coords = range(self._top, self._bottom, self.majorGrid * 8)
        elif 1280 <= len(x_coords) < 2560:
            x_coords = range(self._left, self._right, self.majorGrid * 16)
            y_coords = range(self._top, self._bottom, self.majorGrid * 16)
        elif len(x_coords) >= 2560:  # grid dots are too small to see
            x_coords = range(self._left, self._right, self.majorGrid * 10000)
            y_coords = range(self._top, self._bottom, self.majorGrid * 10000)

        return x_coords, y_coords

    def keyPressEvent(self, event: QKeyEvent):
        self.keyPressedSignal.emit(event.key())
        match event.key():
            case Qt.Key_M:
                self.scene.editModes.setMode('moveItem')
                self.editor.messageLine.setText('Move Item')
            case Qt.Key_F:
                self.scene.fitItemsInView()
            case Qt.Key_Left:
                self.scene.moveSceneLeft()
            case Qt.Key_Right:
                self.scene.moveSceneRight()
            case Qt.Key_Up:
                self.scene.moveSceneUp()
            case Qt.Key_Down:
                self.scene.moveSceneDown()
            case Qt.Key_Escape:
                self.scene.editModes.setMode("selectItem")
                self.editor.messageLine.setText("Select Item")
                self.scene.deselectAll()
                self.scene._selectedItems = None
                if self.scene._selectionRectItem:
                    self.scene.removeItem(self.scene._selectionRectItem)
                    self.scene._selectionRectItem = None
                if self.scene.editModes.moveItem and self._items:

                    self.moveShapesUndoStack(self._items, self._itemsOffset,
                                                 self.scene.mousePressLoc,
                                                 self.scene.mouseMoveLoc)
                    self._items = []
                    self._itemsOffset = []
            case _:
                super().keyPressEvent(event)

    def printView(self, printer):
        """
        Print view using selected Printer.

        Args:
            printer (QPrinter): The printer object to use for printing.

        This method prints the current view using the provided printer. It first creates a QPainter object
        using the printer. Then, it stores the original states of gridbackg and linebackg attributes.
        After that, it calls the revedaPrint method to render the view onto the painter. Finally, it
        restores the gridbackg and linebackg attributes to their original state.
        """
        # Store original states
        original_gridbackg = self.gridbackg
        original_linebackg = self.linebackg

        # Set both to False for printing
        self.gridbackg = False
        self.linebackg = False
        self._transparent = True
        painter = QPainter()
        painter.begin(printer)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.render(painter)
        # Restore original states
        self.gridbackg = original_gridbackg
        self.linebackg = original_linebackg
        self._transparent = False
        # End painting
        painter.end()

class symbolView(editorView):
    def __init__(self, scene, parent):
        self.scene = scene
        self.parent = parent
        super().__init__(self.scene, self.parent)

    def keyPressEvent(self, event: QKeyEvent):
        super().keyPressEvent(event)
        match event.key():
            case Qt.Key_Escape:
                if self.scene._polygonGuideLine:
                    self.scene.finishPolygon(event)
                self.scene._newLine = None
                self.scene._newCircle = None
                self.scene._newPin = None
                self.scene._newRect = None
                self.scene._newArc = None
                self.scene._newLabel = None
                if self.scene._polygonGuideLine:
                    self.scene.removeItem(self.scene._polygonGuideLine)
                self.scene.editModes.setMode('selectItem')


class schematicView(editorView):
    _dotRadius = 10
    def __init__(self, scene, parent):
        self.parent = parent
        self.scene = scene
        super().__init__(self.scene, self.parent)

        self.scene.wireEditFinished.connect(self.mergeSplitViewNets)


    def mousePressEvent(self, event):
        self.viewRect = self.mapToScene(self.rect()).boundingRect().toRect()

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.viewRect = self.mapToScene(self.rect()).boundingRect().toRect()
        viewSnapLinesSet = {guideLineItem for guideLineItem in
            self.scene.items(self.viewRect) if isinstance(guideLineItem, net.guideLine)}

        self.removeSnapLines(viewSnapLinesSet)
        self.mergeSplitViewNets()

        super().mouseReleaseEvent(event)


    def mergeSplitViewNets(self):
        netsInView = (netItem for netItem in self.scene.items(self.viewRect) if
            isinstance(netItem, net.schematicNet))
        for netItem in netsInView:
            if netItem.scene():
                self.scene.mergeSplitNets(netItem)


    def removeSnapLines(self, viewSnapLinesSet):
        undoCommandList = []
        for snapLine in viewSnapLinesSet:
            lines = self.scene.addStretchWires(snapLine.sceneEndPoints[0],
                snapLine.sceneEndPoints[1])

            if lines != []:
                for line in lines:
                    line.inheritGuideLine(snapLine)
                    undoCommandList.append(us.addShapeUndo(self.scene, line))
                self.scene.addUndoMacroStack(undoCommandList,
                                             "Stretch Wires")  # undoCommandList.append(us.addShapesUndo(self.scene, lines))
            self.scene.removeItem(snapLine)

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        xextend = self._right - self._left
        yextend = self._bottom - self._top
        netsInView = [netItem for netItem in self.scene.items(rect) if
            isinstance(netItem, net.schematicNet)]
        if xextend <= 2000 or yextend <= 2000:
            netEndPoints = []
            for netItem in netsInView:
                netEndPoints.extend(netItem.sceneEndPoints)
            pointCountsDict = Counter(netEndPoints)
            dotPoints = [point for point, count in pointCountsDict.items() if count >= 3]
            painter.setPen(schlyr.wirePen)
            painter.setBrush(schlyr.wireBrush)
            for dotPoint in dotPoints:
                painter.drawEllipse(dotPoint, self._dotRadius, self._dotRadius)

    def keyPressEvent(self, event: QKeyEvent):
        """
        Handles the key press event for the editor view.

        Args:
            event (QKeyEvent): The key press event to handle.

        """
        if event.key() == Qt.Key_Escape:
            # Esc key pressed, remove snap rect and reset states
            if self.scene._snapPointRect is not None:
                self.scene._snapPointRect.setVisible(False)
            if self.scene._newNet is not None:
                self.scene.wireEditFinished.emit(self.scene._newNet)
                self.scene._newNet = None
            elif self.scene._stretchNet is not None:
                # Stretch net mode, cancel stretch
                self.scene._stretchNet.setSelected(False)
                self.scene._stretchNet.stretch = False
                self.scene.mergeSplitNets(self.scene._stretchNet)
            self.scene._newInstance = None
            self.scene._newPin = None
            self.scene._newText = None
            # Set the edit mode to select item
            self.scene.editModes.setMode("selectItem")

        super().keyPressEvent(event)


class layoutView(editorView):
    def __init__(self, scene, parent):
        self.scene = scene
        self.parent = parent
        super().__init__(self.scene, self.parent)
        self.setOptimizationFlag(QGraphicsView.DontAdjustForAntialiasing)
        self.setOptimizationFlag(QGraphicsView.DontSavePainterState)
        # Create and set OpenGL widget as viewport
        glWidget = QOpenGLWidget()
        self.setViewport(glWidget)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Escape:

            if self.scene._newPath is not None:
                self.scene._newPath = None
            elif self.scene._newRect:
                if self.scene._newRect.rect.isNull():
                    self.scene.removeItem(self.scene._newRect)
                    self.scene.undoStack.removeLastCommand()
                self.scene._newRect = None
            elif self.scene._stretchPath is not None:
                self.scene._stretchPath.setSelected(False)
                self.scene._stretchPath.stretch = False
                self.scene._stretchPath = None
            elif self.scene.editModes.drawPolygon:
                self.scene.removeItem(self.scene._polygonGuideLine)
                self.scene._newPolygon.points.pop(0)  # remove first duplicate point
                self.scene._newPolygon = None
            elif self.scene.editModes.addInstance:
                self.scene.newInstance = None
                self.scene.layoutInstanceTuple = None
            elif self.scene.editModes.addLabel:
                self.scene._newLabel = None
                self.scene._newLabelTuple = None

            self.scene.editModes.setMode("selectItem")
        super().keyPressEvent(event)
