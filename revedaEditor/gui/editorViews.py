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
from collections import Counter

from PySide6.QtCore import (
    QLine,
    QPoint,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QKeyEvent,
    QPainter,
    QPolygon,
    QWheelEvent,
)
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import (
    QGraphicsView,
)

import revedaEditor.common.net as net
from revedaEditor.backend.pdkLoader import importPDKModule
from revedaEditor.scenes.editorScene import editorScene
from revedaEditor.scenes.layoutScene import layoutScene
from revedaEditor.scenes.schematicScene import schematicScene
from revedaEditor.scenes.symbolScene import symbolScene

schlyr = importPDKModule("schLayers")
fabproc = importPDKModule("process")


class editorView(QGraphicsView):
    """
    The qgraphicsview for qgraphicsscene. It is used for both schematic and layout editors.
    """

    keyPressedSignal = Signal(int)

    # zoomFactorChanged = Signal(float)
    def __init__(self, scene: editorScene, parent):
        super().__init__(scene, parent)

        # Cache parentW references
        self.centralW = parent
        self.editorWindow = self.centralW.editorWindow
        self.viewScene = scene
        self.logger = scene.logger

        # Cache editor properties
        editor = self.editorWindow
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
        # Batch all settings to minimize Qt overhead
        self.setViewportUpdateMode(QGraphicsView.SmartViewportUpdate)
        self.setCacheMode(QGraphicsView.CacheBackground)
        self.setMouseTracking(True)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setInteractive(True)
        self.setCursor(Qt.CrossCursor)
        self.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)

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
                painter.setPen(QColor("gray"))

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
                    QLine(int(x), self._top, int(x), self._bottom) for x in
                    x_coords
                ]

                horizontal_lines = [
                    QLine(self._left, int(y), self._right, int(y)) for y in
                    y_coords
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

        num_lines = len(x_coords)
        if 120 <= num_lines < 240:
            spacing = self.majorGrid * 2
        elif 240 <= num_lines < 480:
            spacing = self.majorGrid * 4
        elif 480 <= num_lines < 960:
            spacing = self.majorGrid * 8
        elif 960 <= num_lines < 1920:
            spacing = self.majorGrid * 16
        elif num_lines >= 1920:
            return range(0, 0), range(0, 0)  # No grid when too dense
        else:
            spacing = self.majorGrid

        if spacing != self.majorGrid:
            x_coords = range(self._left, self._right, spacing)
            y_coords = range(self._top, self._bottom, spacing)

        return x_coords, y_coords

    def keyPressEvent(self, event: QKeyEvent):
        self.keyPressedSignal.emit(event.key())

        match event.key():
            case Qt.Key.Key_M:
                self.viewScene.editModes.setMode("moveItem")
                self.editorWindow.messageLine.setText("Move Item")
            case Qt.Key.Key_F:
                self.viewScene.fitItemsInView()
                self.editorWindow.messageLine.setText("Fit Items In View")
            case Qt.Key.Key_Left:
                self.viewScene.moveSceneLeft()
                self.editorWindow.messageLine.setText("Move View Left")
            case Qt.Key.Key_Right:
                self.viewScene.moveSceneRight()
                self.editorWindow.messageLine.setText("Move View Right")
            case Qt.Key.Key_Up:
                self.viewScene.moveSceneUp()
                self.editorWindow.messageLine.setText("Move View Up")
            case Qt.Key.Key_Down:
                self.viewScene.moveSceneDown()
                self.editorWindow.messageLine.setText("Move View Down")
            case Qt.Key.Key_PageUp:
                self.cycleSelection(event)
            case Qt.Key.Key_Z:
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    self.viewScene.zoomInBy2()
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    self.viewScene.zoomOutBy2()
                else:
                    self.viewScene.editModes.setMode("zoomView")

            case Qt.Key.Key_Escape:
                self.viewScene.deselectAll()
                self.viewScene.selectedItemsSet = set()
                if self.viewScene.selectionRectItem:
                    self.viewScene.removeItem(self.viewScene.selectionRectItem)
                    self.viewScene.selectionRectItem = None
                if self.viewScene.selectedItemGroup:
                    self.viewScene.destroyItemGroup(
                        self.viewScene.selectedItemGroup)
                    self.viewScene.selectedItemGroup = None
                self.viewScene.editModes.setMode('selectItem')
                self.viewScene.messageLine.setText("Select Item")
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
        originalGridbackg = self.gridbackg
        originalLinebackg = self.linebackg

        # Set both to False for printing
        self.gridbackg = False
        self.linebackg = False
        self._transparent = True
        painter = QPainter()
        painter.begin(printer)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.render(painter)
        # Restore original states
        self.gridbackg = originalGridbackg
        self.linebackg = originalLinebackg
        self._transparent = False
        # End painting
        painter.end()

    def cycleSelection(self, event):
        modifiers = event.modifiers()
        if self.viewScene.itemCycler:
            item = next(self.viewScene.itemCycler)
            if modifiers == Qt.KeyboardModifier.ShiftModifier:
                self.viewScene.selectedItemsSet.add(item)
                item.setSelected(True)
            elif modifiers == Qt.KeyboardModifier.ControlModifier:
                try:
                    item.setSelected(False)
                    self.viewScene.selectedItemsSet.remove(item)
                except KeyError:
                    pass
            elif not event.modifiers():
                if self.viewScene.selectedItemsSet:
                    [setItem.setSelected(False) for setItem in
                     self.viewScene.selectedItemsSet]
                item.setSelected(True)
                self.viewScene.selectedItemsSet = {item}


class symbolView(editorView):
    def __init__(self, scene: symbolScene, parent):
        super().__init__(scene, parent)
        self.viewScene: symbolScene = scene
        self.parent = parent

    def keyPressEvent(self, event: QKeyEvent):
        super().keyPressEvent(event)
        match event.key():
            case Qt.Key.Key_Escape:
                if self.viewScene.polygonGuideLine:
                    self.viewScene.finishPolygon(event)
                self.viewScene.newLine = None
                self.viewScene.newCircle = None
                self.viewScene.newPin = None
                self.viewScene.newRect = None
                self.viewScene.newArc = None
                self.viewScene.newLabel = None
                if self.viewScene.polygonGuideLine:
                    self.viewScene.removeItem(self.viewScene.polygonGuideLine)
                self.viewScene.editModes.setMode("selectItem")


class schematicView(editorView):
    _dotRadius = 10

    def __init__(self, scene: schematicScene, parent):
        super().__init__(scene, parent)
        self.viewScene: schematicScene = scene
        self.parent = parent
        self.viewScene.wireEditFinished.connect(self.mergeSplitViewNets)

    def mousePressEvent(self, event):
        self.viewRect = self.mapToScene(self.rect()).boundingRect().toRect()

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.viewRect = self.mapToScene(self.rect()).boundingRect().toRect()
        self.pruneShortNets()
        self.mergeSplitViewNets()

        super().mouseReleaseEvent(event)

    def pruneShortNets(self):
        """Remove nets shorter than snap spacing."""
        snapSpacing = self.viewScene.snapTuple[0]
        netsInView = [
            netItem
            for netItem in self.viewScene.items(self.viewRect)
            if isinstance(netItem, net.schematicNet)
        ]
        for netItem in netsInView:
            if netItem.scene() and netItem.draftLine.length() < snapSpacing:
                self.viewScene.removeItem(netItem)

    def mergeSplitViewNets(self):
        netsInView = (
            netItem
            for netItem in self.viewScene.items(self.viewRect)
            if isinstance(netItem, net.schematicNet)
        )
        for netItem in netsInView:
            if netItem.scene():
                self.viewScene.mergeSplitNets(netItem)

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)

        # Early exit for large views to avoid performance issues
        if (self._right - self._left) > 2000 and (
                self._bottom - self._top) > 2000:
            return

        # Get nets in view with type filtering
        netsInView = [
            item
            for item in self.viewScene.items(rect)
            if isinstance(item, net.schematicNet)
        ]

        if not netsInView:
            return

        # Collect and count endpoints in one pass
        pointCounts = Counter()
        for netItem in netsInView:
            pointCounts.update(netItem.sceneEndPoints)

        # Filter junction points (count >= 3) and draw
        junctionPoints = [point for point, count in pointCounts.items() if
                          count >= 3]

        if junctionPoints:
            painter.setPen(schlyr.wirePen)
            painter.setBrush(schlyr.wireBrush)
            for point in junctionPoints:
                painter.drawEllipse(point, self._dotRadius, self._dotRadius)

    def keyPressEvent(self, event: QKeyEvent):
        """
        Handles the key press event for the editor view.

        Args:
            event (QKeyEvent): The key press event to handle.

        """
        if event.key() == Qt.Key.Key_Escape:
            # Esc key pressed, remove snap rect and reset states
            if self.viewScene._snapPointRect is not None:
                self.viewScene._snapPointRect.setVisible(False)
            if self.viewScene._newNet is not None:
                self.viewScene.wireEditFinished.emit(self.viewScene._newNet)
                self.viewScene._newNet = None
            elif self.viewScene._stretchNet is not None:
                # Stretch net mode, cancel stretch
                self.viewScene._stretchNet.setSelected(False)
                self.viewScene._stretchNet.stretch = False
                self.viewScene.mergeSplitNets(self.viewScene._stretchNet)
                self.viewScene._stretchNet = None
            self.viewScene._newInstance = None
            self.viewScene._newPin = None
            self.viewScene._newText = None
            # Set the edit mode to select item
            self.viewScene.editModes.setMode("selectItem")

        super().keyPressEvent(event)


