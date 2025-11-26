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


# shape class definition for symbol editor.
# base class for all shapes: rectangle, circle, line
import itertools
import math
from pathlib import Path
import numpy as np
from typing import Tuple, Union
from PySide6.QtCore import (
    QPoint,
    QRect,
    QRectF,
    Qt,
    QPointF,
    QLineF,
)
from PySide6.QtGui import (
    QPen,
    QBrush,
    QColor,
    QPixmap,
    QFontMetrics,
    QFont,
    QTextOption,
    QFontDatabase,
    QPainterPath,
    QPolygonF,
    QImage,
    QPainter,
    QTransform,
)
from PySide6.QtWidgets import (
    QStyle,
    QGraphicsItem,
    QGraphicsSceneMouseEvent,
    QGraphicsSceneHoverEvent,
)

import revedaEditor.backend.dataDefinitions as ddef

from revedaEditor.backend.pdkPaths import importPDKModule


class textureCache:
    _file_content_cache = {}
    _pixmap_cache = {}

    @classmethod
    def readFileContent(cls, filePath):
        if filePath not in cls._file_content_cache:
            with open(filePath, "r") as file:
                cls._file_content_cache[filePath] = file.read()
        return cls._file_content_cache[filePath]

    @classmethod
    def createImage(cls, filePath: Path, color: QColor, scale: int = 1)  -> QImage:
        content = cls.readFileContent(str(filePath))

        # Use numpy's loadtxt for faster parsing of text data
        data = np.loadtxt(content.splitlines(), dtype=np.uint8)

        # Scale up the pattern by repeating each pixel
        data_scaled = np.repeat(np.repeat(data, scale, axis=0), scale, axis=1)

        height, width = data_scaled.shape

        # Create QImage with Format_ARGB32 (not premultiplied)
        image = QImage(width, height, QImage.Format.Format_ARGB32)
        # Fill with transparent pixels first
        image.fill(Qt.transparent)

        # Create painter to draw on the image
        painter = QPainter(image)
        painter.setPen(Qt.NoPen)
        # painter.setBrush(QBrush(color))
        # Create semi-transparent color (50% opacity)
        transparent_color = QColor(color)
        transparent_color.setAlpha(230)  # 220 is 90% opacity (range is 0-255)
        painter.setBrush(QBrush(transparent_color))

        # Draw solid rectangles for each pixel that should be colored
        for i in range(height):
            for j in range(width):
                if data_scaled[i, j] == 1:  # Draw colored pixel
                    painter.drawRect(j, i, 1, 1)

        painter.end()
        return image

    @classmethod
    def getCachedPixmap(cls, texturePath, color):
        cache_key = (str(texturePath), color.name())
        if cache_key not in cls._pixmap_cache:
            image = cls.createImage(texturePath, color, 1)
            pixmap = QPixmap.fromImage(image)
            cls._pixmap_cache[cache_key] = pixmap
        return cls._pixmap_cache[cache_key]

    @classmethod
    def clearCaches(cls):
        cls._file_content_cache.clear()
        cls._pixmap_cache.clear()


class layoutShape(QGraphicsItem):
    # Class-level color cache
    _color_cache = {}
    # Class-level pen/brush lookup table
    _pen_brush_cache = {}
    
    def __init__(self) -> None:
        super().__init__()
        
        # Batch flag operations for better performance
        flags = (QGraphicsItem.ItemIsSelectable | 
                QGraphicsItem.ItemSendsGeometryChanges |
                QGraphicsItem.ItemIsFocusable |
                QGraphicsItem.ItemUsesExtendedStyleOption)
        self.setFlags(flags)
        
        # Single method calls
        self.setAcceptHoverEvents(True)
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
        
        # Direct attribute initialization (faster than individual assignments)
        self._pen = self._brush = None
        self._angle = 0
        self._stretch = False
        self._offset = QPoint(0, 0)
        self._flipTuple = (1, 1)
        self._transformedBrush = self._lastScale = None
    
    @classmethod
    def _get_cached_color(cls, color_name):
        if color_name not in cls._color_cache:
            cls._color_cache[color_name] = QColor(color_name)
        return cls._color_cache[color_name]

    def __repr__(self):
        return "layoutShape()"

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged and self.scene():
            # Direct z-value calculation without conditional
            self.setZValue(self.zValue() + (20 * value - 10))
        return super().itemChange(change, value)

    def _definePensBrushes(self, layer):
        # Create cache key from layer properties
        cache_key = (layer.name, layer.purpose, layer.pcolor.name(), 
                    layer.pwidth, layer.pstyle, layer.bcolor.name(), layer.btexture)
        
        if cache_key not in self._pen_brush_cache:
            # Import PDK module when needed to avoid circular imports
            laylyr = importPDKModule('layoutLayers')
            # Create objects only once per unique layer configuration
            texturePath = Path(laylyr.__file__).parent.joinpath(layer.btexture)
            _pixmap = textureCache.getCachedPixmap(texturePath, layer.bcolor)
            
            yellow = self._get_cached_color("yellow")
            red = self._get_cached_color("red")
            
            self._pen_brush_cache[cache_key] = {
                'pen': QPen(layer.pcolor, layer.pwidth, layer.pstyle),
                'brush': QBrush(layer.bcolor, _pixmap),
                'selectedPen': QPen(yellow, layer.pwidth, Qt.DashLine),
                'selectedBrush': QBrush(yellow, _pixmap),
                'stretchPen': QPen(red, layer.pwidth, Qt.SolidLine),
                'stretchBrush': QBrush(red, _pixmap)
            }
        
        # Assign from cache
        cached = self._pen_brush_cache[cache_key]
        self._pen = cached['pen']
        self._brush = cached['brush']
        self._selectedPen = cached['selectedPen']
        self._selectedBrush = cached['selectedBrush']
        self._stretchPen = cached['stretchPen']
        self._stretchBrush = cached['stretchBrush']

    # def _updateTransformedBrush(self, brush: QBrush, scale: float):
    #     """Update transformed brush only when needed"""
    #     # Round scale to reduce cache misses and artifacts
    #     rounded_scale = round(scale, 2)
    #
    #     if self._transformedBrush is None or self._lastScale != rounded_scale:
    #         self._transformedBrush = QBrush(brush)
    #         # Use smooth scaling with proper filtering
    #         transform = QTransform().scale(1 / rounded_scale,
    #                                        1 / rounded_scale)
    #         self._transformedBrush.setTransform(transform)
    #         self._lastScale = rounded_scale
    def _updateTransformedBrush(self, brush: QBrush, scale: float):
        """Update transformed brush only when needed"""
        rounded_scale = max(round(scale, 2), 0.01)  # Prevent division by zero

        if self._transformedBrush is None or self._lastScale != rounded_scale:
            if self._transformedBrush is None:
                self._transformedBrush = QBrush(brush)
            else:
                self._transformedBrush = brush

            transform = QTransform().scale(1 / rounded_scale, 1 / rounded_scale)
            self._transformedBrush.setTransform(transform)
            self._lastScale = rounded_scale

    @property
    def pen(self):
        return self._pen

    @pen.setter
    def pen(self, value: QPen):
        if isinstance(value, QPen):
            self._pen = value

    @property
    def brush(self):
        return self._brush

    @brush.setter
    def brush(self, value: QBrush):
        if isinstance(value, QBrush):
            self._brush = value

    @property
    def angle(self):
        return self._angle

    @angle.setter
    def angle(self, value):
        self._angle = value
        self.prepareGeometryChange()
        self.setRotation(value)

    @property
    def stretch(self):
        return self._stretch

    @stretch.setter
    def stretch(self, value: bool):
        self._stretch = value

    @property
    def view(self):
        if self.scene():
            return self.scene().views()[0]
        else:
            return None

    @property
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, value: Union[QPoint | QPointF]):
        self._offset = value

    # def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
    #     super().mousePressEvent(event)
    #     if self.scene() and self.scene().editModes.moveItem:
    #         self.setFlag(QGraphicsItem.ItemIsMovable, True)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        super().mousePressEvent(event)
        if self.scene():
            self.scene().clearSelection()
            self.setSelected(True)
            if self.scene().editModes.moveItem:
                self.setFlag(QGraphicsItem.ItemIsMovable, True)

    def sceneEvent(self, event):
        """
        Do not propagate event if shape needs to keep still.
        """
        if self.scene() and (
            self.scene().editModes.changeOrigin or self.scene().drawMode
        ):
            return False
        else:
            super().sceneEvent(event)
            return True

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        super().mouseReleaseEvent(event)

    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self.setCursor(Qt.ArrowCursor)
        self.setOpacity(0.75)
        self.setFocus()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        super().hoverLeaveEvent(event)
        self.setCursor(Qt.CrossCursor)
        self.setOpacity(1)
        self.clearFocus()

    def contextMenuEvent(self, event):
        self.setSelected(True)
        self.scene().itemContextMenu.exec_(event.screenPos())

    @property
    def flipTuple(self):
        return self._flipTuple

    @flipTuple.setter
    def flipTuple(self, flipState: Tuple[int, int]):
        # Early exit if no change
        if self._flipTuple == flipState:
            return
        
        # Cache center calculation
        if not hasattr(self, '_cached_center'):
            self._cached_center = self.boundingRect().center()
        center = self._cached_center
        
        # Direct transform creation is faster than modifying existing
        cx, cy = center.x(), center.y()
        sx, sy = flipState
        
        transform = QTransform(sx, 0, 0, sy, cx - sx * cx, cy - sy * cy)
        self.setTransform(transform)
        self._flipTuple = flipState

    @property
    def layer(self):
        return self._layer

    @layer.setter
    def layer(self, value: ddef.layLayer):
        self.prepareGeometryChange()
        self._layer = value
        self._definePensBrushes(self._layer)


