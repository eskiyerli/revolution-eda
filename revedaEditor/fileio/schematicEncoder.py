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
