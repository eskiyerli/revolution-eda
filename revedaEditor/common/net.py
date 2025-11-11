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
#   Add-ons and extensions developed for this software may be distributed
#
#   under their own separate licenses.
#
#    Software: Revolution EDA
#    License: Mozilla Public License 2.0
#    Licensor: Revolution Semiconductor (Registered in the Netherlands)


# net class definition.
from functools import cached_property
from PySide6.QtCore import (
    QPoint,
    Qt,
    QLineF,
    QRectF,
    QPointF,
)
from PySide6.QtGui import (
    QPen,
    QPainterPath,
    QPainter,
    QBrush,
    QColor,
)
from PySide6.QtWidgets import (
    QGraphicsLineItem,
    QGraphicsSimpleTextItem,
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsSceneMouseEvent,
    QGraphicsSceneHoverEvent,
)
import math
from typing import Type, Set, Union
from enum import IntEnum
from revedaEditor.backend.pdkPaths import importPDKModule
from typing import List

schlyr = importPDKModule("schLayers")


class NetMode(IntEnum):
    ORTHOGONAL = 0
    DIAGONAL = 1
    FREE = 2


class netNameStrengthEnum(IntEnum):
    NONAME = 0
    WEAK = 1
    INHERIT = 2
    SET = 3


class schematicNet(QGraphicsItem):

    def __init__(self, start: QPoint, end: QPoint, width: int = 0, mode: int = 0):
        super().__init__()

        # Batch set multiple flags at once using setFlags
        self.setFlags(
            QGraphicsItem.ItemIsSelectable |
            QGraphicsItem.ItemIsFocusable |
            QGraphicsItem.ItemSendsGeometryChanges
        )

        self.setAcceptHoverEvents(True)

        # Basic properties
        self._mode = mode
        self._width = width
        self._flip = (1, 1)
        self._offset = QPoint(0, 0)

        # State flags
        self._stretch: bool = False
        self._nameConflict: bool = False
        self._highlighted: bool = False
        self._nameStrength: int = netNameStrengthEnum.NONAME

        # Collections
        self._flightLinesSet: Set["schematicNet"] = set()
        self._connectedNetsSet: Set["schematicNet"] = set()
        self._netSnapLines: dict = {}
        
        # Track nets connected at each endpoint for rubber-banding
        # Key: endpoint index (0=p1/start, 1=p2/end)
        # Value: dict mapping connected net to which of its endpoints connects
        self._endpointConnections: dict[int, dict["schematicNet", int]] = {0: {}, 1: {}}

        # Line and name initialization
        self.draftLine = QLineF(start, end)
        self._nameItem = self.createEmptyNameItem()

    def createEmptyNameItem(self):
        nameItem = netName("", self)
        nameItem.setPos(self.draftLine.center())
        nameItem.setParentItem(self)
        return nameItem

    @property
    def draftLine(self) -> QLineF:
        return self._draftLine

    @draftLine.setter
    def draftLine(self, line: QLineF):
        self.prepareGeometryChange()
        self.__dict__.pop('_hash_value', None)
        self._draftLine = line
        origin_point = line.p1()
        line_angle = line.angle()

        if self._mode == 0:
            self._angle = 90 * ((line_angle + 45) // 90)
        elif self._mode == 1:
            self._angle = 45 * ((line_angle + 22.5) // 45)
        else:
            self._angle = line_angle

        self._draftLine.setAngle(0)
        self.setTransformOriginPoint(origin_point)

        # Clear the cached _extractRect
        self.__dict__.pop('_extractRect', None)
        extract_rect = self._extractRect
        self._shapeRect = extract_rect.adjusted(-2, -2, 2, 2)
        self._boundingRect = extract_rect.adjusted(-10, -10, 10, 10)
        self.setRotation(-self._angle)

    @cached_property
    def _extractRect(self) -> QRectF:
        p1 = self._draftLine.p1()
        p2 = self._draftLine.p2()
        direction = p2 - p1

        # Early return for zero-length line
        if direction == QPoint(0, 0):
            return QRectF(p1, p2).adjusted(-2, -2, 2, 2).normalized()

        manhattan_length = direction.manhattanLength()
        if manhattan_length == 0:
            return QRectF(p1, p2).normalized()

        # Cache frequently used values and combine calculations
        half_width = 0.5 * self._getPen().width() * (self._width + 1)
        inv_length = 1.0 / manhattan_length

        # Calculate direction components in one step
        direction_x = direction.x() * inv_length
        direction_y = direction.y() * inv_length

        # Calculate perpendicular offsets
        perp_x = -direction_y * half_width
        perp_y = direction_x * half_width

        point1 = QPoint(
            round(p1.x() + perp_x),  # Using round() instead of int() for better precision
            round(p1.y() + perp_y)
        )
        point2 = QPoint(
            round(p2.x() - perp_x),
            round(p2.y() - perp_y)
        )

        return QRectF(point1, point2).normalized()

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.addRect(self._shapeRect)
        return path

    def boundingRect(self):
        return self._boundingRect

    def paint(self, painter: QPainter, option, widget=None):
        pen = self._getPen()
        painter.setPen(pen)
        painter.drawLine(self._draftLine)

    def _getPen(self) -> QPen:
        pen_mapping = {
            self.isSelected(): schlyr.selectedWirePen,
            self._stretch: schlyr.stretchWirePen,
            self._highlighted: schlyr.hilightPen,
            self._nameConflict: schlyr.errorWirePen
        }
        base_pen = next((pen for condition, pen in pen_mapping.items() if condition), schlyr.wirePen)
        return_pen = QPen(base_pen)
        return_pen.setWidth(base_pen.width() * (self._width + 1))
        return return_pen

    def __repr__(self):
        return f"schematicNet({self.sceneEndPoints}, {self._width})"

    def itemChange(self, change, value):
        if self.scene():
            match change:
                case QGraphicsItem.ItemSelectedHasChanged:
                    if value:
                        self.setZValue(self.zValue() + 10)
                        self.scene().selectedNet = self
                    else:
                        self.setZValue(self.zValue() - 10)
                        self.scene().selectedNet = None
                        
        return super().itemChange(change, value)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        scene = self.scene()
        if scene:
            if scene.editModes.moveItem:
                self.setFlag(QGraphicsItem.ItemIsMovable, True)
            elif self._stretch:
                eventPos = event.pos().toPoint()
                if (
                    eventPos - self._draftLine.p1().toPoint()
                ).manhattanLength() <= scene.snapDistance:
                    self.setCursor(Qt.SizeHorCursor)
                    scene.stretchNet.emit(self, "p1")
                elif (
                    eventPos - self._draftLine.p2().toPoint()
                ).manhattanLength() <= self.scene().snapDistance:
                    self.setCursor(Qt.SizeHorCursor)
                    scene.stretchNet.emit(self, "p2")
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self.setSelected(False)
        if self.scene().editModes.moveItem:
            self.setFlag(QGraphicsItem.ItemIsMovable, False)
            self.scene().wireEditFinished.emit(self)
        super().mouseReleaseEvent(event)

    @staticmethod
    def parseArrayNotation(name: str) -> tuple[str, tuple[int, int]]:
        """Parse net/instance array notation like 'name<0:5>' into base name and index range.
        Also handles single instance/net notation like 'name<0>' or 'name<1>'.
        
        Returns:
            tuple[str, tuple[int, int]]: Base name and (start, end) indices.
                                         Returns (-1, -1) if no bus notation.
        """
        if '<' not in name or '>' not in name:
            return name, (-1, -1)
        
        baseName = name.split('<')[0]
        indexRange = name.split('<')[1].split('>')[0]
        
        if ':' not in indexRange:
            singleIndex = int(indexRange)
            return baseName, (singleIndex, singleIndex)
        
        start, end = map(int, indexRange.split(':'))
        return baseName, (start, end)

    @staticmethod
    def _namesMatch(name1: str, name2: str) -> bool:
        """Check if two net names match, considering bus notation.
        Examples: 
        - 'inp' matches 'inp' (exact match)
        - 'inp<7>' matches 'inp<7:0>' (index in range)
        - 'data<3>' matches 'data<7:0>' (index in range)
        """
        if name1 == name2:
            return True
        
        base1, (start1, end1) = schematicNet.parseArrayNotation(name1)
        base2, (start2, end2) = schematicNet.parseArrayNotation(name2)
        
        # Base names must match
        if base1 != base2:
            return False
        
        # If both have no index (-1, -1), base names already matched above
        # If only one has index, they don't match (e.g., 'inp' vs 'inp<7>')
        if (start1 == -1) or (start2 == -1):
            return False
        
        # Check if index/range overlaps
        min1, max1 = min(start1, end1), max(start1, end1)
        min2, max2 = min(start2, end2), max(start2, end2)
        
        return not (max1 < min2 or max2 < min1)

    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        """
        Override the hoverEnterEvent method of QGraphicsItem.

        Args:
            event (QGraphicsSceneHoverEvent): The hover event.

        Returns:
            None
        """
        super().hoverEnterEvent(event)
        # Check if highlightNets flag is set in the scene
        if self.scene().highlightNets:
            self._highlighted = True
            self.scene().nameSceneNets() # first name all the nets in the scene.
            sceneNetsSet = self.scene().findSceneNetsSet()
            self._connectedNetsSet = {
                net for net in sceneNetsSet if self._namesMatch(net.name, self.name)
            }

            # Highlight the connected netItems
            for netItem in self._connectedNetsSet:
                netItem.highlight()
                flightLine = netFlightLine(
                    self.mapToScene(self._draftLine.center()),
                    netItem.mapToScene(netItem.draftLine.center()),
                )
                self._flightLinesSet.add(flightLine)
                self.scene().addItem(flightLine)

    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        super().hoverLeaveEvent(event)
        if self._highlighted:
            self._highlighted = False
            self._clearFlightLines()
            self._unhighlightConnectedNets()

    def _clearFlightLines(self) -> None:
        for flight_line in self._flightLinesSet:
            self.scene().removeItem(flight_line)
        self._flightLinesSet.clear()

    def _unhighlightConnectedNets(self) -> None:
        for net_item in self._connectedNetsSet:
            net_item.unhighlight()

    def isParallel(self, otherNet: "schematicNet") -> bool:
        return abs((self.angle - otherNet.angle) % 180) < 1

    def isOrthogonal(self, otherNet: "schematicNet") -> bool:
        return abs((self.angle - otherNet.angle - 90) % 180) < 1

    def notParallel(self, otherNet: "schematicNet") -> bool:
        return not self.isParallel(otherNet)

    def findOverlapNets(self) -> Set["schematicNet"]:
        """
        Find all netItems in the scene that overlap with self.sceneShapeRect.

        Returns:
            set: A set of netItems that overlap with self.sceneShapeRect.
        """
        if self.scene():
            overlapNets = {
                netItem
                for netItem in self.collidingItems()
                if isinstance(netItem, schematicNet)
            }
            return overlapNets - {self}

    def inheritNetName(self, otherNet: "schematicNet") -> bool:
        """
        Inherit or resolve net names based on name strength and handle conflicts.
        """

        def resolve_name(weakNet: "schematicNet", strongNet: "schematicNet"):
            weakNet.name = strongNet.name
            weakNet.nameStrength = netNameStrengthEnum.INHERIT

        self_strength = self.nameStrength.value
        other_strength = otherNet.nameStrength.value

        if self_strength == 3:  # SET
            if other_strength < 3:
                resolve_name(otherNet, self)
                return True
            if self.name != otherNet.name:
                self.nameConflict = otherNet.nameConflict = True
                return False
            return True

        if self_strength == 2:  # INHERIT
            match other_strength:
                case 0 | 1:  # NONAME or WEAK
                    resolve_name(otherNet, self)
                    return True
                case 2:  # INHERIT
                    if self.name != otherNet.name:
                        self.nameConflict = otherNet.nameConflict = True
                        return False
                    return True
                case 3:
                    resolve_name(self, otherNet)
                    return True

        if self_strength == 1:  # WEAK
            match other_strength:
                case 0:  # NONAME
                    otherNet.nameStrength = netNameStrengthEnum.WEAK
                    otherNet.name = self.name
                    return True
                case 1:  # WEAK
                    if self.name != otherNet.name:
                        self.nameConflict = otherNet.nameConflict = True
                        return False
                    return True
                case 2 | 3:  # INHERIT or SET
                    resolve_name(self, otherNet)
                    return True

        if self_strength == 0:  # NONAME
            if other_strength > 0:
                resolve_name(self, otherNet)
                return True
            else:
                if self.name != "" or otherNet.name != "":
                    self.nameConflict = otherNet.nameConflict = True
                    return False
                return True

        return False

    def mergeNetName(self, otherNet: "schematicNet") -> bool:
        """
        Merge net names based on name strength and handle conflicts.
        """
        if otherNet.nameStrength > self.nameStrength:
            if  otherNet.nameStrength == 3:
                self.name = otherNet.name
                self.nameStrength = netNameStrengthEnum.INHERIT
                return True
            else:
                self.name = otherNet.name
                self.nameStrength = otherNet.nameStrength
                return True
        elif otherNet.nameStrength == self.nameStrength:
            if otherNet.name != self.name:
                self.nameConflict = otherNet.nameConflict = True
                return False
            return True

    def clearName(self):
        """
        Clear the net name and set its strength to NONAME.
        """
        if self.nameStrength.value < 3:
            self.name = ""
            self.nameStrength = netNameStrengthEnum.NONAME


    def inherit(self, otherNet):
        self.name = otherNet.name
        self.nameStrength = otherNet.nameStrength

    @property
    def name(self) -> str:
        if self._nameItem:
            return self._nameItem.name
        else:
            return ""

    @name.setter
    def name(self, name: str):
        if name:
            self.prepareGeometryChange()
            self._nameItem.name = name
            self._nameItem.nameStrength = netNameStrengthEnum.SET
            self._nameItem.setPos(self._draftLine.center())

    @property
    def nameStrength(self) -> int:
        return self._nameItem.nameStrength

    @nameStrength.setter
    def nameStrength(self, value: netNameStrengthEnum):
        self._nameItem.nameStrength = value

    @property
    def nameConflict(self) -> bool:
        return self._nameConflict

    @nameConflict.setter
    def nameConflict(self, value: bool):
        self._nameConflict = value
        self._nameItem.nameConflict = value
        self.update()

    @property
    def endPoints(self):
        return [self._draftLine.p1().toPoint(), self._draftLine.p2().toPoint()]

    def otherEnd(self, point: QPoint) -> QPoint:
        if point == self._draftLine.p1().toPoint():
            return self._draftLine.p2().toPoint()
        else:
            return self._draftLine.p1().toPoint()

    def sceneOtherEnd(self, point: QPoint) -> QPoint:
        return self.mapToScene(self.otherEnd(point)).toPoint()

    @property
    def sceneEndPoints(self) -> List[QPoint]:
        return [
            self.mapToScene(self._draftLine.p1()).toPoint(),
            self.mapToScene(self._draftLine.p2()).toPoint(),
        ]

    @sceneEndPoints.setter
    def sceneEndPoints(self, points: List[QPoint]):
        self.prepareGeometryChange()
        self.draftLine = QLineF(points[0], points[1])

    @property
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, value: Union[QPoint | QPointF]):
        self._offset = value

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, value: int):
        self.prepareGeometryChange()
        self._width = value
        # Invalidate cached hash when width changes
        if hasattr(self, '_hash_value'):
            del self._hash_value
        # Clear the cached _extractRect
        if '_extractRect' in self.__dict__:
            del self.__dict__['_extractRect']
        self.update()

    def highlight(self):
        self._highlighted = True
        self.update()

    def unhighlight(self):
        self._highlighted = False
        self.update()

    @property
    def highlighted(self):
        return self._highlighted

    @highlighted.setter
    def highlighted(self, value: bool):
        self._highlighted = value

    @property
    def sceneShapeRect(self) -> QRectF:
        return self.mapRectToScene(self._shapeRect).normalized().toRect()

    @property
    def stretchSide(self) -> int:
        """
        The end where the net is stretched.
        """
        return self._stretchSide

    @stretchSide.setter
    def stretchSide(self, value: str):
        self.prepareGeometryChange()
        self._stretchSide = value

    @property
    def angle(self) -> float:
        return self._angle

    @angle.setter
    def angle(self, value: float):
        self._angle = value

    @property
    def stretch(self) -> bool:
        return self._stretch

    @stretch.setter
    def stretch(self, value: bool):
        self._stretch = value

    @property
    def mode(self) -> int:
        return self._mode

    @property
    def nameItem(self) -> "netName":
        return self._nameItem

    @nameItem.setter
    def nameItem(self, name: str):
        self._nameItem = netName(name, self)
        self._nameItem.setPos(self._draftLine.center())
        self._nameItem.setParentItem(self)

    @property
    def annotationItem(self) -> "netAnnotation":
        return self._annotationItem

    @annotationItem.setter
    def annotationItem(self, text: str):
        self._annotationItem = netAnnotation(text, self)
        self._annotationItem.setPos(self._draftLine.center() + QPointF(0, -20))
        self._annotationItem.setParentItem(self)

    def clearAnnotation(self):
        if hasattr(self, '_annotationItem') and self._annotationItem:
            if self._annotationItem.scene():
                self._annotationItem.scene().removeItem(self._annotationItem)
            self._annotationItem = None

    def __hash__(self) -> int:
        """Generate a hash value for the schematic net based on its properties."""
        # Cache the hash value since the line length is unlikely to change frequently
        if not hasattr(self, '_hash_value'):
            # Combine multiple properties for a more unique hash
            self._hash_value = hash((
                self.draftLine.length(),
                self.width,
                frozenset((p.x(), p.y()) for p in self.sceneEndPoints)
            ))
        return self._hash_value

    def __eq__(self, other) -> bool:
        """Compare two schematic nets for equality."""
        if not isinstance(other, schematicNet):
            return False
            
        # Compare width first as it's a simple comparison
        if self.width != other.width:
            return False
        
        # Use set comprehension for endpoints comparison
        # Cache the results to avoid multiple set creations
        self_points = frozenset((point.x(), point.y()) for point in self.sceneEndPoints)
        other_points = frozenset((point.x(), point.y()) for point in other.sceneEndPoints)
        
        return self_points == other_points

