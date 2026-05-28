#    “Commons Clause” License Condition v1.0
#   #
#    The Software is provided to you by the Licensor under the License, as defined
#    below, subject to the following condition.
#   #
#    Without limiting other conditions in the License, the grant of rights under the
#    License will not include, and the License does not grant to you, the right to
#    Sell the Software.
#   #
#    For purposes of the foregoing, “Sell” means practicing any or all of the rights
#    granted to you under the License to provide to third parties, for a fee or other
#    consideration (including without limitation fees for hosting) a product or service whose value
#    derives, entirely or substantially, from the functionality of the Software. Any
#    license notice or attribution required by the License must also include this
#    Commons Clause License Condition notice.
#   #
#    Software: Revolution EDA
#    License: Mozilla Public License 2.0
#    Licensor: Revolution Semiconductor (Registered in the Netherlands)

from dataclasses import dataclass
from typing import NamedTuple, Union

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QColor

from revedaEditor.backend import lib_back_end as libb


@dataclass
class EdLayer:
    name: str = ""  # EdLayer name
    purpose: str = "drawing"  # EdLayer purpose
    pcolor: QColor = Qt.black  # pen colour
    pwidth: int = 1  # pen width
    pstyle: Qt.PenStyle = Qt.SolidLine  # pen style
    bcolor: QColor = Qt.transparent  # brush colour
    bstyle: Qt.BrushStyle = Qt.SolidPattern  # brush texture
    z: int = 1  # z-index
    selectable: bool = True  # selectable
    visible: bool = True  # visible
    gdsLayer: int = 0  # gds Layer
    datatype: int = 0  # gds datatype


@dataclass
class LayLayer:
    name: str = "Default"  # EdLayer name
    purpose: str = "drawing"  # EdLayer purpose
    pcolor: QColor = Qt.black  # pen colour
    pwidth: int = 1  # pen width
    pstyle: Qt.PenStyle = Qt.SolidLine  # pen style
    bcolor: QColor = Qt.transparent  # brush colour
    btexture: str = ""  # brush texture
    z: int = 1  # z-index
    selectable: bool = True  # selectable
    visible: bool = True  # visible
    gdsLayer: int = 0  # gds Layer
    datatype: int = 0  # gds datatype

    @classmethod
    def filterByGDSLayer(
            cls, layer_list, gdsLayer: int, gdsDatatype: int
    ) -> "LayLayer":
        for layer in layer_list:
            if layer.gdsLayer == gdsLayer and layer.datatype == gdsDatatype:
                return layer
        return cls()


@dataclass
class EditModes:
    selectItem: bool
    deleteItem: bool
    moveItem: bool
    constrainedMoveItem: bool
    copyItem: bool
    rotateItem: bool
    changeOrigin: bool
    panView: bool
    zoomView: bool
    stretchItem: bool
    alignItems: bool

    def setMode(self, attribute):
        for key in self.__dict__.keys():
            self.__dict__[key] = False
        self.__dict__[attribute] = True

    def mode(self):
        for key, value in self.__dict__.items():
            if value:
                return key


@dataclass
class SymbolModes(EditModes):
    drawPin: bool
    drawArc: bool
    drawRect: bool
    drawLine: bool
    addLabel: bool
    drawCircle: bool
    drawPolygon: bool


@dataclass
class SchematicModes(EditModes):
    drawPin: bool
    drawWire: bool
    drawBus: bool
    drawText: bool
    addInstance: bool
    nameNet: bool


@dataclass
class LayoutModes(EditModes):
    drawPath: bool
    drawPin: bool
    drawArc: bool
    drawPolygon: bool
    addLabel: bool
    addVia: bool
    drawRect: bool
    drawLine: bool
    drawCircle: bool
    drawRuler: bool
    addInstance: bool
    cutShape: bool


@dataclass
class SelectModes:
    selectAll: bool

    def setMode(self, attribute):
        for key in self.__dict__.keys():
            self.__dict__[key] = False
        self.__dict__[attribute] = True


@dataclass
class SchematicSelectModes(SelectModes):
    selectDevice: bool
    selectNet: bool
    selectPin: bool


@dataclass
class LayoutSelectModes(SelectModes):
    selectInstance: bool
    selectPath: bool
    selectVia: bool
    selectLabel: bool
    selectText: bool
    selectPin: bool


# library editor related named tuples
class ViewNameTuple(NamedTuple):
    libraryName: str
    cellName: str
    viewName: str


class CellTuple(NamedTuple):
    libraryName: str
    cellName: str


class ViewItemTuple(NamedTuple):
    LibraryItem: libb.LibraryItem
    CellItem: libb.CellItem
    ViewItem: libb.ViewItem

    def convertToViewNameTuple(self) -> ViewNameTuple:
        return ViewNameTuple(
            libraryName=self.LibraryItem.libraryName,
            cellName=self.CellItem.cellName,
            viewName=self.ViewItem.viewName
        )


class LayoutPinTuple(NamedTuple):
    pinName: str
    pinDir: str
    pinType: str
    pinLayer: LayLayer


class LayoutLabelTuple(NamedTuple):
    labelText: str
    fontFamily: str
    fontStyle: str
    fontHeight: str
    labelAlign: str
    labelOrient: str
    labelLayer: str


class RulerTuple(NamedTuple):
    point: Union[QPoint, QPointF]
    line: tuple
    text: str


# # pdk related classes and namedtuples
# # this tuple defines the minimum dimensions of a via
# # This can be extended to define the maximum dimensions


# used in PDK
class ViaDefTuple(NamedTuple):
    name: str
    layer: LayLayer
    type: str
    minWidth: float
    maxWidth: float
    minHeight: float
    maxHeight: float
    minSpacing: float
    maxSpacing: float


# Used to define the via prototype
class SingleViaTuple(NamedTuple):
    ViaDefTuple: ViaDefTuple
    width: float
    height: float


# both single vias and vias arrays are defined by this
class ArrayViaTuple(NamedTuple):
    SingleViaTuple: SingleViaTuple
    xs: float
    ys: float
    xnum: int
    ynum: int


# rectangle coordinates tuple
class RectCoords(NamedTuple):
    left: float
    top: float
    w: float
    h: float


class LayoutPathDefTuple(NamedTuple):
    name: str
    layer: LayLayer
    type: str
    minWidth: float
    maxWidth: float
    minLength: float
    maxLength: float
    minSpacing: float
    maxSpacing: float


class LayoutPathTuple(NamedTuple):
    name: str
    layer: LayLayer
    pathMode: int
    width: float
    startExtend: float
    endExtend: float
