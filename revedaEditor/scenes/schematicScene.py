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


import json
import os
import pathlib
from dataclasses import dataclass
from typing import AbstractSet, Any, Dict, List, Optional, Set, Tuple, Union, \
    cast

import orjson
import shiboken6
from PySide6.QtCore import (
    QLineF,
    QPoint,
    QPointF,
    QRect,
    QRectF,
    QRegularExpression,
    QTimer,
    Qt,
    Signal,
    Slot,
)
from PySide6.QtGui import (
    QFont,
    QFontDatabase,
    QPen,
    QTransform,
)
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QGraphicsItem,
    QGraphicsItemGroup,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSceneMouseEvent,
)

import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.backend.editFunctions as edf
import revedaEditor.backend.libBackEnd as libb
import revedaEditor.backend.libraryMethods as libm
import revedaEditor.backend.undoStack as us
import revedaEditor.checks.schematic as schk
import revedaEditor.common.labels as lbl
import revedaEditor.connectivity as conn
import revedaEditor.common.net as snet
import revedaEditor.common.params as prm
import revedaEditor.common.shapes as shp  # import the shapes
import revedaEditor.fileio.loadJSON as lj
import revedaEditor.fileio.schematicEncoder as schenc
import revedaEditor.fileio.schemaValidation as sv
import revedaEditor.gui.alignItems as alg
import revedaEditor.gui.fileDialogues as fd
import revedaEditor.gui.propertyDialogues as pdlg
from revedaEditor.backend.pdkLoader import lazyPDKModule
from revedaEditor.common.fileCache import FileCache
from revedaEditor.scenes.editorScene import editorScene

schlyr = lazyPDKModule('schLayers')


@dataclass
class findHit:
    """One find/replace result.

    ``items`` are the scene items to select/zoom (every member wire for a
    net hit); ``rect`` is the union bounding box in scene coordinates."""
    kind: str           # "instance" | "net" | "pin"
    name: str           # matched name
    detail: str         # extra display info (cell ref, direction, ...)
    items: tuple        # member scene items
    rect: QRectF        # union scene bounding rect