class layoutRect(layoutShape):
    sides = ["Left", "Right", "Top", "Bottom"]

    def __init__(
        self,
        start: QPoint,
        end: QPoint,
        layer: ddef.layLayer,
    ):
        super().__init__()
        self._rect = QRectF(start, end).normalized()
        self._start = self._rect.topLeft()
        self._end = self._rect.bottomRight()
        self._layer = layer
        if self._layer.selectable:
            self.setFlag(QGraphicsItem.ItemIsSelectable, True)
            self.setFlag(QGraphicsItem.ItemIsFocusable, True)
        else:
            self.setFlag(QGraphicsItem.ItemIsSelectable, False)
            self.setFlag(QGraphicsItem.ItemIsFocusable, False)
        self._stretch = False
        self._stretchSide = None
        self._stretchPen = QPen(QColor("red"), self._layer.pwidth, Qt.SolidLine)
        self._definePensBrushes(self._layer)
        self.setZValue(self._layer.z)
        self._stretchSidesMap = {
            self.sides[0]: (lambda r: r.topLeft(), lambda r: r.bottomLeft()),
            self.sides[1]: (lambda r: r.topRight(), lambda r: r.bottomRight()),
            self.sides[2]: (lambda r: r.topLeft(), lambda r: r.topRight()),
            self.sides[3]: (lambda r: r.bottomLeft(), lambda r: r.bottomRight())
        }



    def __repr__(self):
        return f"layoutRect({self._start}, {self._end}, {self._layer})"


    def paint(self, painter, option, widget):
        # Cache the rect to avoid multiple attribute lookups
        rect = self._rect

        # Get scale once and cache it
        scale = self.scene().views()[0].transform().m11()

        if self.isSelected():
            painter.setPen(self._selectedPen)
            self._updateTransformedBrush(self._selectedBrush, scale)

            if self.stretch:
                painter.setPen(self._stretchPen)
                # Get the line endpoints from the mapping
                if self._stretchSide in self._stretchSidesMap:
                    start_func, end_func = self._stretchSidesMap[self._stretchSide]
                    painter.drawLine(start_func(rect), end_func(rect))
        else:
            painter.setPen(self._pen)
            self._updateTransformedBrush(self._brush, scale)
        painter.setBrush(self._transformedBrush)
        painter.drawRect(rect)

    def boundingRect(self):
        return self._rect.normalized().adjusted(-2, -2, 2, 2)

    @property
    def rect(self):
        return self._rect

    @rect.setter
    def rect(self, rect: QRect):
        self.prepareGeometryChange()
        self._rect = rect

    @property
    def start(self):
        return self._start

    @start.setter
    def start(self, start: QPoint):
        self.prepareGeometryChange()
        self._rect = QRectF(start, self.end).normalized()
        self._start = start

    @property
    def end(self):
        return self._end

    @end.setter
    def end(self, end: QPoint):
        self.prepareGeometryChange()
        self._rect = QRectF(self.start, end).normalized()
        self._end = end

    @property
    def centre(self):
        return QPoint(
            int(self._rect.x() + self._rect.width() / 2),
            int(self._rect.y() + self._rect.height() / 2),
        )

    @property
    def height(self):
        return self.rect.height()

    @height.setter
    def height(self, height: int):
        self.prepareGeometryChange()
        self._rect.setHeight(height)

    @property
    def width(self):
        return self.rect.width()

    @width.setter
    def width(self, width):
        self.prepareGeometryChange()
        self.rect.setWidth(width)

    @property
    def left(self):
        return self.rect.left()

    @left.setter
    def left(self, left: int):
        self.rect.setLeft(left)

    @property
    def right(self):
        return self.rect.right()

    @right.setter
    def right(self, right: int):
        self.prepareGeometryChange()
        self.rect.setRight(right)

    @property
    def top(self):
        return self.rect.top()

    @top.setter
    def top(self, top: int):
        self.prepareGeometryChange()
        self.rect.setTop(top)

    @property
    def bottom(self):
        return self.rect.bottom()

    @bottom.setter
    def bottom(self, bottom: int):
        self.prepareGeometryChange()
        self.rect.setBottom(bottom)

    @property
    def origin(self):
        return self.rect.bottomLeft()

    @property
    def stretchSide(self):
        return self._stretchSide

    @stretchSide.setter
    def stretchSide(self, value: str):
        self.prepareGeometryChange()
        self._stretchSide = value

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        super().mousePressEvent(event)

        if self._layer.selectable:
            self.setFlag(QGraphicsItem.ItemIsMovable, True)
            self.setFlag(QGraphicsItem.ItemIsSelectable, True)
            eventPos = event.pos().toPoint()
            if self._stretch:
                self.setFlag(QGraphicsItem.ItemIsMovable, False)
                if eventPos.x() == self._rect.left():
                    if self._rect.top() <= eventPos.y() <= self._rect.bottom():
                        self.setCursor(Qt.SizeHorCursor)
                        self._stretchSide = layoutRect.sides[0]
                elif eventPos.x() == self._rect.right():
                    if self._rect.top() <= eventPos.y() <= self._rect.bottom():
                        self.setCursor(Qt.SizeHorCursor)
                        self._stretchSide = layoutRect.sides[1]
                elif eventPos.y() == self._rect.top():
                    if self._rect.left() <= eventPos.x() <= self._rect.right():
                        self.setCursor(Qt.SizeVerCursor)
                        self._stretchSide = layoutRect.sides[2]
                elif eventPos.y() == self._rect.bottom():
                    if self._rect.left() <= eventPos.x() <= self._rect.right():
                        self.setCursor(Qt.SizeVerCursor)
                        self._stretchSide = layoutRect.sides[3]
        else:
            self.setFlag(QGraphicsItem.ItemIsMovable, False)
            self.setFlag(QGraphicsItem.ItemIsSelectable, False)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        eventPos = event.pos().toPoint()
        if self.stretch:
            self.prepareGeometryChange()
            if self.stretchSide == layoutRect.sides[0]:
                self.setCursor(Qt.SizeHorCursor)
                self.rect.setLeft(eventPos.x())
            elif self.stretchSide == layoutRect.sides[1]:
                self.setCursor(Qt.SizeHorCursor)
                self.rect.setRight(eventPos.x() - int(self._pen.width() / 2))
            elif self.stretchSide == layoutRect.sides[2]:
                self.setCursor(Qt.SizeVerCursor)
                self.rect.setTop(eventPos.y())
            elif self.stretchSide == layoutRect.sides[3]:
                self.setCursor(Qt.SizeVerCursor)
                self.rect.setBottom(eventPos.y() - int(self._pen.width() / 2))
            self.update()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        super().mouseReleaseEvent(event)
        if self.stretch:
            self._stretch = False
            self._stretchSide = None
            self.setCursor(Qt.ArrowCursor)


