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

from typing import List
from PySide6.QtCore import (QEvent, QPoint, QRectF, Qt, QSizeF )
from PySide6.QtGui import (QGuiApplication, QTransform, QPainterPath, QPen, QColor)
from PySide6.QtWidgets import (QGraphicsScene, QMenu, QGraphicsItem,
                               QDialog, QGraphicsRectItem,
                               QCompleter,)
from contextlib import contextmanager
import time
import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.backend.undoStack as us
import revedaEditor.gui.propertyDialogues as pdlg


class editorScene(QGraphicsScene):
    # Define MOUSE_EVENTS as a class attribute to avoid recreating it on every call
    MOUSE_EVENTS = {
        QEvent.GraphicsSceneMouseMove,
        QEvent.GraphicsSceneMousePress,
        QEvent.GraphicsSceneMouseRelease
    }

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.editorWindow = parent.parent

        self.majorGrid = self.editorWindow.majorGrid
        self.snapGrid = self.editorWindow.snapGrid
        self.snapTuple = self.editorWindow.snapTuple

        # Initialize mouse-related attributes together
        self.mousePressLoc = self.mouseMoveLoc = self.mouseReleaseLoc = None

        # Use dictionary unpacking for edit modes
        self.editModes = ddef.editModes(**{
            'selectItem': True,
            'deleteItem': False,
            'moveItem': False,
            'copyItem': False,
            'rotateItem': False,
            'changeOrigin': False,
            'panView': False,
            'stretchItem': False
        })

        self.messages = {'selectItem': 'Select Item',
                         'deleteItem': 'Delete Item',
                         'moveItem': 'Move Item',
                         'copyItem': 'Copy Item',
                         'rotateItem': 'Rotate Item',
                         'changeOrigin': 'Change Origin',
                         'panView': 'Pan View at Mouse Press Position',
                         'stretchItem': 'Stretch Item'}
        # Initialize undo stack with limit
        self.undoStack = us.undoStack()
        self.undoStack.setUndoLimit(99)
        self.itemsRefSet: set[QGraphicsItem] = set()

        # Group selection-related attributes
        self.partialSelection = False
        self._selectionRectItem = None
        self._selectedItems = []
        self._selectedItemGroup = None
        self._groupItems = []
        self._draftPen = QPen(Qt.DashLine)
        self._draftPen.setColor(QColor(0, 150, 0))
        self._draftPen.setWidth(int(self.snapGrid / 2))


        # Initialize UI elements
        self.origin = QPoint(0, 0)
        self.cellName = self.editorWindow.file.parent.stem
        self.libraryDict = self.editorWindow.libraryDict
        self.itemContextMenu = QMenu()

        # Get application-level references
        app_main = self.editorWindow.appMainW
        self.appMainW = app_main
        self.logger = app_main.logger
        self.messageLine = self.editorWindow.messageLine
        self.statusLine = self.editorWindow.statusLine

        # Scene properties
        self.readOnly = False
        self.installEventFilter(self)
        self.setMinimumRenderSize(2)
        self._initialGroupPosList = []
        self._initialGroupPos = QPoint(0,0)
        self._finalGroupPosDiff = QPoint(0,0)

    def contextMenuEvent(self, event):
        if self.itemAt(event.scenePos(), QTransform()) is None:
            self.clearSelection()
            self._selectedItems = []
            self._selectedItemGroup = None
            self._groupItems = []
            self.messageLine.setText("No item selected")
        super().contextMenuEvent(event)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        modifiers = QGuiApplication.keyboardModifiers()
        if event.button() == Qt.MouseButton.LeftButton:
            self.mousePressLoc = event.scenePos().toPoint()
            if self.editModes.selectItem:
                self.clearSelection()
                if (modifiers == Qt.KeyboardModifier.ShiftModifier or 
                    modifiers == Qt.KeyboardModifier.ControlModifier):
                    self._selectionRectItem = QGraphicsRectItem()
                    self._selectionRectItem.setRect(
                        QRectF(self.mousePressLoc.x(), self.mousePressLoc.y(), 0, 0)
                    )
                    self._selectionRectItem.setPen(self.draftPen)  # Use property
                    self._selectionRectItem.setZValue(100)
                    self.addItem(self._selectionRectItem)
                else:
                    selectedItems = self.items(self.mousePressLoc)
                    for item in selectedItems:
                        item.setSelected(True)
                    if not selectedItems:
                        self.clearSelection()
                        for item in self.items():
                            item.setSelected(False)
            if self.editModes.moveItem:
                self._selectedItemGroup = self.createItemGroup(
                    self.selectedItems())
                
                self._selectedItemGroup.setFlag(QGraphicsItem.ItemIsMovable, True)
                self._initialGroupPos = QPoint(int(self._selectedItemGroup.pos().x()), int(self._selectedItemGroup.pos().y()))
                self._initialGroupPosList = [QPoint(int(item.pos().x()), int(item.pos().y())) for item in self._selectedItemGroup.childItems()]
            elif self.editModes.panView:
                self.centerViewOnPoint(self.mousePressLoc)
            self.messageLine.setText(self.messages.get(self.editModes.mode(), ""))

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        self.mouseMoveLoc = event.scenePos().toPoint()
        if self.editModes.selectItem and self._selectionRectItem:
            self._selectionRectItem.setRect(
                QRectF(self.mousePressLoc, self.mouseMoveLoc).normalized()
            )

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() != Qt.MouseButton.LeftButton:
            return
        
        modifiers = QGuiApplication.keyboardModifiers()
        self.mouseReleaseLoc = event.scenePos().toPoint()
        
        if self.editModes.moveItem and self._selectedItemGroup:
            _groupItems = self._selectedItemGroup.childItems()
            self._finalGroupPosDiff = self._selectedItemGroup.pos().toPoint() - self._initialGroupPos
            self.destroyItemGroup(self._selectedItemGroup)
            self._selectedItemGroup = None
            self.undoGroupMoveStack(_groupItems, self._initialGroupPosList, self._finalGroupPosDiff)
            [item.setSelected(False) for item in _groupItems]
            self.editModes.setMode("selectItem")

        elif self.editModes.selectItem and self._selectionRectItem:
            self._handleSelectionRect(modifiers)
        else:
            self._handleMouseRelease(self.mouseReleaseLoc, event.button())
        self.messageLine.setText(self.messages.get(self.editModes.mode(), ""))

    def snapToGrid(self, point: QPoint) -> QPoint:
        """Snap point to scene grid."""
        xgrid = self.snapTuple[0]
        ygrid = self.snapTuple[1]
        return QPoint(
            round(point.x() / xgrid) * xgrid,
            round(point.y() / ygrid) * ygrid
        )
    
    def _snapPoint(self, pos: QPoint) -> QPoint:
        """
        Default snapping behavior. Subclasses can override this for more
        advanced snapping (e.g., to items, intersections).
        """
        return self.snapToGrid(pos)

    def _handleMouseRelease(self, mousePos: QPoint, button: Qt.MouseButton):
        pass

    def snapToBase(self, number, base):
        """
        Restrict a number to the multiples of base
        """
        return int(round(float(number) / base)) * base


    def rotateSelectedItems(self, point: QPoint):
        """
        Rotate selected items by 90 degree.
        """
        for item in self.selectedItems():
            self.rotateAnItem(point, item, 90)
        self.editModes.setMode("selectItem")

    def rotateAnItem(self, point: QPoint, item: QGraphicsItem, angle: int):
        """
        Rotate a graphics item around a point by a specified angle with undo support.

        Args:
            point (QPoint): The pivot point for rotation
            item (QGraphicsItem): The item to be rotated
            angle (int): The rotation angle in degrees

        Returns:
            None
        """
        undoCommand = us.undoRotateShape(self, item, point, angle)
        self.undoStack.push(undoCommand)

    def _handleSelectionRect(self, modifiers):
        # default implementation of selection rectangle
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
                self.setSelectionArea(selectionPath, mode=selectionMode)
            case Qt.KeyboardModifier.ControlModifier:
                for item in self.items(selectionPath, mode=selectionMode):
                    item.setSelected(not item.isSelected())
            case _:
                for item in self.items(selectionPath, mode=selectionMode):
                    item.setSelected(True)
        if self._selectionRectItem:
            self.removeItem(self._selectionRectItem)
            self._selectionRectItem = None

    def eventFilter(self, source, event):
        """
        Filter mouse events to snap them to background grid points.
        """
        if self.readOnly:
            return True

        if event.type() in self.MOUSE_EVENTS:
            # Use the _snapPoint method which can be overridden by subclasses
            snappedPos = self._snapPoint(event.scenePos().toPoint())
            event.setScenePos(snappedPos)
            return False

        return super().eventFilter(source, event)

    def copySelectedItems(self):
        '''
        Will be implemented in the subclasses.
        '''

    def flipHorizontal(self):
        for item in self.selectedItems():
            item.flipTuple = (-1, 1)

    def flipVertical(self):
        for item in self.selectedItems():
            item.flipTuple = (1, -1)

    def selectAll(self):
        """
        Select all items in the scene.
        """
        [item.setSelected(True) for item in self.items()]

    def deselectAll(self):
        """
        Deselect all items in the scene.
        """
        [item.setSelected(False) for item in self.selectedItems()]

    def deleteSelectedItems(self):
        if self.selectedItems() is not None:
            for item in self.selectedItems():
                # self.removeItem(item)
                undoCommand = us.deleteShapeUndo(self, item)
                self.undoStack.push(undoCommand)
            self.update()  # update the scene

    def stretchSelectedItems(self):
        if self.selectedItems() is not None:
            try:
                for item in self.selectedItems():
                    if hasattr(item, "stretch"):
                        item.stretch = True
            except AttributeError:
                self.messageLine.setText("Nothing selected")


    def reloadScene(self):
        # Disable updates temporarily for better performance
        for view in self.views():
            view.setUpdatesEnabled(False)

        try:
            # Block signals during reload to prevent unnecessary updates
            self.blockSignals(True)

            # Clear existing items
            self.clear()

            # Reload layout
            self.loadDesign(self.editorWindow.file)

            # Optional: Update scene rect to fit content
            self.setSceneRect(self.itemsBoundingRect())

        finally:
            # Re-enable updates and signals
            self.blockSignals(False)
            for view in self.views():
                view.setUpdatesEnabled(True)
                view.viewport().update()


    def fitItemsInView(self) -> None:
        self.setSceneRect(self.itemsBoundingRect().adjusted(-40, -40, 40, 40))
        self.views()[0].fitInView(self.sceneRect(), Qt.KeepAspectRatio)
        self.views()[0].viewport().update()

    def moveSceneLeft(self) -> None:
        currentSceneRect = self.sceneRect()
        halfWidth = currentSceneRect.width() / 2.0
        newSceneRect = QRectF(currentSceneRect.left() - halfWidth, currentSceneRect.top(),
                              currentSceneRect.width(), currentSceneRect.height(), )
        self.setSceneRect(newSceneRect)

    def moveSceneRight(self) -> None:
        currentSceneRect = self.sceneRect()
        halfWidth = currentSceneRect.width() / 2.0
        newSceneRect = QRectF(currentSceneRect.left() + halfWidth, currentSceneRect.top(),
                              currentSceneRect.width(), currentSceneRect.height(), )
        self.setSceneRect(newSceneRect)

    def moveSceneUp(self) -> None:
        currentSceneRect = self.sceneRect()
        halfWidth = currentSceneRect.width() / 2.0
        newSceneRect = QRectF(currentSceneRect.left(), currentSceneRect.top() - halfWidth,
                              currentSceneRect.width(), currentSceneRect.height(), )
        self.setSceneRect(newSceneRect)

    def moveSceneDown(self) -> None:
        currentSceneRect = self.sceneRect()
        halfWidth = currentSceneRect.width() / 2.0
        newSceneRect = QRectF(currentSceneRect.left(), currentSceneRect.top() + halfWidth,
                              currentSceneRect.width(), currentSceneRect.height(), )
        self.setSceneRect(newSceneRect)

    def centerViewOnPoint(self, point: QPoint) -> None:
        currentSceneRect = self.sceneRect()
        size = QSizeF(currentSceneRect.width(), currentSceneRect.height())
        newSceneRect = QRectF(point.x() - size.width() / 2, point.y() - size.height() / 2,
                              size.width(), size.height())
        self.setSceneRect(newSceneRect)

    def addUndoStack(self, item: QGraphicsItem):
        undoCommand = us.addShapeUndo(self, item)
        self.undoStack.push(undoCommand)

    def deleteUndoStack(self, item: QGraphicsItem):
        undoCommand = us.deleteShapeUndo(self, item)
        self.undoStack.push(undoCommand)

    def addListUndoStack(self, itemList: List) -> None:
        undoCommand = us.addShapesUndo(self, itemList)
        self.undoStack.push(undoCommand)

    def undoGroupMoveStack(self, items: List[QGraphicsItem],
                         startPos: List[QPoint],endPos: QPoint) -> None:

        undoCommand = us.undoGroupMove(self, items, startPos, endPos)
        self.undoStack.push(undoCommand)

    def addUndoMacroStack(self, undoCommands: list, macroName: str = "Macro"):
        self.undoStack.beginMacro(macroName)
        for command in undoCommands:
            self.undoStack.push(command)
        self.undoStack.endMacro()

    def moveBySelectedItems(self):
        if self.selectedItems():
            dlg = pdlg.moveByDialogue(self.editorWindow)
            dlg.xEdit.setText("0")
            dlg.yEdit.setText("0")
            if dlg.exec() == QDialog.Accepted:
                dx = self.snapToBase(float(dlg.xEdit.text()), self.snapTuple[0])
                dy = self.snapToBase(float(dlg.yEdit.text()), self.snapTuple[1])
                moveCommand = us.undoMoveByCommand(self, self.selectedItems(), dx, dy)
                self.undoStack.push(moveCommand)
                self.editorWindow.messageLine.setText(
                    f"Moved items by {dlg.xEdit.text()} and {dlg.yEdit.text()}")
                self.editModes.setMode("selectItem")

    def cellNameComplete(self, dlg: QDialog, cellNameList: List[str]):
        cellNameCompleter = QCompleter(cellNameList)
        cellNameCompleter.setCaseSensitivity(Qt.CaseInsensitive)
        dlg.instanceCellName.setCompleter(cellNameCompleter)

    def viewNameComplete(self, dlg: QDialog, viewNameList: List[str]):
        viewNameCompleter = QCompleter(viewNameList)
        viewNameCompleter.setCaseSensitivity(Qt.CaseInsensitive)
        dlg.instanceViewName.setCompleter(viewNameCompleter)
        dlg.instanceViewName.setText(viewNameList[0])

    @contextmanager
    def measureDuration(self):
        start_time = time.perf_counter()
        try:
            yield
        finally:
            end_time = time.perf_counter()
            self.logger.info(f"Total processing time: {end_time - start_time:.3f} seconds")

    @property
    def draftPen(self):
        return self._draftPen