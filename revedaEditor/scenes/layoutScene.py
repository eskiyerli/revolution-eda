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
from typing import Any, ClassVar, Dict, List, Union, Optional

import orjson
import shiboken6
from quantiphy import Quantity
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
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSceneMouseEvent,
)

import revedaEditor.backend.correspondence as corr
import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.connectivity as conn
import revedaEditor.backend.libraryMethods as libm
import revedaEditor.backend.libraryModelView as lmview
import revedaEditor.backend.undoStack as us
import revedaEditor.common.layoutBoolean as lbool
import revedaEditor.common.layoutFlatten as lflat
import revedaEditor.common.layoutMerge as lmerge
import revedaEditor.common.layoutShapes as lshp  # import layout shapes
import revedaEditor.fileio.exportGDS as gdse
import revedaEditor.fileio.layoutEncoder as layenc
import revedaEditor.fileio.loadJSON as lj
import revedaEditor.fileio.schemaValidation as sv
import revedaEditor.gui.editFunctions as edf
import revedaEditor.gui.fileDialogues as fd
import revedaEditor.gui.layoutDialogues as ldlg
import revedaEditor.gui.propertyDialogues as pdlg
from revedaEditor.backend.pdkLoader import lazyPDKModule
from revedaEditor.gui.alignItems import alignItemsDialogue, alignToLine
from revedaEditor.scenes.editorScene import editorScene