class layoutInstance(layoutShape):
    def __init__(self, shapes: list[layoutShape]):
        super().__init__()
        
        # Direct attribute initialization
        self._shapes = shapes
        self._draft = False
        self._libraryName = self._cellName = self._viewName = self._instanceName = ""
        self._counter = 0
        
        # Cache pen creation
        self._selectedPen = self._get_cached_color("yellow")
        pen = QPen(self._selectedPen, 4, Qt.DashLine)
        pen.setCosmetic(True)
        self._selectedPen = pen
        
        # Batch flag operations
        self.setFiltersChildEvents(True)
        self.setHandlesChildEvents(True)
        self.setFlag(QGraphicsItem.ItemContainsChildrenInShape, True)
        
        # Defer expensive operations
        self._start = None
        self._shapes_set = False
        
        # Set shapes only if not empty
        if shapes:
            self.setShapes()

    def setShapes(self):
        if self._shapes_set or not self._shapes:
            return

        # Batch process all shapes
        for item in self._shapes:
            item.setFlags(QGraphicsItem.ItemStacksBehindParent)
            item.setFlag(QGraphicsItem.ItemIsSelectable, False)
            item.setParentItem(self)
        
        self._shapes_set = True

    def removeShapes(self):
        self.prepareGeometryChange()
        for item in self._shapes:
            item.setParentItem(None)
            del item
        self._shapes = list()

    def __repr__(self):
        return f"layoutInstance({self._shapes})"

    def boundingRect(self):
        return self.childrenBoundingRect().normalized().adjusted(-2, -2, 2, 2)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.NonCosmeticBrushPatterns)
        if option.state & QStyle.State_Selected:
            painter.setPen(self._selectedPen)
            painter.drawRect(self.childrenBoundingRect())


    def sceneEvent(self, event):
        """
        Do not propagate event if shape needs to keep still.
        """
        if not (
            self.scene().selectModes.selectInstance
            or self.scene().selectModes.selectAll
        ):
            return False
        else:
            super().sceneEvent(event)
            return True

    @property
    def libraryName(self):
        return self._libraryName

    @libraryName.setter
    def libraryName(self, value):
        self._libraryName = value

    @property
    def cellName(self):
        return self._cellName

    @cellName.setter
    def cellName(self, value: str):
        self._cellName = value

    @property
    def viewName(self):
        return self._viewName

    @viewName.setter
    def viewName(self, value: str):
        self._viewName = value

    @property
    def instanceName(self):
        return self._instanceName

    @instanceName.setter
    def instanceName(self, value: str):
        assert isinstance(value, str)
        self._instanceName = value

    @property
    def shapes(self):
        return self._shapes

    @shapes.setter
    def shapes(self, value: list[layoutShape]):
        self.removeShapes()
        self._shapes = value
        self.setShapes()

    @property
    def start(self):
        if self._start is None:
            self._start = self.childrenBoundingRect().bottomLeft()
        return self._start.toPoint()

    @property
    def counter(self):
        return self._counter

    @counter.setter
    def counter(self, value: int):
        if isinstance(value, int):
            self._counter = value

    def addShape(self, shape: layoutShape):
        self._shapes.append(shape)
        shape.setParentItem(self)


class layoutPcell(layoutInstance):
    def __init__(self, shapes: list):
        super().__init__(shapes)

    def __repr__(self):
        return f"layoutPcell({self._shapes}"


class layoutLine(layoutShape):
    def __init__(
        self,
        draftLine: QLineF,
        layer: ddef.layLayer,
        width: float = 1.0,
    ):
        super().__init__()
        self._draftLine = draftLine
        self._layer = layer
        self._width = width
        self._pen = QPen(self._layer.pcolor, self._layer.pwidth, self._layer.pstyle)
        self._selectedPen = QPen(QColor("yellow"), self._layer.pwidth, Qt.DashLine)
        self._rect = (
            QRectF(self._draftLine.p1(), self._draftLine.p2())
            .normalized()
            .adjusted(-2, -2, 2, 2)
        )
        self.setZValue(self._layer.z)

    def __repr__(self):
        return f"layoutLine({self._draftLine}, {self._layer}, {self._width})"

    def paint(self, painter, option, widget):
        if self.isSelected():
            painter.setPen(self._selectedPen)
        else:
            painter.setPen(self._pen)
        painter.drawLine(self._draftLine)

    def boundingRect(self):
        return self._rect


# "layer", "name", "mode", "width", "startExtend", "endExtend"