class layoutView(editorView):
    def __init__(self, scene: layoutScene, parent):
        super().__init__(scene, parent)
        self.viewScene: layoutScene = scene
        self.parent = parent
        # # Configure OpenGL viewport for better performance
        glWidget = QOpenGLWidget()
        glWidget.setUpdateBehavior(QOpenGLWidget.UpdateBehavior.PartialUpdate)
        self.setViewport(glWidget)

    def keyPressEvent(self, event: QKeyEvent):
        modifiers = event.modifiers()
        if event.key() == Qt.Key.Key_Escape:
            if self.viewScene.editModes.drawPath and self.viewScene.newPath is not None:
                if self.viewScene.newPath.draftLine.isNull():
                    self.viewScene.undoStack.removeLastCommand()
                self.viewScene.newPath = None
                self.viewScene.editModes.setMode("selectItem")
            elif self.viewScene.editModes.drawRect and self.viewScene.newRect is not None:
                if self.viewScene.newRect.rect.isNull():
                    self.viewScene.removeItem(self.viewScene.newRect)
                    self.viewScene.undoStack.removeLastCommand()
                self.viewScene.newRect = None
                self.viewScene.editModes.setMode("selectItem")
            elif self.viewScene.editModes.stretchItem and self.viewScene.stretchPathItem is not None:
                self.viewScene.stretchPathItem.setSelected(False)
                self.viewScene.stretchPathItem.stretch = False
                self.viewScene.stretchPathItem = None
            elif self.viewScene.editModes.drawPolygon:
                if self.viewScene.polygonGuideLine:
                    self.viewScene.removeItem(self.viewScene.polygonGuideLine)
                if self.viewScene.newPolygon and self.viewScene.newPolygon.points:
                    self.viewScene.newPolygon.points.pop(
                        0)  # remove first duplicate point
                self.viewScene.newPolygon = None
                self.viewScene.editModes.setMode("selectItem")
            elif self.viewScene.editModes.addInstance:
                self.viewScene.newInstance = None
                self.viewScene.layoutInstanceTuple = None
                self.viewScene.editModes.setMode("selectItem")
            elif self.viewScene.editModes.addLabel:
                self.viewScene.newLabel = None
                self.viewScene.newLabelTuple = None
                self.viewScene.editModes.setMode("selectItem")
            elif self.viewScene.editModes.cutShape:
                self.viewScene.finishCutLine()
                self.viewScene.editModes.setMode("selectItem")
            elif self.viewScene.editModes.addVia:
                self.viewScene.arrayViaTuple = None
                self.viewScene.arrayVia = None
                self.viewScene.editModes.setMode("selectItem")
        super().keyPressEvent(event)
