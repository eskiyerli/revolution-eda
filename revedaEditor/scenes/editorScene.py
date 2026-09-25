# 
# Revolution EDA
# 
# Copyright (c) 2026 Revolution Semiconductor
#
# This Source Code Form is subject to the terms of the
# Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
import json
import pathlib
import time

import shiboken6
from contextlib import contextmanager
from itertools import cycle
from typing import TYPE_CHECKING, Any, List, Optional, Union

from PySide6.QtCore import (QEvent, QPoint, QPointF, QRectF, QSizeF, Qt, QRect)
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
        self.setItemIndexMethod(QGraphicsScene.ItemIndexMethod.NoIndex)
        self.containerWidget = parent
        self.editorWindow = self.containerWidget.editorWindow

        self.majorGrid = self.editorWindow.majorGrid
        self.snapGrid = self.editorWindow.snapGrid
        self.snapTuple = self.editorWindow.snapTuple
        self.snapDistance = min(*self.editorWindow.snapTuple)
        self.snapConnectDistance = self.editorWindow.snapConnectDistance

        # Initialize mouse-related attributes together
        self.mousePressLoc = self.mouseMoveLoc = self.mouseReleaseLoc = None
        # Raw (un-snapped) counterparts used for snap-target evaluation so the
        # snap aperture is anchored to the real cursor, not a grid point.
        self.mouseRawLoc = self.mouseReleaseRawLoc = None

        # Use dictionary unpacking for edit modes
        self.editModes = ddef.editModes(
            **{"selectItem": True, "deleteItem": False, "moveItem": False,
               "constrainedMoveItem": False, "copyItem": False, "rotateItem": False,
               "changeOrigin": False, "zoomView": False, "panView": False,
               "stretchItem": False, "alignItems": False, })

        self.messages = {"selectItem": "Select Item", "deleteItem": "Delete Item",
                         "moveItem": "Move Item", "constrainedMoveItem": "Constrained Move (Shift=Ortho+Diagonal, Ctrl=Ortho)",
                         "copyItem": "Copy: click to place",
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
        self.itemCycler = None
        self._groupItems = []
        self.itemsAtPressSet = set()
        self._draftPen = QPen(QColor(0, 150, 0, 128), int(self.snapGrid / 2), Qt.DashLine)
        self._zoomPen = QPen(QColor(255, 0, 0, 255), 2, Qt.DashLine)
        self._zoomPen.setCosmetic(True)
        self._draftPen.setCosmetic(True)

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
        self.setMinimumRenderSize(0)
        self._initialGroupPos = QPointF(0, 0)
        # Scene point the floating copy group is anchored to while pasting.
        self._copyAnchor = QPointF(0, 0)
        # Virtuoso-style copy options (array rows/columns + X/Y pitch),
        # edited via the F3 options form while a copy is armed.
        self.copyOptions = ddef.copyOptions()
        # Undo index of the add-shapes command pushed by beginClipboardPaste;
        # cancelArmedCopy() undoes it to remove the uncommitted copies.
        self._armedCopyUndoIndex = -1
        self.itemCycler = None
        self.mousePressLoc = QPoint(0, 0)
        self.mouseMoveLoc = QPoint(0, 0)
        self.mouseReleaseLoc = QPoint(0, 0)
        self.mouseRawLoc = None
        self.mouseReleaseRawLoc = None
        self.newAlignLine = None
        self._rightZoomPressLoc: Optional[QPoint] = None
        self._rightZoomRectItem: Optional[QGraphicsRectItem] = None
        self._suppressContextMenu: bool = False

    def contextMenuEvent(self, event) -> None:
        if self._suppressContextMenu:
            self._suppressContextMenu = False
            event.accept()
            return
        if self.itemAt(event.scenePos(), QTransform()) is None:
            self.messageLine.setText("No item selected")
        super().contextMenuEvent(event)

    def mousePressEvent(self, event) -> None:
        modifiers = QGuiApplication.keyboardModifiers()
        if event.button() == Qt.MouseButton.LeftButton:
            self.mousePressLoc = self.snapToGrid(event.scenePos().toPoint())
            # Fallback: a click in a different scene while a clipboard copy
            # is armed commits the paste at the click point in this scene.
            # Normally the armed group already migrated on mouseMoveEvent;
            # this covers cases where migration was skipped (busy mode).
            armed = editorScene.armedCopyScene()
            if (armed is not None and armed is not self
                    and self.editModes.selectItem):
                count = self.pasteClipboard(self.mousePressLoc)
                if count:
                    armed.cancelArmedCopy()
                    self.messageLine.setText(f"Pasted {count} item(s)")
                    event.accept()
                    return
            if self.editModes.selectItem:
                clickedItem = self.itemAt(self.mousePressLoc, QTransform())
                if clickedItem:
                    # Handle additive/toggle selection before calling super
                    self.itemsAtPressSet = {item for item in self.items(self.mousePressLoc)
                                            if item.parentItem() is None}
                    self.itemsAtPressSet = self._filterBySelectModes(self.itemsAtPressSet)
                    if self.itemsAtPressSet:
                        self.itemCycler = cycle(self.itemsAtPressSet)
                        item = next(self.itemCycler)
                        if modifiers == Qt.KeyboardModifier.ShiftModifier:
                            self.setSelectedItems(self.selectedItemsSet | {item})
                            event.accept()
                            return
                        elif modifiers == Qt.KeyboardModifier.ControlModifier:
                            if item in self.selectedItemsSet:
                                self.setSelectedItems(self.selectedItemsSet - {item})
                            else:
                                self.setSelectedItems(self.selectedItemsSet | {item})
                            event.accept()
                            return
                        elif modifiers == Qt.KeyboardModifier.NoModifier:
                            self.setSelectedItems({item})
                elif self.selectionRectItem is None:
                    # Starting rubber band selection
                    self.selectionRectItem = QGraphicsRectItem(self.mousePressLoc.x(),
                                                               self.mousePressLoc.y(), 0, 0)
                    self.selectionRectItem.setPen(self._draftPen)
                    self.selectionRectItem.setZValue(100)
                    self.addItem(self.selectionRectItem)

            # Handle other edit modes
            if self.editModes.moveItem or self.editModes.constrainedMoveItem:
                # If there are already selected items, use them for the move
                # (preserves selection from cycle-through with PageUp).
                # Only pick a new item if nothing is currently selected.
                if not self.selectedItems():
                    clickedItem = self.itemAt(self.mousePressLoc, QTransform())
                    # Resolve to top-level parent (e.g. schematicPinPolygon → schematicPin)
                    if clickedItem:
                        while clickedItem.parentItem() is not None:
                            clickedItem = clickedItem.parentItem()
                    if clickedItem:
                        self.setSelectedItems({clickedItem})
                # Create move group from selected items
                if self.selectedItems():
                    # Record each item's pre-group pos()/transform(). Qt's
                    # createItemGroup()/destroyItemGroup() preserve the scene
                    # position of transformed children by folding the
                    # transform-origin offset into pos() and transform(), which
                    # would corrupt the pos-folded coordinates saved to JSON.
                    for item in self.selectedItems():
                        item._groupInitialState = (item.pos(), item.transform())
                    self.selectedItemGroup = self.createItemGroup(self.selectedItems())
                    self._initialGroupPos = self.selectedItemGroup.pos()
                    for item in self.selectedItemGroup.childItems():
                        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
                    event.accept()
                    return
            elif self.editModes.panView:
                self.centerViewOnPoint(self.mousePressLoc)
            elif self.editModes.zoomView:
                if self.zoomRectItem is None:
                    self.zoomRectItem = QGraphicsRectItem(self.mousePressLoc.x(),
                                                          self.mousePressLoc.y(), 0, 0)
                    self.zoomRectItem.setPen(self._zoomPen)
                    self.zoomRectItem.setZValue(100)
                    self.addItem(self.zoomRectItem)

        elif event.button() == Qt.MouseButton.RightButton:
            self._rightZoomPressLoc = event.scenePos().toPoint()
            self._suppressContextMenu = False

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        self.mouseRawLoc = event.scenePos().toPoint()
        self.mouseMoveLoc = self.snapToGrid(self.mouseRawLoc)
        armed = editorScene.armedCopyScene()
        if (armed is not None and armed is not self
                and self.editModes.selectItem
                and not (event.buttons() & (Qt.MouseButton.LeftButton
                                           | Qt.MouseButton.RightButton
                                           | Qt.MouseButton.MiddleButton))
                and self._clipboardAcceptable()):
            # The cursor entered this scene while a clipboard copy is armed
            # in another — migrate the floating group so it tracks the
            # cursor here and a click places it in this scene.
            self.beginClipboardPaste()
        super().mouseMoveEvent(event)
        if self.editModes.selectItem:
            if self.selectionRectItem and self.mousePressLoc:
                self.selectionRectItem.setRect(QRectF(self.mousePressLoc.toPointF(),
                                                      self.mouseMoveLoc.toPointF()).normalized())
        elif self.editModes.zoomView:
            if self.zoomRectItem and self.mousePressLoc:
                self.zoomRectItem.setRect(QRectF(self.mousePressLoc.toPointF(),
                                                 self.mouseMoveLoc.toPointF()).normalized())

        elif self.editModes.constrainedMoveItem and self.selectedItemGroup and self.mousePressLoc:
            offset = self.mouseMoveLoc - self.mousePressLoc
            constrainedOffset = self._applyMoveConstraint(offset)
            self.selectedItemGroup.setPos(constrainedOffset)
        elif self.editModes.moveItem and self.selectedItemGroup and self.mousePressLoc:
            offset = self.mouseMoveLoc - self.mousePressLoc
            self.selectedItemGroup.setPos(offset)
        elif self.editModes.copyItem and self.selectedItemGroup:
            self.selectedItemGroup.setPos(
                QPointF(self.mouseMoveLoc) - self._copyAnchor)

        if (event.buttons() & Qt.MouseButton.RightButton) and self._rightZoomPressLoc is not None:
            currentPos = event.scenePos().toPoint()
            dragRect = QRectF(self._rightZoomPressLoc.toPointF(),
                              currentPos.toPointF()).normalized()
            if self._rightZoomRectItem is None and (
                    dragRect.width() > self.snapDistance or dragRect.height() > self.snapDistance):
                self._rightZoomRectItem = QGraphicsRectItem(0, 0, 0, 0)
                self._rightZoomRectItem.setPen(self._zoomPen)
                self._rightZoomRectItem.setZValue(100)
                self.addItem(self._rightZoomRectItem)
            if self._rightZoomRectItem is not None:
                self._rightZoomRectItem.setRect(dragRect)

    def mouseReleaseEvent(self, event) -> None:
        # if event.button() != Qt.MouseButton.LeftButton:
        #     super().mouseReleaseEvent(event)
        #     return

        modifiers = QGuiApplication.keyboardModifiers()
        self.mouseReleaseRawLoc = event.scenePos().toPoint()
        self.mouseReleaseLoc = self.snapToGrid(self.mouseReleaseRawLoc)

        if event.button() == Qt.MouseButton.RightButton:
            if self._rightZoomRectItem is not None:
                rect = self._rightZoomRectItem.rect().toRect()
                self.removeItem(self._rightZoomRectItem)
                self._rightZoomRectItem = None
                if rect.width() > self.snapDistance and rect.height() > self.snapDistance:
                    self.zoomToRect(rect)
                    self._suppressContextMenu = True
            self._rightZoomPressLoc = None
            super().mouseReleaseEvent(event)
            return

        if (self.editModes.moveItem or self.editModes.constrainedMoveItem) and self.selectedItemGroup:
            _groupItems = self.selectedItemGroup.childItems()
            # The group pos is the rigid move delta applied to all children.
            _posDiff = self.selectedItemGroup.pos() - self._initialGroupPos
            _initialStates = [
                getattr(item, '_groupInitialState', None) for item in _groupItems
            ]

            self.destroyItemGroup(self.selectedItemGroup)
            self.selectedItemGroup = None

            # createItemGroup()/destroyItemGroup() preserve the scene position
            # of transformed children by folding the origin offset into pos()
            # and transform(). Restore the pre-group state plus the move delta
            # so the file encoders see a clean parent-coordinate translation.
            for item, state in zip(_groupItems, _initialStates):
                if state is not None:
                    item.setTransform(state[1])
                    item.setPos(state[0] + _posDiff)
                    del item._groupInitialState

            if _posDiff != QPointF(0, 0):
                self.undoGroupMoveStack(_groupItems, _initialStates, _posDiff)

            self.setSelectedItems(set())
            self.editModes.setMode("selectItem")
        elif self.editModes.copyItem and self.selectedItemGroup:
            self._commitCopyGroup()
            self.editModes.setMode("selectItem")
        elif self.editModes.selectItem:
            if self.selectionRectItem:
                selectionPath = QPainterPath()
                selectionPath.addRect(self.selectionRectItem.sceneBoundingRect())
                selectionMode = (
                    Qt.ItemSelectionMode.IntersectsItemShape if self.partialSelection else Qt.ItemSelectionMode.ContainsItemShape)
                itemsInRectSet = set(
                    [item for item in self.items(selectionPath, mode=selectionMode) if
                     item.parentItem() is None])
                itemsInRectSet = self._filterBySelectModes(itemsInRectSet)
                if modifiers == Qt.KeyboardModifier.ShiftModifier:
                    selectedItems = self.selectedItemsSet | itemsInRectSet
                elif modifiers == Qt.KeyboardModifier.ControlModifier:
                    selectedItems = self.selectedItemsSet ^ itemsInRectSet
                elif modifiers == Qt.KeyboardModifier.NoModifier:
                    selectedItems = itemsInRectSet
                else:
                    selectedItems = self.selectedItemsSet
                self.setSelectedItems(selectedItems)
                self.removeItem(self.selectionRectItem)
                self.selectionRectItem = None
            elif not self.itemsAtPressSet:
                self.itemCycler = None
                self.selectedItemsSet = set()
                self.deselectAll()
                self.clearSelection()
        elif self.editModes.zoomView and self.zoomRectItem:
            self.zoomToRect(self.zoomRectItem.rect().toRect())
            self.editModes.setMode('selectItem')
            self.removeItem(self.zoomRectItem)
            self.zoomRectItem = None
        elif self.editModes.changeOrigin:
            self.origin = self.mouseReleaseLoc
            self.editModes.setMode('selectItem')
        else:
            self._handleMouseRelease(self.mouseReleaseLoc, event.button())
        self.messageLine.setText(self.messages.get(self.editModes.mode(), ""))
        super().mouseReleaseEvent(event)

    def _filterBySelectModes(self, items: set) -> set:
        """Filter items by the scene's active selectModes.

        Subclasses override this to provide editor-specific filtering logic.
        Base implementation returns items unchanged.
        """
        return items

    def setSelectedItems(self, items: set[QGraphicsItem]) -> None:
        """Synchronize the scene's selection set with Qt item selection."""
        for item in self.selectedItems():
            item.setSelected(False)
        for item in items:
            item.setSelected(True)
        self.selectedItemsSet = set(self.selectedItems())

    def snapToGrid(self, point: QPoint) -> QPoint:
        """Snap point to scene grid."""
        xgrid = self.snapTuple[0]
        ygrid = self.snapTuple[1]
        # Final round() ensures QPoint receives ints even when grid is a float.
        return QPoint(
            round(round(point.x() / xgrid) * xgrid),
            round(round(point.y() / ygrid) * ygrid),
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
        """Block all mouse events when scene is read-only."""
        if self.readOnly and event.type() in self.MOUSE_EVENTS:
            return True

        return super().eventFilter(source, event)

    # ---- clipboard copy/paste -------------------------------------------
    # Per-scene contract: the JSON encoder for scene items, the loadJSON
    # factory class that rebuilds them, the persisted record "type" values
    # the scene accepts, and the shape classes eligible for copying.
    _CLIPBOARD_ENCODER: Optional[type] = None
    _CLIPBOARD_FACTORY: Optional[type] = None
    _CLIPBOARD_TYPES: frozenset = frozenset()
    _CLIPBOARD_SHAPES: tuple = ()

    def copySelectionToClipboard(self) -> int:
        """Serialize selected top-level items to the system clipboard as a
        JSON fragment. Returns the record count."""
        if self._CLIPBOARD_ENCODER is None:
            return 0
        selectedItems = [item for item in self.selectedItems()
                         if item.parentItem() is None
                         and isinstance(item, self._CLIPBOARD_SHAPES)]
        if not selectedItems:
            return 0
        records = [json.loads(json.dumps(item, cls=self._CLIPBOARD_ENCODER))
                   for item in selectedItems]
        QGuiApplication.clipboard().setText(json.dumps(records))
        return len(records)

    def _clipboardRecords(self) -> Optional[list]:
        """Return the clipboard fragment's records when every record type is
        acceptable to this scene; None otherwise."""
        text = QGuiApplication.clipboard().text()
        try:
            records = json.loads(text) if text else None
        except json.JSONDecodeError:
            return None
        if not (isinstance(records, list) and records and all(
                isinstance(r, dict) and r.get("type") in self._CLIPBOARD_TYPES
                for r in records)):
            return None
        return records

    def _clipboardAcceptable(self) -> bool:
        """True when the clipboard holds a fragment this scene can paste."""
        return self._CLIPBOARD_FACTORY is not None and \
            self._clipboardRecords() is not None

    def _clipboardShapes(self) -> list:
        """Instantiate the clipboard fragment into this scene's items."""
        records = self._clipboardRecords()
        if not records or self._CLIPBOARD_FACTORY is None:
            return []
        factory = self._CLIPBOARD_FACTORY(self)
        return [shape for shape in (factory.create(record) for record in records)
                if isinstance(shape, self._CLIPBOARD_SHAPES)]

    def _clipboardShapesArray(self) -> list:
        """Instantiate the clipboard fragment as a ``rows``×``columns``
        array of copies per ``copyOptions``. Element (r, c) is offset by
        ``(c * xOffset, r * yOffset)`` scene units — the Virtuoso Delta
        X/Y pitch convention. A zero pitch falls back to the fragment's
        bounding-box size so arrayed copies abut instead of stacking."""
        opts = self.copyOptions
        rows = max(1, int(opts.rows))
        cols = max(1, int(opts.columns))
        dx = self.snapToBase(opts.xOffset, self.snapTuple[0])
        dy = self.snapToBase(opts.yOffset, self.snapTuple[1])
        allShapes = []
        for r in range(rows):
            for c in range(cols):
                batch = self._clipboardShapes()
                if not batch:
                    return allShapes
                if r == 0 and c == 0 and (dx == 0 or dy == 0):
                    # Default pitch: the fragment's own bbox size.
                    rect = batch[0].sceneBoundingRect()
                    for shape in batch[1:]:
                        rect = rect.united(shape.sceneBoundingRect())
                    if dx == 0:
                        dx = self.snapToBase(
                            rect.width(), self.snapTuple[0]) \
                            or self.snapTuple[0]
                    if dy == 0:
                        dy = self.snapToBase(
                            rect.height(), self.snapTuple[1]) \
                            or self.snapTuple[1]
                offset = QPointF(c * dx, r * dy)
                if not offset.isNull():
                    for shape in batch:
                        shape.setPos(shape.pos() + offset)
                allShapes.extend(batch)
        return allShapes

    def _fixClipboardShapes(self, shapes: list) -> None:
        """Subclass hook for post-instantiation fixups such as allocating
        fresh instance names for a batch of pasted items."""

    @staticmethod
    def _clipboardTopLeft(shapes: list) -> QPointF:
        topLeft = shapes[0].sceneBoundingRect().topLeft()
        for shape in shapes[1:]:
            topLeft = QPointF(
                min(topLeft.x(), shape.sceneBoundingRect().left()),
                min(topLeft.y(), shape.sceneBoundingRect().top()))
        return topLeft

    def pasteClipboard(self, at: Optional[QPoint] = None) -> int:
        """Instantiate the clipboard fragment at ``at`` (defaults to the
        last cursor position) and commit it immediately. The fragment's
        bounding-box top-left lands on the point. Returns the item count."""
        if self.readOnly:
            return 0
        shapes = self._clipboardShapesArray()
        if not shapes:
            return 0
        self._fixClipboardShapes(shapes)
        if at is None:
            at = self.mouseMoveLoc or QPoint(0, 0)
        delta = QPointF(self.snapToGrid(at) - self.snapToGrid(
            self._clipboardTopLeft(shapes).toPoint()))
        for shape in shapes:
            shape.setPos(shape.pos() + delta)
        self.addListUndoStack(shapes)
        return len(shapes)

    # Scene holding an armed (uncommitted) clipboard copy — set by
    # beginClipboardPaste so a click in another scene or ESC in any window
    # can resolve it.
    _armedCopyScene: Optional["editorScene"] = None

    @classmethod
    def armedCopyScene(cls) -> Optional["editorScene"]:
        """Return the scene holding an armed clipboard copy, if any."""
        scene = cls._armedCopyScene
        if scene is not None and not shiboken6.isValid(scene):
            cls._armedCopyScene = None
            scene = None
        return scene

    def beginClipboardPaste(self, at: Optional[QPoint] = None) -> int:
        """Instantiate the clipboard fragment as a floating group that
        tracks the cursor; the next left-click commits the placement.
        Returns the item count, 0 when nothing could be pasted."""
        if self.readOnly:
            return 0
        armed = editorScene.armedCopyScene()
        if armed is not None and armed is not self:
            armed.cancelArmedCopy()
        if self.editModes.copyItem and self.selectedItemGroup:
            self._commitCopyGroup()
            self.editModes.setMode("selectItem")
        shapes = self._clipboardShapesArray()
        if not shapes:
            return 0
        self._fixClipboardShapes(shapes)
        self.addListUndoStack(shapes)
        self._armedCopyUndoIndex = self.undoStack.index() - 1
        for shape in shapes:
            shape._groupInitialState = (shape.pos(), shape.transform())
        self.selectedItemGroup = self.createItemGroup(shapes)
        self._initialGroupPos = self.selectedItemGroup.pos()
        self._copyAnchor = QPointF(
            self.snapToGrid(self._clipboardTopLeft(shapes).toPoint()))
        if at is None:
            at = self.mouseMoveLoc or QPoint(0, 0)
        self.selectedItemGroup.setPos(
            QPointF(self.snapToGrid(at)) - self._copyAnchor)
        self.selectedItemGroup.setSelected(True)
        self.editModes.setMode("copyItem")
        editorScene._armedCopyScene = self
        return len(shapes)

    def cancelArmedCopy(self) -> bool:
        """Cancel the armed clipboard paste: dissolve the floating group
        and remove the uncommitted copies along with their undo entry."""
        group = self.selectedItemGroup
        if group is None:
            if editorScene._armedCopyScene is self:
                editorScene._armedCopyScene = None
            return False
        items = group.childItems()
        self.destroyItemGroup(group)
        self.selectedItemGroup = None
        for item in items:
            state = getattr(item, '_groupInitialState', None)
            if state is not None:
                item.setTransform(state[1])
                item.setPos(state[0])
                del item._groupInitialState
        self.clearSelection()
        # The copies were pushed as one add-shapes command; if it is still
        # the top undo entry, undoing it removes them from the scene.
        if (self._armedCopyUndoIndex >= 0
                and self.undoStack.index() == self._armedCopyUndoIndex + 1):
            self.undoStack.removeLastCommand()
        else:
            for item in items:
                self.removeItem(item)
            self.itemsRefSet -= set(items)
        self._armedCopyUndoIndex = -1
        if self.editModes.copyItem:
            self.editModes.setMode("selectItem")
        if editorScene._armedCopyScene is self:
            editorScene._armedCopyScene = None
        return True

    def _commitCopyGroup(self) -> None:
        """Dissolve the floating copy group, restoring each item's pre-group
        pos()/transform() plus the accumulated paste delta."""
        _groupItems = self.selectedItemGroup.childItems()
        _posDiff = self.selectedItemGroup.pos() - self._initialGroupPos
        self.destroyItemGroup(self.selectedItemGroup)
        self.selectedItemGroup = None
        for item in _groupItems:
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
            state = getattr(item, '_groupInitialState', None)
            if state is not None:
                item.setTransform(state[1])
                item.setPos(state[0] + _posDiff)
                del item._groupInitialState
        self._armedCopyUndoIndex = -1
        if editorScene._armedCopyScene is self:
            editorScene._armedCopyScene = None

    def rearmClipboardPaste(self) -> int:
        """Rebuild the armed floating copy with the current
        ``copyOptions`` — called by the options form so edits to
        rows/columns/pitch update the ghost live. Returns the item
        count, 0 when no copy is armed."""
        if not (self.editModes.copyItem and self.selectedItemGroup):
            return 0
        at = self.mouseMoveLoc or QPoint(0, 0)
        self.cancelArmedCopy()
        return self.beginClipboardPaste(at)

    def flipHorizontal(self) -> None:
        for item in self.selectedItems():
            item.flipTuple = (-1, 1)

    def flipVertical(self) -> None:
        for item in self.selectedItems():
            item.flipTuple = (1, -1)

    def selectAll(self) -> None:
        """
        Select all items in the scene.
        """
        self.setSelectedItems(set(self.items()))

    def deselectAll(self) -> None:
        """
        Deselect all items in the scene.
        """
        # Cancel an armed clipboard copy so its floating group isn't
        # orphaned in the scene.
        if editorScene.armedCopyScene() is self:
            self.cancelArmedCopy()
        self.setSelectedItems(set())
        self.itemsAtPressSet.clear()
        self.selectionRectItem = None
        self.zoomRectItem = None
        self.selectedItemGroup = None
        self.itemCycler = None
        self.newAlignLine = None
        self.newNet = None
        # self.stretchNet = None
        self.newInstance = None
        self.newPin = None
        self.newText = None
        self.editModes.setMode("selectItem")
        self.messageLine.setText("All items deselected")

    def deleteSelectedItems(self) -> None:
        if self.selectedItems() is not None:
            for item in self.selectedItems():
                # self.removeItem(item)
                undoCommand = us.deleteShapeUndo(self, item)
                self.undoStack.push(undoCommand)
            self.update()  # update the scene

    def stretchSelectedItems(self) -> None:
        for item in self.selectedItems():
            if hasattr(item, "stretch"):
                item.stretch = True

    def reloadScene(self) -> bool:
        """Reload the current file and report whether its scene was realized."""
        return self._safeLoadDesign(self.editorWindow.file, reload=True)

    def _safeLoadDesign(self, file, reload=False) -> bool:
        """Safely load a design while avoiding painter-state errors."""
        loaded = False
        # Disable all updates and painting
        for view in self.views():
            view.setUpdatesEnabled(False)
            view.viewport().setUpdatesEnabled(False)

        self.blockSignals(True)

        try:
            if reload:
                self.clear()
                self.itemsRefSet.clear()

            # Concrete scenes return True only after successful reconstruction.
            loaded = bool(self.loadDesign(file))
            if loaded and self.items():
                self.setSceneRect(self._fitBoundsRect())
        except Exception as error:
            self.logger.error("Error reloading design scene: %s", error)
            loaded = False
        finally:
            self.blockSignals(False)
            for view in self.views():
                view.setUpdatesEnabled(True)
                view.viewport().setUpdatesEnabled(True)
            QApplication.processEvents()

        return loaded

    def loadDesign(self, filePathObj: pathlib.Path):
        """
        Load the design from the specified file.
        Must be implemented in subclasses.
        """
        raise NotImplementedError("Subclasses must implement loadDesign")

    def _fitBoundsRect(self) -> QRectF:
        """Bounds used by fitItemsInView. Subclasses may substitute a
        stable rect for items whose boundingRect is view-dependent."""
        return self.itemsBoundingRect()

    def fitItemsInView(self) -> None:
        self.setSceneRect(self._fitBoundsRect().adjusted(-40, -40, 40, 40))
        self.views()[0].fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.views()[0].viewport().update()

    def zoomToRect(self, rect: QRect = None) -> None:
        if rect is None and self.zoomRectItem:
            rect = self.zoomRectItem.rect().toRect()
        if rect is not None and not QRectF(rect).isEmpty():
            self.setSceneRect(QRectF(rect).adjusted(-40, -40, 40, 40))
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

    def zoomToRect(self, newSceneRect:QRect):
        self.setSceneRect(newSceneRect)
        view = self.views()[0]
        view.fitInView(newSceneRect, Qt.AspectRatioMode.KeepAspectRatio)
        view.viewport().update()    

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

    def _applyMoveConstraint(self, offset: QPoint) -> QPoint:
        """Apply movement constraint based on keyboard modifiers.

        Shift = Orthogonal + Diagonal (8 directions)
        Ctrl = Only Orthogonal (4 directions: horizontal/vertical)
        None = Free movement (no constraint)

        Args:
            offset: Raw movement offset

        Returns:
            Constrained QPoint
        """
        import math

        modifiers = QGuiApplication.keyboardModifiers()
        dx, dy = offset.x(), offset.y()

        if modifiers == Qt.KeyboardModifier.ControlModifier:
            # Orthogonal only - snap to closest axis
            if abs(dx) > abs(dy):
                return QPoint(dx, 0)
            else:
                return QPoint(0, dy)
        elif modifiers == Qt.KeyboardModifier.ShiftModifier:
            # Orthogonal + Diagonal - snap to 8 directions
            angle = math.atan2(dy, dx)
            dist = math.sqrt(dx * dx + dy * dy)
            # Snap to nearest 45 degrees
            snapped_angle = round(angle / (math.pi / 4)) * (math.pi / 4)
            new_dx = int(dist * math.cos(snapped_angle))
            new_dy = int(dist * math.sin(snapped_angle))
            return QPoint(new_dx, new_dy)
        else:
            # No constraint
            return offset

    def undoGroupMoveStack(self, items: List[QGraphicsItem],
                           initialStates: List, posDiff: QPointF) -> None:
        undoCommand = us.undoGroupMove(self, items, initialStates, posDiff)
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
            self.logger.info(
                f"Total processing time: {end_time - start_time:.3f} seconds"
            )

    @property
    def draftPen(self):
        return self._draftPen