class layoutPath(layoutShape):
    def __init__(
        self,
        draftLine: QLineF,
        layer: ddef.layLayer,
        width: float = 1.0,
        startExtend: int = 0,
        endExtend: int = 0,
        mode: int = 0,
    ):
        """
        Initialize the class instance.

        Args:
            draftLine (QLineF): The draft line.
            layer (ddef.layLayer): The layer.
            width (float, optional): The width. Defaults to 1.0.
            startExtend (int, optional): The start extend. Defaults to 0.
            endExtend (int, optional): The end extend. Defaults to 0.
            mode (int, optional): The mode. Defaults to 0.
        """
        super().__init__()
        self.start = None
        self._draftLine = draftLine
        self._startExtend = startExtend
        self._endExtend = endExtend
        self._width = width
        self._layer = layer
        self._mode = mode
        self._name = ""
        self._stretch = False
        self._stretchSide = None
        self._definePensBrushes(self._layer)
        self._rect = QRectF(0, 0, 0, 0)
        self._angle = 0
        self._rectCorners(self._draftLine.angle())
        self.setZValue(self._layer.z)
        self._drcPen = QPen(QColor(255, 255, 0), 1, Qt.DashLine)

    def __repr__(self):
        return (
            f"layoutPath({self._draftLine}, {self._layer}"
            f"{self._width}, {self._startExtend}, {self._endExtend}, {self._mode})"
        )

    def _rectCorners(self, angle: float):
        match self._mode:
            case 0:  # manhattan
                self._createManhattanPath(angle)
            case 1:  # diagonal
                self._createDiagonalPath(angle)
            case 2:
                self._createAnyAnglePath(angle)
            case 3:
                self._createHorizontalPath(angle)
            case 4:
                self._createVerticalPath(angle)
        self._draftLine.setAngle(0)
        self._rect = self._extractRect()


    def _createManhattanPath(self, angle: float) -> None:
        """
        Creates a Manhattan path based on the given angle.

        :param angle: The angle in degrees.
        :type angle: float

        :return: None
        """
        self._angle = 90 * math.floor(((angle + 45) % 360) / 90)

    def _createDiagonalPath(self, angle: float) -> None:
        """
        Creates a manhattan or diagonal path based on the given angle.
        Parameters:
            angle (float): The angle in degrees.
        Returns:
            None
        """
        self._angle = 45 * math.floor(((angle + 22.5) % 360) / 45)

    def _createAnyAnglePath(self, angle: float) -> None:
        self._angle = angle

    def _createHorizontalPath(self, angle: float) -> None:
        self._angle = 180 * math.floor(((angle + 90) % 360) / 180)

    def _createVerticalPath(self, angle: float) -> None:
        angle = angle % 360
        if 0 <= angle < 180:
            self._angle = 90
        else:
            self._angle = 270

    def _extractRect(self):
        direction = self._draftLine.p2() - self._draftLine.p1()
        if direction == QPoint(0, 0):  # when the mouse pressed first time
            rect = (
                QRectF(self._draftLine.p1(), self._draftLine.p2())
                .adjusted(-2, -2, 2, 2)
                .normalized()
            )
        else:
            direction /= direction.manhattanLength()
            perpendicular = QPointF(-direction.y(), direction.x())
            point1 = (
                self._draftLine.p1()
                + perpendicular * self._width * 0.5
                - direction * self._startExtend
            ).toPoint()
            point2 = (
                self._draftLine.p2()
                - perpendicular * self._width * 0.5
                + direction * self._endExtend
            ).toPoint()
            rect = QRectF(point1, point2).normalized()
        return rect

    def paint(self, painter, option, widget):
        # Get scale once and cache it
        scale = self.scene().views()[0].transform().m11()
        if self.isSelected():
            if self._stretch:
                painter.setPen(self._stretchPen)
                self._updateTransformedBrush(self._stretchBrush, scale)
            else:
                painter.setPen(self._selectedPen)
                self._updateTransformedBrush(self._selectedBrush, scale)
        else:
            painter.setPen(self._pen)
            self._updateTransformedBrush(self._brush, scale)
        painter.setBrush(self._transformedBrush)
        painter.drawLine(self._draftLine)
        painter.drawRect(self._rect)

    def boundingRect(self) -> QRectF:
        return self._rect.adjusted(-2, -2, 2, 2)

    @property
    def draftLine(self):
        return self._draftLine

    @draftLine.setter
    def draftLine(self, line: QLineF):
        self.prepareGeometryChange()
        self._draftLine = line
        angle = self._draftLine.angle()
        self._rectCorners(angle)

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, width: float):
        self._width = width
        self.prepareGeometryChange()
        self._rectCorners(self._angle)

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, value: int):
        self.prepareGeometryChange()
        self._mode = value
        self._rectCorners(self._angle)

    @property
    def stretchSide(self):
        return self._stretchSide

    @stretchSide.setter
    def stretchSide(self, value: str):
        self.prepareGeometryChange()
        self._stretchSide = value

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value

    @property
    def startExtend(self) -> int:
        return self._startExtend

    @startExtend.setter
    def startExtend(self, value: str):
        self.prepareGeometryChange()
        self._startExtend = value
        self._rect = self._extractRect()

    @property
    def endExtend(self) -> int:
        return self._endExtend

    @endExtend.setter
    def endExtend(self, value: str):
        self.prepareGeometryChange()
        self._endExtend = value
        self._rect = self._extractRect()

    @property
    def angle(self) -> float:
        return self._angle

    @angle.setter
    def angle(self, value: float):
        self._angle = value
        self.prepareGeometryChange()
        self._rect = self._extractRect()
        self.setTransformOriginPoint(self.draftLine.p1())
        self.setRotation(-self._angle)

    @property
    def sceneEndPoints(self):
        return [
            self.mapToScene(self._draftLine.p1()).toPoint(),
            self.mapToScene(self._draftLine.p2()).toPoint(),
        ]

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        super().mousePressEvent(event)
        if self._layer.selectable:
            eventPos = event.pos().toPoint()
            if self._stretch:
                if (
                    eventPos - self._draftLine.p1().toPoint()
                ).manhattanLength() <= self.scene().snapDistance:
                    self._stretchSide = "p1"
                    self.setCursor(Qt.SizeHorCursor)
                elif (
                    eventPos - self._draftLine.p2().toPoint()
                ).manhattanLength() <= self.scene().snapDistance:
                    self._stretchSide = "p2"
                    self.setCursor(Qt.SizeHorCursor)
                self.scene().stretchPath(self, self._stretchSide)


