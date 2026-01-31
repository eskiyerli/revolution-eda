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

import revedaEditor.common.net as net
import revedaEditor.common.shapes as shp


class schematicEncoder(json.JSONEncoder):
    def default(self, item: Any) -> Dict[str, Any]:
        if isinstance(item, shp.schematicSymbol):
            return self._encodeSchematicSymbol(item)
        elif isinstance(item, net.schematicNet):
            return self._encodeSchematicNet(item)
        elif isinstance(item, shp.schematicPin):
            return self._encodeSchematicPin(item)
        elif isinstance(item, shp.text):
            return self._encodeText(item)
        return super().default(item)

    def _encodeSchematicSymbol(self, item: shp.schematicSymbol) -> Dict[str, Any]:
        item_label_dict = (
            item.labelDict if item.draft
            else {label.labelName: [label.labelValue, label.labelVisible]
                  for label in item.labels.values()}
        )
        scene_origin = item.scene().origin
        return {
            "type": "sys",
            "lib": item.libraryName,
            "cell": item.cellName,
            "view": item.viewName,
            "nam": item.instanceName,
            "ic": item.counter,
            "ld": item_label_dict,
            "loc": self._subtract_point(item.scenePos(), scene_origin),
            "ang": item.angle,
            "ign": int(item.netlistIgnore),
            "br": item.boundingRect().getCoords(),
            "fl": item.flipTuple,
        }

    def _encodeSchematicNet(self, item: net.schematicNet) -> Dict[str, Any]:
        scene_origin = item.scene().origin
        return {
            "type": "scn",
            "st": self._subtract_point(item.mapToScene(item.draftLine.p1()), scene_origin),
            "end": self._subtract_point(item.mapToScene(item.draftLine.p2()), scene_origin),
            "nam": item.name,
            "ns": item.nameStrength.value,
        }

    def _encodeSchematicPin(self, item: shp.schematicPin) -> Dict[str, Any]:
        return {
            "type": "scp",
            "st": self._subtract_point(item.mapToScene(item.start), item.scene().origin),
            "pn": item.pinName,
            "pd": item.pinDir,
            "pt": item.pinType,
            "ang": item.angle,
            "fl": item.flipTuple,
        }

    def _encodeText(self, item: shp.text) -> Dict[str, Any]:
        return {
            "type": "txt",
            "st": self._subtract_point(item.mapToScene(item.start), item.scene().origin),
            "tc": item.textContent,
            "ff": item.fontFamily,
            "fs": item.fontStyle,
            "th": item.textHeight,
            "ta": item.textAlignment,
            "to": item.textOrient,
            "ang": item.angle,
            "fl": item.flipTuple,
        }

    @staticmethod
    def _subtract_point(point: QPointF, origin: QPointF) -> tuple:
        return (point - origin).toTuple()