class netAnnotation(QGraphicsSimpleTextItem):
    def __init__(self, text: str, parent: schematicNet | None = None):
        super().__init__(text, parent)
        self._parent = parent
        self.setBrush(QBrush(QColor("orange")))
        if self._parent:
            self.setRotation(self._parent.angle)

    @property
    def parent(self):
        return self._parent

    
    @property
    def value(self) -> str:
        return self.text()

    @value.setter
    def value(self, input: str):
        self.prepareGeometryChange()
        self.setText(input)
        self.setRotation(self._parent.angle)
        self.parentItem().update()


class netName(QGraphicsSimpleTextItem):
    def __init__(self, name: str, parent: schematicNet | None = None):
        super().__init__(name, parent)
        self._parent = parent
        self.setBrush(schlyr.wireBrush)
        self._nameConflict = False
        self._nameStrength = netNameStrengthEnum.NONAME
        if self._parent:
            self.setRotation(self._parent.angle)
            self._draftLineCenter = self._parent.draftLine.center()

    def paint(self, painter, option, widget, /):
        if self._nameStrength == netNameStrengthEnum.SET:
            super().paint(painter, option, widget)
        else:
            # Do not paint the name if the strength is not SET
            pass

    @property
    def nameConflict(self) -> bool:
        return self._nameConflict

    @nameConflict.setter
    def nameConflict(self, value: bool):
        if value:
            self.setBrush(schlyr.errorWireBrush)
        else:
            self.setBrush(schlyr.wireBrush)
        self.update()

    @property
    def nameStrength(self) -> int:
        return self._nameStrength

    @nameStrength.setter
    def nameStrength(self, value: int):
        self._nameStrength = value
        if self._nameStrength == netNameStrengthEnum.SET:
            self.setVisible(True)
        else:
            self.setVisible(False)

    @property
    def name(self) -> str:
        return self.text()

    @name.setter
    def name(self, value: str):
        self.prepareGeometryChange()
        self.setText(value)
        self.setRotation(self._parent.angle)
        self.parentItem().update()

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, parent: schematicNet):
        self._parent = parent
        self.setRotation(self._parent.angle)
        self._draftLineCenter = self._parent.draftLine.center()


    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:

        self.setSelected(False)
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        if self._parent:
            self._parent.unhighlight()
        super().mouseReleaseEvent(event)  # type: ignore