class layoutRuler(layoutShape):
    def __init__(
        self,
        draftLine: QLineF,
        width: float,
        tickGap: float,
        tickLength: int,
        tickFont: QFont,
        mode: int = 0,
    ):
        """
        Initialize the TickLine object.

        Args:
            draftLine (QLineF): The draft line.
            width (float): The width of the line.
            tickGap (float): The gap between ticks.
            tickLength (int): The length of the ticks.
            tickFont (QFont): The font for tick labels.
            mode (int, optional): The mode. Defaults to 0.
        """
        super().__init__()

        self._draftLine = draftLine
        self._width = width
        self._tickGap = tickGap
        self._tickLength = tickLength
        self._mode = mode
        self._angle = 0
        self._rect = QRect(0, 0, 0, 0)
        penColour = QColor(255, 255, 40)
        # penColour.setAlpha(128)
        self._pen = QPen(penColour, self._width, Qt.SolidLine)
        self._pen.setCosmetic(True)
        self._selectedPen = QPen(Qt.red, self._width + 1, Qt.SolidLine)
        self._selectedPen.setCosmetic(True)
        # self._pen.setCosmetic(True)
        self._tickTuples = list()
        self._tickFont = tickFont
        self._determineAngle(self._draftLine.angle())
        self._fm = QFontMetrics(self._tickFont)
        self._fontHeight = self._fm.boundingRect("0").height()
        self._fontWidth = self._fm.boundingRect("0.000").width()
        # Enable child event filtering for filters and handles
        self.setFiltersChildEvents(True)
        self.setHandlesChildEvents(True)
        # Enable flag to indicate that the item contains children in shape
        self.setFlag(QGraphicsItem.ItemContainsChildrenInShape, True)
        self._createRulerTicks()
        # self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
        # self.update(self.boundingRect())
        self.setZValue(999)

    def __repr__(self):
        return (
            f"layoutRuler({self._draftLine}, {self._width}, {self._tickGap}, "
            f"{self._tickLength}, {self._tickFont}, {self._mode})"
        )

    def _determineAngle(self, angle: float):
        match self._mode:
            case 0:  # manhattan
                self._createManhattanRuler(angle)
            case 1:  # diagonal
                self._createDiagonalRuler(angle)
            case 2:
                self._createAnyAngleRuler(angle)
        self._draftLine.setAngle(0)
        self.setTransformOriginPoint(self.draftLine.p1())
        self.setRotation(-self._angle)

    def _createManhattanRuler(self, angle):
        if 0 <= angle <= 45 or 360 > angle > 315:
            self._angle = 0
        elif 45 < angle <= 135:
            self._angle = 90
        elif 135 < angle <= 225:
            self._angle = 180
        elif 225 < angle <= 315:
            self._angle = 270

    def _createDiagonalRuler(self, angle):
        if 0 <= angle <= 22.5 or 360 > angle > 337.5:
            self._angle = 0
        elif 22.5 < angle <= 67.5:
            self._angle = 45
        elif 67.5 < angle <= 112.5:
            self._angle = 90
        elif 112.5 < angle <= 157.5:
            self._angle = 135
        elif 157.5 < angle <= 202.5:
            self._angle = 180
        elif 202.5 < angle <= 247.5:
            self._angle = 225
        elif 247.5 < angle <= 292.5:
            self._angle = 270
        elif 292.5 < angle <= 337.5:
            self._angle = 315

    def _createAnyAngleRuler(self, angle):
        self._angle = angle

    def _createRulerTicks(self):
        self._tickTuples = list()
        direction = QPoint(0, 0)
        perpendicular = QPoint(0, 0)
        if self._draftLine.length() >= self._tickGap:
            numberOfTicks = math.ceil(self._draftLine.length() / self._tickGap)
            direction = self._draftLine.p2() - self._draftLine.p1()
            if direction != QPoint(
                0, 0
            ):  # no need for a tick when the line is zero length
                direction /= direction.manhattanLength()
                perpendicular = QPointF(-direction.y(), direction.x())
                for i in range(numberOfTicks):
                    self._tickTuples.append(
                        ddef.rulerTuple(
                            self._draftLine.p1()
                            + i * self._tickGap * direction
                            + perpendicular * self._tickLength,
                            QLineF(
                                self._draftLine.p1() + i * self._tickGap * direction,
                                self._draftLine.p1()
                                + i * self._tickGap * direction
                                + perpendicular * self._tickLength,
                            ),
                            str(float(i * self._tickGap)),
                        )
                    )
        self._tickTuples.append(
            ddef.rulerTuple(
                self.draftLine.p2() + direction * 2,
                QLineF(
                    self._draftLine.p2(),
                    self.draftLine.p2() + +perpendicular * self._tickLength,
                ),
                str(round(self._draftLine.length() / self._tickGap, 3)),
            )
        )
        self._rect = QRectF(
            self._draftLine.p1().toPoint(), self._draftLine.p2().toPoint()
        ).normalized()

    def boundingRect(self) -> QRectF:
        return self._rect.normalized().adjusted(
            -self._fontWidth, -self._fontHeight, self._fontWidth, self._fontHeight
        )

    def paint(self, painter, option, widget):
        if self.isSelected():
            painter.setPen(self._selectedPen)
            painter.drawRect(self.childrenBoundingRect())
        else:
            painter.setPen(self._pen)
        painter.drawLine(self._draftLine)
        painter.setFont(self._tickFont)
        for tickTuple in self._tickTuples:
            painter.drawLine(tickTuple.line)
            painter.save()
            painter.translate(tickTuple.point)
            painter.rotate(self.angle)
            painter.translate(-tickTuple.point)
            painter.drawText(tickTuple.point.x(), tickTuple.point.y(), tickTuple.text)
            painter.restore()

    @property
    def draftLine(self):
        return self._draftLine

    @draftLine.setter
    def draftLine(self, line: QLineF):
        self.prepareGeometryChange()
        self._draftLine = line
        angle = self._draftLine.angle()
        self._determineAngle(angle)
        self._createRulerTicks()

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, width: float):
        self._width = width

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, value: int):
        self._mode = value

    @property
    def tickFont(self):
        return self._tickFont

    @property
    def tickGap(self):
        return self._tickGap


class layoutLabel(layoutShape):
    LABEL_ALIGNMENTS = ["Left", "Center", "Right"]
    LABEL_ORIENTS = ["R0", "R90", "R180", "R270", "MX", "MX90", "MY", "MY90"]
    LABEL_SCALE = 10

    def __init__(
        self,
        start: QPoint,
        labelText: str,
        fontFamily: str,
        fontStyle: str,
        fontHeight: str,
        labelAlign: str,
        labelOrient: str,
        layer: ddef.layLayer,
    ):
        super().__init__()
        self._start = start
        self._labelText = labelText
        self._fontFamily = fontFamily
        self._fontStyle = fontStyle
        self._fontHeight = fontHeight
        self._labelAlign = labelAlign
        self._labelOrient = labelOrient
        self._layer = layer
        self._definePensBrushes(self._layer)
        self._labelFont = QFont(fontFamily)
        self._labelFont.setStyleName(fontStyle)
        self._labelFont.setKerning(False)
        self._labelFont.setPointSize(int(float(self._fontHeight)*self.LABEL_SCALE))
        # self.setOpacity(1)
        self._fm = QFontMetrics(self._labelFont)
        self._rect = self._fm.boundingRect(self._labelText)
        self._labelOptions = QTextOption()
        if self._labelAlign == layoutLabel.LABEL_ALIGNMENTS[0]:
            self._labelOptions.setAlignment(Qt.AlignmentFlag.AlignLeft)
        elif self._labelAlign == layoutLabel.LABEL_ALIGNMENTS[1]:
            self._labelOptions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        elif self._labelAlign == layoutLabel.LABEL_ALIGNMENTS[2]:
            self._labelOptions.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.setOrient()
        self.setZValue(self._layer.z)

    def __repr__(self):
        return (
            f"layoutLabel({self._start}, {self._labelText}, {self._fontFamily}, "
            f"{self._fontStyle}, {self._fontHeight}, {self._labelAlign}, "
            f"{self._labelOrient}, {self._layer})"
        )

    def setOrient(self):
        self.setTransformOriginPoint(self.mapFromScene(self._start))
        if self._labelOrient == layoutLabel.LABEL_ORIENTS[0]:
            self.setRotation(0)
        elif self._labelOrient == layoutLabel.LABEL_ORIENTS[1]:
            self.setRotation(90)
        elif self._labelOrient == layoutLabel.LABEL_ORIENTS[2]:
            self.setRotation(180)
        elif self._labelOrient == layoutLabel.LABEL_ORIENTS[3]:
            self.setRotation(270)
        elif self._labelOrient == layoutLabel.LABEL_ORIENTS[4]:
            self.flipTuple = (-1, 1)
        elif self._labelOrient == layoutLabel.LABEL_ORIENTS[5]:
            self.flipTuple = (-1, 1)
            self.setRotation(90)
        elif self._labelOrient == layoutLabel.LABEL_ORIENTS[6]:
            self.flipTuple = (1, -1)
            self.setRotation(90)

    def boundingRect(self):
        return (
            QRect(
                self._start.x(),
                self._start.y(),
                self._rect.width(),
                self._rect.height(),
            )
            .normalized()
            .adjusted(-2, -2, 2, 2)
        )  #

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.addRect(self.boundingRect())
        return path

    def paint(self, painter, option, widget):
        painter.setFont(self._labelFont)
        if self.isSelected():
            painter.setPen(self._selectedPen)
            painter.drawRect(self.boundingRect())
        else:
            painter.setPen(self._pen)
        painter.drawText(
            QPoint(self._start.x(), self._start.y() + self._rect.height()),
            self._labelText,
        )
        painter.drawPoint(self._start)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if self._layer.selectable:
            self.setFlag(QGraphicsItem.ItemIsMovable, True)
            self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        else:
            self.setFlag(QGraphicsItem.ItemIsMovable, False)
            self.setFlag(QGraphicsItem.ItemIsSelectable, False)

    @property
    def start(self):
        return self._start

    @start.setter
    def start(self, value: QPoint):
        self.prepareGeometryChange()
        self._start = value

    @property
    def labelText(self):
        return self._labelText

    @labelText.setter
    def labelText(self, value):
        self.prepareGeometryChange()
        self._labelText = value
        self._rect = self._fm.boundingRect(self._labelText)

    @property
    def labelFont(self):
        return self._labelFont

    @property
    def fontFamily(self) -> str:
        return self._labelFont.family()

    @fontFamily.setter
    def fontFamily(self, familyName):
        fontFamilies = QFontDatabase.families(QFontDatabase.Latin)
        fixedFamilies = [
            family for family in fontFamilies if QFontDatabase.isFixedPitch(family)
        ]
        if familyName in fixedFamilies:
            self._labelFont.setFamily(familyName)
        else:
            self.scene().logger.error(f"Not a valid font name: {familyName}")

    @property
    def fontStyle(self):
        return self._labelFont.styleName()

    @fontStyle.setter
    def fontStyle(self, value):
        if value in QFontDatabase.styles(self._labelFont.family()):
            self._labelFont.setStyleName(value)
        else:
            self.scene().logger.error(f"Not a valid font style: {value}")

    @property
    def fontHeight(self):
        return self._fontHeight

    @fontHeight.setter
    def fontHeight(self, value: str):
        self.prepareGeometryChange()
        self._fontHeight = value
        self._labelFont.setPointSize(int(float(self._fontHeight)*self.LABEL_SCALE))
        self._fm = QFontMetrics(self._labelFont)
        self._rect = self._fm.boundingRect(self._labelText)

    @property
    def labelAlign(self):
        return self._labelAlign

    @labelAlign.setter
    def labelAlign(self, value):
        self.prepareGeometryChange()
        self._labelAlign = value

    @property
    def labelOrient(self):
        return self._labelOrient

    @labelOrient.setter
    def labelOrient(self, value):
        self.prepareGeometryChange()
        self._labelOrient = value


