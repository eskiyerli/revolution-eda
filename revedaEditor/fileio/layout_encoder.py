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

import inspect
import json
from typing import Dict, Any

from PySide6.QtCore import QPointF

import revedaEditor.common.layout_shapes as lshp
from revedaEditor.backend.pdk_loader import importPDKModule

laylyr = importPDKModule('layout_layers')
pcells = importPDKModule('pcells')


class LayoutEncoder(json.JSONEncoder):
    def default(self, item: Any) -> Dict[str, Any]:
        if isinstance(item, lshp.LayoutPcell):
            return self._encodePcell(item)
        elif isinstance(item, lshp.LayoutInstance):
            return self._encodeLayoutInstance(item)
        elif isinstance(item, lshp.LayoutRect):
            return self._encodeLayoutRect(item)
        elif isinstance(item, lshp.LayoutPath):
            return self._encodeLayoutPath(item)
        elif isinstance(item, lshp.LayoutViaArray):
            return self._encodeLayoutViaArray(item)
        elif isinstance(item, lshp.LayoutPin):
            return self._encodeLayoutPin(item)
        elif isinstance(item, lshp.LayoutLabel):
            return self._encodeLayoutLabel(item)
        elif isinstance(item, lshp.LayoutPolygon):
            return self._encodeLayoutPolygon(item)

        return super().default(item)

    def _encodeLayoutInstance(self, item: lshp.LayoutInstance) -> Dict[str, Any]:
        return {
            "type": "Inst",
            "lib": item.libraryName,
            "cell": item.cellName,
            "view": item.viewName,
            "nam": item.instanceName,
            "ic": item.counter,
            "loc": self._subtract_point(item.scenePos(), item.scene().origin),
            "ang": item.angle,
            "fl": item.flipTuple,
        }

    def _encodeLayoutRect(self, item: lshp.LayoutRect) -> Dict[str, Any]:
        return {
            "type": "Rect",
            "tl": item.mapToScene(item.rect.topLeft()).toTuple(),
            "br": item.mapToScene(item.rect.bottomRight()).toTuple(),
            "ang": item.angle,
            "ln": laylyr.pdkAllLayers.index(item.layer),
            "fl": item.flipTuple,
        }

    def _encodeLayoutPath(self, item: lshp.LayoutPath) -> Dict[str, Any]:
        return {
            "type": "Path",
            "dfl1": item.mapToScene(item.draftLine.p1()).toTuple(),
            "dfl2": item.mapToScene(item.draftLine.p2()).toTuple(),
            "ln": laylyr.pdkAllLayers.index(item.layer),
            "w": item.width,
            "se": item.startExtend,
            "ee": item.endExtend,
            "md": item.mode,
            "nam": item.name,
            "ang": item.angle,
            "fl": item.flipTuple,
        }

    def _encodeLayoutViaArray(self, item: lshp.LayoutViaArray) -> Dict[str, Any]:
        viaDict = {
            "vdt": item.via.ViaDefTuple.name,
            "st": item.via.mapToScene(item.via.start).toTuple(),
            "w": item.via.width,
            "h": item.via.height,
            "ang": item.angle,
            "fl": item.flipTuple,
        }
        return {
            "type": "Via",
            "st": item.mapToScene(item.start).toTuple(),
            "via": viaDict,
            "xs": item.xs,
            "ys": item.ys,
            "xn": item.xnum,
            "yn": item.ynum,
        }

    def _encodeLayoutPin(self, item: lshp.LayoutPin) -> Dict[str, Any]:
        return {
            "type": "Pin",
            "tl": item.mapToScene(item.rect.topLeft()).toTuple(),
            "br": item.mapToScene(item.rect.bottomRight()).toTuple(),
            "pn": item.pinName,
            "pd": item.pinDir,
            "pt": item.pinType,
            "ln": laylyr.pdkAllLayers.index(item.layer),
            "ang": item.angle,
            "fl": item.flipTuple,
        }

    def _encodeLayoutLabel(self, item: lshp.LayoutLabel) -> Dict[str, Any]:
        return {
            "type": "Label",
            "st": item.mapToScene(item.start).toTuple(),
            "lt": item.labelText,
            "ff": item.fontFamily,
            "fs": item.fontStyle,
            "fh": item.fontHeight,
            "la": item.labelAlign,
            "lo": item.labelOrient,
            "ln": laylyr.pdkAllLayers.index(item.layer),
            "ang": item.angle,
            "fl": item.flipTuple,
        }

    def _encodeLayoutPolygon(self, item: lshp.LayoutPolygon) -> Dict[str, Any]:
        return {
            "type": "Polygon",
            "ps": [item.mapToScene(point).toTuple() for point in item.points],
            "ln": laylyr.pdkAllLayers.index(item.layer),
            "ang": item.angle,
            "fl": item.flipTuple,
        }

    def _encodePcell(self, item) -> Dict[str, Any]:
        init_args = inspect.signature(item.__class__.__init__).parameters
        args_used = [param for param in init_args if (param != "self")]
        argDict = {arg: getattr(item, arg) for arg in args_used if hasattr(item, arg)}
        return {
            "type": "Pcell",
            "lib": item.libraryName,
            "cell": item.cellName,
            "view": item.viewName,
            "nam": item.instanceName,
            "ic": item.counter,
            "loc": item.pos().toPoint().toTuple(),
            "ang": item.angle,
            "fl": item.flipTuple,
            "params": argDict,
        }

    @staticmethod
    def _subtract_point(point: QPointF, origin: QPointF) -> tuple:
        return (point - origin).toTuple()


