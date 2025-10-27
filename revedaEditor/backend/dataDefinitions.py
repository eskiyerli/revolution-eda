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

from typing import NamedTuple, Union
from dataclasses import dataclass
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtGui import QColor


@dataclass
class edLayer:
    name: str = ""  # edLayer name
    purpose: str = "drawing"  # edLayer purpose
    pcolor: QColor = Qt.black  # pen colour
    pwidth: int = 1  # pen width
    pstyle: Qt.PenStyle = Qt.SolidLine  # pen style
    bcolor: QColor = Qt.transparent  # brush colour
    bstyle: Qt.BrushStyle = Qt.SolidPattern  # brush texture
    z: int = 1  # z-index
    selectable: bool = True  # selectable
    visible: bool = True  # visible
    gdsLayer: int = 0  # gds edLayer
    datatype: int = 0  # gds datatype


@dataclass
class layLayer:
    name: str = "Default"  # edLayer name
    purpose: str = "drawing"  # edLayer purpose
    pcolor: QColor = Qt.black  # pen colour
    pwidth: int = 1  # pen width
    pstyle: Qt.PenStyle = Qt.SolidLine  # pen style
    bcolor: QColor = Qt.transparent  # brush colour
    btexture: str = ""  # brush texture
    z: int = 1  # z-index
    selectable: bool = True  # selectable
    visible: bool = True  # visible
    gdsLayer: int = 0  # gds edLayer
    datatype: int = 0  # gds datatype

    @classmethod
    def filterByGDSLayer(cls, layer_list, gdsLayer: int, gdsDatatype: int) -> 'layLayer':
        for layer in layer_list:
            if layer.gdsLayer == gdsLayer and layer.datatype == gdsDatatype:
                return layer
        return cls()

@dataclass
class editModes:
    selectItem: bool
    deleteItem: bool
    moveItem: bool
    copyItem: bool
    rotateItem: bool
    changeOrigin: bool
    panView: bool
    stretchItem: bool

    def setMode(self, attribute):
        for key in self.__dict__.keys():
            self.__dict__[key] = False
        self.__dict__[attribute] = True


@dataclass
class symbolModes(editModes):
    drawPin: bool
    drawArc: bool
    drawRect: bool
    drawLine: bool
    addLabel: bool
    drawCircle: bool
    drawPolygon: bool


@dataclass
class schematicModes(editModes):
    drawPin: bool
    drawWire: bool
    drawBus: bool
    drawText: bool
    addInstance: bool
    nameNet: bool


@dataclass
class layoutModes(editModes):
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


@dataclass
class selectModes:
    selectAll: bool

    def setMode(self, attribute):
        for key in self.__dict__.keys():
            self.__dict__[key] = False
        self.__dict__[attribute] = True


@dataclass
class schematicSelectModes(selectModes):
    selectDevice: bool
    selectNet: bool
    selectPin: bool


@dataclass
class layoutSelectModes(selectModes):
    selectInstance: bool
    selectPath: bool
    selectVia: bool
    selectLabel: bool
    selectText: bool
    selectPin: bool


# library editor related named tuples
class viewTuple(NamedTuple):
    libraryName: str
    cellName: str
    viewName: str


class cellTuple(NamedTuple):
    libraryName: str
    cellName: str


class viewItemTuple(NamedTuple):
    libraryItem: object
    cellItem: object
    viewItem: object


# layout related tuples
class layoutPathTuple(NamedTuple):
    layer: layLayer
    name: str
    mode: str
    width: float
    startExtend: bool
    endExtend: bool


class layoutPinTuple(NamedTuple):
    pinName: str
    pinDir: str
    pinType: str
    pinLayer: layLayer


class layoutLabelTuple(NamedTuple):
    labelText: str
    fontFamily: str
    fontStyle: str
    fontHeight: str
    labelAlign: str
    labelOrient: str
    labelLayer: str


class rulerTuple(NamedTuple):
    point: Union[QPoint, QPointF]
    line: tuple
    text: str


# # pdk related classes and namedtuples
# # this tuple defines the minimum dimensions of a via
# # This can be extended to define the maximum dimensions

# used in PDK
class viaDefTuple(NamedTuple):
    name: str
    layer: layLayer
    type: str
    minWidth: float
    maxWidth: float
    minHeight: float
    maxHeight: float
    minSpacing: float
    maxSpacing: float

# Used to define the via prototype
class singleViaTuple(NamedTuple):
    viaDefTuple: viaDefTuple
    width: float
    height: float

# both single vias and vias arrays are defined by this
class arrayViaTuple(NamedTuple):
    singleViaTuple: singleViaTuple
    xs: float
    ys: float
    xnum: int
    ynum: int


# rectangle coordinates tuple


class rectCoords(NamedTuple):
    left: float
    top: float
    w: float
    h: float