class layoutPin(layoutShape):
    pinDirs = ["Input", "Output", "Inout"]
    pinTypes = ["Signal", "Ground", "Power", "Clock", "Digital", "Analog"]

    def __init__(
        self,
        start,
        end,
        pinName: str,
        pinDir: str,
        pinType: str,
        layer: ddef.layLayer,
    ):
        super().__init__()
        self._pinName = pinName
        self._pinDir = pinDir
        self._pinType = pinType
        self._connected = False  # True if the pin is connected to a net.
        self._rect = QRect(start, end).normalized()
        self._start = self._rect.topLeft()
        self._end = self._rect.bottomRight()
        self._layer = layer
        self._definePensBrushes(self._layer)
        self._label = None
        self._stretchSide = None
        self._stretchPen = QPen(QColor("red"), self._layer.pwidth, Qt.SolidLine)
        self.setZValue(self._layer.z)


    def __repr__(self):
        return (
            f"layoutPin({self._start}, {self._end}, {self._pinName}, {self._pinDir}, "
            f"{self._pinType}, {self._layer})"
        )

    def paint(self, painter, option, widget):
        # Get scale once and cache it
        scale = self.scene().views()[0].transform().m11()
        if self.isSelected():
            painter.setPen(self._selectedPen)
            self._updateTransformedBrush(self._selectedBrush, scale)
        else:
            painter.setPen(self._pen)
            self._updateTransformedBrush(self._brush, scale)
        painter.setBrush(self._brush)
        painter.drawRect(self._rect)

    def boundingRect(self):
        return self._rect.adjusted(-2, 2, 2, 2)

    @property
    def pinName(self):
        return self._pinName

    @pinName.setter
    def pinName(self, value):
        self._pinName = value

    @property
    def pinDir(self):
        return self._pinDir

    @pinDir.setter
    def pinDir(self, value):
        self._pinDir = value

    @property
    def pinType(self):
        return self._pinType

    @pinType.setter
    def pinType(self, value):
        self._pinType = value

    @property
    def start(self):
        return self._start

    @start.setter
    def start(self, start: QPoint):
        self.prepareGeometryChange()
        self._rect = QRectF(start, self._end).normalized()
        self._start = self._rect.topLeft()

    @property
    def end(self):
        return self._end

    @end.setter
    def end(self, end: QPoint):
        self.prepareGeometryChange()
        self._rect = QRectF(self._start, end).normalized()
        self._end = self._rect.bottomRight()

    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, value: layoutLabel):
        if isinstance(value, layoutLabel):
            self._label = value
        else:
            self.scene().logger.error("Not a Label")

    @property
    def rect(self):
        return self._rect

    @rect.setter
    def rect(self, rect: QRect):
        self.prepareGeometryChange()
        self._rect = rect

    @property
    def stretchSide(self):
        return self._stretchSide

    @stretchSide.setter
    def stretchSide(self, value: str):
        self.prepareGeometryChange()
        self._stretchSide = value

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        super().mousePressEvent(event)
        if self._layer.selectable:
            self.setFlag(QGraphicsItem.ItemIsMovable, True)
            self.setFlag(QGraphicsItem.ItemIsSelectable, True)
            eventPos = event.pos().toPoint()
            if self._stretch:
                self.setFlag(QGraphicsItem.ItemIsMovable, False)
                if eventPos.x() == self._rect.left():
                    if self._rect.top() <= eventPos.y() <= self._rect.bottom():
                        self.setCursor(Qt.SizeHorCursor)
                        self._stretchSide = layoutRect.sides[0]
                elif eventPos.x() == self._rect.right():
                    if self._rect.top() <= eventPos.y() <= self._rect.bottom():
                        self.setCursor(Qt.SizeHorCursor)
                        self._stretchSide = layoutRect.sides[1]
                elif eventPos.y() == self._rect.top():
                    if self._rect.left() <= eventPos.x() <= self._rect.right():
                        self.setCursor(Qt.SizeVerCursor)
                        self._stretchSide = layoutRect.sides[2]
                elif eventPos.y() == self._rect.bottom():
                    if self._rect.left() <= eventPos.x() <= self._rect.right():
                        self.setCursor(Qt.SizeVerCursor)
                        self._stretchSide = layoutRect.sides[3]
        else:
            self.setFlag(QGraphicsItem.ItemIsMovable, False)
            self.setFlag(QGraphicsItem.ItemIsSelectable, False)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        eventPos = event.pos().toPoint()
        if self._stretch and self._stretchSide:
            self.prepareGeometryChange()
            if self.stretchSide == layoutRect.sides[0]:
                self.setCursor(Qt.SizeHorCursor)
                self.rect.setLeft(eventPos.x())
            elif self.stretchSide == layoutRect.sides[1]:
                self.setCursor(Qt.SizeHorCursor)
                self.rect.setRight(eventPos.x() - int(self._pen.width() / 2))
            elif self.stretchSide == layoutRect.sides[2]:
                self.setCursor(Qt.SizeVerCursor)
                self.rect.setTop(eventPos.y())
            elif self.stretchSide == layoutRect.sides[3]:
                self.setCursor(Qt.SizeVerCursor)
                self.rect.setBottom(eventPos.y() - int(self._pen.width() / 2))
            self.update()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        super().mouseReleaseEvent(event)
        if self.stretch:
            self._stretch = False
            self._stretchSide = None
            self.setCursor(Qt.ArrowCursor)


