# SPDX-License-Identifier: MPL-2.0
#
# Revolution EDA
# Copyright (c) 2024-2026 Revolution Semiconductor

import json
from typing import Dict, Any

from PySide6.QtCore import QPointF

import revedaEditor.common.net as net
import revedaEditor.common.shapes as shp
import revedaEditor.fileio.schemaValidation as sv


class schematicEncoder(json.JSONEncoder):
    def default(self, item: Any) -> Dict[str, Any]:
        if isinstance(item, shp.schematicGroup):
            return self._encodeSchematicGroup(item)
        if isinstance(item, shp.schematicSymbol):
            return self._encodeSchematicSymbol(item)
        elif isinstance(item, net.schematicNet):
            return self._encodeSchematicNet(item)
        elif isinstance(item, shp.schematicPin):
            return self._encodeSchematicPin(item)
        elif isinstance(item, shp.text):
            return self._encodeText(item)
        return super().default(item)

    def _encodeSchematicSymbol(self, item: shp.schematicSymbol,
                               scene_origin: QPointF | None = None) -> Dict[str, Any]:
        item_label_dict = (
            item.labelDict if item.draft
            else {label.labelName: [label.labelValue, label.labelVisible]
                  for label in item.labels.values()}
        )
        scene_origin = scene_origin if scene_origin is not None else item.scene().origin
        record = {
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
        if item.netSet:
            record["nst"] = dict(item.netSet)
        # Schematic<->layout correspondence (backend/correspondence): written
        # only for symbols carrying a canonical sdl stamp (e.g. the generated
        # lvs_schematic view). Same persisted shape as layout Inst records.
        sdl = getattr(item, "_sdlSource", None)
        if sv.is_canonical_sdl_source(sdl):
            record["sdl"] = sdl
        return record

    def _encodeSchematicGroup(self, item: shp.schematicGroup) -> Dict[str, Any]:
        """Persist a symbols-only mosaic in the group's local frame."""
        groupOrigin = item.scenePos()
        return {
            "type": "Group",
            "loc": self._subtract_point(groupOrigin, item.scene().origin),
            "items": [self._encodeSchematicSymbol(symbol, groupOrigin)
                      for symbol in item.symbols],
        }

    def _encodeSchematicNet(self, item: net.schematicNet) -> Dict[str, Any]:
        scene_origin = item.scene().origin
        record = {
            "type": "scn",
            "st": self._subtract_point(item.mapToScene(item.draftLine.p1()), scene_origin),
            "end": self._subtract_point(item.mapToScene(item.draftLine.p2()), scene_origin),
            "nam": item.name,
            "ns": item.nameStrength.value,
        }
        if item.netExpr:
            record["nx"] = item.netExpr
        return record

    def _encodeSchematicPin(self, item: shp.schematicPin) -> Dict[str, Any]:
        record = {
            "type": "scp",
            "st": self._subtract_point(item.mapToScene(item.start), item.scene().origin),
            "pn": item.pinName,
            "pd": item.pinDir,
            "pt": item.pinType,
            "ang": item.angle,
            "fl": item.flipTuple,
        }
        if item.netExpr:
            record["nx"] = item.netExpr
        return record

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