fabproc = lazyPDKModule("process")
laylyr = lazyPDKModule("layoutLayers")
schlyr = lazyPDKModule("schLayers")
pcells = lazyPDKModule("pcells")


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
        lshp.layoutMultipart,
        lshp.layoutGroup,
        lshp.layoutRuler,
    )
    # Clipboard contract for editorScene.copySelectionToClipboard et al.
    _CLIPBOARD_ENCODER = layenc.layoutEncoder
    _CLIPBOARD_FACTORY = lj.layoutItems
    _CLIPBOARD_TYPES = frozenset(
        {"Inst", "Pcell", "Rect", "Path", "Label", "Pin", "Polygon", "Via",
         "Ruler", "Multipart", "Group"})
    _CLIPBOARD_SHAPES = LAYOUT_SHAPES
    # Object filter categories shown below the LSW, mapped to the layout
    # shape classes they control. Pin name labels are filtered with pins.
    objectFilterClasses = {
        "Instances": (lshp.layoutInstance,),
        "Pins": (lshp.layoutPin,),
        "Vias": (lshp.layoutVia, lshp.layoutViaArray),
        "Labels": (lshp.layoutLabel,),
        "Paths": (lshp.layoutPath,),
        "Shapes": (lshp.layoutRect, lshp.layoutPolygon, lshp.layoutMultipart),
        "Groups": (lshp.layoutGroup,),
    }
    alignLineFinished = Signal(lshp.alignLine)
    connectivityInvalidated = Signal()
    connectivityRebuilt = Signal()

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
            drawPolygon=False,
            addLabel=False,
            addVia=False,
            drawRect=False,
            drawRuler=False,
            drawMultipart=False,
            stretchItem=False,
            addInstance=False,
            cutShape=False,
            alignItems=False,
            highlightNet=False,
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
            "drawPolygon": "Draw Polygon",
            "addLabel": "Add Label",
            "addVia": "Add Via",
            "drawRect": "Draw Rect",
            "drawRuler": "Draw Ruler",
            "drawMultipart": "Draw Multipart: click start, click to finish",
            "addInstance": "Add Instance",
            "cutShape": "Cut Shape",
            "highlightNet": "Highlight Net: click a shape, pin, or label",
        })
        self.newInstance = None
        self.layoutInstanceTuple = None
        # F3 placement options: prepared PCell values and/or mosaic geometry
        # consumed by the next addLayoutInstance() click.
        self.pendingInstanceOptions = None
        self._scale = fabproc.dbu if fabproc else 1000
        self.itemCounter = 0
        self.newPath = None
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
        self._newMultipart = None
        # (kind, params) set by the multipart create dialogue; params carry
        # item-local geometry anchors that the two-click draw fills in.
        self.newMultipartSpec = None
        self._selectionRectItem = None
        # Ruler labels render inverse-scaled, so the font size is an actual
        # screen point size — not a scene-unit size.
        self.rulerFont = self.setRulerFont(12)
        self.rulerFont.setKerning(False)
        self.rulerWidth = 2
        # Ruler options (F3 while drawing): angle constraint and edge snap.
        self.rulerMode = 0
        self.rulerSnapToEdge = True
        self.setItemIndexMethod(QGraphicsScene.ItemIndexMethod.BspTreeIndex)
        self._draftPen = QPen(Qt.PenStyle.DashLine)
        self._draftPen.setColor(QColor(0, 150, 0))
        self._draftPen.setWidth(2)
        self._draftPen.setCosmetic(True)
        self.setMinimumRenderSize(0.2)
        self.newAlignLine = None
        self.alignLineFinished.connect(alignToLine)
        # Unified layout connectivity cache (revedaEditor.connectivity.layout
        # engine, shared with RCX's record-level path).
        self._connectivityCache = None
        self._connectivityItemGroup = {}
        # Bulk loading suppresses repeated cache invalidation and flyline
        # geometry work while a large set of top-level items is inserted.
        self._bulkLoadDepth = 0
        self._connectivityDirtyDuringBulkLoad = False
        self._discardQueuedBulkChange = False
        # member item -> overlay QGraphicsRectItem
        self._netHighlightItems = {}
        # Schematic->layout rat's nest: drawn layoutFlightLine items, their
        # cached endpoint pins (net -> [layoutPin]), the source schematic
        # tuple, and a re-entrancy guard for sync loops.
        self._flylines = []
        self._flylinePins = {}
        self._flylineSource = None
        self._syncingFlylines = False
        self.changed.connect(self.markConnectivityDirty)
        # Undo/redo moves don't emit changed() reliably — refresh flyline
        # topology (island merge/split) on command-stack index changes.
        self.undoStack.indexChanged.connect(self._onUndoIndexChanged)

    @property
    def drawMode(self):
        return any(
            (
                self.editModes.drawPath,
                self.editModes.drawPin,
                self.editModes.drawPolygon,
                self.editModes.drawRect,
                self.editModes.drawRuler,
                self.editModes.drawMultipart,
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
        elif (self.editModes.highlightNet
              and event.button() == Qt.MouseButton.LeftButton):
            self.highlightNetAtPoint(self.mousePressLoc)
            event.accept()
            return
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
        if self.editModes.drawPath:
            if self.newPath is not None and self.newPath.scene() is None:
                self.newPath = None  # removed while drawing (e.g. undo)
            if self.newPath is not None:
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
            anchor = (self.newInstance.childrenBoundingRect().bottomLeft().toPoint()
                      if isinstance(self.newInstance, lshp.layoutGroup)
                      else self.newInstance.start)
            self.newInstance.setPos(self.snapToGrid(self.mouseMoveLoc - anchor))
        # Handle drawing polygon mode
        elif self.editModes.drawPolygon and self.newPolygon is not None:
            self.polygonGuideLine.setLine(
                QLineF(self.newPolygon.points[-1], self.mouseMoveLoc)
            )
        elif self.editModes.drawRuler and self._newRuler is not None:
            if self._newRuler.scene() is None:
                self._newRuler = None  # removed while drawing (e.g. undo)
            if self._newRuler is not None:
                rulerEnd = self.mouseMoveLoc
                if self.rulerSnapToEdge:
                    snapped = self.snapToClosestEdge(
                        self.mouseMoveLoc, ruler=self._newRuler)
                    if snapped != self.mouseMoveLoc:
                        rulerEnd = snapped
                self._newRuler.draftLine = QLineF(
                    self._newRuler.draftLine.p1(), rulerEnd
                )
        elif self.editModes.drawMultipart and self._newMultipart is not None:
            self._newMultipart.updateDraftGeometry(self.mouseMoveLoc)
        # Handle adding via mode with array via tuple
        elif self.editModes.addVia and self.arrayVia is not None:
            self.arrayVia.setPos(self.mouseMoveLoc - self.arrayVia.start)

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
        statusText = (
            f"Cursor Position: ({cursorPosition.x():.3f}u, {cursorPosition.y():.3f}u)"
        )
        if self.editModes.drawRuler and self._newRuler is not None:
            rulerLength = self.toLayoutDistance(
                self._newRuler.draftLine.length())
            statusText += f"   Ruler: {rulerLength:.3f}u"
        self.statusLine.showMessage(statusText)
        self.messageLine.setText(self.messages.get(self.editModes.mode(), self.editModes.mode()))

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        # The changed signal re-anchors flyline geometry live; a committed
        # move can also merge/split connectivity islands, so force the
        # connectivity rebuild (-> _syncFlylines) once per release.
        if self._flylinePins:
            _ = self.connectivity

    def _handleMouseRelease(self, mousePos: QPoint, button: Qt.MouseButton) -> None:
        if button != Qt.MouseButton.LeftButton:
            return
        try:
            if self.editModes.drawPath:
                self.drawLayoutPath(mousePos)
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
            elif self.editModes.drawMultipart:
                self.drawLayoutMultipart(mousePos)
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
        exclude: Optional[QGraphicsItem] = None,
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
            if isinstance(item, lshp.layoutRuler) or item is ruler or item is exclude or getattr(item, "drcError", False):
                continue
            edges = lshp.layoutRuler._extractItemEdges(item)
            for p1, p2 in edges:
                ptOnEdge = lshp.layoutRuler._closestPointOnSegment(pointF, p1, p2)
                dist = QLineF(pointF, ptOnEdge).length()
                if dist < bestDist:
                    bestDist = dist
                    closestPoint = ptOnEdge
        return closestPoint

    _RULER_MODE_NAMES: ClassVar = {0: "Manhattan", 1: "Diagonal",
                                   2: "Any Angle"}

    def applyRulerMode(self, mode: int) -> None:
        """Set the ruler angle constraint (F3 options) for the in-progress
        ruler — re-snapped to the current mouse position — and future ones."""
        self.rulerMode = mode
        if self._newRuler is not None:
            # The mode setter re-snaps the draft; its end-point already
            # tracks the last mouse position (mouseMoveEvent keeps it in
            # sync while drawRuler is active).
            self._newRuler.mode = mode

    def drawLayoutRuler(self):
        if self._newRuler:
            # Snap the endpoint before finalizing
            endPt = (self.snapToClosestEdge(
                self.mouseReleaseLoc, ruler=self._newRuler)
                if self.rulerSnapToEdge else self.mouseReleaseLoc)
            self._newRuler.draftLine = QLineF(
                self._newRuler.draftLine.p1(), endPt
            )
            if self._newRuler.draftLine.isNull():
                self.undoStack.removeLastCommand()
            self._newRuler = None
        else:
            startPt = (self.snapToClosestEdge(self.mouseReleaseLoc)
                       if self.rulerSnapToEdge else self.mouseReleaseLoc)
            self._newRuler = lshp.layoutRuler(
                QLineF(startPt, startPt),
                self.rulerWidth,
                self.rulerFont,
                self.rulerMode,
            )
            self.addUndoStack(self._newRuler)

    def drawLayoutMultipart(self, mousePos: QPoint):
        """Two-click draw for composite items: first click anchors the item
        at the cursor, the second fixes the geometry (ring extents for a
        guard ring, far endpoint for shielded path / bus route)."""
        if self._newMultipart is not None:
            self._newMultipart.updateDraftGeometry(mousePos)
            if self._newMultipart.childrenBoundingRect().isEmpty():
                # Degenerate geometry (start == end): drop the draft.
                self.undoStack.removeLastCommand()
            self._newMultipart = None
            return
        if self.newMultipartSpec is None:
            return
        kind, params = self.newMultipartSpec
        cls = lshp.MULTIPART_KINDS.get(kind)
        if cls is None:
            self.messageLine.setText(f"Unknown multipart kind: {kind}")
            return
        self._newMultipart = cls(dict(params))
        self._newMultipart.setPos(mousePos)
        self._newMultipart.updateDraftGeometry(mousePos)
        self.addUndoStack(self._newMultipart)

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

    def mergeSelectedItems(self):
        """Merge mergeable selected items (see common/layoutMerge.py)."""
        # Dissolve a live selection group first so merge sees real items,
        # not children of an in-progress move/copy group.
        if self.selectedItemGroup is not None:
            self.destroyItemGroup(self.selectedItemGroup)
            self.selectedItemGroup = None
        produced, consumed = lmerge.mergeLayoutItems(
            list(self.selectedItemsSet), self.logger
        )
        if not produced:
            self.messageLine.setText("No mergeable items selected")
            return
        for item in consumed:
            item.setSelected(False)
        self.undoStack.push(us.addDeleteShapesUndo(self, produced, consumed))
        for item in produced:
            # addDeleteShapesUndo bypasses addUndoStack's filter hook.
            self._applyObjectFilter(item)
        self.setSelectedItems(set(produced))
        self.messageLine.setText(
            f"Merged {len(consumed)} items into {len(produced)} shape(s)"
        )

    def groupSelectedItems(self):
        """Combine the selected top-level items into a persistent
        ``layoutGroup`` that selects/moves/copies as one unit."""
        if self.selectedItemGroup is not None:
            self.destroyItemGroup(self.selectedItemGroup)
            self.selectedItemGroup = None
        members = [
            item
            for item in self.selectedItemsSet
            if item.parentItem() is None
            and isinstance(item, tuple(self.LAYOUT_SHAPES))
        ]
        if len(members) < 2:
            self.messageLine.setText("Select at least two items to group")
            return
        for item in members:
            item.setSelected(False)
        group = lshp.layoutGroup()
        self.undoStack.push(us.undoGroupShapes(self, group, members, True))
        self._applyObjectFilter(group)
        self.setSelectedItems({group})
        self.messageLine.setText(f"Grouped {len(members)} items")

    def ungroupSelectedItems(self):
        """Explode each selected ``layoutGroup`` back into top-level items."""
        if self.selectedItemGroup is not None:
            self.destroyItemGroup(self.selectedItemGroup)
            self.selectedItemGroup = None
        groups = [
            item
            for item in self.selectedItemsSet
            if isinstance(item, lshp.layoutGroup)
        ]
        if not groups:
            self.messageLine.setText("No grouped items selected")
            return
        released = []
        for group in groups:
            members = list(group.shapes)
            self.undoStack.push(us.undoGroupShapes(self, group, members, False))
            for item in members:
                self._applyObjectFilter(item)
            released.extend(members)
        self.setSelectedItems(set(released))
        self.messageLine.setText(f"Ungrouped {len(groups)} group(s)")

    def booleanSelectedItems(self, op: str, amount: float = 0.0):
        """Apply a boolean/size layer op to the selection (see
        common/layoutBoolean.py). ``op`` is one of or/and/xor/not/grow/shrink;
        ``amount`` is the sizing distance in scene units for grow/shrink."""
        if self.selectedItemGroup is not None:
            self.destroyItemGroup(self.selectedItemGroup)
            self.selectedItemGroup = None
        produced, consumed = lbool.booleanLayerItems(
            list(self.selectedItemsSet), op, amount, self.logger
        )
        if not produced:
            self.messageLine.setText(f"Layer op '{op}' produced no shapes")
            return
        for item in consumed:
            item.setSelected(False)
        self.undoStack.push(us.addDeleteShapesUndo(self, produced, consumed))
        for item in produced:
            self._applyObjectFilter(item)
        self.setSelectedItems(set(produced))
        self.messageLine.setText(
            f"Layer op '{op}': {len(consumed)} -> {len(produced)} shape(s)"
        )

    def flattenSelection(self):
        """Replace selected layout instances with their contents as
        top-level shapes (see common/layoutFlatten.py). Mosaic elements and
        nested instances are expanded recursively."""
        if self.selectedItemGroup is not None:
            self.destroyItemGroup(self.selectedItemGroup)
            self.selectedItemGroup = None
        instances = [
            item
            for item in self.selectedItemsSet
            if isinstance(item, (lshp.layoutInstance, lshp.layoutMultipart))
        ]
        if not instances:
            self.messageLine.setText("No instances selected to flatten")
            return
        produced = []
        for instance in instances:
            produced.extend(lflat.flattenInstance(instance, self.logger))
        if not produced:
            self.messageLine.setText("Flatten produced no shapes")
            return
        for item in instances:
            item.setSelected(False)
        self.undoStack.push(us.addDeleteShapesUndo(self, produced, instances))
        for item in produced:
            self._applyObjectFilter(item)
        self.setSelectedItems(set(produced))
        self.messageLine.setText(
            f"Flattened {len(instances)} instance(s) into {len(produced)} shape(s)"
        )

    def makeCellFromSelection(self, libName: str, cellName: str,
                              overwrite: bool = False):
        """Write the selected top-level items to ``lib/cell/layout.json`` and
        replace them with an instance of the new cell.

        The cell's contents are shifted so the selection's bounding-box
        bottom-left is the cell origin; the replacement instance is placed at
        that offset, leaving the view unchanged.  An existing cellview file
        is never clobbered unless ``overwrite`` is true (the GUI asks first);
        the new cell is registered in the library model so the browser shows
        it without a refresh."""
        if self.selectedItemGroup is not None:
            self.destroyItemGroup(self.selectedItemGroup)
            self.selectedItemGroup = None
        items = [
            item
            for item in self.selectedItemsSet
            if item.parentItem() is None
            and isinstance(item, tuple(self.LAYOUT_SHAPES))
            and not isinstance(item, lshp.layoutRuler)
        ]
        if not items:
            self.messageLine.setText("No layout shapes selected")
            return False
        libPath = self.libraryDict.get(libName)
        if libPath is None:
            self.messageLine.setText(f"Unknown library: {libName}")
            return False
        cellDir = pathlib.Path(libPath) / cellName
        filePathObj = cellDir / "layout.json"
        if filePathObj.exists() and not overwrite:
            self.messageLine.setText(
                f"{libName}/{cellName}/layout already exists")
            return False
        cellDir.mkdir(parents=True, exist_ok=True)

        # Rebuild items at cell-local coordinates: origin at the selection
        # bounds' bottom-left so the instance lands back on the same spot.
        bounds = None
        for item in items:
            itemBounds = item.sceneBoundingRect()
            bounds = itemBounds if bounds is None else bounds.united(itemBounds)
        origin = QPointF(bounds.bottomLeft())
        factory = lj.layoutItems(self)
        records = json.loads(json.dumps(items, cls=layenc.layoutEncoder))
        cellShapes = [
            shape
            for data in records
            if (shape := factory.create(data)) is not None
        ]
        for shape in cellShapes:
            shape.moveBy(-origin.x(), -origin.y())

        cellRecords = json.loads(json.dumps(cellShapes, cls=layenc.layoutEncoder))
        cellData = [
            sv.make_view_header("layout"),
            {"snapGrid": (self.majorGrid / fabproc.dbu,
                          self.snapGrid / fabproc.dbu)},
            *cellRecords,
        ]
        with filePathObj.open("w") as f:
            json.dump(cellData, f, cls=layenc.layoutEncoder, separators=(",", ":"))
        self._registerNewCellview(libName, cellName, cellDir, filePathObj)

        instance = lshp.layoutInstance(cellShapes)
        instance.libraryName = libName
        instance.cellName = cellName
        instance.viewName = "layout"
        self.itemCounter += 1
        instance.counter = self.itemCounter
        instance.instanceName = f"I{self.itemCounter}"
        instance.setPos(origin)

        for item in items:
            item.setSelected(False)
        self.undoStack.push(us.addDeleteShapesUndo(self, [instance], items))
        self.setSelectedItems({instance})
        self.messageLine.setText(
            f"Created {libName}/{cellName}/layout from {len(items)} item(s)"
        )
        return True

    def _registerNewCellview(self, libName: str, cellName: str,
                             cellDir: pathlib.Path,
                             viewPath: pathlib.Path) -> None:
        """Insert the freshly written cell/view into the app library model so
        the browser shows it without a rescan.  No-op when no model is
        attached (headless/test contexts)."""
        model = getattr(getattr(self.editorWindow, "appMainW", None),
                        "libraryModel", None)
        if model is None:
            return
        import revedaEditor.backend.libBackEnd as libb
        libItem = libm.getLibItem(model, libName)
        if libItem is None:
            return
        cellIt = libm.getCellItem(libItem, cellName)
        if cellIt is None:
            cellIt = libb.cellItem(cellDir)
            libItem.appendRow(cellIt)
        if libm.getViewItem(cellIt, "layout") is None:
            cellIt.appendRow(libb.viewItem(viewPath))

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

        # layoutPolygon expects integer QPoint vertices; normalize rect
        # corners (QPointF) so the split results remain stretchable.
        points = [QPoint(round(p.x()), round(p.y())) for p in points]

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

            # Create two new polygons using list slicing. Intersection points
            # are QPointF; layoutPolygon expects integer QPoint vertices.
            p1, p2 = p1.toPoint(), p2.toPoint()
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

    def _splitPath(self, item: lshp.layoutPath, line: QLineF):
        """Split a path where the cut line crosses its centreline."""
        p1, p2 = item.sceneEndPoints
        intersectionType, cutPoint = line.intersects(
            QLineF(p1.toPointF(), p2.toPointF())
        )
        if intersectionType != QLineF.IntersectionType.BoundedIntersection:
            return
        if (
            QLineF(p1.toPointF(), cutPoint).isNull()
            or QLineF(cutPoint, p2.toPointF()).isNull()
        ):
            return
        path1 = lshp.layoutPath(
            QLineF(p1.toPointF(), cutPoint),
            item.layer,
            item.width,
            item.startExtend,
            0,
            item.mode,
        )
        path1.name = item.name
        path2 = lshp.layoutPath(
            QLineF(cutPoint, p2.toPointF()),
            item.layer,
            item.width,
            0,
            item.endExtend,
            item.mode,
        )
        path2.name = item.name
        self.undoStack.beginMacro("Split Path")
        self.deleteUndoStack(item)
        self.addUndoStack(path1)
        self.addUndoStack(path2)
        self.undoStack.endMacro()

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
            if self.newInstance is None:
                return
            self.addUndoStack(self.newInstance)
            anchor = (self.newInstance.childrenBoundingRect().bottomLeft().toPoint()
                      if isinstance(self.newInstance, lshp.layoutGroup)
                      else self.newInstance.start)
            self.newInstance.setPos(
                self.snapToGrid(self.mouseReleaseLoc - anchor))

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
        # Second release finalizes the in-progress rectangle; return to
        # select mode instead of anchoring another one.
        if self.newRect:
            if self.newRect.rect.isNull():
                self.removeItem(self.newRect)
                self.undoStack.removeLastCommand()
            self.newRect = None
            self.editModes.setMode("selectItem")
            self.editorWindow.messageLine.setText(
                self.messages.get("selectItem", "Select Item")
            )
            return
        self.editorWindow.messageLine.setText("Rectangle mode.")
        # Create a new rectangle
        self.newRect = lshp.layoutRect(
            self.mouseReleaseLoc,
            self.mouseReleaseLoc,
            self.selectEdLayer,
        )
        self.addUndoStack(self.newRect)

    def drawLayoutPath(self, point: QPoint):
        """
        Commit the in-progress path segment at ``point`` and start the next
        one, so a multi-segment path is a chain of segments sharing on-grid
        vertices.
        """
        self.editorWindow.messageLine.setText("Path mode")
        if self.newPath is not None and self.newPath.scene() is None:
            # In-progress segment was removed while drawing (e.g. undo).
            self.newPath = None
        if self.newPath is not None:
            self.newPath.draftLine = QLineF(self.newPath.draftLine.p1(), point)
            if self.newPath.draftLine.isNull():
                # Zero-length click: keep the segment open for a real end point.
                return
            startPoint = self.newPath.sceneEndPoints[1]
            self.newPath = None
            continuation = True
        else:
            startPoint = point
            continuation = False
        self._createLayoutPath(startPoint, continuation)

    _PATH_MODE_NAMES: ClassVar = {0: "Manhattan", 1: "Diagonal", 2: "Any Angle",
                                  3: "Horizontal", 4: "Vertical"}
    _PATH_MODE_CYCLE: ClassVar = (0, 1, 2)  # manhattan -> diagonal -> any angle

    def cyclePathMode(self) -> None:
        """Cycle the path snap mode mid-draw (F3) — the layout counterpart
        of ``schematicScene.cycleWireDrawMode``. Updates the in-progress
        segment's constraint as well as future segments."""
        if self.newPathTuple is None:
            return
        order = self._PATH_MODE_CYCLE
        current = self.newPathTuple.pathMode
        nextMode = (order[(order.index(current) + 1) % len(order)]
                    if current in order else order[0])
        self.newPathTuple = self.newPathTuple._replace(pathMode=nextMode)
        if self.newPath is not None:
            self.newPath.mode = nextMode
        self.editorWindow.messageLine.setText(
            f"Path Angle: {self._PATH_MODE_NAMES[nextMode]}")

    def _createLayoutPath(self, point: QPoint, continuation: bool = False):
        startExtend = int(self.newPathTuple.startExtend)
        if continuation:
            # A chained segment must reach half the path width behind the
            # joint, otherwise a turn leaves a notch at the outer corner.
            startExtend = max(startExtend, round(self.newPathTuple.width / 2))
        self.newPath = lshp.layoutPath(
            QLineF(point, point),
            self.newPathTuple.layer,
            self.newPathTuple.width,
            startExtend,
            int(self.newPathTuple.endExtend),
            self.newPathTuple.pathMode,
        )
        self.newPath.name = self.newPathTuple.name
        self.addUndoStack(self.newPath)

    def addNewInstance(self) -> Union[lshp.layoutInstance, lshp.layoutPcell]:
        newInstance = self.instLayout(self.layoutInstanceTuple)
        if newInstance is None:
            return None
        options = self.pendingInstanceOptions
        if isinstance(newInstance, lshp.layoutPcell) and options is None:
            # Preserve the pre-F3 PCell flow: first placement opens the
            # parameter/mosaic form when no explicit placement options exist.
            dlg = ldlg.layoutInstanceDialogue(self.editorWindow)
            dlg.instanceLibName.setText(newInstance.libraryName)
            dlg.instanceCellName.setText(newInstance.cellName)
            dlg.instanceViewName.setText(newInstance.viewName)
            dlg.arrayGroup.show()
            dlg.rowsEdit.setText("1")
            dlg.colsEdit.setText("1")
            dlg.rowPitchEdit.setText("0")
            dlg.colPitchEdit.setText("0")
            lineEditDict = self.extractPcellInstanceParameters(newInstance)
            if lineEditDict:
                dlg.pcellParamsGroup.show()
                for key, value in lineEditDict.items():
                    dlg.pcellParamsLayout.addRow(key, value)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                instanceValuesDict = {
                    key: value.text() for key, value in lineEditDict.items()}
                if instanceValuesDict:
                    newInstance(*instanceValuesDict.values())
                arraySpec = dlg.arraySpec()
                if arraySpec is not None:
                    rows, cols, rowPitch, colPitch = arraySpec
                    arraySpec = (rows, cols, rowPitch * fabproc.dbu,
                                 colPitch * fabproc.dbu)
                # Retain the accepted options so repeated placements reuse
                # them through the options branch instead of reopening the
                # form on every click.
                self.pendingInstanceOptions = {
                    "pcellValues": instanceValuesDict,
                    "arraySpec": arraySpec,
                }
                if arraySpec is not None:
                    return self._makeLayoutMosaicGroup(
                        newInstance, arraySpec, instanceValuesDict)
        elif options is not None:
            pcellValues = options.get("pcellValues")
            if isinstance(newInstance, lshp.layoutPcell) and pcellValues:
                newInstance(*pcellValues.values())
            arraySpec = options.get("arraySpec")
            if arraySpec is not None:
                return self._makeLayoutMosaicGroup(newInstance, arraySpec,
                                                    pcellValues)
        # Keep the source/options live while addInstance mode remains active:
        # this enables repeated placement and lets F3 revise the next instance.
        # Escape clears this state when placement is finished.
        return newInstance

    def _makeLayoutMosaicGroup(self, baseInstance, arraySpec, pcellValues=None):
        """Create an ungroupable layout mosaic of independent instances."""
        rows, cols, rowPitch, colPitch = arraySpec
        members = [baseInstance]
        baseInstance.setPos(0, 0)
        for row in range(max(1, int(rows))):
            for col in range(max(1, int(cols))):
                if row == 0 and col == 0:
                    continue
                member = self.instLayout(self.layoutInstanceTuple)
                if member is None:
                    continue
                if isinstance(member, lshp.layoutPcell) and pcellValues:
                    member(*pcellValues.values())
                member.setPos(col * colPitch, row * rowPitch)
                members.append(member)
        return lshp.layoutGroup(members)

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

            # Gate child files on schema compatibility before any record or
            # pcell-class processing; unknown future versions must not
            # partially instantiate.
            viewPath = str(layoutInstanceTuple.viewItem.viewPath)
            try:
                if viewType == "layout":
                    decodedData, compatibility = sv.prepare_design_data(
                        decodedData, "layout", viewPath)
                elif viewType == "pcell":
                    decodedData, compatibility = sv.prepare_pcell_definition(
                        decodedData, viewPath)
                else:
                    compatibility = None
            except sv.DesignFileValidationError as error:
                for err in error.errors or [str(error)]:
                    self.logger.error(
                        f"Instance file '{viewPath}': {err}")
                return None
            if compatibility is not None and compatibility.migrated:
                self.logger.info(
                    f"Migrated {viewType} schema "
                    f"{compatibility.sourceVersion} to "
                    f"{compatibility.targetVersion}: {viewPath}")

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
                    isinstance(pcell_cls, type) and issubclass(pcell_cls, lshp.layoutPcell)
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
        """Replace layout instances from a selected schematic cellview."""
        from PySide6.QtWidgets import QMessageBox

        if not self.sdlMutationAllowed():
            return
        existingInstances = self.findScenelayoutCellSet()
        if existingInstances:
            reply = QMessageBox.question(
                self.editorWindow,
                "Existing Layout Instances",
                f"There are {len(existingInstances)} layout instances on the scene.\n\n"
                "Continuing will remove all existing instances and place new ones "
                "from the schematic.\n\nDo you want to proceed?",
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if reply != QMessageBox.StandardButton.Ok:
                self.logger.info("Schematic-driven layout cancelled by user")
                return
            self.deleteListUndoStack(list(existingInstances))

        try:
            with schematicTuple.viewItem.viewPath.open("rb") as schematicFile:
                data = orjson.loads(schematicFile.read())
        except (OSError, orjson.JSONDecodeError) as error:
            self.logger.error(f"Failed to load schematic: {error}")
            return

        records = [
            item for item in (data[2:] if len(data) > 2 else [])
            if isinstance(item, dict) and item.get("type") == "sys"
        ]
        if not records:
            self.logger.info("No schematic instances found to place")
            return

        createdCount = 0
        for record in records:
            layoutTuple = self._resolveLayoutView(
                record.get("lib", ""), record.get("cell", ""))
            if layoutTuple:
                if self._createLayoutInstanceFromSch(
                        layoutTuple, record, None):
                    createdCount += 1
            else:
                self.logger.warning(
                    f"No layout/pcell view for "
                    f"{record.get('lib')}/{record.get('cell')}")
        self.logger.info(
            f"Created {createdCount} layout instances from schematic")

    def updateFromSchematic(self, schematicTuple: ddef.viewItemTuple) -> dict:
        """Incrementally sync layout instances against a schematic cellview.

        The correspondence diff (``backend/correspondence.py``) decides the
        plan; this method applies it inside one undo macro:

        * ``to_add``    — schematic instances with no layout counterpart are
          placed via :meth:`_createLayoutInstanceFromSch` (layout or pcell
          view resolution as before).
        * ``to_remove`` — instances whose ``sdl`` names this schematic but
          whose source instance vanished are deleted.
        * ``to_update`` — matched instances whose stored labels drifted get
          their pcell parameters re-applied.
        * ``adopted``   — unsourced instances matching a schematic instance
          by name+cell are stamped with ``sdl`` and treated as managed.

        Returns a stats dict: ``added/removed/updated/adopted/skipped``.
        """
        if not self.sdlMutationAllowed():
            return {"added": 0, "removed": 0, "updated": 0, "adopted": 0,
                    "skipped": 0}
        sourceKey = (
            schematicTuple.libraryItem.libraryName,
            schematicTuple.cellItem.cellName,
            schematicTuple.viewItem.viewName,
        )
        schematicPath = schematicTuple.viewItem.viewPath
        try:
            with schematicPath.open("rb") as f:
                data = orjson.loads(f.read())
        except (OSError, orjson.JSONDecodeError) as e:
            self.logger.error(f"Failed to load schematic: {e}")
            return {"added": 0, "removed": 0, "updated": 0, "adopted": 0,
                    "skipped": 0}

        schInsts = corr.schematicInstances(data[2:] if len(data) > 2 else [])
        if not schInsts:
            self.logger.info("No schematic instances found to sync")
        descriptors = self._sdlDescriptors()
        plan = corr.correspondenceDiff(schInsts, descriptors, sourceKey)

        stats = {"added": 0, "removed": 0, "updated": 0, "adopted": 0,
                 "skipped": 0}
        if not (plan.to_add or plan.to_remove or plan.to_update
                or plan.adopted):
            self.logger.info("Layout already matches schematic")
        else:
            self.undoStack.beginMacro("Update from schematic")
            try:
                if plan.to_remove:
                    self.deleteListUndoStack(
                        [desc["item"] for desc in plan.to_remove])
                    stats["removed"] = len(plan.to_remove)
                for desc, record in plan.adopted:
                    item = desc["item"]
                    item._sdlSource = corr.makeSdlSource(
                        *sourceKey, record.get("nam", ""),
                        record.get("ld", {}))
                    stats["adopted"] += 1
                    if self._syncInstanceParams(item, record):
                        stats["updated"] += 1
                for desc, record in plan.to_update:
                    item = desc["item"]
                    if self._syncInstanceParams(item, record):
                        item._sdlSource = corr.makeSdlSource(
                            *sourceKey, record.get("nam", ""),
                            record.get("ld", {}))
                        stats["updated"] += 1
                for record in plan.to_add:
                    layoutTuple = self._resolveLayoutView(
                        record.get("lib", ""), record.get("cell", ""))
                    if layoutTuple and self._createLayoutInstanceFromSch(
                            layoutTuple, record, schematicTuple):
                        stats["added"] += 1
                    else:
                        stats["skipped"] += 1
                        self.logger.warning(
                            f"No layout/pcell view for "
                            f"{record.get('lib')}/{record.get('cell')}")
            finally:
                self.undoStack.endMacro()

        # Remember the source so flylines/cross-probing can rebuild without
        # re-picking the schematic, then redraw the rat's nest.
        self._flylineSource = schematicTuple
        self.rebuildFlylines(schematicTuple)
        self.logger.info(
            f"Schematic sync: +{stats['added']} -{stats['removed']} "
            f"~{stats['updated']} adopted {stats['adopted']} "
            f"skipped {stats['skipped']}")
        return stats

    def sdlMutationAllowed(self) -> bool:
        """Return whether an SDL adapter operation may mutate this scene."""
        if not self.readOnly:
            return True
        self.logger.warning("SDL mutation refused for read-only layout")
        self.messageLine.setText("Layout is read-only — SDL update was not applied")
        return False

    def layoutInstanceDescriptors(self) -> list:
        """Return opaque top-level instance descriptors for SDL adapters."""
        return [
            {
                "item": item,
                "name": item.instanceName,
                "cell": item.cellName,
                "sdl": getattr(item, "_sdlSource", None),
            }
            for item in self.topLevelLayoutInstances()
        ]

    def _sdlDescriptors(self) -> list:
        return self.layoutInstanceDescriptors()

    def applySchematicParameters(self, item, record: dict) -> bool:
        """Apply mapped schematic parameters through the core PCell path."""
        if not self.sdlMutationAllowed():
            return False
        if isinstance(item, lshp.layoutPcell):
            return self._applyPcellParams(
                item, record.get("cell", ""), record.get("ld", {}))
        return True

    def _syncInstanceParams(self, item, record: dict) -> bool:
        return self.applySchematicParameters(item, record)

    def resolveLayoutView(self, libName: str, cellName: str):
        """Resolve a cell's layout or PCell view for an SDL adapter."""
        import revedaEditor.backend.libBackEnd as libb

        libPath = self.libraryDict.get(libName)
        if not libPath:
            return None
        cellPath = libPath / cellName
        if not cellPath.exists():
            return None
        for viewName in ("layout", "pcell"):
            viewPath = cellPath / f"{viewName}.json"
            if viewPath.exists():
                return ddef.viewItemTuple(
                    libb.libraryItem(libPath), libb.cellItem(cellPath),
                    libb.viewItem(viewPath))
        return None

    def _resolveLayoutView(self, lib_name: str, cell_name: str):
        return self.resolveLayoutView(lib_name, cell_name)

    def stampSdlSource(self, item, source: dict) -> bool:
        """Apply validated canonical correspondence metadata to an item."""
        if not self.sdlMutationAllowed() or not sv.is_canonical_sdl_source(source):
            return False
        item._sdlSource = dict(source)
        return True

    def removeLayoutItemsUndo(self, items) -> bool:
        """Remove items through one core undo command when writable."""
        if not self.sdlMutationAllowed():
            return False
        itemList = list(items)
        if itemList:
            self.deleteListUndoStack(itemList)
        return True

    def _loadPcellParameterMap(self) -> dict:
        """Raw ``pcellParameterMap.json`` contents (``mappings``,
        ``pinMappings``), or ``{}`` when the PDK ships none."""
        mapPath = pathlib.Path(fabproc.__file__).parent / "pcellParameterMap.json"
        try:
            with mapPath.open("rb") as mapFile:
                return orjson.loads(mapFile.read())
        except (OSError, orjson.JSONDecodeError) as error:
            self.logger.error(f"Failed to load PCell parameter map: {error}")
            return {}

    def _getPcellParameterMap(self, cellName: str) -> dict:
        return self._loadPcellParameterMap().get(
            "mappings", {}).get(cellName, {})

    def _getPcellPinMap(self, cellName: str) -> dict:
        """Schematic-pin -> layout-pin name map declared for ``cellName``.

        PDK cells whose symbol pins are named differently from their
        layout/pcell pins (e.g. symbol ``P``/``M`` vs layout
        ``PLUS``/``MINUS``) declare the correspondence under
        ``pinMappings`` in pcellParameterMap.json. Cells with matching
        names need no entry.
        """
        return self._loadPcellParameterMap().get(
            "pinMappings", {}).get(cellName, {})

    def _layoutPinInInstance(self, inst, pinName: str,
                             pinMap: dict | None = None):
        """First descendant layoutPin of ``inst`` matching schematic pin
        ``pinName``, translated through the cell's pinMappings entry.
        ``pinMap`` lets callers reuse a fetched map across lookups."""
        if pinMap is None:
            pinMap = self._getPcellPinMap(getattr(inst, "cellName", ""))
        layPinName = pinMap.get(pinName, pinName)
        for pin in self._childLayoutPins(inst):
            if pin.pinName == layPinName:
                return pin
        return None

    def _schematicPinName(self, inst, layPinName: str) -> str:
        """Inverse of the cell's pinMappings entry (layout pin -> symbol
        pin), identity when unmapped."""
        for schName, layName in self._getPcellPinMap(
                getattr(inst, "cellName", "")).items():
            if layName == layPinName:
                return schName
        return layPinName

    def _applyPcellParams(self, inst, schCellName: str, labels: dict) -> bool:
        """Apply schematic labels to a pcell via the PDK parameter map.

        With no map the pcell keeps its current/default values. Returns
        False when required parameters have no matching label.
        """
        if not isinstance(inst, lshp.layoutPcell):
            return True
        callParameters = inspect.signature(inst.__call__).parameters
        parameterMap = self._getPcellParameterMap(schCellName)
        if not parameterMap:
            # No schematic->PCell parameter mapping: fall back to the
            # PCell's default parameter values rather than failing.
            lineEditDict = self.extractPcellInstanceParameters(inst)
            if lineEditDict:
                instanceValuesDict = {
                    key: value.text() for key, value in lineEditDict.items()
                }
                if instanceValuesDict:
                    inst(*instanceValuesDict.values())
            return True
        params, missing = corr.pcellParamsFor(
            callParameters, parameterMap, labels)
        if missing:
            self.logger.error(
                f"Missing PCell parameters for {inst.instanceName}: "
                f"{', '.join(missing)}")
            return False
        inst(**params)
        return True

    def createLayoutInstanceFromRecord(
            self, viewTuple: ddef.viewItemTuple, record: dict,
            sdlSource: dict | None = None):
        """Create one undoable layout instance through the SDL adapter."""
        if not self.sdlMutationAllowed():
            return None
        # Store current tuple and set the new one
        oldTuple = self.layoutInstanceTuple
        self.layoutInstanceTuple = viewTuple
        try:
            newInst = self.instLayout(viewTuple)
            if newInst is None:
                return None
            if not self.applySchematicParameters(newInst, record):
                return None
            # Inherit properties from schematic
            newInst.instanceName = record.get("nam", "")
            newInst.counter = record.get("ic", 0)
            newInst.angle = record.get("ang", 0)
            newInst.flipTuple = tuple(record.get("fl", (1, 1)))
            # Convert the schematic grid location to layout scene coordinates.
            loc = record.get("loc", (0, 0))
            if isinstance(loc, (list, tuple)) and len(loc) >= 2:
                newInst.setPos(loc[0] * 10, loc[1] * 10)
            # Persisted correspondence stamp (see backend/correspondence).
            if sdlSource is not None and not self.stampSdlSource(
                    newInst, sdlSource):
                return None
            # Add to scene via undo stack
            self.addUndoStack(newInst)
            return newInst
        except Exception as error:
            self.logger.error(
                f"Error creating layout instance from schematic: {error}")
            return None
        finally:
            # Restore original tuple
            self.layoutInstanceTuple = oldTuple

    def _createLayoutInstanceFromSch(
            self, viewTuple: ddef.viewItemTuple, record: dict,
            schematicTuple: ddef.viewItemTuple | None) -> bool:
        """Compatibility wrapper around the versioned SDL adapter."""
        source = None
        if schematicTuple is not None:
            source = corr.makeSdlSource(
                schematicTuple.libraryItem.libraryName,
                schematicTuple.cellItem.cellName,
                schematicTuple.viewItem.viewName,
                record.get("nam", ""), record.get("ld", {}))
        return self.createLayoutInstanceFromRecord(
            viewTuple, record, source) is not None

    def saveLayoutCell(self, filePathObj: pathlib.Path,
                       markClean: bool = True) -> None:
        """Save the layout cell to a JSON file.

        Args:
            filePathObj (pathlib.Path): Path object for the output file
            markClean (bool): Clear the undo stack after a real save; autosave
                passes False so the undo history is preserved.

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
                sv.make_view_header("layout"),
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
            if markClean:
                self.undoStack.clear()
            lj.PCellCache.clear_caches()
            lj.layoutItems.clear_caches()

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
            self, export_dir: pathlib.Path, unit: float, precision: float, dbu: int,
            format_type: str = "GDS", layerMap: dict | None = None,
            cellNameMap: dict | None = None, flattenDepth: int | None = None,
    ):
        """Export cell in the specified format (GDS or OAS)."""
        # layerMap: {(gdsLayer, datatype): (gdsLayer, datatype)}; cellNameMap:
        # {lib_cell_view or cellName: exported name}; flattenDepth: None keeps
        # full hierarchy, N keeps refs only for instances at depth <= N.
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
            exportObj.layerMap = layerMap
            exportObj.cellNameMap = cellNameMap
            exportObj.flattenDepth = flattenDepth

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
            self, gdsExportDir: pathlib.Path, gdsUnit: float, gdsPrecision: float,
            dbu: int, layerMap: dict | None = None,
            cellNameMap: dict | None = None, flattenDepth: int | None = None,
    ):
        """Export cell as GDS format."""
        self._exportCell(gdsExportDir, gdsUnit, gdsPrecision, dbu, "GDS",
                         layerMap, cellNameMap, flattenDepth)

    def exportCellOAS(
            self, oasExportDir: pathlib.Path, gdsUnit: float, gdsPrecision: float,
            dbu: int, layerMap: dict | None = None,
            cellNameMap: dict | None = None, flattenDepth: int | None = None,
    ):
        """Export cell as OAS format."""
        self._exportCell(oasExportDir, gdsUnit, gdsPrecision, dbu, "OAS",
                         layerMap, cellNameMap, flattenDepth)

    def loadDesign(self, filePathObj: pathlib.Path) -> bool:
        """Load the layout cell from the given JSON file."""
        try:
            with filePathObj.open("rb") as file:
                decodedData = orjson.loads(file.read())
            try:
                decodedData, compatibility = sv.prepare_design_data(
                    decodedData, "layout", str(filePathObj))
            except sv.DesignFileValidationError as error:
                for err in error.errors or [str(error)]:
                    self.logger.error(
                        f"Layout compatibility error in "
                        f"'{filePathObj.name}': {err}")
                return False
            if compatibility.migrated:
                self.logger.info(
                    f"Migrated layout schema {compatibility.sourceVersion} "
                    f"to {compatibility.targetVersion}")
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
                    # Semantic connectivity check on the decoded records via
                    # the shared layout engine (same path RCX uses).
                    try:
                        _groups, _names, diagnostics = \
                            conn.checkLayoutRecords(
                                decodedData[2:], laylyr, fabproc)
                        for diag in diagnostics:
                            if diag.severity == "error":
                                self.logger.error(diag.message)
                            else:
                                self.logger.warning(diag.message)
                    except Exception as e:
                        self.logger.warning(
                            f"Layout connectivity check skipped: {e}")
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
        signalsWereBlocked = self.signalsBlocked()
        beginBulkLoad = getattr(self, "_beginBulkLoad", None)
        endBulkLoad = getattr(self, "_endBulkLoad", None)
        self.setItemIndexMethod(QGraphicsScene.ItemIndexMethod.NoIndex)
        # Qt's changed signal and the layoutScene addItem override both fire
        # per insertion. Keep them quiet until every record has been added.
        self.blockSignals(True)
        if callable(beginBulkLoad):
            beginBulkLoad()
        # Register items into itemsRefSet incrementally as they are created,
        # avoiding a sorted self.items() scan over the whole scene afterwards.
        refSet = getattr(self, "itemsRefSet", None)
        refAdd = refSet.add if refSet is not None else None
        addItem = self.addItem
        try:
            for item in decoded_data:
                if isinstance(item, dict):
                    try:
                        shape = factory_create(item)
                        if shape is not None:
                            addItem(shape)
                            if refAdd is not None:
                                refAdd(shape)
                                stack = shape.childItems()
                                while stack:
                                    child = stack.pop()
                                    refAdd(child)
                                    stack.extend(child.childItems())
                    except Exception as e:
                        self.logger.error(
                            f"Layout record skipped on load: {e}")
        finally:
            self.setItemIndexMethod(index_method)
            if hasattr(self, "_applyObjectFilters"):
                self._applyObjectFilters()
            if callable(endBulkLoad):
                endBulkLoad(discardQueuedChanged=not signalsWereBlocked)
            self.blockSignals(signalsWereBlocked)

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
                        case _:
                            if isinstance(item, lshp.layoutPcell):
                                self.layoutInstanceProperties(item, True)
                            elif isinstance(item, lshp.layoutMultipart):
                                self.layoutMultipartProperties(item)

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

    def layoutMultipartProperties(self, item):
        dlg = ldlg.multipartPropertiesDialogue(self.editorWindow, item)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        newItem = type(item)(dlg.parsedParams())
        newItem.setPos(item.pos())
        newItem.angle = item.angle
        newItem.flipTuple = item.flipTuple
        self.undoStack.push(us.addDeleteShapeUndo(self, newItem, item))

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

        # Mosaic fields (pitches are scene dbu; the dialog works in um).
        dlg.arrayGroup.show()
        dlg.rowsEdit.setText(str(item.rows))
        dlg.colsEdit.setText(str(item.cols))
        dlg.rowPitchEdit.setText(str(item.rowPitch / fabproc.dbu))
        dlg.colPitchEdit.setText(str(item.colPitch / fabproc.dbu))

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
            arraySpec = dlg.arraySpec()
            if arraySpec is not None:
                rows, cols, rowPitch, colPitch = arraySpec
                newLayoutInstance.setArray(
                    rows, cols,
                    rowPitch * fabproc.dbu, colPitch * fabproc.dbu,
                )
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
        # A deferred pcell keeps its real params in the pending loader; the
        # ctor-param attributes still hold defaults until realisation.
        pending = getattr(instance, "deferredParams", None)
        if pending is not None:
            argDict = {
                arg: pending[arg] if arg in pending else getattr(instance, arg)
                for arg in argsUsed
            }
        else:
            argDict = {arg: getattr(instance, arg) for arg in argsUsed}
        # Numeric attrs hold raw SI values (e.g. 2e-06 metres); render them
        # so the dialogue shows "2u".  The text round-trips through
        # Quantity() unchanged when the pcell is rebuilt on accept.
        lineEditDict = {}
        for key, value in argDict.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                try:
                    value = Quantity(value).render(prec=3)
                except (ValueError, TypeError):
                    value = str(value)
            lineEditDict[key] = edf.shortLineEdit(value)
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

    def _fixClipboardShapes(self, shapes: list) -> None:
        """Allocate fresh instance names for pasted layout instances,
        including instances nested inside groups."""
        stack = list(shapes)
        while stack:
            shape = stack.pop()
            if isinstance(shape, lshp.layoutGroup):
                stack.extend(shape.shapes)
            elif isinstance(shape, (lshp.layoutInstance, lshp.layoutPcell)):
                self.itemCounter += 1
                shape.instanceName = f"I{self.itemCounter}"
                shape.counter = int(self.itemCounter)

    def deleteAllRulers(self):
        # A ruler is added on its first click and finalized on the second. Do
        # not keep a reference to it after the bulk-delete command removes it.
        self._newRuler = None
        sceneRulerSet = {
            item for item in self.items() if isinstance(item, lshp.layoutRuler)
        }
        if sceneRulerSet:
            self.deleteListUndoStack(list(sceneRulerSet))

    def deleteSelectedRulers(self):
        """Delete only the rulers in the current selection (Shift+K still
        clears all). Returns True when at least one ruler was removed."""
        selectedRulers = [
            item
            for item in self.selectedItems()
            if isinstance(item, lshp.layoutRuler)
        ]
        # A live move/copy selection group hides its members from
        # selectedItems(); check group children as well.
        if self.selectedItemGroup is not None:
            selectedRulers.extend(
                item
                for item in self.selectedItemGroup.childItems()
                if isinstance(item, lshp.layoutRuler)
            )
        if not selectedRulers:
            return False
        self.deleteListUndoStack(selectedRulers)
        return True

    def topLevelLayoutInstances(self) -> list:
        """Return top-level layout/PCell instances for plugin adapters."""
        return [item for item in self.items()
                if item.parentItem() is None
                and isinstance(item, lshp.layoutInstance)]

    def topLevelLayoutPins(self) -> list:
        """Return top-level layout pins for plugin adapters."""
        return [item for item in self.items()
                if item.parentItem() is None
                and isinstance(item, lshp.layoutPin)]

    def descendantLayoutPins(self, container) -> list:
        """Return nested and array-aware pins below a layout container."""
        return self._childLayoutPins(container)

    def pcellPinMap(self, cellName: str) -> dict:
        """Return the PDK schematic-pin to layout-pin mapping for a cell."""
        return self._getPcellPinMap(cellName)

    def layoutPinInInstance(self, instance, pinName: str, pinMap=None):
        """Resolve a schematic pin name to a descendant layout pin."""
        return self._layoutPinInInstance(instance, pinName, pinMap)

    def connectivityGroupForItem(self, item):
        """Return the current connectivity group containing an item."""
        _ = self.connectivity
        return self._connectivityItemGroup.get(item)

    def _fitBoundsRect(self) -> QRectF:
        """Fit bounds that exclude rulers' zoom-dependent label margin.

        layoutRuler.boundingRect() pads itself by a margin proportional
        to 1/view-zoom (its tick labels render at a fixed screen size),
        so feeding itemsBoundingRect() into fitInView() would zoom out
        further on every press. Rulers contribute their stable shape()
        bound instead.
        """
        fitRect = QRectF()
        for item in self.items():
            if isinstance(item, lshp.layoutRuler):
                fitRect = fitRect.united(
                    item.mapToScene(item.shape().boundingRect()).boundingRect())
            else:
                fitRect = fitRect.united(item.sceneBoundingRect())
        return fitRect

    def addOverlayItem(self, item) -> None:
        """Add a visual overlay without invalidating design connectivity."""
        super().addItem(item)

    def removeOverlayItem(self, item) -> None:
        """Remove a visual overlay without invalidating design connectivity."""
        if shiboken6.isValid(item) and item.scene() is self:
            super().removeItem(item)

    # --- Layout connectivity (revedaEditor.connectivity.layout engine) ---

    def _beginBulkLoad(self):
        self._bulkLoadDepth += 1

    def _endBulkLoad(self, discardQueuedChanged: bool = False):
        self._bulkLoadDepth -= 1
        if self._bulkLoadDepth:
            return
        if self._connectivityDirtyDuringBulkLoad:
            self._connectivityDirtyDuringBulkLoad = False
            self._connectivityCache = None
            self._discardQueuedBulkChange = discardQueuedChanged
            self._updateFlylineGeometry()
            self.connectivityInvalidated.emit()

    def markConnectivityDirty(self, *args):
        """Invalidate cached connectivity after a scene change."""
        if args and self._discardQueuedBulkChange:
            # QGraphicsScene posts one changed signal after its signals are
            # unblocked. The bulk completion above already invalidated the
            # cache and refreshed overlays for that exact batch.
            self._discardQueuedBulkChange = False
            return
        if self._bulkLoadDepth:
            self._connectivityDirtyDuringBulkLoad = True
            return
        self._connectivityCache = None
        self._updateFlylineGeometry()
        self.connectivityInvalidated.emit()

    def addItem(self, item):
        super().addItem(item)
        self.markConnectivityDirty()

    def removeItem(self, item):
        super().removeItem(item)
        self.markConnectivityDirty()
        # Drop the highlight overlay if a highlighted member was removed.
        overlay = self._netHighlightItems.pop(item, None)
        if overlay is not None and shiboken6.isValid(overlay) \
                and overlay.scene() is self:
            super().removeItem(overlay)

    def rebuildConnectivity(self):
        """Rebuild layout net groups from current scene contents.

        Uses the same connectivity.layout engine as RCX's record-level path.
        Top-level shapes, pins, labels, and vias participate, and instance/
        Pcell/multipart internals are expanded into the groups (the adapter
        resolves children in scene coordinates) so highlight-net reaches
        metal inside instances such as substrate taps. Internal items carry
        no name anchors — nets are still named by top-level pins/labels.
        """
        topLevelItems = [item for item in self.items()
                         if item.parentItem() is None]
        groups, _names, conflicts, _s, _v, _a = conn.analyzeLayoutItems(
            topLevelItems, touchTolerance=1.0)
        self._connectivityCache = groups
        self._connectivityItemGroup = {}
        for group in groups:
            for shape in group.shapes:
                if shape.item is not None:
                    self._connectivityItemGroup[shape.item] = group
            for via in group.vias:
                if via.item is not None:
                    self._connectivityItemGroup[via.item] = group
        for conflict in conflicts:
            self.logger.error(conflict)
        # Drop highlight overlays whose member left every net (deleted
        # shapes, realized/unrealized instance children, etc.).
        kept = {}
        for item, overlay in self._netHighlightItems.items():
            if (shiboken6.isValid(item)
                    and item in self._connectivityItemGroup):
                kept[item] = overlay
                continue
            if shiboken6.isValid(overlay) and overlay.scene() is self:
                super().removeItem(overlay)
        self._netHighlightItems = kept
        # Islands may have merged/split — re-evaluate flyline topology
        # against the fresh map.
        self._syncFlylines()
        self.connectivityRebuilt.emit()
        return groups

    @property
    def connectivity(self):
        """Cached list of connectivity.layout NetGroups, rebuilt on change."""
        if self._connectivityCache is None:
            self.rebuildConnectivity()
        return self._connectivityCache

    def _layoutGroupAtPoint(self, x: float, y: float, tol: float = 1.0):
        """First net group whose shape/via footprint contains (x, y)."""
        for group in self.connectivity:
            if any(s.footprint.contains_point(x, y, tol)
                   for s in group.shapes) or \
               any(v.footprint.contains_point(x, y, tol)
                   for v in group.vias):
                return group
        return None

    def highlightNetAtPoint(self, point) -> str | None:
        """Highlight every member of the net under ``point`` (scene coords).

        Clicked labels resolve through their anchor position. Highlights are
        additive until clearNetHighlights(). Returns the net name, or None
        when no net was found.
        """
        _ = self.connectivity  # ensure the item->group map is fresh
        target = None
        for item in self.items(point):
            target = self._connectivityItemGroup.get(item)
            if target is not None:
                break
            if isinstance(item, lshp.layoutLabel):
                anchor = item.mapToScene(item.start)
                target = self._layoutGroupAtPoint(anchor.x(), anchor.y())
                if target is not None:
                    break
        if target is None:
            target = self._layoutGroupAtPoint(point.x(), point.y())
        if target is None:
            self.messageLine.setText("No net found at this point")
            return None
        for shape in target.shapes:
            self._addNetHighlightRect(shape.item)
        for via in target.vias:
            self._addNetHighlightRect(via.item)
        self.messageLine.setText(f"Highlighted net: {target.name}")
        return target.name

    def _addNetHighlightRect(self, item) -> None:
        if item is None or not shiboken6.isValid(item):
            return
        if item in self._netHighlightItems:
            return
        color = getattr(getattr(item, "layer", None), "pcolor", None)
        pen = QPen(color if isinstance(color, QColor)
                   else QColor(255, 255, 0))
        pen.setWidth(3)
        pen.setCosmetic(True)
        pen.setStyle(Qt.PenStyle.DashLine)
        highlight = QGraphicsRectItem(item.sceneBoundingRect())
        highlight.setPen(pen)
        highlight.setZValue(1e9)
        highlight.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        highlight.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,
                          False)
        self.addOverlayItem(highlight)
        self._netHighlightItems[item] = highlight

    def clearNetHighlights(self) -> None:
        """Remove all net-highlight overlay rectangles."""
        for highlight in self._netHighlightItems.values():
            if shiboken6.isValid(highlight) and highlight.scene() is self:
                self.removeOverlayItem(highlight)
        self._netHighlightItems = {}

    def _clearFlylineItems(self) -> None:
        """Remove drawn flyline items; cached endpoint pins survive."""
        for flyline in self._flylines:
            if shiboken6.isValid(flyline) and flyline.scene() is self:
                # Bypass the overridden removeItem — flylines are pure
                # overlay and must not dirty connectivity.
                self.removeOverlayItem(flyline)
        self._flylines = []

    def clearFlylines(self) -> None:
        """Remove all drawn flylines and forget their endpoints."""
        self._clearFlylineItems()
        self._flylinePins = {}

    def _inferFlylineSource(self):
        """Locate the schematic cellview named by an SDL-stamped instance."""
        import revedaEditor.backend.libBackEnd as libb

        for item in self.items():
            if item.parentItem() is not None or \
                    not isinstance(item, lshp.layoutInstance):
                continue
            key = corr.sdlSourceKey(getattr(item, "_sdlSource", None))
            if not key:
                continue
            lib, cell, view = key
            libPath = self.libraryDict.get(lib)
            if libPath is None:
                continue
            viewPath = libPath / cell / f"{view or 'schematic'}.json"
            if not viewPath.exists():
                continue
            return ddef.viewItemTuple(
                libb.libraryItem(libPath),
                libb.cellItem(libPath / cell),
                libb.viewItem(viewPath))
        return None

    @staticmethod
    def _childLayoutPins(container) -> list:
        """All descendant layoutPin items (nested instances, arrays)."""
        pins, stack, seen = [], [], set()
        stack += list(getattr(container, "shapes", []) or [])
        stack += list(getattr(container, "arrayShapes", []) or [])
        while stack:
            child = stack.pop()
            if id(child) in seen or not shiboken6.isValid(child):
                continue
            seen.add(id(child))
            if isinstance(child, lshp.layoutPin):
                pins.append(child)
            stack += list(getattr(child, "shapes", []) or [])
            stack += list(getattr(child, "arrayShapes", []) or [])
        return pins

    def rebuildFlylines(self, schematicTuple=None) -> int:
        """Redraw the schematic->layout rat's nest.

        Schematic pin->net endpoints (``corr.flylineEndpoints``) are mapped
        onto layout pin positions; a flyline is drawn between connectivity
        islands the schematic joins but the layout has not merged, so routed
        segments produce no line. Returns the number of flylines drawn.
        """
        self.clearFlylines()
        if schematicTuple is None:
            schematicTuple = self._flylineSource \
                or self._inferFlylineSource()
        if schematicTuple is None:
            return 0
        self._flylineSource = schematicTuple
        try:
            with schematicTuple.viewItem.viewPath.open("rb") as f:
                data = orjson.loads(f.read())
        except (OSError, orjson.JSONDecodeError) as e:
            self.logger.error(f"Failed to load schematic for flylines: {e}")
            return 0
        pinLocator = lj.makeSymbolPinLocator(self.libraryDict)
        endpoints, _diags = corr.flylineEndpoints(
            data[2:] if len(data) > 2 else [], pinLocator)

        sdlInsts, namedInsts, topPins = {}, {}, {}
        for item in self.items():
            if item.parentItem() is not None:
                continue
            if isinstance(item, lshp.layoutInstance):
                sdlName = corr.sdlInstName(
                    getattr(item, "_sdlSource", None))
                if sdlName:
                    sdlInsts.setdefault(sdlName, item)
                if item.instanceName:
                    namedInsts.setdefault(item.instanceName, item)
            elif isinstance(item, lshp.layoutPin):
                topPins.setdefault(item.pinName, item)

        pinMaps = {}  # cellName -> pinMappings entry, fetched once per cell

        def resolveEndpoint(endpoint):
            instName, pinName = endpoint
            if not instName:
                pin = topPins.get(pinName)
                return (pin.sceneBoundingRect().center(), pin) \
                    if pin else None
            inst = sdlInsts.get(instName) or namedInsts.get(instName)
            if inst is None:
                return None
            cellName = getattr(inst, "cellName", "")
            if cellName not in pinMaps:
                pinMaps[cellName] = self._getPcellPinMap(cellName)
            pin = self._layoutPinInInstance(inst, pinName,
                                            pinMaps[cellName])
            return (pin.sceneBoundingRect().center(), pin) \
                if pin is not None else None

        _ = self.connectivity  # ensure the item->group map is fresh
        self._flylinePins = {}
        drawn = 0
        for netName, eps in endpoints.items():
            pins = [r[1] for r in
                    (resolveEndpoint(e) for e in eps) if r]
            if len(pins) < 2:
                continue
            # Cache endpoint items so _syncFlylines re-resolves islands
            # after moves without re-reading the schematic.
            self._flylinePins[netName] = pins
            drawn += self._drawFlylineIslands(netName, pins)
        if drawn:
            self.messageLine.setText(
                f"Flylines: {drawn} unrouted connection(s)")
        return drawn

    def _drawFlylineIslands(self, netName: str, pins: list) -> int:
        """Draw flylines between connectivity islands of ``pins``.

        Pins already merged into one layout net group collapse to a single
        island representative; each remaining island gets a line to the
        first. Returns the number of lines drawn.
        """
        _ = self.connectivity  # ensure the item->group map is fresh
        islands, ungrouped = {}, []
        for pin in pins:
            group = self._connectivityItemGroup.get(pin)
            if group is None:
                ungrouped.append(pin)
            else:
                islands.setdefault(id(group), pin)
        reps = list(islands.values()) + ungrouped
        if len(reps) < 2:
            return 0
        anchorPin = reps[0]
        anchor = anchorPin.sceneBoundingRect().center()
        drawn = 0
        for pin in reps[1:]:
            flyline = lshp.layoutFlightLine(
                QLineF(anchor, pin.sceneBoundingRect().center()),
                netName, anchorPin, pin)
            # Flylines are visual overlays; bypass the scene override so
            # rebuilding their topology cannot invalidate the just-built
            # design connectivity cache.
            self.addOverlayItem(flyline)
            self._flylines.append(flyline)
            drawn += 1
        return drawn

    def _onUndoIndexChanged(self, *_):
        """Refresh flyline topology after undo/redo positional changes."""
        if self._flylinePins:
            _ = self.connectivity  # rebuild -> _syncFlylines

    def _updateFlylineGeometry(self):
        """Re-anchor drawn flylines to current pin positions.

        Called from markConnectivityDirty on every scene change — cheap
        (no connectivity work), so lines track instance moves live.
        Flylines whose endpoint pins left the scene are dropped.
        """
        if self._syncingFlylines or not self._flylines:
            return
        self._syncingFlylines = True
        try:
            alive = []
            for flyline in self._flylines:
                if not shiboken6.isValid(flyline):
                    continue
                if flyline.scene() is not self or not flyline.syncLine():
                    self.removeOverlayItem(flyline)
                    continue
                alive.append(flyline)
            self._flylines = alive
        finally:
            self._syncingFlylines = False

    def _syncFlylines(self):
        """Recompute flyline islands from cached endpoint pins.

        Runs at the end of rebuildConnectivity — pins re-resolve against
        the fresh item->group map, so islands that merged (routing
        completed) drop their line and newly-split islands gain one. No
        file I/O: endpoints were resolved once by rebuildFlylines.
        """
        if self._syncingFlylines or not self._flylinePins:
            return
        self._syncingFlylines = True
        try:
            self._clearFlylineItems()
            drawn = 0
            for netName, pins in self._flylinePins.items():
                pins = [p for p in pins if shiboken6.isValid(p)
                        and p.scene() is self]
                if len(pins) < 2:
                    continue
                drawn += self._drawFlylineIslands(netName, pins)
            if drawn:
                self.messageLine.setText(
                    f"Flylines: {drawn} unrouted connection(s)")
        finally:
            self._syncingFlylines = False

    # ------------------------------------------------------------------
    # Schematic<->layout cross-probing
    # ------------------------------------------------------------------

    def _sdlSourceKeyForScene(self):
        """(lib, cell, view) of the schematic this layout was synced from."""
        if self._flylineSource is not None:
            t = self._flylineSource
            return (t.libraryItem.libraryName, t.cellItem.cellName,
                    t.viewItem.viewName)
        for item in self.items():
            if item.parentItem() is None and \
                    isinstance(item, lshp.layoutInstance):
                key = corr.sdlSourceKey(
                    getattr(item, "_sdlSource", None))
                if key:
                    return key
        return None

    def _layoutPinForEndpoint(self, instName: str, pinName: str):
        """Scene layoutPin matching an (instName, pinName) endpoint."""
        if not instName:
            for item in self.items():
                if item.parentItem() is None and \
                        isinstance(item, lshp.layoutPin) and \
                        item.pinName == pinName:
                    return item
            return None
        for item in self.items():
            if item.parentItem() is not None or \
                    not isinstance(item, lshp.layoutInstance):
                continue
            if corr.sdlInstName(getattr(item, "_sdlSource", None)) \
                    == instName or item.instanceName == instName:
                pin = self._layoutPinInInstance(item, pinName)
                if pin is not None:
                    return pin
        return None

    def _endpointsForGroup(self, group) -> list:
        """(instName, pinName) endpoints for member pins of a net group."""
        endpoints = []
        for shape in group.shapes:
            item = shape.item
            if item is None or not isinstance(item, lshp.layoutPin):
                continue
            ancestor = item.parentItem()
            while ancestor is not None and \
                    not isinstance(ancestor, lshp.layoutInstance):
                ancestor = ancestor.parentItem()
            if ancestor is None:
                endpoints.append(("", item.pinName))
            else:
                sdlName = corr.sdlInstName(
                    getattr(ancestor, "_sdlSource", None))
                endpoints.append(
                    (sdlName or ancestor.instanceName,
                     self._schematicPinName(ancestor, item.pinName)))
        return endpoints

    def probeTargets(self):
        """Return selected instance names and layout net endpoints."""
        _ = self.connectivity  # ensure the item->group map is fresh
        instances, netEndpoints = [], []
        for item in self.selectedItems():
            if isinstance(item, lshp.layoutInstance) and \
                    item.parentItem() is None:
                instances.append(
                    corr.sdlInstName(getattr(item, "_sdlSource", None))
                    or item.instanceName)
                continue
            group = self._connectivityItemGroup.get(item)
            if group is not None:
                netEndpoints.extend(self._endpointsForGroup(group))
        return instances, netEndpoints

    def _probeTargets(self):
        return self.probeTargets()

    def probeSchematic(self) -> None:
        """Cross-probe selected instances/nets into the source schematic."""
        key = self._sdlSourceKeyForScene()
        if key is None:
            self.messageLine.setText(
                "No schematic source — run Update from Schematic")
            return
        appMainW = getattr(self.editorWindow, "appMainW", None)
        editor = (appMainW.openViews.get(ddef.viewNameTuple(*key))
                  if appMainW is not None else None)
        if editor is None:
            self.messageLine.setText(
                f"Open {key[0]}/{key[1]}/{key[2]} to probe")
            return
        instances, netEndpoints = self.probeTargets()
        if not instances and not netEndpoints:
            self.messageLine.setText(
                "Select instances or net members to probe")
            return
        count = editor.centralW.scene.selectProbeTargets(
            instances=instances, netEndpoints=netEndpoints)
        self.messageLine.setText(f"Probed {count} item(s) in schematic")
        editor.raise_()
        editor.activateWindow()

    def selectProbeTargets(self, instances=(), netEndpoints=()) -> int:
        """Select instances by name; highlight groups for endpoints.

        ``instances`` are schematic instance names (matched against sdl
        source names and layout instanceName); ``netEndpoints`` are
        (instName, pinName) pairs resolved through layout connectivity.
        """
        wanted = set(instances)
        count = 0
        if wanted:
            self.clearSelection()
            for item in self.items():
                if item.parentItem() is not None or \
                        not isinstance(item, lshp.layoutInstance):
                    continue
                if item.instanceName in wanted or \
                        corr.sdlInstName(
                            getattr(item, "_sdlSource", None)) in wanted:
                    item.setSelected(True)
                    count += 1
            if count and self.views():
                rect = self.selectedItems()[0].sceneBoundingRect()
                for it in self.selectedItems()[1:]:
                    rect = rect.united(it.sceneBoundingRect())
                self.views()[0].fitInView(
                    rect.adjusted(-200, -200, 200, 200),
                    Qt.KeepAspectRatio)
        count += self.highlightNetGroupsForEndpoints(netEndpoints)
        return count

    def highlightNetGroupsForEndpoints(self, endpoints) -> int:
        """Highlight net groups containing any resolved endpoint pin."""
        _ = self.connectivity  # ensure the item->group map is fresh
        seen, count = set(), 0
        for instName, pinName in endpoints:
            pin = self._layoutPinForEndpoint(instName, pinName)
            if pin is None:
                continue
            group = self._connectivityItemGroup.get(pin)
            if group is None or id(group) in seen:
                continue
            seen.add(id(group))
            for shape in group.shapes:
                self._addNetHighlightRect(shape.item)
            for via in group.vias:
                self._addNetHighlightRect(via.item)
            count += 1
        return count

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