class layoutVia(layoutShape):
    def __init__(
        self,
        start: QPoint,
        viaDefTuple: ddef.viaDefTuple,
        width: int,
        height: int,
    ):
        super().__init__()
        end = start + QPoint(width, height)
        self._rect = QRectF(start, end).normalized().toRect()
        self._start = self._rect.topLeft()
        self._end = self._rect.bottomRight()
        self._viaDefTuple = viaDefTuple
        self._layer = viaDefTuple.layer
        self._type = viaDefTuple.type
        self._width = width
        self._height = height
        self._definePensBrushes(self._layer)
        self.setZValue(self._layer.z)


    def __repr__(self):
        return f"layoutVia({self._start}, {self._end}, {self._layer})"

    def paint(self, painter, option, widget):
        scale = self.scene().views()[0].transform().m11()
        if self.isSelected():
            painter.setPen(self._selectedPen)
        else:
            painter.setPen(self._pen)
        self._updateTransformedBrush(self._brush, scale)
        painter.setBrush(self._transformedBrush)
        painter.drawRect(self._rect)
        painter.drawLine(self._rect.bottomLeft(), self._rect.topRight())
        painter.drawLine(self._rect.topLeft(), self._rect.bottomRight())

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if self._layer.selectable:
            self.setFlag(QGraphicsItem.ItemIsMovable, True)
            self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        else:
            self.setFlag(QGraphicsItem.ItemIsMovable, False)
            self.setFlag(QGraphicsItem.ItemIsSelectable, False)

    def boundingRect(self):
        return self._rect.normalized().adjusted(-2, -2, 2, 2)

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.addRect(self.boundingRect())
        return path

    @property
    def rect(self):
        return self._rect

    @rect.setter
    def rect(self, rect: QRect):
        self.prepareGeometryChange()
        self._rect = rect

    @property
    def start(self):
        return self._start

    @start.setter
    def start(self, start: QPoint):
        self.prepareGeometryChange()
        self._rect.moveTo(self.mapFromScene(start))

    @property
    def width(self):
        return self._rect.width()

    @width.setter
    def width(self, value: int):
        self.prepareGeometryChange()
        self._rect.setWidth(value)

    @property
    def height(self):
        return self._rect.height()

    @height.setter
    def height(self, value: int):
        self._rect.setHeight(value)

    @property
    def viaDefTuple(self):
        return self._viaDefTuple

    @property
    def type(self):
        return self._type


class layoutViaArray(layoutShape):
    def __init__(self, start: QPoint, prototype_via, xs: float,
                 ys: float, xnum: int, ynum: int,
                 ):
        super().__init__()
        self._prototype_via = prototype_via
        self._ynum = ynum # number of rows
        self._xnum = xnum # number of columns
        self._xs = xs # column spacing
        self._ys = ys # row spacing
        self._start = start # top-left corner location
        self._via =  layoutVia(
                    self._start,
                    self._prototype_via.viaDefTuple,
                    self._prototype_via.width,
                    self._prototype_via.height
                )
        self._via_array = []
        self._create_array()
        self.setFiltersChildEvents(True)
        self.setHandlesChildEvents(True)
        self.setFlag(QGraphicsItem.ItemContainsChildrenInShape, True)
        self._selectedPen = QPen(QColor("yellow"), 4, Qt.DashLine)
        self._selectedPen.setCosmetic(True)

    def _create_array(self):
        # Pre-calculate constants
        x_step = self._xs + self._prototype_via.width
        y_step = self._ys + self._prototype_via.height
        start_x, start_y = self._start.x(), self._start.y()
        via_def = self._prototype_via.viaDefTuple
        via_width = self._prototype_via.width
        via_height = self._prototype_via.height

        # Create flat list using itertools.product
        vias = [self._create_via(start_x + col * x_step, start_y + row * y_step,
                                 via_def, via_width, via_height)
                for row, col in
                itertools.product(range(self._ynum), range(self._xnum))]

        # Reshape into 2D array
        self._via_array = [vias[i:i + self._xnum] for i in
                           range(0, len(vias), self._xnum)]

    def _create_via(self, x, y, via_def, width, height):
        via = layoutVia(QPoint(x, y), via_def, width, height)
        via.setFlag(QGraphicsItem.ItemIsSelectable, False)
        via.setFlag(QGraphicsItem.ItemStacksBehindParent, True)
        via.setParentItem(self)
        return via

    # def _create_array(self):
    #     self._via_array = []
    #     for row in range(self._ynum):
    #         via_row = []
    #         for col in range(self._xnum):
    #             x = self._start.x() + col * (self._xs +
    #                                          self._prototype_via.width)
    #             y = self._start.y() + row * (self._ys +
    #                                          self._prototype_via.height)
    #             via = layoutVia(
    #                 QPoint(x, y),
    #                 self._prototype_via.viaDefTuple,
    #                 self._prototype_via.width,
    #                 self._prototype_via.height
    #             )
    #             via.setFlag(QGraphicsItem.ItemIsSelectable, False)
    #             via.setFlag(QGraphicsItem.ItemStacksBehindParent, True)
    #             via.setParentItem(self)
    #             via_row.append(via)
    #         self._via_array.append(via_row)

    def boundingRect(self) -> QRectF:
        return self.childrenBoundingRect()

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.addRect(self.childrenBoundingRect())
        return path

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.NonCosmeticBrushPatterns)
        if option.state & QStyle.State_Selected:
            painter.setPen(self._selectedPen)
            painter.drawRect(self.childrenBoundingRect())


    @property
    def via_array(self):
        return self._via_array

    @property
    def ynum(self):
        return self._ynum

    @property
    def xnum(self):
        return self._xnum

    @property
    def start(self)-> QPoint:
        return self._start

    @property
    def xs(self) -> float:
        return self._xs

    @property
    def ys(self):
        return self._ys

    @property
    def via(self):
        return self._via

    @property
    def height(self):
        return self._via.height

    @property
    def width(self):
        return self._via.width


