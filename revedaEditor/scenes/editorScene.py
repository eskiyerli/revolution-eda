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

import pathlib
import time
from contextlib import contextmanager
from itertools import cycle
from typing import TYPE_CHECKING, List, Union

from PySide6.QtCore import (QEvent, QPoint, QRectF, QSizeF, Qt, )
from PySide6.QtGui import QColor, QGuiApplication, QPainterPath, QPen, QTransform
from PySide6.QtWidgets import (QApplication, QCompleter, QDialog, QGraphicsItem,
                               QGraphicsRectItem, QGraphicsScene, QMenu, )

import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.backend.undoStack as us
import revedaEditor.gui.propertyDialogues as pdlg

if TYPE_CHECKING:
    import revedaEditor.common.layoutShapes as lshp
    import revedaEditor.common.shapes as shp


class editorScene(QGraphicsScene):
    # Define MOUSE_EVENTS as a class attribute to avoid recreating it on every call
    MOUSE_EVENTS = {QEvent.Type.GraphicsSceneMouseMove, QEvent.Type.GraphicsSceneMousePress,
                    QEvent.Type.GraphicsSceneMouseRelease, }

    def __init__(self, parent):
        super().__init__(parent)
        self.containerWidget = parent
        self.editorWindow = self.containerWidget.editorWindow

        self.majorGrid = self.editorWindow.majorGrid
        self.snapGrid = self.editorWindow.snapGrid
        self.snapTuple = self.editorWindow.snapTuple
        self.snapDistance = min(*self.editorWindow.snapTuple)

        # Initialize mouse-related attributes together
        self.mousePressLoc = self.mouseMoveLoc = self.mouseReleaseLoc = None

        # Use dictionary unpacking for edit modes
        self.editModes = ddef.editModes(
            **{"selectItem": True, "deleteItem": False, "moveItem": False,
               "copyItem": False, "rotateItem": False, "changeOrigin": False,
               "zoomView": False, "panView": False, "stretchItem": False,
               "alignItems": False, })

        self.messages = {"selectItem": "Select Item", "deleteItem": "Delete Item",
                         "moveItem": "Move Item", "copyItem": "Copy Item",
                         "rotateItem": "Rotate Item",
                         "changeOrigin": "Change Origin",
                         "panView": "Pan View at Mouse Press Position",
                         "zoomView": "Draw a rectangle to zoom in",
                         "stretchItem": "Stretch Item",
                         "alignItems": "Select Alignment Option.", }
        # Initialize undo stack with limit
        self.undoStack = us.undoStack()
        self.undoStack.setUndoLimit(99)
        self.itemsRefSet: set[QGraphicsItem] = set()

        # Group selection-related attributes
        self.partialSelection = False
        self.selectionRectItem: Union[QGraphicsRectItem, None] = None
        self.zoomRectItem: Union[QGraphicsRectItem, None] = None
        self.selectedItemsSet: set[QGraphicsItem] = set()
        self.selectedItemGroup = None
        self._groupItems = []
        self.itemsAtPressSet = set()
        self._draftPen = QPen(QColor(0, 150, 0, 128), int(self.snapGrid / 2), Qt.DashLine)
        self._zoomPen = QPen(QColor(255, 0, 0, 255), 2, Qt.DashLine)
        self._draftPen.setCosmetic(True)
        self._zoomPen.setCosmetic(True)

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
        self._initialGroupPos = QPoint(0, 0)
        self._finalGroupPosDiff = QPoint(0, 0)
        self.itemCycler = None
        self.mousePressLoc = QPoint(0, 0)
        self.mouseMoveLoc = QPoint(0, 0)
        self.mouseReleaseLoc = QPoint(0, 0)
        self.newAlignLine = None

    def contextMenuEvent(self, event):
        if self.itemAt(event.scenePos(), QTransform()) is None:
            # self.clearSelection()
            # self.selectedItemList = []
            # self.selectedItemGroup = None
            # self._groupItems = []
            self.messageLine.setText("No item selected")
        super().contextMenuEvent(event)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        modifiers = QGuiApplication.keyboardModifiers()
        if event.button() == Qt.MouseButton.LeftButton:
            self.mousePressLoc = event.scenePos().toPoint()
            if self.editModes.selectItem:
                if (self.selectionRectItem is None and self.itemAt(self.mousePressLoc,
                                                                   QTransform()) is None):
                    self.selectionRectItem = QGraphicsRectItem(self.mousePressLoc.x(),
                                                               self.mousePressLoc.y(), 0, 0)
                    self.selectionRectItem.setPen(self._draftPen)  # Use property
                    self.selectionRectItem.setZValue(100)
                    self.addItem(self.selectionRectItem)
                elif self.itemAt(self.mousePressLoc, QTransform()):
                    self.itemsAtPressSet = {item for item in self.items(self.mousePressLoc)
                                            if item.parentItem() is None}
                    if self.itemsAtPressSet:
                        self.itemCycler = cycle(self.itemsAtPressSet)
                        item = next(self.itemCycler)
                        if modifiers == Qt.KeyboardModifier.ShiftModifier:
                            self.selectedItemsSet |= {item}
                            item.setSelected(True)
                        elif modifiers == Qt.KeyboardModifier.ControlModifier:
                            if item in self.selectedItemsSet:
                                self.selectedItemsSet.remove(item)
                                item.setSelected(False)
                            else:
                                self.selectedItemsSet.add(item)
                                item.setSelected(True)
                        elif modifiers == Qt.KeyboardModifier.NoModifier:
                            self.clearSelection()
                            self.selectedItemsSet = {item}
                            item.setSelected(True)

            if self.editModes.moveItem:
                self.selectedItemGroup = self.createItemGroup(self.selectedItems())

                self.selectedItemGroup.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable,
                                               True)
                self._initialGroupPos = QPoint(int(self.selectedItemGroup.pos().x()),
                                               int(self.selectedItemGroup.pos().y()), )
                self._initialGroupPosList = [item.pos().toPoint() for item in
                                             self.selectedItemGroup.childItems()]
            elif self.editModes.panView:
                self.centerViewOnPoint(self.mousePressLoc)
            elif self.editModes.zoomView:
                if self.zoomRectItem is None:
                    self.zoomRectItem = QGraphicsRectItem(self.mousePressLoc.x(),
                                                          self.mousePressLoc.y(), 0, 0)
                    self.zoomRectItem.setPen(self._zoomPen)  # Use property
                    self.zoomRectItem.setZValue(100)
                    self.addItem(self.zoomRectItem)
            self.messageLine.setText(self.messages.get(self.editModes.mode(), ""))

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        self.mouseMoveLoc = event.scenePos().toPoint()
        if self.editModes.selectItem:
            if self.selectionRectItem:
                self.selectionRectItem.setRect(QRectF(self.mousePressLoc.toPointF(),
                                                      self.mouseMoveLoc.toPointF()).normalized())
        elif self.editModes.zoomView:
            if self.zoomRectItem:
                self.zoomRectItem.setRect(QRectF(self.mousePressLoc.toPointF(),
                                                 self.mouseMoveLoc.toPointF()).normalized())

        elif self.editModes.copyItem and self.selectedItemGroup:
            offset = self.mouseMoveLoc - self.mousePressLoc
            self.selectedItemGroup.setPos(offset)

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            super().mouseReleaseEvent(event)
            return

        modifiers = QGuiApplication.keyboardModifiers()
        self.mouseReleaseLoc = event.scenePos().toPoint()

        if self.editModes.moveItem and self.selectedItemGroup:
            _groupItems = self.selectedItemGroup.childItems()
            self._finalGroupPosDiff = (
                    self.selectedItemGroup.pos().toPoint() - self._initialGroupPos)
            self.destroyItemGroup(self.selectedItemGroup)
            self.selectedItemGroup = None
            self.undoGroupMoveStack(_groupItems, self._initialGroupPosList,
                                    self._finalGroupPosDiff)
            [item.setSelected(False) for item in _groupItems]
            self.editModes.setMode("selectItem")
        elif self.editModes.copyItem and self.selectedItemGroup:
            self.destroyItemGroup(self.selectedItemGroup)
            self.selectedItemGroup = None
            self.editModes.setMode(
                "selectItem")  # self.deselectAll()  # self.clearSelection()
        elif self.editModes.selectItem:
            if self.selectionRectItem:
                selectionPath = QPainterPath()
                selectionPath.addRect(self.selectionRectItem.sceneBoundingRect())
                selectionMode = (
                    Qt.ItemSelectionMode.IntersectsItemShape if self.partialSelection else Qt.ItemSelectionMode.ContainsItemShape)
                itemsInRectSet = set(
                    [item for item in self.items(selectionPath, mode=selectionMode) if
                     item.parentItem() is None])
                if modifiers == Qt.KeyboardModifier.ShiftModifier:
                    self.selectedItemsSet |= itemsInRectSet
                elif modifiers == Qt.KeyboardModifier.ControlModifier:
                    for item in itemsInRectSet:
                        item.setSelected(False)
                    self.selectedItemsSet -= itemsInRectSet
                elif modifiers == Qt.KeyboardModifier.NoModifier:
                    self.selectedItemsSet = itemsInRectSet
                for item in self.selectedItemsSet:
                    item.setSelected(True)
                self.removeItem(self.selectionRectItem)
                self.selectionRectItem = None
            elif not self.itemsAtPressSet:
                self.deselectAll()
                self.clearSelection()
        elif self.editModes.zoomView and self.zoomRectItem:
            self.zoomToRect()
            self.editModes.setMode('selectItem')
            self.removeItem(self.zoomRectItem)
            self.zoomRectItem = None
        else:
            self._handleMouseRelease(self.mouseReleaseLoc, event.button())
        self.messageLine.setText(self.messages.get(self.editModes.mode(), ""))

    def snapToGrid(self, point: QPoint) -> QPoint:
        """Snap point to scene grid."""
        xgrid = self.snapTuple[0]
        ygrid = self.snapTuple[1]
        return QPoint(round(point.x() / xgrid) * xgrid, round(point.y() / ygrid) * ygrid)

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

    def rotateAnItem(self, point: QPoint,
                     item: Union["shp.symbolShape", "lshp.layoutShape"], angle: int, ):
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
        """
        Will be implemented in the subclasses.
        """

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
        [item.setSelected(False) for item in self.selectedItemsSet]
        self.selectedItemsSet = set()

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
        """Reload scene with proper painter state management."""
        self._safeLoadDesign(self.editorWindow.file, reload=True)

    def _safeLoadDesign(self, file, reload=False):
        """Safely load design with painter error prevention."""
        # Disable all updates and painting
        for view in self.views():
            view.setUpdatesEnabled(False)
            view.viewport().setUpdatesEnabled(False)

        self.blockSignals(True)

        try:
            if reload:
                self.clear()

            # Call subclass-specific loadDesign
            self.loadDesign(file)

            # Update scene rect after loading
            if self.items():
                self.setSceneRect(self.itemsBoundingRect())

        finally:
            self.blockSignals(False)
            for view in self.views():
                view.setUpdatesEnabled(True)
                view.viewport().setUpdatesEnabled(True)

            # Single deferred update
            QApplication.processEvents()

    def loadDesign(self, filePathObj: pathlib.Path):
        """
        Load the design from the specified file.
        Must be implemented in subclasses.
        """
        raise NotImplementedError("Subclasses must implement loadDesign")

    def fitItemsInView(self) -> None:
        self.setSceneRect(self.itemsBoundingRect().adjusted(-40, -40, 40, 40))
        self.views()[0].fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.views()[0].viewport().update()

    def zoomToRect(self) -> None:
        if self.zoomRectItem:
            self.setSceneRect(self.zoomRectItem.rect().adjusted(-40, -40, 40, 40))
            self.views()[0].fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            self.views()[0].viewport().update()

    def zoomInBy2(self):
        sceneRect = self.sceneRect()
        # New size is half of current (zoom by 2)
        newWidth = sceneRect.width() * 0.5
        newHeight = sceneRect.height() * 0.5

        # Prefer the last known mouse scene position; fall back to scene center
        mousePos = (self.mouseMoveLoc if self.mouseMoveLoc is not None and (
                self.mouseMoveLoc.x() != 0 or self.mouseMoveLoc.y() != 0) else sceneRect.center())

        # Center the new scene rect at the mouse position
        newSceneRect = QRectF(mousePos.x() - newWidth / 2.0, mousePos.y() - newHeight / 2.0,
                              newWidth, newHeight, )

        self.setSceneRect(newSceneRect)
        view = self.views()[0]
        view.fitInView(newSceneRect, Qt.AspectRatioMode.KeepAspectRatio)
        view.viewport().update()

    def zoomOutBy2(self):
        sceneRect = self.sceneRect()
        # New size is half of current (zoom by 2)
        newWidth = sceneRect.width() * 2
        newHeight = sceneRect.height() * 2

        # Prefer the last known mouse scene position; fall back to scene center
        mousePos = (self.mouseMoveLoc if self.mouseMoveLoc is not None and (
                self.mouseMoveLoc.x() != 0 or self.mouseMoveLoc.y() != 0) else sceneRect.center())

        # Center the new scene rect at the mouse position
        newSceneRect = QRectF(mousePos.x() - newWidth / 2.0, mousePos.y() - newHeight / 2.0,
                              newWidth, newHeight, )

        self.setSceneRect(newSceneRect)
        view = self.views()[0]
        view.fitInView(newSceneRect, Qt.AspectRatioMode.KeepAspectRatio)
        view.viewport().update()

    # def zoomOutBy2(self):
    #     sceneRect = self.sceneRect()
    #     # Adjust the scene rectangle to zoom in by reducing its size by 25% on all sides
    #     sceneRect.adjust(-0.25 * sceneRect.width(), -0.25 * sceneRect.height(),
    #                      0.25 * sceneRect.width(), 0.25 * sceneRect.height())
    #     self.setSceneRect(sceneRect)
    #     view = self.views()[0]
    #     view.fitInView(sceneRect, Qt.AspectRatioMode.KeepAspectRatio)
    #     view.viewport().update()

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
                              size.width(), size.height(), )
        self.setSceneRect(newSceneRect)

    def addUndoStack(self, item: QGraphicsItem):
        undoCommand = us.addShapeUndo(self, item)
        self.undoStack.push(undoCommand)

    def deleteUndoStack(self, item: QGraphicsItem):
        undoCommand = us.deleteShapeUndo(self, item)
        self.undoStack.push(undoCommand)

    def addListUndoStack(self, itemList: List[QGraphicsItem]) -> None:
        undoCommand = us.addShapesUndo(self, itemList)
        self.undoStack.push(undoCommand)

    def deleteListUndoStack(self, itemList: List[QGraphicsItem]) -> None:
        undoCommand = us.deleteShapesUndo(self, itemList)
        self.undoStack.push(undoCommand)

    def undoGroupMoveStack(self, items: List[QGraphicsItem], startPos: List[QPoint],
                           endPos: QPoint) -> None:
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
            if dlg.exec() == QDialog.DialogCode.Accepted:
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
