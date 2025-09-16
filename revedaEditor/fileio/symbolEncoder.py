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

import revedaEditor.common.shapes as shp
import revedaEditor.common.labels as lbl


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
    def _get_common_fields(self, item):
        """Extract common fields for items with scene position."""
        return {
            "loc": (item.scenePos() - item.scene().origin).toTuple(),
            "ang": item.angle,
            "fl": item.flipTuple,
        }

    def default(self, item):
        type_handlers = {
            shp.symbolRectangle: lambda i: {"type": "rect", "rect": i.rect.getCoords(), **self._get_common_fields(i)},
            shp.symbolLine: lambda i: {"type": "line", "st": i.start.toTuple(), "end": i.end.toTuple(), **self._get_common_fields(i)},
            shp.symbolCircle: lambda i: {"type": "circle", "cen": i.centre.toTuple(), "end": i.end.toTuple(), **self._get_common_fields(i)},
            shp.symbolArc: lambda i: {"type": "arc", "st": i.start.toTuple(),
                                      "end": i.end.toTuple(),
                                      **self._get_common_fields(i),
                                      "at":
                                          shp.symbolArc.arcTypes.index(
                                              i.arcType)},
            shp.symbolPolygon: lambda i: {"type": "polygon", "ps": [i.mapToScene(p).toTuple() for p in i.points], "fl": i.flipTuple},
            shp.symbolPin: lambda i: {"type": "pin", "st": i.start.toTuple(), "nam": i.pinName, "pd": i.pinDir, "pt": i.pinType, **self._get_common_fields(i)},
            shp.text: lambda i: {"type": "text", "st": i.start.toTuple(), "tc": i.textContent, "ff": i.fontFamily, "fs": i.fontStyle, "th": i.textHeight, "ta": i.textAlignment, "to": i.textOrient, **self._get_common_fields(i)},
            lbl.symbolLabel: lambda i: {"type": "label", "st": i.start.toTuple(), "nam": i.labelName, "def": i.labelDefinition, "txt": i.labelText, "val": i.labelValue, "vis": i.labelVisible, "lt": i.labelType, "ht": i.labelHeight, "al": i.labelAlign, "or": i.labelOrient, "use": i.labelUse, "loc": (i.scenePos() - i.scene().origin).toTuple(), "fl": i.flipTuple},
            symbolAttribute: lambda i: {"type": "attr", "nam": i.name, "def": i.definition},
        }
        
        handler = type_handlers.get(type(item))
        return handler(item) if handler else super().default(item)