# class layoutViaArray(layoutShape):
#     def __init__(
#         self,
#         start: QPoint,
#         via: layoutVia,
#         xs: float,
#         ys: float,
#         xnum: int,
#         ynum: int,
#     ):
#         super().__init__()
#         self._start = start
#         self._via = via  # prototype via
#         self._xnum = xnum
#         self._ynum = ynum
#         self._xs = xs
#         self._ys = ys
#         # Initialize flags and properties first
#         self.setFiltersChildEvents(True)
#         self.setHandlesChildEvents(True)
#         self.setFlag(QGraphicsItem.ItemContainsChildrenInShape, True)
#         self._selectedPen = QPen(QColor("yellow"), 1, Qt.DashLine)
#         # Now place vias after parent is fully initialized
#         self._placeVias(self._via, self._xnum, self._ynum)
#         self._rect = self.childrenBoundingRect()
#
#     def _placeVias(self, via: layoutVia, xnum: int, ynum: int) -> None:
#         for childVia in self.childItems():
#             if self.scene():
#                 self.scene().removeItem(childVia)
#
#         for i, j in itertools.product(range(xnum), range(ynum)):
#             item = layoutVia(
#                 QPoint(
#                     int(self._start.x() + i * (self._xs + via.width)),
#                     int(self._start.y() + j * (self._ys + via.height)),
#                 ),
#                 via.viaDefTuple,
#                 int(via.width),
#                 int(via.height),
#             )
#
#             item.setFlag(QGraphicsItem.ItemIsSelectable, False)
#             item.setFlag(QGraphicsItem.ItemStacksBehindParent, True)
#             item.setParentItem(self)
#
#     def __repr__(self):
#         return (f"layoutViaArray("
#                 f"{self._start},{self._via}, {self._xs}, {self._ys},"
#                 f" {self._xnum},"
#                 f" {self._ynum})")
#
#     def boundingRect(self) -> QRectF:
#         return self.childrenBoundingRect()
#
#     def paint(self, painter, option, widget):
#         if self.isSelected():
#             painter.setPen(self._selectedPen)
#             painter.drawRect(self._rect)
#         else:
#             super().paint(painter,option,widget)
#
#     def shape(self) -> QPainterPath:
#         path = QPainterPath()
#         path.addRect(self._rect)
#         return path
#
#     @property
#     def start(self):
#         return self._start
#
#     @start.setter
#     def start(self, start: QPoint):
#         self.prepareGeometryChange()
#         self._start = start
#         self._placeVias(self._via, self._xnum, self._ynum)
#         self._rect = self.childrenBoundingRect()
#
#     @property
#     def xnum(self) -> int:
#         return self._xnum
#
#     @xnum.setter
#     def xnum(self, value: int):
#         self.prepareGeometryChange()
#         self._xnum = value
#         self._placeVias(self._via, self._xnum, self._ynum)
#         self._rect = self.childrenBoundingRect()
#
#     @property
#     def ynum(self) -> int:
#         return self._ynum
#
#     @ynum.setter
#     def ynum(self, value: int):
#         self.prepareGeometryChange()
#         self._ynum = value
#         self._placeVias(self._via, self._xnum, self._ynum)
#         self._rect = self.childrenBoundingRect()
#
#     @property
#     def via(self):
#         return self._via
#
#     @via.setter
#     def via(self, value: layoutVia):
#         self.prepareGeometryChange()
#         self._via = value
#         self._placeVias(self._via, self._xnum, self._ynum)
#         self._rect = self.childrenBoundingRect()
#
#     @property
#     def width(self):
#         return self._via.width
#
#     @width.setter
#     def width(self, value: float):
#         self.prepareGeometryChange()
#         self._via.width = value
#         self._placeVias(self._via, self._xnum, self._ynum)
#         self._rect = self.childrenBoundingRect()
#
#     @property
#     def height(self):
#         return self._via.height
#
#     @height.setter
#     def height(self, value: float):
#         self.prepareGeometryChange()
#         self._via.height = value
#         self._placeVias(self._via, self._xnum, self._ynum)
#         self._rect = self.childrenBoundingRect()
#
#     @property
#     def xs(self) -> float:
#         return self._xs
#
#     @xs.setter
#     def xs(self, value: float):
#         self.prepareGeometryChange()
#         self._xs = value
#         self._placeVias(self._via, self._xnum, self._ynum)
#         self._rect = self.childrenBoundingRect()
#
#     @property
#     def ys(self) -> float:
#         return self._ys
#
#     @ys.setter
#     def ys(self, value: float):
#         self.prepareGeometryChange()
#         self._ys = value
#         self._placeVias(self._via, self._xnum, self._ynum)
#         self._rect = self.childrenBoundingRect()
#
#     @property
#     def viaDefTuple(self):
#         return self._via.viaDefTuple
#
#     @viaDefTuple.setter
#     def viaDefTuple(self, value: ddef.viaDefTuple):
#         self._via.viaDefTuple = value
#         self.prepareGeometryChange()
#         self._placeVias(self._via, self._xnum, self._ynum)
#         self._rect = self.childrenBoundingRect()


class layoutPolygon(layoutShape):
    __slots__ = ('_points', '_layer', '_polygon', '_selectedCorner', '_selectedCornerIndex')
    
    def __init__(self, points: list, layer: ddef.layLayer):
        super().__init__()
        self._points = points
        self._layer = layer
        self._selectedCorner = QPoint(99999, 99999)
        self._selectedCornerIndex = 999
        
        # Defer expensive operations
        self._polygon = None
        self._definePensBrushes(self._layer)
        self.setZValue(self._layer.z)
        self._flipTuple = (1, 1)  # Direct assignment instead of property

    def __repr__(self):
        return f"layoutPolygon({self._points}, {self._layer})"

    def paint(self, painter, option, widget):
        # Cache frequently accessed values
        selected = self.isSelected()
        scale = self.scene().views()[0].transform().m11()
        
        # Set pen and brush based on selection state
        if selected:
            painter.setPen(self._selectedPen)
            self._updateTransformedBrush(self._selectedBrush, scale)
            # Use cached corner coordinates (avoid QPoint creation)
            if self._stretch and self._selectedCorner.x() != 99999:
                painter.drawEllipse(self._selectedCorner, 5, 5)
        else:
            painter.setPen(self._pen)
            self._updateTransformedBrush(self._brush, scale)
        
        painter.setBrush(self._transformedBrush)
        painter.drawPolygon(self.polygon)


    def boundingRect(self) -> QRectF:
        return self.polygon.boundingRect()

    @property
    def polygon(self):
        if self._polygon is None:
            self._polygon = QPolygonF(self._points)
        return self._polygon

    @property
    def points(self) -> list:
        return self._points

    @points.setter
    def points(self, value: list):
        self.prepareGeometryChange()
        self._points = value
        self._polygon = None  # Invalidate cache

    def addPoint(self, point: QPoint):
        self.prepareGeometryChange()
        self._points.append(point)
        self._polygon = None  # Invalidate cache

    @property
    def tempLastPoint(self):
        return self._points[-1]

    @tempLastPoint.setter
    def tempLastPoint(self, value: QPoint):
        self.prepareGeometryChange()
        self._polygon = QPolygonF([*self._points, value])

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        super().mousePressEvent(event)
        if self._layer.selectable:
            self.setFlag(QGraphicsItem.ItemIsMovable, True)
            self.setFlag(QGraphicsItem.ItemIsSelectable, True)
            eventPos = event.pos().toPoint()
            if self._stretch:
                self.setFlag(QGraphicsItem.ItemIsMovable, False)
                for point in self._points:
                    if (
                        eventPos - point
                    ).manhattanLength() <= self.scene().snapDistance:
                        self._selectedCorner = point
                        self._selectedCornerIndex = self._points.index(point)
        else:
            self.setFlag(QGraphicsItem.ItemIsMovable, False)
            self.setFlag(QGraphicsItem.ItemIsSelectable, False)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        eventPos = event.pos().toPoint()
        if self._stretch and self._selectedCornerIndex != 999:
            self._points[self._selectedCornerIndex] = eventPos
            self.points = self._points
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        super().mouseReleaseEvent(event)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        if self.stretch:
            self._stretch = False
            self._stretchSide = None
            self.setCursor(Qt.ArrowCursor)
            self._selectedCornerIndex = 999