class netFlightLine(QGraphicsPathItem):
    wireHighlightPen = QPen(
        schlyr.wireHilightLayer.pcolor,
        schlyr.wireHilightLayer.pwidth,
        schlyr.wireHilightLayer.pstyle,
    )

    def __init__(self, start: QPoint, end: QPoint):
        self._start = start
        self._end = end
        super().__init__()
        self._createPath()

    def __repr__(self):
        return f"netFlightLine({self.mapToScene(self._start)},{self.mapToScene(self._end)})"

    def _createPath(self) -> None:
        line = QLineF(self._start, self._end)
        perpendicularLine = QLineF(
            line.center(), line.center() + QPointF(-line.dy(), line.dx())
        )
        perpendicularLine.setLength(100)

        path = QPainterPath()
        path.moveTo(self._start)
        path.quadTo(perpendicularLine.p2(), self._end)
        self.setPath(path)

    def paint(self, painter: QPainter, *_) -> None:
        painter.setPen(netFlightLine.wireHighlightPen)
        painter.drawPath(self.path())


class guideLine(QGraphicsLineItem):
    def __init__(self, start: QPoint, end: QPoint):
        self._start = start
        self._end = end
        super().__init__(QLineF(self._start, self._end))
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setPen(schlyr.guideLinePen)
        self._name: str = ""
        self._nameStrength: netNameStrengthEnum = netNameStrengthEnum.NONAME

    @property
    def sceneEndPoints(self) -> list[QPoint]:
        """
        Returns a list of the end points of the net in scene coordinates.

        Returns:
            list[QPoint]: A list of the end points of the net in scene coordinates.
        """
        return [
            self.mapToScene(self.line().p1()).toPoint(),
            self.mapToScene(self.line().p2()).toPoint(),
        ]

    def __repr__(self):
        return f"guideLine({self.mapToScene(self.line().p1()), self.mapToScene(self.line().p2())}"

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        if name != "":  # net name should not be an empty string
            self._name = name

    @property
    def nameStrength(self) -> netNameStrengthEnum:
        return self._nameStrength

    @nameStrength.setter
    def nameStrength(self, value: netNameStrengthEnum):
        assert isinstance(value, netNameStrengthEnum)
        self._nameStrength = value

    def inherit(self, otherNet: schematicNet):
        """
        This method is used to carry the name information of the original net
        to stretch net.
        """
        assert isinstance(otherNet, schematicNet)
        self.name = otherNet.name
        self.nameStrength = otherNet.nameStrength
