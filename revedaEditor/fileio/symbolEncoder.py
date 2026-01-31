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

import json
from typing import Dict, Any

from PySide6.QtCore import QPointF

import revedaEditor.common.labels as lbl
import revedaEditor.common.shapes as shp


class symbolAttribute(object):
    def __init__(self, name: str, definition: str):
        self._name = name
        self._definition = definition

    def __str__(self):
        return f"{self.name}: {self.definition}"

    def __repr__(self):
        return f"{type(self)}({self.name},{self.definition})"

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        assert isinstance(value, str)
        self._name = value

    @property
    def definition(self):
        return self._definition

    @definition.setter
    def definition(self, value):
        assert isinstance(value, str)
        self._definition = value


class symbolEncoder(json.JSONEncoder):
    def default(self, item: Any) -> Dict[str, Any]:
        if isinstance(item, shp.symbolRectangle):
            return self._encodeSymbolRectangle(item)
        elif isinstance(item, shp.symbolLine):
            return self._encodeSymbolLine(item)
        elif isinstance(item, shp.symbolCircle):
            return self._encodeSymbolCircle(item)
        elif isinstance(item, shp.symbolArc):
            return self._encodeSymbolArc(item)
        elif isinstance(item, shp.symbolPolygon):
            return self._encodeSymbolPolygon(item)
        elif isinstance(item, shp.symbolPin):
            return self._encodeSymbolPin(item)
        elif isinstance(item, shp.text):
            return self._encodeText(item)
        elif isinstance(item, lbl.symbolLabel):
            return self._encodeSymbolLabel(item)
        elif isinstance(item, symbolAttribute):
            return self._encodeSymbolAttribute(item)
        return super().default(item)

    def _encodeSymbolRectangle(self, item: shp.symbolRectangle) -> Dict[str, Any]:
        return {
            "type": "rect",
            "rect": item.rect.getCoords(),
            "loc": self._subtract_point(item.scenePos(), item.scene().origin),
            "ang": item.angle,
            "fl": item.flipTuple,
        }

    def _encodeSymbolLine(self, item: shp.symbolLine) -> Dict[str, Any]:
        return {
            "type": "line",
            "st": item.start.toTuple(),
            "end": item.end.toTuple(),
            "loc": self._subtract_point(item.scenePos(), item.scene().origin),
            "ang": item.angle,
            "fl": item.flipTuple,
        }

    def _encodeSymbolCircle(self, item: shp.symbolCircle) -> Dict[str, Any]:
        return {
            "type": "circle",
            "cen": item.centre.toTuple(),
            "end": item.end.toTuple(),
            "loc": self._subtract_point(item.scenePos(), item.scene().origin),
            "ang": item.angle,
            "fl": item.flipTuple,
        }

    def _encodeSymbolArc(self, item: shp.symbolArc) -> Dict[str, Any]:
        return {
            "type": "arc",
            "st": item.start.toTuple(),
            "end": item.end.toTuple(),
            "loc": self._subtract_point(item.scenePos(), item.scene().origin),
            "ang": item.angle,
            "fl": item.flipTuple,
            "at": shp.symbolArc.arcTypes.index(item.arcType),
        }

    def _encodeSymbolPolygon(self, item: shp.symbolPolygon) -> Dict[str, Any]:
        return {
            "type": "polygon",
            "ps": [item.mapToScene(p).toTuple() for p in item.points],
            "fl": item.flipTuple,
        }

    def _encodeSymbolPin(self, item: shp.symbolPin) -> Dict[str, Any]:
        return {
            "type": "pin",
            "st": item.start.toTuple(),
            "nam": item.pinName,
            "pd": item.pinDir,
            "pt": item.pinType,
            "loc": self._subtract_point(item.scenePos(), item.scene().origin),
            "ang": item.angle,
            "fl": item.flipTuple,
        }

    def _encodeText(self, item: shp.text) -> Dict[str, Any]:
        return {
            "type": "text",
            "st": item.start.toTuple(),
            "tc": item.textContent,
            "ff": item.fontFamily,
            "fs": item.fontStyle,
            "th": item.textHeight,
            "ta": item.textAlignment,
            "to": item.textOrient,
            "loc": self._subtract_point(item.scenePos(), item.scene().origin),
            "ang": item.angle,
            "fl": item.flipTuple,
        }

    def _encodeSymbolLabel(self, item: lbl.symbolLabel) -> Dict[str, Any]:
        return {
            "type": "label",
            "st": item.start.toTuple(),
            "nam": item.labelName,
            "def": item.labelDefinition,
            "txt": item.labelText,
            "val": item.labelValue,
            "vis": item.labelVisible,
            "lt": item.labelType,
            "ht": item.labelHeight,
            "al": item.labelAlign,
            "or": item.labelOrient,
            "use": item.labelUse,
            "loc": self._subtract_point(item.scenePos(), item.scene().origin),
            "fl": item.flipTuple,
        }

    def _encodeSymbolAttribute(self, item: symbolAttribute) -> Dict[str, Any]:
        return {
            "type": "attr",
            "nam": item.name,
            "def": item.definition,
        }

    @staticmethod
    def _subtract_point(point: QPointF, origin: QPointF) -> tuple:
        return (point - origin).toTuple()