class GdsImportEncoder(json.JSONEncoder):
    def default(self, item):
        common = {"ang": item.angle, "fl": item.flipTuple}

        match type(item):
            case lshp.LayoutInstance:
                return {"type": "Inst", "lib": item.libraryName, "cell": item.cellName,
                        "view": item.viewName, "nam": item.instanceName, "ic": item.counter,
                        "loc": item.pos().toTuple(), **common}
            case lshp.LayoutPath:
                return {"type": "Path",
                        "dfl1": item.mapToScene(item.draftLine.p1()).toTuple(),
                        "dfl2": item.mapToScene(item.draftLine.p2()).toTuple(),
                        "ln": laylyr.pdkAllLayers.index(item.layer), "w": item.width,
                        "se": item.startExtend, "ee": item.endExtend, "md": item.mode,
                        "nam": item.name, **common}
            case lshp.LayoutViaArray:
                return {"type": "Via", "st": item.mapToScene(item.start).toTuple(),
                        "via": {"st": item.via.mapToScene(item.via.start).toTuple(),
                                "vdt": item.via.ViaDefTuple.NetName, "w": item.via.width,
                                "h": item.via.height, **common},
                        "xs": item.xs, "ys": item.ys, "xn": item.xnum, "yn": item.ynum}
            case lshp.LayoutPin:
                return {"type": "Pin", "tl": item.mapToScene(item.rect.topLeft()).toTuple(),
                        "br": item.mapToScene(item.rect.bottomRight()).toTuple(),
                        "pn": item.pinName, "pd": item.pinDir, "pt": item.pinType,
                        "ln": laylyr.pdkAllLayers.index(item.layer), **common}
            case lshp.LayoutLabel:
                return {"type": "Label", "st": item.mapToScene(item.start).toTuple(),
                        "lt": item.labelText, "ff": item.fontFamily, "fs": item.fontStyle,
                        "fh": item.fontHeight, "la": item.labelAlign,
                        "lo": item.labelOrient,
                        "ln": laylyr.pdkAllLayers.index(item.layer), **common}
            case lshp.LayoutPolygon:
                return {"type": "Polygon",
                        "ps": [item.mapToScene(point).toTuple() for point in item.points],
                        "ln": laylyr.pdkAllLayers.index(item.layer), **common}