class schematicScene(editorScene):
    wireEditFinished = Signal(snet.schematicNet)
    alignLineFinished = Signal(shp.alignLine)
    stretchNet = Signal(snet.schematicNet, str)
    SCHEMATIC_SHAPES = (snet.schematicNet, shp.schematicPin, shp.text,
                        shp.schematicSymbol, shp.schematicGroup)
    # Clipboard contract for editorScene.copySelectionToClipboard et al.
    _CLIPBOARD_ENCODER = schenc.schematicEncoder
    _CLIPBOARD_FACTORY = lj.schematicItems
    _CLIPBOARD_TYPES = frozenset({"sys", "scn", "scp", "txt", "Group"})
    _CLIPBOARD_SHAPES = SCHEMATIC_SHAPES

    def __init__(self, parent):
        super().__init__(parent)

        # Initialize counters
        self.instCounter = 0
        self.instanceCounter = 0
        self.netCounter = 0

        # Unified connectivity cache (revedaEditor.connectivity engine).
        # Rebuilt by rebuildConnectivity(); invalidated on any scene change.
        self._connectivityCache = None
        self._connectivitySegIdByItem = {}
        self._connectivityPortIdByItem = {}
        self.changed.connect(self.markConnectivityDirty)

        # Initialize modes with default values
        self.editModes = ddef.schematicModes(selectItem=True, deleteItem=False,
                                             moveItem=False, constrainedMoveItem=False,
                                             copyItem=False,
                                             rotateItem=False, changeOrigin=False,
                                             panView=False, zoomView=False, drawPin=False,
                                             drawWire=False, drawBus=False,
                                             drawText=False, addInstance=False,
                                             stretchItem=False, nameNet=False,
                                             alignItems=False)
        # Merge with parent's messages
        self.messages.update({
            'drawPin': 'Draw Pin', 'drawWire': 'Draw Wire', 'drawBus': 'Draw Bus',
            'drawText': 'Draw Text', 'addInstance': 'Add Instance',
            'nameNet': 'Name Net', 'drawSymbol': 'Draw Symbol',
        })

        self.selectModes = ddef.schematicSelectModes(selectAll=True,
                                                     selectDevice=False,
                                                     selectNet=False,
                                                     selectPin=False,
                                                     selectText=False)

        # Initialize selection trackers
        self.selectedNet = None
        self.selectedPin = None
        self.selectedSymbol = None
        self.selectedSymbolPin = None

        # Initialize pin defaults
        self.pinName = ""
        self.pinType = "Signal"
        self.pinDir = "Input"
        self.pinExpr = ""
        # When True, resolved (inherited/auto) net names are drawn on wires
        # alongside SET names — toggled via the editor's Show Resolved Names.
        self.showResolvedNames = False

        # Initialize internal state trackers
        self._newNet = None
        self._stretchNet = None
        self._newInstance = None
        self._newPin = None
        self._newText = None
        self._newNetNameObj = None
        self.textTuple = None
        self.netNameString = None
        self.newInstanceTuple: Optional[ddef.viewNameTuple] = None
        # Parameter values captured by the place-with-params form
        # (createInstClick); applied to each placed instance's labels.
        self.pendingInstanceParams = None
        # Rows, columns, X pitch, Y pitch for the next schematic placement;
        # a mosaic expands to independent ordinary schematic instances.
        self.pendingInstanceArraySpec = None
        self.newAlignLine = None
        self._snapPointRect = self.defineSnapRect()
        self._moveMacroActive = False

        # Wire drawing state
        self._wireDrawMode = snet.NetMode.ORTHOGONAL
        self._wireAutoRoute = True
        self._routeHorizontalFirst: Optional[bool] = None
        self._routeGhost: Optional[snet.guideLine] = None
        self._wireChainActive = False
        self._wireCommands = []
        self._wireResumePoints = []
        self._wireCommandIndices = []
        self._wireWidth = 0
        self._suppressWireRestart = False
        # Bus ripper state: member name carried by the in-progress wire
        # chain, and a one-shot index override (tests/scripts skip the
        # member-index prompt by setting _busRipIndex first).
        self._wirePendingName = ""
        self._busRipIndex = None

        # Stretch state
        self._stretchBody: Optional[Dict[str, Any]] = None
        self._stretchOriginalNet = None

        # Net name auto-increment state
        self._netNameAuto = None

        # error shapes
        self.overlapRectSet = set()
        self.lastCheckViolations = []

        # Initialize view properties
        self.highlightNets = False
        self.hierarchyTrail = ""
        self.parentEditor = None
        self.parentObj = None
        # Edit-in-place ghost groups: {schematicSymbol: QGraphicsItemGroup}
        self._eipGroups = {}

        # Probe state
        self.probeMode = False
        self.removeProbeMode_ = False
        self.probePinNames: Set[str] = set()
        self._probedNets: Dict[str, Set[snet.schematicNet]] = dict()
        self._probeColorIndex: int = 0
        self._probeColorMap: Dict[str, int] = dict()

        # Font initialization
        self._initializeFont()

        # Connect signals
        self.wireEditFinished.connect(self._handleWireFinished)
        self.stretchNet.connect(self._handleStretchNet)
        self.alignLineFinished.connect(alg.alignToLine)

        # Initialize cache
        self._symbolCache = FileCache()

        # Connect to main window's symbol changed signal
        if self.appMainW:
            self.appMainW.symbolChanged.connect(self._handleSymbolChanged)

    def _initializeFont(self):
        """Initialize fixed-width font settings."""
        fontFamilies = QFontDatabase.families(QFontDatabase.WritingSystem.Latin)

        # Find first fixed-pitch font family
        fixedFamily = next((family for family in fontFamilies if
                            QFontDatabase.isFixedPitch(family)), None)
        if fixedFamily is None:
            self.fixedFont = QFontDatabase.systemFont(
                QFontDatabase.SystemFont.FixedFont)
            self.fixedFont.setKerning(False)
            return

        # Get font style and create font
        styles = QFontDatabase.styles(fixedFamily)
        fontStyle = styles[1] if len(styles) > 1 else (styles[0] if styles else "")
        self.fixedFont = QFont(fixedFamily)
        if fontStyle:
            self.fixedFont.setStyleName(fontStyle)

        # Set font size
        sizes = QFontDatabase.pointSizes(fixedFamily, fontStyle)
        if len(sizes) > 3:
            self.fixedFont.setPointSize(sizes[3])
        elif sizes:
            self.fixedFont.setPointSize(min(sizes, key=lambda s: abs(s - 9)))
        self.fixedFont.setKerning(False)

    def defineSnapRect(self):
        snapPointRect = QGraphicsRectItem()
        snapPointRect.setRect(QRect(-4, -4, 8, 8))
        snapPointRect.setZValue(100)
        snapPointRect.setVisible(False)
        if schlyr and hasattr(schlyr, 'guideLinePen'):
            snapPen = QPen(schlyr.guideLinePen)
            snapPen.setCosmetic(False)
            snapPointRect.setPen(snapPen)

        return snapPointRect

    def _ensureSnapPointRect(self):
        """Return a valid _snapPointRect, recreating it if the C++ object was deleted."""
        try:
            # Accessing scene() raises RuntimeError if the C++ object is dead.
            _ = self._snapPointRect.scene()
        except RuntimeError:
            self._snapPointRect = self.defineSnapRect()
        return self._snapPointRect

    @property
    def schemModes(self) -> ddef.schematicModes:
        """editModes narrowed to the schematic mode set for this scene."""
        return cast(ddef.schematicModes, self.editModes)

    @property
    def drawMode(self):
        return any((self.schemModes.drawPin, self.schemModes.drawWire,
                    self.schemModes.drawText))

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton and self.schemModes.stretchItem:
            mousePos = event.scenePos().toPoint()
            self._initiateStretch(mousePos)
        elif self.selectedItemGroup and self.schemModes.moveItem:
            # Check if any movable items have connected nets that need stretching
            self._moveMacroActive = False
            hasStretchableItems = any(
                isinstance(item, (shp.schematicSymbol, shp.schematicPin,
                                  snet.schematicNet))
                for item in self.selectedItemGroup.childItems()
            )
            if hasStretchableItems:
                # Begin macro to group net deletions, replacements, and position
                # change as a single undoable operation
                self.undoStack.beginMacro("Move Items")
                self._moveMacroActive = True

            for item in self.selectedItemGroup.childItems():
                if isinstance(item, shp.schematicSymbol) or isinstance(item,
                                                                       shp.schematicPin):
                    item.generatePinNetDict()
                    item.initializeSnapLines(self)
                elif isinstance(item, snet.schematicNet):
                    item.generateEndPointNetDict()
                    item.initializeSnapLines()

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Handle mouse move event."""
        # super() already records mouseRawLoc and the snapped mouseMoveLoc.
        super().mouseMoveEvent(event)
        rawLoc = self.mouseRawLoc
        moveLoc = self.mouseMoveLoc
        if rawLoc is None or moveLoc is None:
            return

        if self._newInstance and self.schemModes.addInstance:
            self._newInstance.setPos(moveLoc)
        elif self._newPin and self.schemModes.drawPin:

            self._newPin.setPos(moveLoc - self._newPin.start)
        elif self.schemModes.drawWire or self.schemModes.drawBus:
            if self._newNet is not None and self._newNet.scene() is None:
                self._newNet = None  # removed while drawing (e.g. undo)
            # findSnapPoint already returns a grid-aligned point (a connection
            # point when one is nearby, otherwise the grid-snapped cursor).
            ignoredSet = {self._newNet} if self._newNet is not None else set()
            netEndPoint = self.findSnapPoint(rawLoc, ignoredSet)
            snapRect = self._ensureSnapPointRect()
            if snapRect.scene() is None:
                self.addItem(snapRect)
            snapRect.setVisible(True)
            snapRect.setPos(netEndPoint)
            self._updateWirePreview(netEndPoint)
        elif self.newAlignLine and self.schemModes.alignItems:
            self.newAlignLine.draftLine = QLineF(
                self.newAlignLine.draftLine.p1(), moveLoc)
        elif self._stretchNet and self.schemModes.stretchItem:
            # findSnapPoint returns a grid-aligned connection point when nearby,
            # otherwise the grid-snapped cursor.
            netEndPoint = self.findSnapPoint(rawLoc, set())
            snapRect = self._ensureSnapPointRect()
            snapRect.setVisible(True)
            snapRect.setPos(netEndPoint)
            if self._stretchBody is not None:
                self._updateBodyStretch(netEndPoint)
            else:
                self._stretchNet.draftLine = QLineF(
                    self._stretchNet.draftLine.p1(), netEndPoint)
        elif self._newText and self.schemModes.drawText:

            self._newText.start = moveLoc
        elif self.schemModes.moveItem and self.selectedItemGroup:
            for item in self.selectedItemGroup.childItems():
                if isinstance(item, (shp.schematicSymbol, shp.schematicPin,
                                     snet.schematicNet)):
                    item.updateSnapLines()

        # Hide snap indicator when not drawing or stretching a net
        if not (self.schemModes.drawWire or self.schemModes.drawBus or
                self.schemModes.stretchItem):
            self._ensureSnapPointRect().setVisible(False)
            self._clearRouteGhost()

        cursorPosition = self.snapToGrid(moveLoc - self.origin)
        self.statusLine.showMessage(
            f"Cursor Position: ({cursorPosition.x()}, {cursorPosition.y()})")
        self.messageLine.setText(
            self.messages.get(self.schemModes.mode() or "", ""))

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        # Finalize snap lines for group net moves before the group is destroyed in super()
        if self.schemModes.moveItem and self.selectedItemGroup:
            for item in self.selectedItemGroup.childItems():
                if isinstance(item, snet.schematicNet):
                    item._finishSnapLines()
            # super() triggers destroyItemGroup -> ItemPositionHasChanged ->
            # symbol/pin _finishSnapLines, then pushes undoGroupMoveStack
            super().mouseReleaseEvent(event)
            # End the macro started in mousePressEvent (groups net deletions,
            # replacements, and position change as single undo step)
            if getattr(self, '_moveMacroActive', False):
                self.undoStack.endMacro()
                self._moveMacroActive = False
        else:
            super().mouseReleaseEvent(event)

    def _handleMouseRelease(self, mousePos: QPoint,
                            button: Qt.MouseButton) -> None:
        """
        Handle mouse release logic.

        :param mouseReleaseLoc: QPoint instance
        :param button: Qt.MouseButton instance
        """

        if button == Qt.MouseButton.LeftButton:
            # Abandoned wire draft left over by a mode switch: close it out.
            if self._newNet is not None and not (
                    self.schemModes.drawWire or self.schemModes.drawBus):
                self._finishWire()
            # Same for a stretch interrupted by a mode switch.
            if self._stretchNet is not None and not self.schemModes.stretchItem:
                self._cancelStretch()
            # modifiers = QGuiApplication.keyboardModifiers()
            if self.schemModes.addInstance:
                self._handleAddInstance(mousePos)
            elif self.schemModes.drawPin:
                self._handleDrawPin(mousePos)
            elif self.schemModes.drawWire:
                self._handleDrawWire(self._releaseRawLoc(mousePos))
            elif self.schemModes.drawBus:
                self._handleDrawBus(self._releaseRawLoc(mousePos))
            elif self.schemModes.drawText:
                self._handleDrawText(mousePos)
            elif self.schemModes.rotateItem:
                self.rotateSelectedItems(mousePos)
            elif self.schemModes.stretchItem:
                self._handleStretchItem()
            elif self.schemModes.nameNet:
                self._handleNameNet(mousePos)
            elif self.schemModes.alignItems:
                self._handleAlignItemLine(mousePos)

    def _cursorRawLoc(self) -> QPoint:
        """Raw cursor position for snap evaluation; falls back to the snapped
        location when no raw position has been recorded (e.g. in tests)."""
        raw = getattr(self, 'mouseRawLoc', None)
        return raw if raw is not None else (self.mouseMoveLoc or QPoint(0, 0))

    def _releaseRawLoc(self, fallback: QPoint) -> QPoint:
        raw = getattr(self, 'mouseReleaseRawLoc', None)
        return raw if raw is not None else fallback

    def _handleAddInstance(self, eventLoc: QPoint) -> None:
        """Place one symbol or a schematic placement mosaic at ``eventLoc``."""
        instanceTuple = self.newInstanceTuple
        if instanceTuple is None:
            return
        if self._newInstance:
            self._newInstance = None
        arraySpec = getattr(self, "pendingInstanceArraySpec", None)
        if arraySpec is None:
            self._newInstance = self.drawInstance(instanceTuple, eventLoc)
            if self._newInstance is None:
                return
            self._applyPendingInstanceParams(self._newInstance)
            self._newInstance.setSelected(True)
            return

        rows, columns, xPitch, yPitch = arraySpec
        instances = []
        for row in range(max(1, rows)):
            for column in range(max(1, columns)):
                position = self.snapToGrid(
                    eventLoc + QPoint(column * xPitch, row * yPitch))
                instance = self.instSymbol(instanceTuple, position)
                if instance is None:
                    continue
                self._applyPendingInstanceParams(instance)
                instances.append(instance)
        if not instances:
            return
        # A schematic mosaic is a persistent symbols-only group. Every member
        # remains an independent device with its own labels and callbacks.
        group = shp.schematicGroup(instances)
        self.addUndoStack(group)
        group.setSelected(True)
        self._newInstance = instances[-1]

    def ungroupSelectedItems(self):
        """Release selected schematic mosaic groups into their symbols."""
        groups = [item for item in self.selectedItemsSet
                  if isinstance(item, shp.schematicGroup)]
        if not groups:
            self.messageLine.setText("No grouped schematic items selected")
            return
        released = []
        for group in groups:
            members = list(group.symbols)
            self.undoStack.push(us.undoGroupShapes(self, group, members, False))
            released.extend(members)
        self.setSelectedItems(set(released))
        self.messageLine.setText(f"Ungrouped {len(groups)} mosaic group(s)")

    def _applyPendingInstanceParams(self, instance) -> None:
        """Write place-with-form label values onto a placed instance."""
        pending = getattr(self, "pendingInstanceParams", None)
        if not pending:
            return
        for name, value in pending.items():
            label = instance.labels.get(f"@{name.lstrip('@')}") or instance.labels.get(name)
            if label is not None:
                label.labelValue = value
        self._resolveInstanceLabels(instance)

    def _resolveInstanceLabels(self, instance) -> None:
        """Resolve NLP labels before callback-driven PyLabels."""
        for labelItem in instance.labels.values():
            if labelItem.labelType == lbl.symbolLabel.labelTypes[1]:
                labelItem.labelDefs()
        for labelItem in instance.labels.values():
            if labelItem.labelType == lbl.symbolLabel.labelTypes[2]:
                labelItem.labelDefs()

    def instanceLabelRows(self, item: shp.schematicSymbol) -> tuple[list[dict], list[str]]:
        """Return the persistent label rows for an instance edit form.

        ParamDefs only enrich matching NLP-label carriers: they provide widget
        typing, validation and declaration order.  Every non-predefined label
        is still represented, including literal normal labels and computed
        PyLabels.  The latter two are read-only because their values are
        defined by the symbol text and callback respectively.
        """
        pyLabelType = lbl.symbolLabel.labelTypes[2]
        nlpLabelType = lbl.symbolLabel.labelTypes[1]
        normalLabelType = lbl.symbolLabel.labelTypes[0]
        labels = {
            name: label for name, label in item.labels.items()
            if name and label.labelDefinition not in lbl.symbolLabel.predefinedLabels
        }
        nlpNames = [name for name, label in labels.items()
                    if label.labelType == nlpLabelType]
        bindings, missingCarriers = prm.paramDefLabelBindings(item.paramDefs,
                                                               nlpNames)
        rows: List[Dict[str, object]] = []
        claimed = set()
        for pdef, name in bindings:
            label = labels[name]
            claimed.add(name)
            rows.append({"labelName": name, "value": label.labelValue,
                         "paramDef": pdef, "isEditable": pdef.display,
                         "isVisible": pdef.display,
                         "isPyLabel": False, "section": "Parameters"})

        def addUnbound(labelType, section, editable=False, isPyLabel=False):
            for name, label in sorted(
                    ((name, label) for name, label in labels.items()
                     if name not in claimed and label.labelType == labelType),
                    key=lambda entry: entry[1].labelName.lower()):
                rows.append({"labelName": name, "value": label.labelValue,
                             "paramDef": None, "isEditable": editable,
                             "isPyLabel": isPyLabel, "section": section})

        # The label order is deliberate: ParamDef declaration order first,
        # then unmatched NLP labels, normal labels, and computed PyLabels.
        addUnbound(nlpLabelType, "Instance Parameters", editable=True)
        addUnbound(normalLabelType, "Normal Labels")
        addUnbound(pyLabelType, "Derived Parameters", isPyLabel=True)
        return rows, missingCarriers

    def _handleDrawPin(self, mouseReleaseLoc: QPoint) -> None:
        """
        Handle draw pin logic.

        :param mouseReleaseLoc: QPoint instance
        """
        # if self._newPin:
        #     self._newPin = None
        self._newPin = self.addPin(mouseReleaseLoc)
        if self._newPin is not None:
            self._newPin.setSelected(True)

    def _handleDrawWire(self, eventLoc: QPoint) -> None:
        """Handle draw wire logic with continuous mode."""
        self._handleDrawNet(eventLoc, width=0)

    def _handleDrawNet(self, eventLoc: QPoint, width: int = 0) -> None:
        """
        Commit the in-progress net at the snapped point and start the next
        one, so a multi-segment net is a chain of segments sharing on-grid
        vertices. With auto-route enabled the commit routes a Manhattan
        two-segment path; landing on a connection point ends the wire.
        """
        if self._suppressWireRestart:
            # The release that follows a double-click wire termination.
            self._suppressWireRestart = False
            return
        ignoredSet = {self._newNet} if self._newNet is not None else set()
        # findSnapTarget already returns a grid-aligned point.
        snapPoint, isConnection = self.findSnapTarget(eventLoc, ignoredSet)

        snapRect = self._ensureSnapPointRect()
        if snapRect.scene() is None:
            self.addItem(snapRect)
        snapRect.setVisible(True)
        snapRect.setPos(snapPoint)
        self._wireWidth = width

        if self._newNet is not None and self._newNet.scene() is None:
            # In-progress segment was removed while drawing (e.g. undo).
            self._newNet = None
        if self._newNet is None:
            # First click of a new wire.
            self._routeHorizontalFirst = None
            self._wirePendingName = self._ripBusMemberName(snapPoint, width)
            newNet = self._createNet(snapPoint, width)
            if self._wirePendingName:
                newNet.name = self._wirePendingName
            return
        endPoint = self._commitWirePoint(snapPoint, width)
        if endPoint is None:
            # Degenerate click: keep the segment open for a real end point.
            return
        if isConnection and endPoint == snapPoint:
            # Landed on a pin or an existing net: the wire is complete. A
            # constrained end point that did not reach the target keeps the
            # chain going instead of finishing on an unconnected wire.
            self._finishWire()
            return
        self._createNet(endPoint, width)

    def _createNet(self, point: QPoint,
                   width: int = 0) -> snet.schematicNet:
        newNet = snet.schematicNet(point, point, width, self._wireDrawMode)
        self._newNet = newNet
        self.addItem(newNet)
        if not self._wireChainActive:
            # Each committed segment is its own undo step on the stack;
            # the parallel lists track this chain's commands so
            # popWireVertex can step back through them while drawing.
            self._wireChainActive = True
            self._wireCommands = []
            self._wireResumePoints = []
            self._wireCommandIndices = []
        return newNet

    def _commitWirePoint(self, snapPoint: QPoint, width: int) -> Optional[
        QPoint]:
        """Commit the in-progress wire to snapPoint: a single constrained
        segment in manual mode, or a Manhattan two-segment route when
        auto-route is active. Returns the committed end point, or None for a
        degenerate click."""
        draft = self._newNet
        if draft is None:
            return None
        startPoint = draft.sceneEndPoints[0]
        corner = self._routeCorner(startPoint, snapPoint)
        legs = ([(startPoint, corner), (corner, snapPoint)]
                if corner is not None else [(startPoint, snapPoint)])
        if all(a == b for a, b in legs):
            return None
        if draft.scene() is not None:
            self.removeItem(draft)
        self._newNet = None
        self._clearRouteGhost()
        endPoint = None
        for segStart, segEnd in legs:
            committed = self._commitSegment(segStart, segEnd, width)
            if committed is not None:
                endPoint = committed
        return endPoint

    def _commitSegment(self, start: QPoint, end: QPoint,
                       width: int) -> Optional[QPoint]:
        """Create one net segment, run merge/split, and capture the complete
        net diff (segment plus any consumed nets) as a single undoable
        command. Returns the segment's effective end point."""
        segment = snet.schematicNet(start, end, width, self._wireDrawMode)
        if segment.draftLine.isNull():
            return None
        if self._wirePendingName:
            segment.name = self._wirePendingName
        startPoint, endPoint = segment.sceneEndPoints
        netsBefore = self.findSceneNetsSet()
        self.addItem(segment)
        self.mergeSplitNets(segment)
        # Nets created by the drawn segment's own merge are the wire being
        # drawn; pierced-bus fragments split below keep their bus name.
        ownNets = self.findSceneNetsSet() - netsBefore
        self._splitPiercedNets(startPoint, endPoint)
        netsAfter = self.findSceneNetsSet()
        newNets = list(netsAfter - netsBefore)
        oldNets = list(netsBefore - netsAfter)
        if self._wirePendingName:
            # Skip bus-width results: a member wire merged into the trunk
            # extends the bus rather than ripping a member off it.
            for netItem in ownNets & netsAfter:
                if not netItem.width:
                    netItem.name = self._wirePendingName
        if newNets or oldNets:
            command = us.addDeleteShapesUndo(self, newNets, oldNets)
            command.setText("Draw Wire")
            self.undoStack.push(command)
            if self._wireChainActive:
                self._wireCommands.append(command)
                self._wireResumePoints.append(startPoint)
                # Stack index just above the pushed command: popWireVertex
                # uses it to tell whether the command still tops the stack.
                self._wireCommandIndices.append(self.undoStack.index())
        self.invalidate(
            segment.mapToScene(segment.boundingRect()).boundingRect().adjusted(
                -self.snapGrid, -self.snapGrid, self.snapGrid, self.snapGrid),
            QGraphicsScene.SceneLayer.BackgroundLayer)
        return endPoint

    def _splitPiercedNets(self, *points: QPoint) -> None:
        """Split any existing wire whose body passes through one of the given
        points, so T-junctions get a vertex (junction dot + connectivity)
        immediately instead of after leaving draw mode."""
        for point in points:
            probe = QRectF(point.x() - 1, point.y() - 1, 2, 2)
            for item in list(self.items(probe)):
                if (isinstance(item, snet.schematicNet)
                        and item.scene() is self
                        and not self._isEipGhost(item)
                        and item.sceneShapeRect.contains(point)
                        and point not in item.sceneEndPoints):
                    self.mergeSplitNets(item)

    def _routeCorner(self, start: QPoint, end: QPoint) -> Optional[QPoint]:
        """Manhattan corner for auto-route; None when auto-route is off, the
        draw mode is not orthogonal, or start/end are already axis-aligned."""
        if (not self._wireAutoRoute
                or self._wireDrawMode != snet.NetMode.ORTHOGONAL):
            return None
        if start.x() == end.x() or start.y() == end.y():
            return None
        horizontalFirst = (self._routeHorizontalFirst
                           if self._routeHorizontalFirst is not None else
                           abs(end.x() - start.x()) >= abs(end.y() - start.y()))
        return (QPoint(end.x(), start.y()) if horizontalFirst
                else QPoint(start.x(), end.y()))

    def _updateWirePreview(self, netEndPoint: QPoint) -> None:
        """Update the in-progress wire preview: a single constrained segment,
        or a two-segment Manhattan route when auto-route is active."""
        if self._newNet is None:
            self._clearRouteGhost()
            return
        startPoint = self._newNet.sceneEndPoints[0]
        corner = self._routeCorner(startPoint, netEndPoint)
        if corner is not None:
            self._newNet.draftLine = QLineF(startPoint, corner)
            ghost = self._ensureRouteGhost()
            ghost.draftLine = QLineF(corner, netEndPoint)
        else:
            self._newNet.draftLine = QLineF(startPoint, netEndPoint)
            self._clearRouteGhost()

    def _ensureRouteGhost(self) -> snet.guideLine:
        if self._routeGhost is None or self._routeGhost.scene() is None:
            self._routeGhost = snet.guideLine(QPoint(0, 0), QPoint(0, 0))
            self.addItem(self._routeGhost)
        return self._routeGhost

    def _clearRouteGhost(self) -> None:
        if self._routeGhost is not None:
            if self._routeGhost.scene() is not None:
                self.removeItem(self._routeGhost)
            self._routeGhost = None

    def _finishWire(self) -> None:
        """Terminate the in-progress wire, committing a pending segment, and
        close out the wire chain. The draw mode stays active."""
        if self._newNet is not None:
            draft = self._newNet
            if draft.scene() is not None:
                endPoint = self.findSnapPoint(self._cursorRawLoc(), {draft})
                if endPoint != draft.sceneEndPoints[0]:
                    self._commitWirePoint(endPoint, draft.width)
                else:
                    self.removeItem(draft)
                    self._newNet = None
            else:
                self._newNet = None
        self._endWireChain()
        self._ensureSnapPointRect().setVisible(False)

    def _endWireChain(self) -> None:
        """Reset wire-chain tracking once the chain has ended. Committed
        segments stay on the undo stack as per-segment commands."""
        self._wireChainActive = False
        self._wireCommands = []
        self._wireResumePoints = []
        self._wireCommandIndices = []
        self._routeHorizontalFirst = None
        self._wirePendingName = ""
        self._clearRouteGhost()

    def popWireVertex(self) -> None:
        """Remove the last committed wire segment and resume the chain from
        its start point (Backspace during wire drawing)."""
        if not (self.schemModes.drawWire or self.schemModes.drawBus):
            return
        if self._wireCommands:
            command = self._wireCommands.pop()
            resumePoint = self._wireResumePoints.pop()
            stackIndex = self._wireCommandIndices.pop()
            if self.undoStack.index() == stackIndex:
                # The segment still tops the stack: undo through the stack
                # so the index and redo bookkeeping stay consistent.
                self.undoStack.undo()
            else:
                try:
                    # Stack traffic moved the command off the top (e.g. an
                    # external undo): revert it surgically and keep it from
                    # firing again as a stale stack entry.
                    command.undo()
                    command.disable()
                except RuntimeError:
                    # A truncating push already deleted the command object.
                    pass
            if self._newNet is not None and self._newNet.scene() is not None:
                self.removeItem(self._newNet)
            self._newNet = None
            self._createNet(resumePoint, self._wireWidth)
        elif self._newNet is not None:
            # Nothing committed yet: drop the draft entirely.
            if self._newNet.scene() is not None:
                self.removeItem(self._newNet)
            self._newNet = None
            self._endWireChain()

    def cycleWireDrawMode(self) -> None:
        modes = list(snet.NetMode)
        self._wireDrawMode = modes[(modes.index(self._wireDrawMode) + 1) %
                                   len(modes)]
        self._clearRouteGhost()
        self.messageLine.setText(
            f"Wire Angle: {self._wireDrawMode.name.title()}")

    def toggleWireAutoRoute(self) -> None:
        self._wireAutoRoute = not self._wireAutoRoute
        self._clearRouteGhost()
        self.messageLine.setText(
            f"Auto Route: {'On' if self._wireAutoRoute else 'Off'}")

    def flipRouteOrientation(self) -> None:
        self._routeHorizontalFirst = (not self._routeHorizontalFirst
                                      if self._routeHorizontalFirst is not None
                                      else False)
        if self._newNet is not None:
            self._updateWirePreview(
                self.findSnapPoint(self._cursorRawLoc(), {self._newNet}))

    def _handleAlignItemLine(self, eventLoc: QPoint) -> None:
        if self.newAlignLine is None:
            from PySide6.QtWidgets import (
                QApplication,
            )
            alignDlg = [w for w in QApplication.topLevelWidgets() if isinstance(w,
                alg.alignItemsDialogue) and w.isVisible() and w.scene == self][
                0]
            if alignDlg.horizontalAlignButton.isChecked():
                self.newAlignLine = shp.alignLine(QLineF(eventLoc, eventLoc), 1,
                                                  0)  # horizontal
            else:
                self.newAlignLine = shp.alignLine(QLineF(eventLoc, eventLoc), 1,
                                                  1)
            self.addUndoStack(self.newAlignLine)
        else:
            self.newAlignLine.draftLine = QLineF(
                self.newAlignLine.draftLine.p1(), eventLoc)
            self.alignLineFinished.emit(self.newAlignLine)
            # self.newAlignLine = None
            self.schemModes.setMode('selectItem')

    def _handleDrawBus(self, eventLoc: QPoint):
        """Handle draw bus logic with continuous mode."""
        self._handleDrawNet(eventLoc, width=1)

    # ---- bus ripper ------------------------------------------------------

    def _ripBusMemberName(self, point: QPoint, width: int) -> str:
        """Bus ripper: a plain wire started on a bus-named net or pin gets
        named ``base<i>`` for the chosen member index. Returns "" when the
        start point is not on a bus (or the rip is cancelled)."""
        if width:
            return ""  # drawing a bus trunk, not a member
        target = self._busRangeAtPoint(point)
        if target is None:
            return ""
        base, lo, hi = target
        index = self._busMemberIndex(base, lo, hi)
        return f"{base}<{index}>" if index is not None else ""

    def _busRangeAtPoint(self, point: QPoint):
        """Return (base, lo, hi) when a bus-named net or pin sits at point."""
        probe = QRectF(point.x() - 2, point.y() - 2, 4, 4)
        for item in self.items(probe):
            if self._isEipGhost(item):
                continue
            if isinstance(item, snet.schematicNet):
                name = item.name
            elif isinstance(item, (shp.symbolPin, shp.schematicPin)):
                name = item.pinName
            else:
                continue
            if name:
                base, (lo, hi) = snet.schematicNet.parseArrayNotation(name)
                if lo >= 0:
                    return base, lo, hi
        return None

    def _busMemberIndex(self, base: str, lo: int, hi: int) -> Optional[int]:
        """Pick the member index for a rip: one-shot ``_busRipIndex``
        override, immediate for single-member pins, else prompt."""
        # Buses may descend (a<7:0>): normalize before range checks/prompts.
        loB, hiB = min(lo, hi), max(lo, hi)
        if self._busRipIndex is not None:
            index = self._busRipIndex
            self._busRipIndex = None
            return index if loB <= index <= hiB else None
        if hiB == loB:
            return lo
        from PySide6.QtWidgets import QInputDialog
        view = self.views()[0] if self.views() else None
        index, ok = QInputDialog.getInt(
            view, "Rip Bus Member",
            f"Member index of {base}<{lo}:{hi}>:", lo, loB, hiB)
        return index if ok else None

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
            self._completeStretch(self._cursorRawLoc())

    def _cancelStretch(self) -> None:
        """Restore original geometry when a stretch is aborted (Escape)."""
        if self._stretchBody is not None:
            body = self._stretchBody
            netItem = body['net']
            self.addItem(netItem)
            for removedNet in getattr(netItem, '_removedNets', []):
                self.addItem(removedNet)
                self.itemsRefSet.add(removedNet)
            for snapLinesSet in body['snapLines'].values():
                for snapLine in list(snapLinesSet):
                    if snapLine.scene() is not None:
                        self.removeItem(snapLine)
            self._stretchBody = None
        else:
            origNet = getattr(self, '_stretchOriginalNet', None)
            if origNet is not None and origNet.scene() is None:
                self.addItem(origNet)
        if self._stretchNet is not None:
            if self._stretchNet.scene() is not None:
                self.removeItem(self._stretchNet)
            self._stretchNet = None
        self._stretchOriginalNet = None
        self._ensureSnapPointRect().setVisible(False)
        for view in self.views():
            view.setCursor(Qt.CursorShape.ArrowCursor)

    def _completeStretch(self, releasePos: QPoint) -> None:
        """
        Complete a stretch operation on mouse release.

        Snaps release position to grid/connection point, creates replacement
        manhattan-routed net segments, assigns original net properties, resolves
        connectivity, and pushes a single undo command.

        The undo command captures the FINAL state after merge/split so that undo
        removes all replacement nets (including any produced by mergeSplitNets)
        and restores the original net plus any existing nets consumed by merging.
        """
        if self._stretchBody is not None:
            self._completeBodyStretch(releasePos)
            return
        try:
            origNet = self._stretchOriginalNet
            if origNet is None:
                return
            # findSnapPoint returns a grid-aligned point: a nearby connection
            # point when available, otherwise the grid-snapped release position.
            snappedRelease = self.findSnapPoint(releasePos, set())

            anchorPoint = self._stretchAnchorPoint

            if snappedRelease == anchorPoint:
                # Zero-length result: remove original net, push no undo command
                # (original net was already removed from scene in _initiateStretch)
                pass
            elif snappedRelease == self._stretchClickedEndpoint:
                # No geometric change: user released at the original clicked
                # endpoint position. Restore the original net without pushing
                # any undo command (nothing actually changed).
                self.addItem(origNet)
            else:
                # Create manhattan segments from anchor to snapped release,
                # preserving the original wire's direction.
                newSegments = self.addStretchWires(
                    anchorPoint, snappedRelease,
                    getattr(self._stretchNet, 'horizontalFirst', None))

                # Defensive filter: discard any zero-length segments
                # (p1 == p2) that may slip through from addStretchWires
                newSegments = [
                    seg for seg in newSegments
                    if seg.draftLine.p1().toPoint() != seg.draftLine.p2().toPoint()
                ]

                if newSegments:
                    # Assign original net's name, nameStrength, and width
                    for segment in newSegments:
                        segment.inherit(origNet)
                        segment.width = self._stretchOriginalWidth

                    # Snapshot nets currently in the scene BEFORE adding new
                    # segments, so we can detect what mergeSplitNets changes.
                    netsBefore = self.findSceneNetsSet()

                    # Add segments to scene
                    for segment in newSegments:
                        self.addItem(segment)

                    # Call mergeSplitNets on each new segment for connectivity.
                    # This may remove some of our new segments (merged) and add
                    # different ones, or remove existing scene nets (merged into
                    # our new ones).
                    for segment in newSegments:
                        if segment.scene() is not None:
                            self.mergeSplitNets(segment)

                    # Snapshot nets after merge/split to determine final state
                    netsAfter = self.findSceneNetsSet()

                    # allNewNets: nets that now exist but didn't before
                    allNewNets = list(netsAfter - netsBefore)

                    # consumedNets: existing nets that were removed by merging
                    consumedNets = list(netsBefore - netsAfter)

                    # The undo must restore the original net AND any existing
                    # nets that were consumed during merge/split
                    allOldNets = [origNet] + consumedNets

                    # Push single undo command capturing the complete operation
                    undoCommand = us.addDeleteShapesUndo(
                        self, allNewNets, allOldNets)
                    self.undoStack.push(undoCommand)

        except Exception as e:
            self.logger.error(f"Error in _completeStretch: {e}", exc_info=True)
        finally:
            # Clean up: remove guideLine from scene, reset stretch state,
            # hide snap indicator, restore default cursor
            if self._stretchNet and self._stretchNet.scene() is not None:
                self.removeItem(self._stretchNet)
            self._stretchNet = None
            self._stretchOriginalNet = None
            self._stretchClickedEndpoint = None
            self._ensureSnapPointRect().setVisible(False)
            for view in self.views():
                view.setCursor(Qt.CursorShape.ArrowCursor)

    def _handleNameNet(self, mouseReleaseLoc):
        if not self.netNameString:
            return
        # Find the schematicNet under the cursor in a single click
        clickedNet = next(
            (item for item in self.items(mouseReleaseLoc)
             if isinstance(item, snet.schematicNet)
             and not self._isEipGhost(item)), None)
        if clickedNet is None:
            # Missed the net: stay in nameNet mode for another try.
            self.messageLine.setText(
                "No net under cursor - click a net to name it")
            return
        self.undoStack.push(
            us.changeNetNameUndo(self, [clickedNet], self._nextNetName()))
        clickedNet.setSelected(False)
        if self.netNameString is None:
            # Bounded bus range exhausted: leave the mode.
            self._newNetNameObj = None
            self.schemModes.setMode("selectItem")

    def _nextNetName(self) -> str:
        """Resolve the label to apply now and advance auto-increment state.

        'base'     -> applies 'base' on every click until Escape
        'base<i>'  -> applies 'base<i>', 'base<i+1>', ... (unbounded)
        'base<i:j>'-> applies 'base<i>' ... 'base<j>', then exits the mode
        """
        if self._netNameAuto is None:
            nameStr = self.netNameString
            if nameStr is None:
                return ""
            base, (start, end) = snet.schematicNet.parseArrayNotation(nameStr)
            if start == -1:
                self._netNameAuto = {'repeat': True, 'base': base}
            else:
                hasRange = ':' in nameStr.split('<', 1)[1]
                self._netNameAuto = {
                    'repeat': False, 'base': base, 'next': start,
                    'last': end if hasRange else None,
                    'step': 1 if end >= start else -1}
        auto = self._netNameAuto
        if auto['repeat']:
            return auto['base']
        applyIndex = auto['next']
        applyName = f"{auto['base']}<{applyIndex}>"
        if auto['last'] is not None and applyIndex == auto['last']:
            self.netNameString = None
            self._netNameAuto = None
        else:
            auto['next'] += auto['step']
            self.netNameString = applyName
        return applyName

    def updateStretchNet(self):
        stretchNet = self._stretchNet
        if stretchNet is None:
            return
        # findSnapPoint returns a grid-aligned point already.
        netEndPoint = self.findSnapPoint(self._cursorRawLoc(), set())
        stretchNet.draftLine = QLineF(stretchNet.draftLine.p1(), netEndPoint)

    @Slot(snet.schematicNet)
    def _handleWireFinished(self, newNet: snet.schematicNet):
        """
        check if the new net is valid. If it has zero length, remove it. Otherwise process it.

        """

        if newNet.draftLine.length() < 1:
            # Drafts are no longer pushed to the undo stack; a zero-length
            # one is simply discarded.
            if newNet.scene() == self:
                self.removeItem(newNet)
        else:
            newNetSceneRect = newNet.sceneBoundingRect().adjusted(-self.snapGrid,
                                                                  -self.snapGrid,
                                                                  self.snapGrid,
                                                                  self.snapGrid)
            netsBefore = self.findSceneNetsSet()
            startPoint, endPoint = newNet.sceneEndPoints
            self.mergeSplitNets(newNet)
            self._splitPiercedNets(startPoint, endPoint)
            netsAfter = self.findSceneNetsSet()
            newNets = list(netsAfter - netsBefore)
            oldNets = list(netsBefore - netsAfter)
            if newNets or oldNets:
                self.undoStack.push(
                    us.addDeleteShapesUndo(self, newNets, oldNets))
            self.invalidate(newNetSceneRect, QGraphicsScene.SceneLayer.BackgroundLayer)

    def _replaceNets(self, oldNets, newNets, name_source_net):
        """Replace a set of nets in the scene with a new set.

        Reconciliation is done by geometry (schematicNet.__eq__), NOT object
        identity: any old net whose geometry already matches a new net is kept
        as-is, and only genuinely new geometries are added. This guarantees the
        scene ends up with exactly one net per distinct geometry, so overlapping
        duplicates collapse into a single object.
        """
        # Expand oldNets to EVERY scene net object sharing a geometry with the
        # nets being consumed. schematicNet.__eq__/__hash__ compare by geometry,
        # so a plain set of nets silently collapses exact duplicates into one
        # element - meaning duplicate *objects* would otherwise be left behind
        # in the scene. Gathering them here is what makes overlapping duplicates
        # actually disappear on merge/delete.
        consumedGeometries = set(oldNets)
        allOldObjects = [
            item for item in self.items()
            if isinstance(item, snet.schematicNet) and item in consumedGeometries
        ]
        # Ensure the originally supplied objects are included even if not
        # currently reported by self.items() (e.g. just added this pass).
        for net in oldNets:
            if all(net is not obj for obj in allOldObjects):
                allOldObjects.append(net)

        keptIds = set()

        for newNet in newNets:
            existing = next(
                (obj for obj in allOldObjects if obj == newNet
                 and id(obj) not in keptIds),
                None,
            )
            if existing is not None:
                # Geometry already present: keep one existing object and fold
                # the new net's name into it.
                existing.mergeNetName(name_source_net)
                keptIds.add(id(existing))
            else:
                self.addItem(newNet)
                newNet.mergeNetName(name_source_net)

        # Remove every old net object that was not kept. id()-based so duplicate
        # objects that are __eq__ to a kept net are still removed.
        for net in allOldObjects:
            if id(net) in keptIds:
                continue
            if net.scene() is self:
                self.removeItem(net)

    def mergeSplitNets(self, inputNet: snet.schematicNet):
        merged, outputNet, processedNets = self.mergeNets(inputNet)

        if merged:
            # processedNets are the originals consumed by the merge (includes
            # inputNet and every parallel/overlapping duplicate).
            splitDone, splitOutputNets = self.splitInputNet(outputNet)
            newNets = splitOutputNets if splitDone else {outputNet}
            self._replaceNets(processedNets, newNets, outputNet)
        else:
            splitDone, splitOutputNets = self.splitInputNet(inputNet)
            if splitDone:
                self._replaceNets({inputNet}, splitOutputNets, inputNet)

    def cleanUpNets(self):
        """Run mergeSplitNets on every net in the scene to remove duplicates."""
        netSnapshot = list(
            item for item in self.items() if isinstance(item, snet.schematicNet)
            and not self._isEipGhost(item)
        )
        for netItem in netSnapshot:
            if netItem.scene() is self:
                self.mergeSplitNets(netItem)

    def mergeNets(self, inputNet: snet.schematicNet) -> Tuple[
        bool, snet.schematicNet, Set[snet.schematicNet]]:
        """
        Merges overlapping nets and returns the merged net.
        """
        otherNets = inputNet.findOverlapNets()
        if not otherNets:
            return False, inputNet, set()

        collinearNets = {net for net in otherNets
                         if inputNet.overlapsCollinearly(net)}
        if not collinearNets:
            return False, inputNet, set()

        points = list(inputNet.sceneEndPoints)  # Create a copy
        busExists = int(any(net.width for net in collinearNets) or inputNet.width)

        for net in collinearNets:
            points.extend(net.sceneEndPoints)

        furthestPoints = self.findFurthestPoints(points)
        # Snap furthest points to grid to ensure merged net is properly aligned
        p1 = self.snapToGrid(furthestPoints[0])
        p2 = self.snapToGrid(furthestPoints[1])
        mergedNet = snet.schematicNet(p1, p2, width=busExists)

        processedNets = collinearNets | {inputNet}
        for net in processedNets:
            mergedNet.mergeNetName(net)

        return True, mergedNet, processedNets

    def splitInputNet(self, inputNet) -> tuple[bool, Set[snet.schematicNet]]:
        sceneShapeRect = inputNet.sceneShapeRect
        sceneItems = [item for item in self.items(sceneShapeRect)
                      if not self._isEipGhost(item)]

        splitPointsSet = set()

        # Single iteration to collect all relevant points
        for item in sceneItems:
            if isinstance(item, snet.schematicNet) and inputNet.isOrthogonal(
                    item):
                for point in item.sceneEndPoints:
                    if sceneShapeRect.contains(point):
                        splitPointsSet.add(point)
            elif isinstance(item, (shp.symbolPin, shp.schematicPin)):
                splitPointsSet.add(item.mapToScene(item.start).toPoint())

        if not splitPointsSet:
            return False, set()

        # Create ordered points list
        splitPointsList = [inputNet.sceneEndPoints[0], *splitPointsSet,
                           inputNet.sceneEndPoints[1], ]
        orderedPoints = list(dict.fromkeys(self.orderPoints(splitPointsList)))

        # Create split nets
        splitNetSet = set()
        is_selected = inputNet.isSelected()

        for i in range(len(orderedPoints) - 1):
            # Snap points to grid to ensure split nets are properly aligned
            p1 = self.snapToGrid(orderedPoints[i])
            p2 = self.snapToGrid(orderedPoints[i + 1])
            splitNet = snet.schematicNet(p1, p2, inputNet.width)
            if not splitNet.draftLine.isNull():
                if is_selected:
                    splitNet.setSelected(True)
                splitNetSet.add(splitNet)

        return True, splitNetSet

    def _snapRadius(self) -> int:
        """Effective connection-snap radius. Capped at half a snap grid so a
        connection point can only capture the cursor when it is essentially on
        top of it — otherwise a wire end would visibly jump a full grid cell
        sideways onto a neighbouring pin or wire."""
        return max(1, min(self.snapConnectDistance,
                          self.snapTuple[0] // 2, self.snapTuple[1] // 2))

    def findSnapPoint(self, eventLoc: QPoint,
                      ignoredSet: set[snet.schematicNet]) -> QPoint:
        return self.findSnapTarget(eventLoc, ignoredSet)[0]

    def findSnapTarget(self, eventLoc: QPoint,
                       ignoredSet: set[snet.schematicNet]) -> Tuple[
        QPoint, bool]:
        """Snap the raw cursor position eventLoc to a nearby connection point
        (pin, net endpoint, or net body) or to the grid.
        Returns (point, isConnection)."""
        # Always work from the grid-snapped cursor so the returned point is
        # grid-aligned even when no connection point is found. This is the
        # single source of truth for net endpoint placement and keeps the
        # behaviour identical across draw and stretch code paths.
        gridPoint = self.snapToGrid(eventLoc)

        snapRadius = self._snapRadius()
        snapRect = QRect(eventLoc.x() - snapRadius,
                         eventLoc.y() - snapRadius,
                         2 * snapRadius,
                         2 * snapRadius, )
        # The rect is only a broad phase: a candidate must also be within the
        # radius in Manhattan distance (the square corner would otherwise
        # reach sqrt(2)-times farther), unless it coincides with the plain
        # grid point — landing there costs nothing and still terminates a wire.
        snapPoints = {
            point for point in self.findConnectPoints(snapRect, ignoredSet)
            if (point - eventLoc).manhattanLength() <= snapRadius
               or point == gridPoint}

        if not snapPoints:
            return gridPoint, False

        # Deterministic selection: pick the connection point nearest to the
        # cursor, breaking ties by (x, y) so the same candidate always wins.
        # Sorting (instead of min over an unordered set) prevents the endpoint
        # from jittering between equidistant candidates as the mouse moves.
        closestPoint = min(
            sorted(snapPoints, key=lambda p: (p.x(), p.y())),
            key=lambda p: (p - eventLoc).manhattanLength(),
        )
        return closestPoint, True

    def findConnectPoints(self, sceneRect: QRect,
                          ignoredSet: AbstractSet[QGraphicsItem]
                          ) -> set[QPoint]:
        """Collect grid-aligned connection points inside sceneRect: net
        endpoints, pins, and the projection of the probe point onto any wire
        body (for T-junction snaps). Points are snapped to grid so that
        snapping to them can never drag a net endpoint off-grid."""
        snapPoints = set()
        rectItems = {item for item in self.items(sceneRect)
                     if not self._isEipGhost(item)} - ignoredSet
        probePoint = sceneRect.center()
        for item in rectItems:
            if isinstance(item, snet.schematicNet):
                if any(sceneRect.contains(ep) for ep in item.sceneEndPoints):
                    snapPoints.add(self.snapToGrid(
                        next(ep for ep in item.sceneEndPoints
                             if sceneRect.contains(ep))))
                    continue
                projected = self._projectPointOnNet(probePoint, item)
                if projected is not None:
                    snapPoints.add(projected)
            elif isinstance(item, (shp.symbolPin, shp.schematicPin)):
                snapPoints.add(
                    self.snapToGrid(item.mapToScene(item.start).toPoint()))
        return snapPoints

    def _projectPointOnNet(self, point: QPoint,
                           netItem: snet.schematicNet) -> Optional[QPoint]:
        """Project point onto the net body and return a grid-aligned point
        that stays on the segment, or None. Used to snap a wire end onto the
        middle of an existing wire to form a T-junction."""
        p1, p2 = netItem.sceneEndPoints
        direction = QPointF(p2 - p1)
        lengthSq = QPointF.dotProduct(direction, direction)
        if lengthSq < 1.0:
            return None
        t = QPointF.dotProduct(QPointF(point - p1), direction) / lengthSq
        if t <= 0.0 or t >= 1.0:
            return None
        projection = QPointF(p1) + direction * t
        if (projection - QPointF(point)).manhattanLength() > \
                self._snapRadius():
            return None
        snapped = self.snapToGrid(projection.toPoint())
        if snapped == p1 or snapped == p2:
            return None
        # Grid rounding must not pull the point off the wire body.
        if not netItem.sceneShapeRect.contains(snapped):
            return None
        return snapped

    @staticmethod
    def orderPoints(points: list[QPoint]) -> list[QPoint]:
        currentPoint = points.pop(0)
        orderedPoints = [currentPoint]

        while points:
            nearest_point_index = min(
                range(len(points)),
                key=lambda i: (points[i] - currentPoint).manhattanLength()
            )
            orderedPoints.append(points[nearest_point_index])
            currentPoint = points.pop(nearest_point_index)

        return orderedPoints

    @staticmethod
    def findFurthestPoints(points: list[QPoint]) -> tuple[QPoint, QPoint]:
        """
        Find the two points with the maximum distance between them.
        """
        max_distance = 0
        furthest_points: Optional[Tuple[QPoint, QPoint]] = None

        for i in range(len(points)):
            for j in range(i + 1, len(points)):
                distance = (points[i] - points[j]).manhattanLength()
                if distance > max_distance:
                    max_distance = distance
                    furthest_points = (points[i], points[j])

        if furthest_points is None:
            raise ValueError("findFurthestPoints requires at least two points")
        return furthest_points

    @Slot(str, str, str)
    def _handleSymbolChanged(self, libName: str, cellName: str, viewName: str):
        """Reload symbol instances when their definition changes."""
        from revedaEditor.fileio.loadJSON import clear_symbol_cache
        clear_symbol_cache()
        for item in self.items():
            if isinstance(item, shp.schematicSymbol):
                if (item.libraryName == libName and
                    item.cellName == cellName and
                    item.viewName == viewName):
                    item.reload()

    def _findNearestEndpoint(
        self, mousePos: QPoint
    ) -> Optional[Tuple[snet.schematicNet, QPoint, QPoint]]:
        """
        Search scene for nets with an endpoint within snapDistance of mousePos.
        Returns (net, clickedEndpoint, anchorEndpoint) or None.
        If both endpoints of the same net are within snapDistance, pick the one
        farther by Manhattan distance as anchor.
        """
        snapDist = min(self.snapTuple)
        bestNet = None
        bestClickedEnd = None
        bestAnchorEnd = None
        bestDist = snapDist + 1  # Initialize beyond threshold

        for netItem in self.findSceneNetsSet():
            endpoints = netItem.sceneEndPoints
            p1, p2 = endpoints[0], endpoints[1]

            dist_p1 = (p1 - mousePos).manhattanLength()
            dist_p2 = (p2 - mousePos).manhattanLength()

            p1_within = dist_p1 <= snapDist
            p2_within = dist_p2 <= snapDist

            if not p1_within and not p2_within:
                continue

            # Determine clicked endpoint (closer to mousePos) and anchor (the other)
            if p1_within and p2_within:
                # Both within snap distance: clicked = closer, anchor = farther
                if dist_p1 <= dist_p2:
                    clickedEnd, anchorEnd, closestDist = p1, p2, dist_p1
                else:
                    clickedEnd, anchorEnd, closestDist = p2, p1, dist_p2
            elif p1_within:
                clickedEnd, anchorEnd, closestDist = p1, p2, dist_p1
            else:
                clickedEnd, anchorEnd, closestDist = p2, p1, dist_p2

            # Keep the net with the closest endpoint to mousePos
            if closestDist < bestDist:
                bestDist = closestDist
                bestNet = netItem
                bestClickedEnd = clickedEnd
                bestAnchorEnd = anchorEnd

        if (bestNet is not None and bestClickedEnd is not None
                and bestAnchorEnd is not None):
            return (bestNet, bestClickedEnd, bestAnchorEnd)
        return None

    def _initiateStretch(self, mousePos: QPoint) -> bool:
        """
        Find nearest net endpoint within snap distance of mousePos.
        If found, remove original net, create guideLine from anchor to mousePos,
        store stretch state, set appropriate cursor, and show snap indicator.
        Returns True if stretch initiated, False otherwise.
        """
        result = self._findNearestEndpoint(mousePos)
        if result is None:
            # No endpoint nearby: try grabbing the wire body instead.
            return self._initiateBodyStretch(mousePos)

        netItem, clickedEndpoint, anchorEndpoint = result
        self._stretchBody = None

        # Capture endpoint positions before removing from scene
        # (mapToScene requires the item to be in a scene)
        p1, p2 = netItem.sceneEndPoints[0], netItem.sceneEndPoints[1]

        # Store stretch state: original net properties
        self._stretchOriginalNet = netItem
        self._stretchAnchorPoint = anchorEndpoint
        self._stretchClickedEndpoint = clickedEndpoint
        self._stretchOriginalName = netItem.name
        self._stretchOriginalNameStrength = netItem.nameStrength
        self._stretchOriginalWidth = netItem.width

        # Remove original net from scene
        self.removeItem(netItem)

        # Create guideLine from anchor to cursor position
        self._stretchNet = snet.guideLine(anchorEndpoint, mousePos)
        self._stretchNet.inherit(netItem)
        self.addItem(self._stretchNet)

        # Determine net orientation and set cursor accordingly
        # A horizontal net has same Y for both endpoints
        # A vertical net has same X for both endpoints
        if p1.y() == p2.y():
            # Horizontal net
            for view in self.views():
                view.setCursor(Qt.CursorShape.SizeHorCursor)
        elif p1.x() == p2.x():
            # Vertical net
            for view in self.views():
                view.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            # Diagonal or other — use horizontal as default
            for view in self.views():
                view.setCursor(Qt.CursorShape.SizeHorCursor)

        # Show snap indicator rect at cursor position
        snapRect = self._ensureSnapPointRect()
        if snapRect.scene() is None:
            self.addItem(snapRect)
        snapRect.setPos(mousePos)
        snapRect.setVisible(True)

        return True

    def _initiateBodyStretch(self, mousePos: QPoint) -> bool:
        """Grab the body of a wire segment: the drag slides the segment
        perpendicular to its direction while nets attached at both ends
        rubber-band, like Virtuoso's edge stretch."""
        probe = QRectF(mousePos.x() - 1, mousePos.y() - 1, 2, 2)
        candidates = [item for item in self.items(probe)
                      if isinstance(item, snet.schematicNet)
                      and item.sceneShapeRect.contains(mousePos)]
        if not candidates:
            return False
        netItem = candidates[0]  # items() is in descending stacking order
        p1, p2 = netItem.sceneEndPoints
        horizontal = abs(p2.y() - p1.y()) <= abs(p2.x() - p1.x())

        # Replace each attached net with a guideLine anchored at this net's
        # endpoints; the originals are restored/replaced on completion.
        netItem.generateEndPointNetDict()
        netItem.initializeSnapLines()
        self._stretchBody = {
            'net': netItem, 'p1': p1, 'p2': p2, 'horizontal': horizontal,
            'width': netItem.width, 'snapLines': netItem._netSnapLines,
            'delta': QPoint(0, 0)}
        self.removeItem(netItem)

        # Preview item for the sliding segment.
        self._stretchNet = snet.guideLine(p1, p2)
        self._stretchNet.inherit(netItem)
        self.addItem(self._stretchNet)

        cursor = (Qt.CursorShape.SizeVerCursor if horizontal
                  else Qt.CursorShape.SizeHorCursor)
        for view in self.views():
            view.setCursor(cursor)

        snapRect = self._ensureSnapPointRect()
        if snapRect.scene() is None:
            self.addItem(snapRect)
        snapRect.setPos(mousePos)
        snapRect.setVisible(True)
        return True

    def _updateBodyStretch(self, netEndPoint: QPoint) -> None:
        """Update the body-stretch preview: the grabbed segment slides
        perpendicular to its direction, attached guideLines follow."""
        body = self._stretchBody
        stretchNet = self._stretchNet
        if body is None or stretchNet is None:
            return
        if body['horizontal']:
            delta = QPoint(0, netEndPoint.y() - body['p1'].y())
        else:
            delta = QPoint(netEndPoint.x() - body['p1'].x(), 0)
        body['delta'] = delta
        stretchNet.draftLine = QLineF(body['p1'] + delta,
                                      body['p2'] + delta)
        for index, snapLinesSet in body['snapLines'].items():
            movedEnd = (body['p1'] if index == 0 else body['p2']) + delta
            for snapLine in list(snapLinesSet):
                snapLine.draftLine = QLineF(movedEnd, snapLine.line().p2())

    def _completeBodyStretch(self, releasePos: QPoint) -> None:
        """Commit a body stretch: recreate the slid segment and re-route the
        nets attached at both ends, captured as one undoable command."""
        body = self._stretchBody
        if body is None:
            return
        netItem = body['net']
        try:
            netEndPoint = self.findSnapPoint(releasePos, set())
            if body['horizontal']:
                delta = QPoint(0, netEndPoint.y() - body['p1'].y())
            else:
                delta = QPoint(netEndPoint.x() - body['p1'].x(), 0)

            removedNets = [netItem] + list(
                getattr(netItem, '_removedNets', []))
            if delta == QPoint(0, 0):
                # No movement: restore the originals as they were.
                for originalNet in removedNets:
                    self.addItem(originalNet)
                    self.itemsRefSet.add(originalNet)
                for snapLinesSet in body['snapLines'].values():
                    for snapLine in list(snapLinesSet):
                        if snapLine.scene() is not None:
                            self.removeItem(snapLine)
            else:
                netsBefore = self.findSceneNetsSet()
                newBody = snet.schematicNet(body['p1'] + delta,
                                            body['p2'] + delta)
                newBody.inherit(netItem)
                newBody.width = body['width']
                self.addItem(newBody)
                newSegments = [newBody]
                for index, snapLinesSet in body['snapLines'].items():
                    movedEnd = (body['p1'] if index == 0 else body['p2']) + delta
                    for snapLine in list(snapLinesSet):
                        if snapLine.scene() is None:
                            continue
                        farEnd = snapLine.line().p2().toPoint()
                        if farEnd != movedEnd:
                            for seg in self.addStretchWires(
                                    movedEnd, farEnd,
                                    snapLine.horizontalFirst):
                                seg.inherit(snapLine)
                                seg.width = snapLine.width
                                self.addItem(seg)
                                newSegments.append(seg)
                        self.removeItem(snapLine)
                for segment in newSegments:
                    if segment.scene() is not None:
                        self.mergeSplitNets(segment)
                if newBody.scene() is not None:
                    self._splitPiercedNets(*newBody.sceneEndPoints)
                netsAfter = self.findSceneNetsSet()
                allNewNets = list(netsAfter - netsBefore)
                consumedNets = list(netsBefore - netsAfter)
                undoCommand = us.addDeleteShapesUndo(
                    self, allNewNets, removedNets + consumedNets)
                self.undoStack.push(undoCommand)
        except Exception as e:
            self.logger.error(f"Error in _completeBodyStretch: {e}",
                              exc_info=True)
        finally:
            if self._stretchNet and self._stretchNet.scene() is not None:
                self.removeItem(self._stretchNet)
            self._stretchNet = None
            self._stretchBody = None
            self._ensureSnapPointRect().setVisible(False)
            for view in self.views():
                view.setCursor(Qt.CursorShape.ArrowCursor)

    def _handleStretchNet(self, netItem: snet.schematicNet, stretchEnd: str):
        match stretchEnd:
            case "p2":
                stretchNet = snet.schematicNet(netItem.sceneEndPoints[0],
                                              netItem.sceneEndPoints[1])
            case "p1":
                stretchNet = snet.schematicNet(netItem.sceneEndPoints[1],
                                              netItem.sceneEndPoints[0])
            case _:
                return
        self._stretchNet = stretchNet
        stretchNet.stretch = True
        stretchNet.mergeNetName(netItem)
        addDeleteStretchNetCommand = us.addDeleteShapeUndo(self, stretchNet,
                                                           netItem)
        self.undoStack.push(addDeleteStretchNetCommand)

    def generatePinNetMap(self, sceneSymbolSet: set[shp.schematicSymbol]):
        """
        For symbols in sceneSymbolSet, find which pin is connected to which net.
        Handles both single pins and bus connections.
        """
        for symbolItem in sceneSymbolSet:
            self.genSymbolPinNetMap(symbolItem)

    @staticmethod
    def _isEipGhost(item) -> bool:
        """True for items hosted by an edit-in-place ghost group — they
        render inside the parent scene but belong to the child cellview.
        Only direct group children carry ``_eipChild``, so walk the
        ``parentItem`` chain to catch nested pins/labels inside ghost
        symbols."""
        while item is not None:
            if getattr(item, "_eipChild", False):
                return True
            item = item.parentItem()
        return False

    def findSceneSymbolSet(self) -> set[shp.schematicSymbol]:
        """
        Find all the symbols on the scene as a set.
        """
        return {item for item in self.items() if
                isinstance(item, shp.schematicSymbol)
                and not self._isEipGhost(item)}

    def findSceneNetsSet(self) -> set[snet.schematicNet]:
        return {item for item in self.items() if
                isinstance(item, snet.schematicNet)
                and not self._isEipGhost(item)}

    def _filterBySelectModes(self, items: set) -> set:
        """Filter rubber-band selected items by the active selection filter."""
        if self.selectModes.selectAll:
            return items
        return {item for item in items if self._itemPassesFilter(item)}

    def _itemPassesFilter(self, item) -> bool:
        """Check if an item passes the current selection filter."""
        if self.selectModes.selectDevice and isinstance(
                item, (shp.schematicSymbol, shp.schematicGroup)):
            return True
        if self.selectModes.selectNet and isinstance(item, snet.schematicNet):
            return True
        if self.selectModes.selectPin and isinstance(item, shp.schematicPin):
            return True
        if self.selectModes.selectText and isinstance(item, shp.text):
            return True
        return False

    def findRectSymbolPin(self, rect: Union[QRect, QRectF]) -> set[shp.symbolPin]:
        pinsRectSet = {item for item in self.items(rect) if
                       isinstance(item, shp.symbolPin)
                       and not self._isEipGhost(item)}
        return pinsRectSet

    def findRectSchemPins(self, rect: Union[QRect, QRectF]) -> set[
        shp.schematicPin]:
        pinsRectSet = {item for item in self.items(rect) if
                       isinstance(item, shp.schematicPin)
                       and not self._isEipGhost(item)}
        return pinsRectSet

    def findSceneSchemPinsSet(self) -> set[shp.schematicPin]:
        pinsSceneSet = {item for item in self.items() if
                        isinstance(item, shp.schematicPin)
                        and not self._isEipGhost(item)}
        if pinsSceneSet:  # check pinsSceneSet is empty
            return pinsSceneSet
        else:
            return set()

    def addStretchWires(self, start: QPoint, end: QPoint,
                        horizontalFirst: Optional[bool] = None) -> List[
        "snet.schematicNet"]:
        """
        Add wires between two points. Diagonal displacements produce a
        single-bend L route whose first leg follows the original wire's
        direction (``horizontalFirst``), like Virtuoso's stretch; when the
        direction is unknown the dominant delta wins.

        Args:
            start (QPoint): The starting point of the wire.
            end (QPoint): The ending point of the wire.
            horizontalFirst: True for a horizontal-then-vertical route,
                False for vertical-then-horizontal, None to pick by the
                dominant delta.

        Returns:
            List[snet.schematicNet]: A list of schematic net objects representing the wires.
        """
        try:
            if start == end:
                self.logger.warning(
                    "Start and end points are the same. No wire added.")
                return []

            if start.y() == end.y() or start.x() == end.x():
                # Horizontal or vertical line
                return [snet.schematicNet(start, end)]

            if horizontalFirst is None:
                horizontalFirst = (abs(end.x() - start.x())
                                   >= abs(end.y() - start.y()))
            corner = (QPoint(end.x(), start.y()) if horizontalFirst
                      else QPoint(start.x(), end.y()))

            return [snet.schematicNet(segStart, segEnd)
                    for segStart, segEnd in ((start, corner), (corner, end))
                    if segStart != segEnd]

        except Exception as e:
            self.logger.error(f"Error in addStretchWires: {e}", exc_info=True)
            return []

    def addPin(self, pos: QPoint) -> Optional[shp.schematicPin]:
        try:
            pin = shp.schematicPin(pos, self.pinName, self.pinDir, self.pinType)
            pin.netExpr = self.pinExpr
            self.addUndoStack(pin)
            return pin
        except Exception as e:
            self.logger.error(f"Pin add error: {e}")
            return None

    def addNote(self, pos: QPoint, textTuple: Tuple) -> shp.text:
        """
        Changed the method name not to clash with qgraphicsscene addText method.
        """
        text = shp.text(pos, *textTuple)
        self.addUndoStack(text)
        return text

    def drawInstance(self, instanceTuple: ddef.viewNameTuple, pos: QPoint):
        """
        Add an instance of a symbol to the scene.
        """
        instance = self.instSymbol(instanceTuple, pos)
        if instance:  # Add check for None
            self.addUndoStack(instance)
            return instance
        else:
            return None

    def _allocInstanceName(self, used: Optional[set] = None) -> tuple[int, str]:
        """Allocate a unique ``I<n>`` counter/name pair, skipping instance
        names already present on the scene (manually renamed or pasted
        instances included).  ``used`` may carry extra names — e.g. several
        symbols pasted at once aren't in the scene yet — and is updated with
        the allocated name."""
        if used is None:
            used = {item.instanceName for item in self.items()
                    if isinstance(item, shp.schematicSymbol)
                    and not self._isEipGhost(item)}
        self.instanceCounter += 1
        while f"I{self.instanceCounter}" in used:
            self.instanceCounter += 1
        name = f"I{self.instanceCounter}"
        used.add(name)
        return self.instanceCounter, name

    def instSymbol(self, instanceTuple: ddef.viewNameTuple, pos: QPoint,
                   allocateName: bool = True):
        viewItem = libm.findViewItem(self.appMainW.libraryModel,
                                     instanceTuple.libraryName,
                                     instanceTuple.cellName,
                                     instanceTuple.viewName, )
        if viewItem is None:
            self.logger.error(
                f"Symbol not found in library: "
                f"{instanceTuple.libraryName}/{instanceTuple.cellName}/"
                f"{instanceTuple.viewName}")
            return None
        viewPath = viewItem.viewPath
        try:
            # Use FileCache with mtime invalidation
            items = self._symbolCache.get_json(viewPath)
            if items is None:
                self.logger.error(f"Cannot load symbol file: {viewPath}")
                return
            try:
                items, compatibility = sv.prepare_design_data(
                    items, "symbol", str(viewPath))
            except sv.DesignFileValidationError as error:
                self.logger.error(
                    f"Incompatible symbol file {viewPath}: "
                    f"{'; '.join(error.errors or [str(error)])}")
                return None
            if compatibility.migrated:
                self.logger.info(
                    f"Migrated symbol schema {compatibility.sourceVersion} "
                    f"to {compatibility.targetVersion}: {viewPath}")

            # Use comprehensions for better performance
            itemAttributes = {item["nam"]: item["def"] for item in items[2:] if
                              item["type"] == "attr"}

            itemShapes = [lj.symbolItems(self).create(item) for item in items[2:]
                          if item["type"] != "attr"]
            symbolInstance = shp.schematicSymbol(itemShapes, itemAttributes)
            cellItem = viewItem.parent()
            libItem = cellItem.parent() if cellItem is not None else None
            # Position the instance. Use setPos() rather than a raw ``pos``
            # attribute: assigning ``symbolInstance.pos = ...`` would shadow the
            # inherited QGraphicsItem.pos() method with a QPoint, breaking every
            # later ``item.pos()`` call (e.g. move-group setup in editorScene).
            symbolInstance.setPos(pos)

            # A detached preview must not consume an I<n> number.  It still
            # receives stable identity fields so predefined labels and PDK
            # callbacks evaluate exactly as they do for a placed instance.
            if allocateName:
                counter, instanceName = self._allocInstanceName()
            else:
                counter, instanceName = 0, "I0"
            instanceProperties = {"counter": counter,
                                  "instanceName": instanceName,
                                  "libraryName": getattr(libItem, "libraryName",
                                                         ""),
                                  "cellName": getattr(cellItem, "cellName", ""),
                                  "viewName": viewItem.viewName, }

            for prop, value in instanceProperties.items():
                setattr(symbolInstance, prop, value)
            self._resolveInstanceLabels(symbolInstance)

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

    def _fixClipboardShapes(self, shapes: list) -> None:
        """Allocate fresh instance names, including grouped mosaic members."""
        usedNames = {item.instanceName for item in self.items()
                     if isinstance(item, shp.schematicSymbol)
                     and not self._isEipGhost(item)}
        stack = list(shapes)
        while stack:
            shape = stack.pop()
            if isinstance(shape, shp.schematicGroup):
                stack.extend(shape.symbols)
            elif isinstance(shape, shp.schematicSymbol):
                counter, name = self._allocInstanceName(usedNames)
                shape.instanceName = name
                shape.counter = counter
                [label.labelDefs() for label in shape.labels.values()]

    def saveSchematic(self, file: pathlib.Path, markClean: bool = True) -> bool:
        """
        Save the schematic to a file with optimized memory usage and error handling.

        Args:
            file (pathlib.Path): The file path to save the schematic to.
            markClean (bool): Clear the undo stack after a real save; autosave
                passes False so the undo history is preserved.

        Raises:
            IOError: If there are file operation errors
            JSONEncodeError: If there are JSON serialization errors
        """
        tempFile: Optional[pathlib.Path] = None
        try:
            self.cleanUpNets()
            self.itemsRefSet = set(self.items())
            # Ensure parentW directory exists
            file.parent.mkdir(parents=True, exist_ok=True)

            # Create temporary file in the same directory
            tempFile = file.with_suffix(".tmp")
            # Write to temporary file first
            with self.measureDuration():
                with tempFile.open(mode="w", buffering=8192) as f:
                    # Start array
                    f.write("[\n")

                    header_items = [sv.make_view_header("schematic"), {
                        "snapGrid": (self.majorGrid, self.snapGrid),
                        "snapConnectDistance": self.snapConnectDistance}, ]
                    json.dump(header_items[0], f)
                    f.write(",\n")
                    json.dump(header_items[1], f)
                    topLevelItems = filter(
                        lambda item: item.parentItem() is None
                        and isinstance(item, self.SCHEMATIC_SHAPES)
                        and not self._isEipGhost(item),
                        self.items())
                    # Stream items
                    for item in list(topLevelItems):
                        f.write(",\n")
                        try:
                            json.dump(item, f, cls=schenc.schematicEncoder)
                        except Exception as json_err:
                            self.logger.error(
                                f"Failed to serialize item: {str(json_err)}")
                            return False

                    # Persist check markers so the error browser survives
                    # save/load without re-running checks.
                    for violation in self.lastCheckViolations:
                        f.write(",\n")
                        json.dump(self._violationToRecord(violation), f)

                    # Close array
                    f.write("\n]")

                    # Ensure all data is written to disk
                    f.flush()
                    os.fsync(f.fileno())

                # Atomic file replacement
                tempFile.replace(file)

                self.logger.info(
                    f"Saved schematic to {self.editorWindow.cellName}:"
                    f"{self.editorWindow.viewName}")
                lj.schematicItems._load_sym_json.cache_clear()
                if markClean:
                    self.undoStack.clear()
                return True
        except IOError as io_err:
            self.logger.error(f"IO Error while saving schematic: {str(io_err)}")
            return False
        except Exception as e:
            self.logger.error(
                f"Unexpected error while saving schematic: {str(e)}")
            # Clean up temporary file if it exists
            if tempFile is not None and tempFile.exists():
                tempFile.unlink()
            return False
        finally:
            if tempFile is not None and tempFile.exists():
                tempFile.unlink()

    @staticmethod
    def findEditorTypeString(editorWindow):
        """
        This function returns the type of the parentW editor as a string.
        The type of the parentW editor is determined by finding the last dot in the
        string representation of the type of the parentW editor and returning the
        string after the last dot. If there is no dot in the string representation
        of the type of the parentW editor, the entire string is returned.
        """
        index: int = str(type(editorWindow)).rfind(".")
        if index == -1:
            return str(type(editorWindow))
        else:
            return str(type(editorWindow))[index + 1: -2]

    def loadDesign(self, filePathObj: pathlib.Path) -> bool:
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
            with filePathObj.open("rb") as file:
                decodedData = orjson.loads(file.read())
            try:
                decodedData, compatibility = sv.prepare_design_data(
                    decodedData, "schematic", str(filePathObj))
            except sv.DesignFileValidationError as error:
                for err in error.errors or [str(error)]:
                    self.logger.error(
                        f"Schematic compatibility error in "
                        f"'{filePathObj.name}': {err}")
                return False
            if compatibility.migrated:
                self.logger.info(
                    f"Migrated schematic schema {compatibility.sourceVersion} "
                    f"to {compatibility.targetVersion}")
            with self.measureDuration():
                viewDict, gridSettings, *itemData = decodedData

                self._restoreMarkers(itemData)
                if gridSettings and gridSettings.get("snapGrid"):
                    self.editorWindow.configureGridSettings(
                        decodedData[1].get("snapGrid",
                                           (self.majorGrid, self.snapGrid)))
                snapConnectDistance = decodedData[1].get("snapConnectDistance")
                if snapConnectDistance is not None:
                    self.editorWindow.snapConnectDistance = snapConnectDistance
                    self.snapConnectDistance = snapConnectDistance
                self.blockSignals(True)
                try:
                    self.createSchematicItems(itemData)
                finally:
                    self.blockSignals(False)
                # Semantic connectivity check on the decoded records via the
                # shared engine — same diagnostics aiTerminal/importers get.
                self._logRecordDiagnostics(itemData)
            self.itemsRefSet = set(self.items())
            return True

        except (orjson.JSONDecodeError, FileNotFoundError) as e:
            self.logger.error(f"File error while loading schematic: {e}")
            return False
        except KeyError as e:
            self.logger.error(f"Invalid schematic format - missing key: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error loading schematic: {e}")
            return False

    def _logRecordDiagnostics(self, itemData: List[Dict]) -> None:
        """Run conn.checkRecords on loaded records and log the findings.

        Errors (name conflicts, malformed records) are logged individually;
        warnings (floating pins, dangling ends) are summarized to keep the
        log readable on in-progress schematics.
        """
        try:
            _result, diagnostics = conn.checkRecords(
                itemData,
                pinLocator=lj.makeSymbolPinLocator(self.libraryDict),
                endpointTol=1.0,
                bodyTol=max(self.snapDistance // 2, 2),
                portTol=self.snapDistance)
        except Exception as e:
            self.logger.warning(f"Connectivity record check skipped: {e}")
            return
        warnings = []
        for diag in diagnostics:
            if diag.severity == "error":
                self.logger.error(diag.message)
            else:
                warnings.append(diag.message)
        if warnings:
            self.logger.warning(
                f"Connectivity check: {len(warnings)} warning(s) in "
                f"schematic records. First: {warnings[0]}")

    def createSchematicItems(self, itemsList: List[Dict]):
        factory = lj.schematicItems(self)
        for itemDict in itemsList:
            itemShape = factory.create(itemDict)
            if (isinstance(itemShape,
                           shp.schematicSymbol) and itemShape.counter > self.instanceCounter):
                self.instanceCounter = itemShape.counter + 1

            if itemShape is not None:
                self.addItem(itemShape)

    def viewObjProperties(self):
        """
        Display the properties of the selected object.
        """
        try:
            selectedItems = [item for item in self.selectedItems() if
                             item.parentItem() is None]
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
                        parentItem = item.parentItem()
                        if isinstance(parentItem, snet.schematicNet):
                            self.setNetProperties(parentItem)
        except Exception as e:
            self.logger.error(e)

    def setInstanceProperties(self, item: shp.schematicSymbol):
        # Get available views for the instance's cell
        availableViews = []
        try:
            libItem = libm.getLibItem(self.editorWindow.libraryView.libraryModel, 
                                      item.libraryName)
            if libItem:
                cellItem = libm.getCellItem(libItem, item.cellName)
                if cellItem:
                    availableViews = [cellItem.child(row).viewName 
                                    for row in range(cellItem.rowCount())]
        except Exception as e:
            self.logger.warning(f"Failed to get available views for {item.cellName}: {e}")
        
        dlg = pdlg.instanceProperties(self.editorWindow, availableViews=availableViews)
        dlg.libNameEdit.setText(item.libraryName)
        dlg.cellNameEdit.setText(item.cellName)
        dlg.cellNameEdit.setEnabled(True)

        # Set the current view name in the combo box
        if item.viewName in availableViews:
            dlg.viewNameEdit.setCurrentText(item.viewName)
        else:
            dlg.viewNameEdit.addItem(item.viewName)
            dlg.viewNameEdit.setCurrentText(item.viewName)
        dlg.instNameEdit.setText(item.instanceName)
        location = (item.scenePos() - self.origin).toTuple()
        dlg.xLocationEdit.setText(str(location[0]))
        dlg.yLocationEdit.setText(str(location[1]))
        dlg.angleEdit.setText(str(item.angle))
        dlg.netSetEdit.setText(conn.formatNetSet(item.netSet))

        # Build the label rows in a stable, deterministic order and remember
        # the widgets so that Apply/OK can share the same read-back path.
        self._buildInstanceLabelRows(dlg, item)
        self._connectInstanceLabelPreview(dlg, item)
        self._applyInstanceProperties(dlg, item)

        # now list instance attributes; the reserved paramDefs attr is
        # authored via the Parameters table, not as raw JSON here
        for counter, name in enumerate(
                k for k in item.symattrs.keys() if k != prm.PARAMDEFS_ATTR):
            dlg.instanceAttributesLayout.addWidget(edf.boldLabel(name, dlg),
                                                   counter, 0)
            labelNameEdit = edf.longLineEdit()
            labelNameEdit.setReadOnly(True)
            labelNameEdit.setText(item.symattrs.get(name))
            labelNameEdit.setToolTip(f"{name} attribute (Read Only)")
            dlg.instanceAttributesLayout.addWidget(labelNameEdit, counter, 1)

        # Apply recomputes pyLabels live without committing to the undo stack.
        dlg.applyButton.clicked.connect(
            lambda: self._applyInstanceProperties(dlg, item))

        if dlg.exec() == QDialog.DialogCode.Accepted:
            location = QPoint(int(float(dlg.xLocationEdit.text().strip())),
                              int(float(dlg.yLocationEdit.text().strip())), )
            newInstance = self._buildInstanceFromDialog(dlg, item, location)
            if newInstance:
                newInstance.setPos(self.snapToGrid(location - self.origin))
                newInstance.flipTuple = item.flipTuple
                self.undoStack.push(
                    us.addDeleteShapeUndo(self, newInstance, item))

    def _connectInstanceLabelPreview(self, dlg, item: shp.schematicSymbol):
        """Refresh callback labels as soon as an editable field changes."""
        timer = QTimer(dlg)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._applyInstanceProperties(dlg, item))
        dlg._labelPreviewTimer = timer

        def schedulePreview(*_args):
            timer.start(0)

        for row in dlg.labelRows:
            if not row["isEditable"]:
                continue
            valueEdit = row["valueEdit"]
            if hasattr(valueEdit, "toggled"):
                valueEdit.toggled.connect(schedulePreview)
            elif hasattr(valueEdit, "currentTextChanged"):
                valueEdit.currentTextChanged.connect(schedulePreview)
            else:
                valueEdit.textChanged.connect(schedulePreview)

    def _buildInstanceLabelRows(self, dlg, item: shp.schematicSymbol):
        """Populate the dialog from every persistent, non-predefined label."""
        rows, missingCarriers = self.instanceLabelRows(item)
        if missingCarriers:
            self.logger.warning(
                "%s has paramDefs without NLP label carriers: %s",
                item.instanceName, ", ".join(missingCarriers))
        dlg.labelRows = []
        # ParamDef display=False rows stay off the form; apply carries their
        # values over from the original instance via hiddenLabelNames.
        dlg.hiddenLabelNames = []
        rowIndex = 0
        section = None

        for sourceRow in rows:
            if not sourceRow.get("isVisible", True):
                dlg.hiddenLabelNames.append(sourceRow["labelName"])
                continue
            if sourceRow["section"] != section:
                section = sourceRow["section"]
                dlg.instanceLabelsLayout.addWidget(
                    edf.boldLabel(section, dlg), rowIndex, 0, 1, 3)
                rowIndex += 1
            label = item.labels[sourceRow["labelName"]]
            dlg.instanceLabelsLayout.addWidget(
                edf.boldLabel(label.labelName.lstrip("@"), dlg), rowIndex, 0)
            pdef = sourceRow["paramDef"]
            if pdef is not None:
                valueWidget, getValue, setValue = pdlg.paramValueWidget(
                    pdef, str(label.labelValue), dlg)
            else:
                valueWidget = edf.longLineEdit()
                valueWidget.setText(str(label.labelValue))
                getValue = valueWidget.text
                setValue = valueWidget.setText
            if not sourceRow["isEditable"]:
                valueWidget.setReadOnly(True)
                valueWidget.setToolTip("Computed or literal label (Read Only)")
            dlg.instanceLabelsLayout.addWidget(valueWidget, rowIndex, 1)
            visibleCombo = QComboBox(dlg)
            visibleCombo.setInsertPolicy(QComboBox.NoInsert)
            visibleCombo.addItems(["True", "False"])
            visibleCombo.setCurrentIndex(0 if label.labelVisible else 1)
            dlg.instanceLabelsLayout.addWidget(visibleCombo, rowIndex, 2)
            dlg.labelRows.append({
                **sourceRow,
                "valueEdit": valueWidget,
                "getValue": getValue,
                "setValue": setValue,
                "visibleCombo": visibleCombo,
            })
            rowIndex += 1

    def _applyDialogLabelValues(self, instance, dlg, item: shp.schematicSymbol,
                                validate: bool) -> None:
        """Copy editable dialog rows to ``instance`` then resolve dependents."""
        siblingValues = {
            name: str(label.labelValue) for name, label in item.labels.items()
        }
        siblingValues.update({
            row["labelName"]: row["getValue"]() for row in dlg.labelRows
            if row.get("isEditable", not row.get("isPyLabel", False))
        })
        for row in dlg.labelRows:
            label = instance.labels.get(row["labelName"])
            if label is None:
                continue
            if not row.get("isEditable", not row.get("isPyLabel", False)):
                # Computed/literal values are immutable here, but visibility
                # remains an instance-level property for every label type.
                label.labelVisible = row["visibleCombo"].currentText() == "True"
                continue
            newValue = row["getValue"]()
            pdef = row.get("paramDef")
            if validate and pdef is not None:
                errors = prm.validateValue(pdef, newValue, siblingValues)
                if errors:
                    self.logger.warning(
                        f"{instance.instanceName} {row['labelName']}: "
                        f"{'; '.join(errors)}")
                    oldLabel = item.labels.get(row["labelName"])
                    newValue = str(oldLabel.labelValue) if oldLabel else str(label.labelValue)
                else:
                    newValue = prm.normalizeValue(pdef, newValue)
            label.labelValue = newValue
            label.labelVisible = row["visibleCombo"].currentText() == "True"

        # Old hand-built dialog stubs can still request hidden-label carryover.
        for name in getattr(dlg, "hiddenLabelNames", ()):
            oldLabel = item.labels.get(name)
            newLabel = instance.labels.get(name)
            if oldLabel is not None and newLabel is not None:
                newLabel.labelValue = oldLabel.labelValue
                newLabel.labelVisible = oldLabel.labelVisible
        self._resolveInstanceLabels(instance)

    def _buildInstanceFromDialog(self, dlg, item: shp.schematicSymbol,
                                 location: QPoint):
        """Create the committed replacement instance from dialog state."""
        libraryName = dlg.libNameEdit.text().strip()
        cellName = dlg.cellNameEdit.text().strip()
        netlistViewName = dlg.viewNameEdit.currentText().strip()
        symbolViewTuple = ddef.viewNameTuple(libraryName, cellName, "symbol")
        newInstance = self.instSymbol(symbolViewTuple, location)
        if newInstance is None:
            return None
        newInstance.viewName = netlistViewName
        newInstance.instanceName = dlg.instNameEdit.text().strip()
        newInstance.angle = float(dlg.angleEdit.text().strip())
        newInstance.counter = item.counter
        newInstance.netSet = dlg.netSetEdit.text().strip()
        self._applyDialogLabelValues(newInstance, dlg, item, validate=True)
        return newInstance

    def _previewInstanceFromDialog(self, dlg, item: shp.schematicSymbol,
                                   location: QPoint):
        """Build a detached, non-allocating instance for live callbacks."""
        symbolViewTuple = ddef.viewNameTuple(item.libraryName, item.cellName,
                                             "symbol")
        preview = self.instSymbol(symbolViewTuple, location, allocateName=False)
        if preview is None:
            return None
        preview.viewName = dlg.viewNameEdit.currentText().strip()
        preview.instanceName = dlg.instNameEdit.text().strip()
        preview.counter = item.counter
        self._applyDialogLabelValues(preview, dlg, item, validate=False)
        return preview

    def _applyInstanceProperties(self, dlg, item: shp.schematicSymbol):
        """Refresh PyLabels immediately without mutating scene or undo state."""
        try:
            location = QPoint(int(float(dlg.xLocationEdit.text().strip())),
                              int(float(dlg.yLocationEdit.text().strip())))
        except ValueError:
            location = QPoint(0, 0)
        previewInstance = self._previewInstanceFromDialog(dlg, item, location)
        if previewInstance is None:
            return
        for row in dlg.labelRows:
            if not row.get("isPyLabel", False):
                continue
            label = previewInstance.labels.get(row["labelName"])
            if label is not None:
                row["setValue"](str(label.labelValue))

    def setNetProperties(self, netItem: snet.schematicNet):
        dlg = pdlg.netProperties(self.editorWindow)
        dlg.netStartPointEditX.setText(
            str(round(netItem.mapToScene(netItem.draftLine.p1()).x())))
        dlg.netStartPointEditY.setText(
            str(round(netItem.mapToScene(netItem.draftLine.p1()).y())))
        dlg.netEndPointEditX.setText(
            str(round(netItem.mapToScene(netItem.draftLine.p2()).x())))
        dlg.netEndPointEditY.setText(
            str(round(netItem.mapToScene(netItem.draftLine.p2()).y())))
        dlg.netNameEdit.setText(netItem.name)
        dlg.netExprEdit.setText(netItem.netExpr)
        dlg.widthButtonGroup.button(netItem.width).setChecked(True)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            netName = dlg.netNameEdit.text().strip()
            netStartX = float(dlg.netStartPointEditX.text())
            netStartY = float(dlg.netStartPointEditY.text())
            netStart = self.snapToGrid(QPoint(netStartX, netStartY))
            netEndX = float(dlg.netEndPointEditX.text())
            netEndY = float(dlg.netEndPointEditY.text())
            netEnd = self.snapToGrid(QPoint(netEndX, netEndY))
            newNet = snet.schematicNet(netStart, netEnd, netItem.mode)
            newNet.nameStrength = snet.netNameStrengthEnum.SET
            if self.isValidNetName(netName):
                newNet.name = netName
            else:
                self.logger.warning(f"{netName} is malformed, please correct.")
                newNet.name = netItem.name
            newNet.width = dlg.widthButtonGroup.checkedId()
            netExpr = dlg.netExprEdit.text().strip()
            if netExpr and conn.parseNetExpr(netExpr) is None:
                self.logger.warning(
                    f"Malformed net expression {netExpr!r}; ignored.")
            else:
                newNet.netExpr = netExpr
            self.undoStack.push(us.addDeleteShapeUndo(self, newNet, netItem))

    def setTextProperties(self, item):
        dlg = pdlg.noteTextEdit(self.editorWindow)
        dlg.plainTextEdit.setText(item.textContent)
        dlg.familyCB.setCurrentText(item.fontFamily)
        dlg.fontStyleCB.setCurrentText(item.fontStyle)
        dlg.fontsizeCB.setCurrentText(item.textHeight)
        dlg.textAlignmCB.setCurrentText(item.textAlignment)
        dlg.textOrientCB.setCurrentText(item.textOrient)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            # item.prepareGeometryChange()
            start = item.mapToScene(item.start)
            newText = shp.text(start, dlg.plainTextEdit.toPlainText(),
                               dlg.familyCB.currentText(),
                               dlg.fontStyleCB.currentText(),
                               dlg.fontsizeCB.currentText(),
                               dlg.textAlignmCB.currentText(),
                               dlg.textOrientCB.currentText(), )
            self.rotateAnItem(start, newText, int(float(item.textOrient[1:])))
            self.undoStack.push(us.addDeleteShapeUndo(self, newText, item))
        return item

    def setSchematicPinProperties(self, item: shp.schematicPin):
        dlg = pdlg.schematicPinPropertiesDialog(self.editorWindow)
        dlg.pinName.setText(item.pinName)
        dlg.pinDir.setCurrentText(item.pinDir)
        dlg.pinType.setCurrentText(item.pinType)
        dlg.netExprEdit.setText(item.netExpr)
        dlg.angleEdit.setText(str(item.angle))
        dlg.xlocationEdit.setText(str(item.mapToScene(item.start).x()))
        dlg.ylocationEdit.setText(str(item.mapToScene(item.start).y()))
        if dlg.exec() == QDialog.DialogCode.Accepted:
            pinName = dlg.pinName.text().strip()
            pinDir = dlg.pinDir.currentText()
            pinType = dlg.pinType.currentText()
            itemStartPos = QPoint(int(float(dlg.xlocationEdit.text().strip())),
                                  int(float(dlg.ylocationEdit.text().strip())), )
            start = self.snapToGrid(itemStartPos - self.origin)
            angle = float(dlg.angleEdit.text().strip())
            newPin = shp.schematicPin(QPoint(0, 0), pinName, pinDir, pinType)
            newPin.setPos(start)
            newPin.angle = angle
            netExpr = dlg.netExprEdit.text().strip()
            if netExpr and conn.parseNetExpr(netExpr) is None:
                self.logger.warning(
                    f"Malformed net expression {netExpr!r}; ignored.")
            else:
                newPin.netExpr = netExpr
            self.undoStack.push(us.addDeleteShapeUndo(self, newPin, item))

    def hilightNets(self):
        """
        Show the connections the selected items.
        """
        try:
            self.highlightNets = bool(
                self.editorWindow.hilightNetAction.isChecked())
        except Exception as e:
            self.logger.error(e)

    def probeNets(self):
        """Toggle probe mode on/off."""
        try:
            self.probeMode = bool(
                self.editorWindow.probeNetAction.isChecked())
            if self.probeMode:
                self.removeProbeMode_ = False
                self.editorWindow.removeProbeNetAction.setChecked(False)
            else:
                self.clearProbe()
        except Exception as e:
            self.logger.error(e)

    def removeProbeMode(self):
        """Toggle remove-probe mode on/off."""
        try:
            self.removeProbeMode_ = bool(
                self.editorWindow.removeProbeNetAction.isChecked())
            if self.removeProbeMode_:
                self.probeMode = False
                self.editorWindow.probeNetAction.setChecked(False)
            if not self.removeProbeMode_:
                self.clearProbe()
        except Exception as e:
            self.logger.error(e)

    def clearProbe(self):
        """Clear all probes and reset probe state. Also clears probes
        from related editors in the hierarchy."""
        from PySide6.QtWidgets import QApplication
        # Clear local probes
        for netSet in self._probedNets.values():
            for netItem in netSet:
                if shiboken6.isValid(netItem) and netItem.scene():
                    netItem.unprobe()
        self._probedNets.clear()
        self._probeColorMap.clear()
        self.probePinNames.clear()
        # Clear probes from related editors
        editor = self.editorWindow
        openWindows = {w for w in QApplication.topLevelWidgets()
                       if hasattr(w, 'centralW') and hasattr(w.centralW, 'scene')}
        relatedEditors = set()
        editor.findRelated(editor, relatedEditors, openWindows)
        for w in relatedEditors:
            if w == editor:
                continue
            relatedScene = w.centralW.scene
            if not hasattr(relatedScene, '_probedNets'):
                continue
            if relatedScene._probedNets:
                for netSet in relatedScene._probedNets.values():
                    for netItem in netSet:
                        if shiboken6.isValid(netItem) and netItem.scene():
                            netItem.unprobe()
                relatedScene._probedNets.clear()
                relatedScene._probeColorMap.clear()
                relatedScene.probePinNames.clear()

    def reapplyProbesAfterReload(self):
        """Reapply probes after a scene reload. The reload destroys all
        QGraphicsItems, so _probedNets holds stale references. Rebuild
        from the surviving _probeColorMap (net name → color index)."""
        if not self._probeColorMap:
            return
        savedProbes = dict(self._probeColorMap)
        self._probedNets.clear()
        self._probeColorMap.clear()
        self.probePinNames.clear()
        for netName, colorIndex in savedProbes.items():
            self.addProbe(netName, propagate=False, colorIndex=colorIndex)

    def addProbe(self, netName: str, propagate: bool = True,
                 colorIndex: Optional[int] = None):
        """Add a probe for the given net name. Probes all matching nets
        with a cycling color pen. When propagate is True, also propagates
        the probe to all related editors in the hierarchy."""
        if not netName:
            return
        if netName in self._probedNets:
            return
        if colorIndex is None:
            colorIndex = self._probeColorIndex
            self._probeColorIndex = (self._probeColorIndex + 1) % len(
                schlyr.probePens)
        probePen = schlyr.probePens[colorIndex % len(schlyr.probePens)]
        self.nameSceneNets()
        sceneNetsSet = self.findSceneNetsSet()
        matchingNets = {
            net for net in sceneNetsSet
            if snet.schematicNet._namesMatch(net.name, netName)
        }
        self._probedNets[netName] = matchingNets
        self._probeColorMap[netName] = colorIndex
        for netItem in matchingNets:
            netItem.probe(probePen)
        if propagate:
            self._propagateProbeHierarchy(netName, {self.editorWindow},
                                          colorIndex)

    def removeProbe(self, netName: str, propagate: bool = True):
        """Remove a specific probe by net name. When propagate is True,
        also removes corresponding probes from related editors."""
        netSet = self._probedNets.pop(netName, None)
        self._probeColorMap.pop(netName, None)
        if netSet:
            for netItem in netSet:
                if shiboken6.isValid(netItem) and netItem.scene():
                    netItem.unprobe()
        if propagate:
            self._propagateRemoveProbe(netName, {self.editorWindow})

    def _propagateProbeHierarchy(self, netName: str, visited: set,
                                 colorIndex: int = 0):
        """Propagate a probe to all related editors in the hierarchy."""
        editor = self.editorWindow
        # Propagate up to parent
        if editor.parentEditor and editor.parentEditor not in visited:
            parentScene = editor.parentEditor.centralW.scene
            if hasattr(parentScene, 'addProbe'):
                visited.add(editor.parentEditor)
                parentNetNames = self._mapNetToParent(netName, editor)
                for parentNetName in parentNetNames:
                    parentScene.addProbe(parentNetName, propagate=False,
                                         colorIndex=colorIndex)
                    parentScene._propagateProbeHierarchy(
                        parentNetName, visited, colorIndex)
                    parentScene._propagateProbeDown(
                        parentNetName, visited, colorIndex)

        # Propagate down to children
        self._propagateProbeDown(netName, visited, colorIndex)

    def _propagateProbeDown(self, netName: str, visited: set,
                             colorIndex: int = 0):
        """Propagate probe down to child editors by finding which pins of
        the parent symbol are connected to the probed net, then probing
        the matching schematic pins in the child scene."""
        from PySide6.QtWidgets import QApplication
        editor = self.editorWindow
        self.nameSceneNets()
        for w in QApplication.topLevelWidgets():
            if not hasattr(w, 'centralW') or not hasattr(w.centralW, 'scene'):
                continue
            if w in visited:
                continue
            if not hasattr(w, 'parentEditor') or w.parentEditor != editor:
                continue
            if not hasattr(w, 'parentObj'):
                continue
            visited.add(w)
            childScene = w.centralW.scene
            if not hasattr(childScene, 'probeMode'):
                continue
            parentSymbol = schematicScene._liveParentSymbol(w, self)
            if parentSymbol is None or not hasattr(parentSymbol, 'pins'):
                continue
            # Find which pins of the parent symbol are connected to the
            # probed net, using the connectivity engine's pin->group map.
            childPinNames = set()
            self.genSymbolPinNetMap(parentSymbol)
            for pinName, pinNetName in parentSymbol.pinNetMap.items():
                if (pinNetName and not pinNetName.startswith("dnet")
                        and snet.schematicNet._namesMatch(pinNetName,
                                                          netName)):
                    childPinNames.add(pinName)
            if childPinNames:
                childScene.probePinNames |= childPinNames
                childScene.applyProbe(colorIndex)
                # Continue propagating from child for the current probe only
                for childProbeName in list(childScene._probedNets.keys()):
                    if snet.schematicNet._namesMatch(childProbeName, netName):
                        childScene._propagateProbeDown(
                            childProbeName, visited, colorIndex)

    @staticmethod
    def _liveParentSymbol(editor, parentScene):
        """Return the live parent-instance item for a descended editor.

        ``editor.parentObj`` is captured at descend time; a parent scene
        reload destroys the scene items and leaves a deleted C++ wrapper
        behind. When the stored reference is stale or detached, re-resolve
        the instance by name (a stale wrapper's Python attrs survive, and
        the child scene's ``hierarchyTrail`` ends with the instance name)
        and refresh ``editor.parentObj``.
        """
        parentSymbol = getattr(editor, "parentObj", None)
        try:
            if (parentSymbol is not None
                    and parentSymbol.scene() is parentScene):
                return parentSymbol
        except RuntimeError:
            pass  # stale wrapper; re-resolve below
        instName = ""
        if parentSymbol is not None:
            try:
                instName = parentSymbol.instanceName or ""
            except RuntimeError:
                instName = ""
        if not instName:
            childScene = getattr(getattr(editor, "centralW", None), "scene",
                                 None)
            trail = getattr(childScene, "hierarchyTrail", "") or ""
            instName = trail.rstrip(".").rsplit(".", 1)[-1]
        if not instName:
            return None
        parentSymbol = next(
            (item for item in parentScene.findSceneSymbolSet()
             if item.instanceName == instName), None)
        if parentSymbol is not None:
            editor.parentObj = parentSymbol
        return parentSymbol

    def _mapNetToParent(self, netName: str, editor) -> set:
        """Map a net name in the current scene to net name(s) in the parent
        scene by finding schematic pins connected to the probed net, then
        finding nets connected to the matching pins on the parent symbol."""
        parentNetNames = set()
        self.nameSceneNets()
        # Find child schematic pins connected to the probed net via the
        # connectivity engine's port->group map.
        result = self.connectivity
        portIdByItem = self._connectivityPortIdByItem
        matchingPinNames = set()
        for pinItem in self.findSceneSchemPinsSet():
            portId = portIdByItem.get(pinItem)
            groupIndex = (result.portGroup.get(portId)
                          if portId is not None else None)
            if (groupIndex is not None and snet.schematicNet._namesMatch(
                    result.groups[groupIndex].name, netName)):
                matchingPinNames.add(pinItem.pinName)

        if not matchingPinNames or not editor.parentEditor:
            return parentNetNames

        # Find nets connected to matching pins on the parent symbol
        parentScene = editor.parentEditor.centralW.scene
        parentScene.nameSceneNets()
        parentSymbol = schematicScene._liveParentSymbol(editor, parentScene)
        if parentSymbol is None or not hasattr(parentSymbol, 'pins'):
            return parentNetNames

        parentScene.genSymbolPinNetMap(parentSymbol)
        for pinName, pinNetName in parentSymbol.pinNetMap.items():
            if pinName in matchingPinNames and not pinNetName.startswith(
                    "dnet"):
                parentNetNames.add(pinNetName)
        return parentNetNames

    def _propagateRemoveProbe(self, netName: str, visited: set):
        """Remove corresponding probes from related editors."""
        from PySide6.QtWidgets import QApplication
        editor = self.editorWindow
        # Remove from parent
        if editor.parentEditor and editor.parentEditor not in visited:
            parentScene = editor.parentEditor.centralW.scene
            if hasattr(parentScene, '_probedNets'):
                visited.add(editor.parentEditor)
                parentNetNames = self._mapNetToParent(netName, editor)
                for parentNetName in parentNetNames:
                    parentScene.removeProbe(parentNetName, propagate=False)
                    parentScene._propagateRemoveProbe(parentNetName, visited)
        # Remove from children
        for w in QApplication.topLevelWidgets():
            if not hasattr(w, 'centralW') or not hasattr(w.centralW, 'scene'):
                continue
            if w in visited:
                continue
            if not hasattr(w, 'parentEditor') or w.parentEditor != editor:
                continue
            visited.add(w)
            childScene = w.centralW.scene
            if not hasattr(childScene, '_probedNets'):
                continue
            # Remove all probes in child that match through pin mapping
            for childProbeName in list(childScene._probedNets.keys()):
                childScene.removeProbe(childProbeName, propagate=False)
                childScene._propagateRemoveProbe(childProbeName, visited)

    def applyProbe(self, colorIndex: int = 0):
        """Apply probe from parent pin names. Called after child scene is loaded."""
        if not self.probePinNames:
            return
        probePen = schlyr.probePens[colorIndex % len(schlyr.probePens)]
        self.nameSceneNets()
        sceneNetsSet = self.findSceneNetsSet()
        schemPinsSet = self.findSceneSchemPinsSet()

        result = self.connectivity
        portIdByItem = self._connectivityPortIdByItem
        for pinItem in schemPinsSet:
            if pinItem.pinName in self.probePinNames:
                portId = portIdByItem.get(pinItem)
                groupIndex = (result.portGroup.get(portId)
                              if portId is not None else None)
                if groupIndex is not None:
                    probeName = result.groups[groupIndex].name
                    if probeName in self._probedNets:
                        continue
                    matchingNets = {
                        net for net in sceneNetsSet
                        if snet.schematicNet._namesMatch(net.name, probeName)
                    }
                    self._probedNets[probeName] = matchingNets
                    for netItem in matchingNets:
                        netItem.probe(probePen)

    def goDownHier(self):
        """
        Go down the hierarchy, opening the selected view.
        """
        try:
            selectedSymbol = [item for item in self.selectedItems() if
                              isinstance(item, shp.schematicSymbol)][0]

            if isinstance(selectedSymbol, shp.schematicSymbol):
                dlg = fd.goDownHierDialogue(self.editorWindow)
                libItem = libm.getLibItem(
                    self.appMainW.libraryModel,
                    selectedSymbol.libraryName, )
                cellItem = libm.getCellItem(libItem, selectedSymbol.cellName)
                descendableTypes = {"schematic", "symbol",
                                    *libb.TEXT_VIEW_SUFFIXES}
                viewNames = [cellItem.child(i).text() for i in
                             range(cellItem.rowCount()) if
                             getattr(cellItem.child(i), "viewType",
                                     None) in descendableTypes]
                dlg.viewListCB.addItems(viewNames)
                if dlg.exec() == QDialog.DialogCode.Accepted:
                    selectedSymbol.setSelected(False)
                    self.saveSchematic(self.editorWindow.file)
                    viewItem = libm.getViewItem(
                        cellItem, dlg.viewListCB.currentText()
                    )
                    viewItemT = ddef.viewItemTuple(libItem, cellItem, viewItem)
                    openViewNameT = self.editorWindow.libraryView.openCellView(
                            viewItemT)

                    childWindow = self.editorWindow.appMainW.openViews.get(
                        openViewNameT)
                    if (childWindow is not None
                            and viewItem.viewType == "schematic"):
                        parentInstanceName = [labelItem.labelValue for labelItem in
                             selectedSymbol.labels.values() if
                             labelItem.labelType == "NLPLabel" and
                            labelItem.labelDefinition == "[@instName]"][0]
                        childWindow.centralW.scene.hierarchyTrail = (
                            f"{self.hierarchyTrail}{parentInstanceName}.")
                    if childWindow:
                        childWindow.parentEditor = self.editorWindow
                        childWindow.parentObj = selectedSymbol
                        childWindowType = self.findEditorTypeString(childWindow)

                        if childWindowType == "symbolEditor":
                            childWindow.symbolToolbar.addAction(
                                childWindow.goUpAction)
                            if dlg.buttonId == 2:
                                childWindow.centralW.scene.readOnly = True
                        elif childWindowType == "schematicEditor":
                            childWindow.schematicToolbar.addAction(
                                childWindow.goUpAction)
                            if dlg.buttonId == 2:
                                childWindow.centralW.scene.readOnly = True
                        elif hasattr(childWindow, "textEdit"):
                            if (hasattr(childWindow, "textToolbar")
                                    and hasattr(childWindow, "goUpAction")):
                                childWindow.textToolbar.addAction(
                                    childWindow.goUpAction)
                            if dlg.buttonId == 2:
                                childWindow.textEdit.setReadOnly(True)

                        # Propagate probes to child scene
                        if self.probeMode and self._probedNets:
                            childScene = getattr(
                                getattr(childWindow, "centralW", None),
                                "scene", None)
                            if hasattr(childScene, 'probePinNames'):
                                self._propagateProbeToChild(
                                    childScene, selectedSymbol)

        except IndexError:
            pass

    def _propagateProbeToChild(self, childScene, selectedSymbol):
        """Propagate all active probes to a child scene by finding which
        pins of the selected symbol are connected to each probed net and
        passing those pin names to the child scene. Each probe retains
        its own color."""
        self.nameSceneNets()
        if not hasattr(selectedSymbol, 'pins'):
            return
        # Build a map of pin name → connected net name for the symbol via
        # the connectivity engine's pin->group map.
        self.genSymbolPinNetMap(selectedSymbol)
        pinToNet = {pinName: netName for pinName, netName in
                    selectedSymbol.pinNetMap.items()
                    if netName and not netName.startswith("dnet")}
        # For each probed net, find matching pins and apply probe to child
        childScene.probeMode = True
        for idx, probedNetName in enumerate(self._probedNets):
            childPinNames = set()
            for pinName, netName in pinToNet.items():
                if snet.schematicNet._namesMatch(netName, probedNetName):
                    childPinNames.add(pinName)
            if childPinNames:
                childScene.probePinNames |= childPinNames
                childScene.applyProbe(idx % len(schlyr.probePens))

    # ---- descend edit-in-place -----------------------------------------

    def descendInPlace(self, symbolItem=None,
                     viewName: str = "schematic") -> Optional[
        QGraphicsItemGroup]:
        """Render the selected instance's child cellview ghosted inside
        this scene.

        Child items are created by the normal ``schematicItems`` factory,
        grouped under the instance's transform (pos/angle/flip) and marked
        ``_eipChild`` so connectivity, checks and save paths ignore them.
        ``setEipEditable(True)`` lets ghost children be selected for
        property edits; ``saveInPlaceEdits`` writes them back to the child
        file. Re-descending the same instance returns the existing group.
        """
        if symbolItem is None:
            symbols = [item for item in self.selectedItems()
                       if isinstance(item, shp.schematicSymbol)]
            if not symbols:
                return None
            symbolItem = symbols[0]
        if symbolItem in self._eipGroups:
            return self._eipGroups[symbolItem]
        file = self._childViewFile(symbolItem, viewName)
        if file is None:
            self.logger.warning(
                f"Edit-in-place: no child view for "
                f"{symbolItem.libraryName}/{symbolItem.cellName}")
            return None
        children, skipped = self._loadChildItems(file)
        if not children:
            return None
        group = QGraphicsItemGroup()
        group.setHandlesChildEvents(False)
        self.addItem(group)
        group.setZValue(-10)  # ghosts render below real items
        # Children join at identity transform first (addToGroup preserves
        # apparent scene position); the instance transform is applied to
        # the finished group afterwards.
        for child in children:
            child._eipChild = True
            child.setOpacity(0.35)
            child.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,
                          False)
            group.addToGroup(child)
        # Compose like the live item transform: flipTuple sits in the item's
        # manual transform matrix which Qt applies *outside* rotation, so the
        # chain must be translate -> scale(flip) -> rotate(angle).
        tr = QTransform()
        pos = symbolItem.scenePos()
        tr.translate(pos.x(), pos.y())
        tr.scale(*symbolItem.flipTuple)
        tr.rotate(symbolItem.angle)
        group.setTransform(tr)
        group._eipSkippedRecords = skipped
        self._eipGroups[symbolItem] = group
        self.markConnectivityDirty()
        return group

    def _childViewFile(self, symbolItem,
                       viewName: str = "schematic") -> Optional[pathlib.Path]:
        """Resolve the child cellview file for edit-in-place: the cell's
        schematic view first, then the instance's own view as fallback."""
        libraryPath = self.libraryDict.get(symbolItem.libraryName)
        if libraryPath is None:
            return None
        cellDir = libraryPath.joinpath(symbolItem.cellName)
        for name in (viewName, symbolItem.viewName):
            file = cellDir.joinpath(f"{name}.json")
            if file.exists():
                return file
        return None

    def _loadChildItems(self, file: pathlib.Path) -> list:
        """Instantiate a child cellview's records as scene items (not added
        to any scene yet)."""
        try:
            decodedData = orjson.loads(file.read_bytes())
        except (orjson.JSONDecodeError, OSError) as e:
            self.logger.error(f"Edit-in-place read failed for {file}: {e}")
            return []
        factory = lj.schematicItems(self)
        children, skipped = [], []
        for record in decodedData[2:]:
            shape = factory.create(record) if isinstance(record, dict) else None
            if shape is not None:
                children.append(shape)
            else:
                # Records the factory cannot instantiate (e.g. 'mrk' check
                # markers, unknown types) must survive a saveInPlaceEdits
                # round-trip; keep them verbatim for re-emission.
                skipped.append(record)
        return children, skipped

    def setEipEditable(self, flag: bool) -> None:
        """Allow/prevent selecting ghost children for property edits."""
        for group in self._eipGroups.values():
            for child in group.childItems():
                child.setFlag(
                    QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, flag)
                if not flag:
                    child.setSelected(False)

    def saveInPlaceEdits(self, symbolItem=None) -> int:
        """Write edited ghost children back to their child cellview file.

        Item records are encoded with ``mapToScene`` (parent coords) then
        back-transformed through the inverse instance transform into the
        child file's coordinate frame. ``ang``/``fl`` fields are item-local
        already and pass through unchanged. Returns files written."""
        written = 0
        for inst, group in (self._eipGroups.items() if symbolItem is None
                            else [(symbolItem,
                                   self._eipGroups.get(symbolItem))]):
            if group is None:
                continue
            file = self._childViewFile(inst)
            if file is None:
                continue
            trInv, ok = group.transform().inverted()
            if not ok:
                self.logger.error("Edit-in-place: non-invertible transform")
                continue
            try:
                decoded = orjson.loads(file.read_bytes())
            except (orjson.JSONDecodeError, OSError) as e:
                self.logger.error(f"Edit-in-place reload failed: {e}")
                continue
            out = list(decoded[:2])  # preserve child header + grid settings
            for child in group.childItems():
                record = json.loads(
                    json.dumps(child, cls=schenc.schematicEncoder))
                self._eipRecordToLocal(record, trInv)
                out.append(record)
            # Re-emit records the item factory could not create (markers,
            # unknown types) so a save doesn't silently drop them.
            out.extend(getattr(group, "_eipSkippedRecords", ()))
            try:
                file.write_bytes(orjson.dumps(
                    out, option=orjson.OPT_INDENT_2))
                written += 1
                self.logger.info(f"Edit-in-place saved {file}")
            except OSError as e:
                self.logger.error(f"Edit-in-place write failed: {e}")
        return written

    def _eipRecordToLocal(self, record: dict, trInv: QTransform) -> None:
        """Back-transform a record's scene-coordinate fields into the child
        file's coordinate frame (the ghost group's local space)."""
        origin = self.origin

        def toLocal(value):
            point = trInv.map(
                QPointF(value[0] + origin.x(), value[1] + origin.y()))
            return [point.x(), point.y()]

        for key in ("st", "end", "loc"):
            if key in record:
                record[key] = toLocal(record[key])
        if "br" in record:
            x0, y0, x1, y1 = record["br"]
            corners = [toLocal((x0, y0)), toLocal((x1, y0)),
                       toLocal((x0, y1)), toLocal((x1, y1))]
            xs = [p[0] for p in corners]
            ys = [p[1] for p in corners]
            record["br"] = [min(xs), min(ys), max(xs), max(ys)]

    def ascendInPlace(self, symbolItem=None) -> int:
        """Remove edit-in-place ghost groups. Returns groups removed."""
        targets = ([symbolItem] if symbolItem is not None
                   else list(self._eipGroups))
        removed = 0
        for inst in targets:
            group = self._eipGroups.pop(inst, None)
            if group is not None and group.scene() is self:
                self.removeItem(group)
                removed += 1
        if removed:
            self.markConnectivityDirty()
        return removed

    def ignoreSymbol(self):
        if self.selectedItems() is not None:
            for item in self.selectedItems():
                if isinstance(item, shp.schematicSymbol):
                    item.netlistIgnore = not item.netlistIgnore
        else:
            self.logger.warning("No symbol selected")

    def renumberInstances(self):
        symbolList = [item for item in self.items() if
                      isinstance(item, shp.schematicSymbol)
                      and not self._isEipGhost(item)]

        for index, symbolInstance in enumerate(symbolList):
            symbolInstance.counter = index
            if symbolInstance.instanceName.startswith("I"):
                # Preserve array notation like I2<0:5>
                if "<" in symbolInstance.instanceName and ">" in symbolInstance.instanceName:
                    array_part = symbolInstance.instanceName[
                        symbolInstance.instanceName.find("<"):]
                    symbolInstance.instanceName = f"I{index}{array_part}"
                else:
                    symbolInstance.instanceName = f"I{index}"
                for label in symbolInstance.labels.values():
                    label.labelDefs()
        self.instanceCounter = index + 1
        self.saveSchematic(self.editorWindow.file)
        self.reloadScene()

    ### netlisting related methods
    def genSymbolPinNetMap(self, symbolItem: shp.schematicSymbol):
        """Populate symbolItem.pinNetMap from the connectivity engine."""
        result = self.connectivity
        portIdByItem = self._connectivityPortIdByItem
        # Process connected pins and collect unconnected ones in single pass
        unconnectedPins = []
        for pinName, pinItem in symbolItem.pins.items():
            portId = portIdByItem.get(pinItem)
            groupIndex = (result.portGroup.get(portId)
                          if portId is not None else None)
            if groupIndex is not None:
                symbolItem.pinNetMap[pinName] = result.groups[
                    groupIndex].name
                pinItem.connected = True
            else:
                # An unconnected pin carrying a net expression is an
                # inherited connection — it netlists to the resolved
                # expression, not a dangling dnet.
                exprNet = (result.portExprNet.get(portId)
                           if portId is not None else None)
                if exprNet:
                    symbolItem.pinNetMap[pinName] = exprNet
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
                if pinName in symbolItem.pinNetMap:
                    ordered_map[pinName] = symbolItem.pinNetMap[pinName]
                else:
                    self.logger.warning(
                        f"{symbolItem.instanceName}: pinOrder entry "
                        f"'{pinName}' has no matching pin, skipping.")
            symbolItem.pinNetMap = ordered_map


    # --- Unified connectivity (revedaEditor.connectivity engine) -----------

    def markConnectivityDirty(self, *args):
        """Invalidate the cached connectivity result on any scene change."""
        self._connectivityCache = None

    def addItem(self, item):
        super().addItem(item)
        self.markConnectivityDirty()

    def removeItem(self, item):
        super().removeItem(item)
        self.markConnectivityDirty()

    def rebuildConnectivity(self, netSet: Optional[dict] = None
                            ) -> conn.ConnectivityResult:
        """Rebuild the connectivity model from current scene contents.

        Returns the fresh ConnectivityResult and caches it along with the
        item<->primitive id maps used to push results back onto items.

        ``netSet`` optionally supplies {exprName: localNet} bindings for
        net-expression evaluation (inherited connections); ``None``
        evaluates expressions to their defaults — the normal canvas
        context. Pass ``conn.terminalBinds(names)`` when collecting a
        subcircuit definition so expression names stay symbolic.
        """
        pinItems = [pinItem for symbolItem in self.findSceneSymbolSet()
                    for pinItem in symbolItem.pins.values()]
        pinItems.extend(self.findSceneSchemPinsSet())
        result, segById, portById = conn.analyzeItems(
            self.findSceneNetsSet(), pinItems,
            endpointTol=1.0,
            bodyTol=max(self.snapDistance // 2, 2),
            portTol=self.snapDistance,
            netSet=netSet)
        self._connectivityCache = result
        self._connectivitySegById = segById
        self._connectivityPortById = portById
        self._connectivitySegIdByItem = {item: segId for segId, item in
                                         segById.items()}
        self._connectivityPortIdByItem = {item: portId for portId, item in
                                          portById.items()}
        return result

    @property
    def connectivity(self) -> conn.ConnectivityResult:
        """Cached connectivity result, rebuilt when the scene changed."""
        if self._connectivityCache is None:
            self.rebuildConnectivity()
        return self._connectivityCache

    _STRENGTH_TO_ENUM = {
        conn.NONAME: snet.netNameStrengthEnum.NONAME,
        conn.WEAK: snet.netNameStrengthEnum.WEAK,
        conn.INHERIT: snet.netNameStrengthEnum.INHERIT,
        conn.SET: snet.netNameStrengthEnum.SET,
    }

    def collectNetExprNames(self) -> dict[str, str]:
        """{exprName: default} for every net expression used in this scene.

        Covers net/pin ``netExpr`` attributes including pins of symbol
        instances — i.e. the implicit terminal names this cell needs when
        netlisted as a subcircuit.
        """
        names, problems = conn.exprNamesFromItems(
            item for item in self.items() if not self._isEipGhost(item))
        for problem in problems:
            self.logger.warning(problem)
        return names

    def nameSceneNets(self, netSet: Optional[dict] = None):
        """Name all nets in the scene via the unified connectivity engine.

        Resolves names (global pins > schematic pins > SET names > auto
        net<N>), writes them back onto the net items, and reports conflicts
        collected by the engine. ``netSet`` supplies net-expression
        bindings (see rebuildConnectivity).
        """
        result = self.rebuildConnectivity(netSet=netSet)
        segIdByItem = self._connectivitySegIdByItem
        for netItem in self.findSceneNetsSet():
            segId = segIdByItem.get(netItem)
            name, strength = result.segName.get(segId, ("", conn.NONAME))
            if name:
                # name setter forces SET; assign name first, then strength.
                netItem.name = name
                netItem.nameStrength = self._STRENGTH_TO_ENUM[strength]
            else:
                netItem.clearName()
            netItem.nameConflict = segId in result.segConflicts
        for conflict in result.conflicts:
            self.logger.error(conflict.message)
        self.netCounter = result.autoCount

    def toggleResolvedNames(self, flag: bool):
        """Show/hide resolved (non-SET) net names on the canvas.

        When enabled, every wire whose name was resolved by the
        connectivity engine — inherited, global-pin, expression or auto
        names — displays it alongside explicitly SET names.
        """
        self.showResolvedNames = flag
        if flag:
            self.nameSceneNets()  # ensure resolved names are current
        for netItem in self.findSceneNetsSet():
            netItem.nameItem.updateVisibility()
        self.update()

    # ---- find / replace -------------------------------------------------

    def findItems(self, kind: str = "any", pattern: str = "",
                  prop: str = "") -> List["findHit"]:
        """Search the scene for items matching a name pattern.

        ``kind`` is one of ``"instance"``, ``"net"``, ``"pin"`` or ``"any"``.
        ``pattern`` accepts shell-style wildcards (``*``, ``?``); an empty
        pattern matches everything. ``prop`` optionally filters instances by
        property as ``name=value`` (label value, or ``lib``/``cell``/``view``
        for the referenced cell) or bare ``name`` for existence.

        Nets are searched by their resolved connectivity name (one hit per
        electrical net, carrying every member wire). Returns ``findHit``
        records in deterministic order.
        """
        import fnmatch
        pat = (pattern or "").strip() or "*"
        hits: List[findHit] = []
        if kind in ("instance", "any"):
            hits.extend(self._findInstances(pat, prop))
        if kind in ("net", "any"):
            hits.extend(self._findNets(pat))
        if kind in ("pin", "any"):
            hits.extend(h for h in self._findPins(pat))
        hits.sort(key=lambda h: (h.kind, h.name))
        return hits

    def _findInstances(self, pattern: str, prop: str) -> List["findHit"]:
        import fnmatch
        hits = []
        for item in self.findSceneSymbolSet():
            if not fnmatch.fnmatchcase(item.instanceName, pattern):
                continue
            if prop and not self._instancePropMatch(item, prop):
                continue
            hits.append(findHit(
                kind="instance", name=item.instanceName,
                detail=f"{item.libraryName}/{item.cellName}/{item.viewName}",
                items=(item,), rect=item.sceneBoundingRect()))
        return hits

    @staticmethod
    def _instancePropMatch(item, prop: str) -> bool:
        key, sep, value = prop.partition("=")
        key = key.strip().lstrip("@")
        value = value.strip()
        if key in ("lib", "cell", "view"):
            actual = {"lib": item.libraryName, "cell": item.cellName,
                      "view": item.viewName}[key]
            return actual == value if sep else bool(actual)
        label = item.labels.get(key)
        if label is None:
            return False
        return (label.labelValue.strip() == value if sep
                else bool(label.labelValue.strip()))

    def _findNets(self, pattern: str) -> List["findHit"]:
        import fnmatch
        result = self.connectivity
        segById = self._connectivitySegById
        membersByName: Dict[str, list] = {}
        for segId, (name, _strength) in result.segName.items():
            if name and fnmatch.fnmatchcase(name, pattern):
                membersByName.setdefault(name, []).append(segId)
        hits = []
        for name, segIds in membersByName.items():
            items = tuple(segById[s] for s in segIds if s in segById)
            if not items:
                continue
            rect = items[0].sceneBoundingRect()
            for it in items[1:]:
                rect = rect.united(it.sceneBoundingRect())
            hits.append(findHit(kind="net", name=name,
                                detail=f"{len(items)} segment(s)",
                                items=items, rect=rect))
        return hits

    def _findPins(self, pattern: str) -> List["findHit"]:
        import fnmatch
        hits = []
        for item in self.findSceneSchemPinsSet():
            if fnmatch.fnmatchcase(item.pinName, pattern):
                hits.append(findHit(
                    kind="pin", name=item.pinName,
                    detail=f"{item.pinDir} {item.pinType}",
                    items=(item,), rect=item.sceneBoundingRect()))
        return hits

    def replaceHitName(self, hit: "findHit", findText: str,
                       replaceText: str) -> str:
        """Rename one find hit. Literal ``findText`` is substring-replaced;
        a wildcard pattern renames to ``replaceText`` verbatim. Returns the
        new name (empty string when nothing changed)."""
        if not hit.name:
            return ""
        if any(ch in findText for ch in "*?"):
            newName = replaceText
        elif findText and findText in hit.name:
            newName = hit.name.replace(findText, replaceText)
        else:
            return ""
        if not newName or newName == hit.name:
            return ""
        if hit.kind == "instance":
            hit.items[0].instanceName = newName
        elif hit.kind == "pin":
            hit.items[0].pinName = newName
        elif hit.kind == "net":
            self.undoStack.push(
                us.changeNetNameUndo(self, list(hit.items), newName))
        return newName

    # ------------------------------------------------------------------
    # Schematic<->layout cross-probing
    # ------------------------------------------------------------------

    def netEndpointsForItem(self, netItem) -> list:
        """(instName, pinName) ports of the group containing ``netItem``.

        Sheet-level pins come back as ``("", pinName)`` — the same endpoint
        convention ``backend/correspondence.flylineEndpoints`` produces, so
        the layout side resolves both identically.
        """
        result = self.connectivity
        segId = self._connectivitySegIdByItem.get(netItem)
        if segId is None:
            return []
        group = result.groupOf(segId)
        if group is None:
            return []
        endpoints = []
        for portId in group.ports:
            pinItem = self._connectivityPortById.get(portId)
            if pinItem is None:
                continue
            parent = pinItem.parentItem()
            if isinstance(parent, shp.schematicSymbol):
                endpoints.append((parent.instanceName, pinItem.pinName))
            else:
                endpoints.append(("", pinItem.pinName))
        return endpoints

    def selectProbeTargets(self, instances=(), netEndpoints=()) -> int:
        """Select instances by name plus nets containing any endpoint port.

        Used by cross-probing (and scriptable tooling): ``instances`` are
        schematic instance names, ``netEndpoints`` are (instName, pinName)
        pairs as produced by ``netEndpointsForItem``/``flylineEndpoints``.
        Returns the number of items selected.
        """
        items = []
        wanted = set(instances)
        if wanted:
            items += [i for i in self.findSceneSymbolSet()
                      if i.instanceName in wanted]
        if netEndpoints:
            result = self.connectivity
            wantedEP = set(netEndpoints)
            segIds = set()
            for portId, pinItem in self._connectivityPortById.items():
                parent = pinItem.parentItem()
                key = ((parent.instanceName, pinItem.pinName)
                       if isinstance(parent, shp.schematicSymbol)
                       else ("", pinItem.pinName))
                if key not in wantedEP:
                    continue
                groupIndex = result.portGroup.get(portId)
                if groupIndex is not None:
                    segIds |= result.groups[groupIndex].members
            segById = self._connectivitySegById
            items += [segById[s] for s in segIds if s in segById]
        if not items:
            return 0
        self.clearSelection()
        rect = items[0].sceneBoundingRect()
        for it in items:
            it.setSelected(True)
            rect = rect.united(it.sceneBoundingRect())
        if self.views():
            self.views()[0].fitInView(
                rect.adjusted(-100, -100, 100, 100), Qt.KeepAspectRatio)
        return len(items)

    def probeTargets(self):
        """Return selected symbol names and schematic net endpoints."""
        instances, netEndpoints = [], []
        for item in self.selectedItems():
            if isinstance(item, shp.schematicSymbol):
                instances.append(item.instanceName)
            elif isinstance(item, snet.schematicNet):
                netEndpoints.extend(self.netEndpointsForItem(item))
            elif isinstance(item, shp.schematicPin):
                netEndpoints.append(("", item.pinName))
        return instances, netEndpoints

    def probeLayout(self) -> None:
        """Cross-probe selected symbols/nets into the sibling layout editor."""
        appMainW = getattr(self.editorWindow, "appMainW", None)
        key = ddef.viewNameTuple(self.editorWindow.libName,
                                 self.editorWindow.cellName, "layout")
        editor = (appMainW.openViews.get(key)
                  if appMainW is not None else None)
        if editor is None:
            self.messageLine.setText(
                f"Open {key.libraryName}/{key.cellName}/layout to probe")
            return
        instances, netEndpoints = self.probeTargets()
        if not instances and not netEndpoints:
            self.messageLine.setText("Select symbols or nets to probe")
            return
        count = editor.centralW.scene.selectProbeTargets(
            instances=instances, netEndpoints=netEndpoints)
        self.messageLine.setText(f"Probed {count} item(s) in layout")
        editor.raise_()
        editor.activateWindow()

    def checkErrors(self, enabledRuleIds=None):
        """
        Run the enabled schematic check rules and mark violations on the
        canvas. ``enabledRuleIds=None`` runs all registered rules; an empty
        set runs none. Markers are colored by severity (red=error,
        magenta=warning) and collected in ``overlapRectSet`` for
        ``deleteErrors``.
        """
        self.logger.info("Checking for errors...")
        self.deleteErrors()
        if enabledRuleIds is not None and not enabledRuleIds:
            self.logger.info("No check rules enabled.")
            return
        context = schk.buildCheckContext(self)
        violations = schk.runChecks(context, enabledRuleIds)
        self._drawViolations(violations)
        errorCount = sum(
            1 for v in violations
            if v.severity == schk.checkSeverity.ERROR)
        for violation in violations:
            if violation.severity == schk.checkSeverity.ERROR:
                self.logger.error(violation.message)
            else:
                self.logger.warning(violation.message)
        self.lastCheckViolations = violations
        self.logger.info(
            f"Check complete: {errorCount} error(s), "
            f"{len(violations) - errorCount} warning(s).")

    _SEVERITY_PENS = {
        "error": lambda: QPen(Qt.red, 1, Qt.DashDotLine),
        "warning": lambda: QPen(Qt.magenta, 1, Qt.DashDotLine),
    }

    def _drawViolations(self, violations) -> None:
        """Draw marker rects for violations into ``overlapRectSet``."""
        errorPen = self._SEVERITY_PENS["error"]()
        warningPen = self._SEVERITY_PENS["warning"]()
        for violation in violations:
            pen = (errorPen if violation.severity == schk.checkSeverity.ERROR
                   else warningPen)
            for marker in violation.markers:
                self.overlapRectSet.add(self.addRect(marker, pen))

    @staticmethod
    def _violationToRecord(violation) -> dict:
        """Encode a checkViolation as an ``mrk`` record."""
        return {
            "type": "mrk",
            "rule": violation.ruleId,
            "sev": ("error" if violation.severity == schk.checkSeverity.ERROR
                    else "warning"),
            "msg": violation.message,
            "rects": [[r.x(), r.y(), r.width(), r.height()]
                      for r in violation.markers],
        }

    def _restoreMarkers(self, itemData: List[Dict]) -> None:
        """Rebuild ``lastCheckViolations`` and markers from ``mrk`` records."""
        records = [r for r in itemData
                   if isinstance(r, dict) and r.get("type") == "mrk"]
        if not records:
            return
        violations = []
        for record in records:
            try:
                violations.append(schk.checkViolation(
                    ruleId=record["rule"],
                    severity=(schk.checkSeverity.ERROR
                              if record.get("sev") == "error"
                              else schk.checkSeverity.WARNING),
                    message=record.get("msg", ""),
                    markers=[QRectF(r[0], r[1], r[2], r[3])
                             for r in record.get("rects", [])]))
            except (KeyError, TypeError, IndexError) as e:
                self.logger.warning(f"Malformed mrk record skipped: {e}")
        self.lastCheckViolations = violations
        self._drawViolations(violations)

    def deleteErrors(self):
        self.logger.info("Deleting errors...")
        for rectItem in self.overlapRectSet:
            if shiboken6.isValid(rectItem) and rectItem.scene() is self:
                self.removeItem(rectItem)
        self.overlapRectSet.clear()

    @staticmethod
    def isValidNetName(text: str) -> bool:
        """
        Validates if the string is either:
        1. A string without any < or > characters
        2. A string ending with <int:int> where int is a positive integer

        Returns True if valid, False otherwise
        """
        # Pattern for string ending with <int:int>
        bus_pattern = QRegularExpression(r"^.*<(\d+):(\d+)>$")

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

    @staticmethod
    def createBusRanges(start: int, end: int):
        if start < end:
            resultRange = range(start, end + 1)
        else:
            resultRange = range(start, end - 1, -1)
        return resultRange

    @staticmethod
    def parseBusNotation(name: str) -> tuple[str, tuple[int, int]]:
        """
        Parse bus notation like 'name<0:5>' into base name and index range.
        Also handles single net notation like 'name<0>' or 'name<1>'.
    
        Args:
        name (str): The net name with optional bus notation.
    
        Returns:
        tuple[str, tuple[int, int]]: A tuple containing the base name and a tuple of start and end indices.
        """
        # Check if the name does not contain bus notation
        if '<' not in name or '>' not in name:
            return name, (0, 0)

        baseName = name.split('<')[0]  # Extract the base name before '<'
        indexRange = name.split('<')[1].split('>')[
            0]  # Extract the content inside '<>'

        # Check if it's a single index (e.g., 'name<0>')
        if ':' not in indexRange:
            singleIndex = int(indexRange)
            return baseName, (singleIndex, singleIndex)

        # Handle range notation (e.g., 'name<0:5>')
        start, end = map(int, indexRange.split(':'))
        return baseName, (start, end)
