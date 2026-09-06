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

import functools
import inspect
import json
from typing import Any, Dict

import revedaEditor.common.layoutShapes as lshp
from revedaEditor.backend.pdkLoader import importPDKModule

laylyr = importPDKModule("layoutLayers")


@functools.lru_cache(maxsize=128)
def _pcell_parameter_names(pcell_type: type) -> tuple[str, ...]:
    """Return constructor parameters once per PCell class."""
    return tuple(
        name
        for name in inspect.signature(pcell_type.__init__).parameters
        if name != "self"
    )


class layoutEncoder(json.JSONEncoder):
    def default(self, item: Any) -> Dict[str, Any]:
        if isinstance(item, lshp.layoutPcell):
            return self._encodePcell(item)
        elif isinstance(item, lshp.layoutInstance):
            return self._encodeLayoutInstance(item)
        elif isinstance(item, lshp.layoutRect):
            return self._encodeLayoutRect(item)
        elif isinstance(item, lshp.layoutPath):
            return self._encodeLayoutPath(item)
        elif isinstance(item, lshp.layoutViaArray):
            return self._encodeLayoutViaArray(item)
        elif isinstance(item, lshp.layoutPin):
            return self._encodeLayoutPin(item)
        elif isinstance(item, lshp.layoutLabel):
            return self._encodeLayoutLabel(item)
        elif isinstance(item, lshp.layoutPolygon):
            return self._encodeLayoutPolygon(item)
        elif isinstance(item, lshp.layoutRuler):
            return self._encodeLayoutRuler(item)

        return super().default(item)

    def _encodeLayoutInstance(self, item: lshp.layoutInstance) -> Dict[str, Any]:
        return {
            "type": "Inst",
            "lib": item.libraryName,
            "cell": item.cellName,
            "view": item.viewName,
            "nam": item.instanceName,
            "ic": item.counter,
            "loc": item.scenePos().toTuple(),
            "top": item.transformOriginPoint().toTuple(),
            "ang": item.angle,
            "fl": item.flipTuple,
        }

    def _encodeLayoutRect(self, item: lshp.layoutRect) -> Dict[str, Any]:
        # Store geometry rotation/flip-neutral: local corners offset by pos()
        # only (NOT mapToScene, which bakes in the current rotation/flip). The
        # transform origin ("top") is persisted so the loader can re-apply
        # "ang"/"fl" about the same pivot. Baking the transform into the corners
        # AND re-applying "ang" on load caused shapes to rotate on every reopen.
        #
        # Both geometry and "top" are stored in the same pos-folded frame
        # (pos() + local): the loader rebuilds the shape with pos()=0, so the
        # transform origin (which lives in item-local coordinates) must be
        # shifted by pos() to stay at the same scene pivot.
        return {
            "type": "Rect",
            "tl": (item.pos() + item.rect.topLeft()).toTuple(),
            "br": (item.pos() + item.rect.bottomRight()).toTuple(),
            "top": (item.pos() + item.transformOriginPoint()).toTuple(),
            "ang": item.angle,
            "ln": laylyr.pdkAllLayers.index(item.layer),
            "fl": item.flipTuple,
        }

    def _encodeLayoutPath(self, item: lshp.layoutPath) -> Dict[str, Any]:
        # Rotation/flip-neutral geometry; see _encodeLayoutRect.
        return {
            "type": "Path",
            "dfl1": (item.pos() + item.draftLine.p1()).toTuple(),
            "dfl2": (item.pos() + item.draftLine.p2()).toTuple(),
            "top": (item.pos() + item.transformOriginPoint()).toTuple(),
            "ln": laylyr.pdkAllLayers.index(item.layer),
            "w": item.width,
            "se": item.startExtend,
            "ee": item.endExtend,
            "md": item.mode,
            "nam": item.name,
            "ang": item.angle,
            "fl": item.flipTuple,
        }

    def _encodeLayoutViaArray(self, item: lshp.layoutViaArray) -> Dict[str, Any]:
        # Via arrays use a canonical local origin: each child cut is assembled
        # from (0, 0) and the array's parent pos() is its scene placement. This
        # avoids folding an absolute child start into the parent transform on
        # every save/reopen cycle.
        viaDict = {
            "vdt": item.via.viaDefTuple.name,
            "st": (0, 0),
            "w": item.via.width,
            "h": item.via.height,
            # Per-instance metal enclosure overrides (um). Persisted so a via
            # keeps its drawn coverage even if the PDK default later changes.
            "be": item.via.bottomEnclosure,
            "te": item.via.topEnclosure,
        }
        return {
            "type": "Via",
            "coordMode": "parent",
            "anchorMode": "firstCut",
            # Store the actual first-cut scene position so the anchor remains
            # invariant under rotation and flip.
            "st": item.mapToScene(item.start).toTuple(),
            "via": viaDict,
            "xs": item.xs,
            "ys": item.ys,
            "xn": item.xnum,
            "yn": item.ynum,
            # Keep the local origin at zero; the first-cut anchor and transform
            # fields fully describe the array's placement.
            "top": (0, 0),
            "ang": item.angle,
            "fl": item.flipTuple,
        }

    def _encodeLayoutPin(self, item: lshp.layoutPin) -> Dict[str, Any]:
        # Rotation/flip-neutral geometry; see _encodeLayoutRect.
        return {
            "type": "Pin",
            "tl": (item.pos() + item.rect.topLeft()).toTuple(),
            "br": (item.pos() + item.rect.bottomRight()).toTuple(),
            "top": (item.pos() + item.transformOriginPoint()).toTuple(),
            "pn": item.pinName,
            "pd": item.pinDir,
            "pt": item.pinType,
            "ln": laylyr.pdkAllLayers.index(item.layer),
            "ang": item.angle,
            "fl": item.flipTuple,
        }

    def _encodeLayoutLabel(self, item: lshp.layoutLabel) -> Dict[str, Any]:
        # Labels derive their orientation from labelOrient (see setOrient), not
        # the generic rotate path, so only the anchor is stored pos-folded; the
        # loader recreates orientation from labelOrient instead of re-applying
        # generic ang/fl.
        return {
            "type": "Label",
            "st": (item.pos() + item.start).toTuple(),
            "lt": item.labelText,
            "ff": item.fontFamily,
            "fs": item.fontStyle,
            "fh": item.fontHeight,
            "la": item.labelAlign,
            "lo": item.labelOrient,
            "ang": item.angle,
            "fl": item.flipTuple,
            "ln": laylyr.pdkAllLayers.index(item.layer),
        }

    def _encodeLayoutPolygon(self, item: lshp.layoutPolygon) -> Dict[str, Any]:
        # Rotation/flip-neutral geometry; see _encodeLayoutRect.
        return {
            "type": "Polygon",
            "ps": [(item.pos() + point).toTuple() for point in item.points],
            "top": (item.pos() + item.transformOriginPoint()).toTuple(),
            "ln": laylyr.pdkAllLayers.index(item.layer),
            "ang": item.angle,
            "fl": item.flipTuple,
        }

    def _encodeLayoutRuler(self, item: lshp.layoutRuler) -> Dict[str, Any]:
        # Rotation/flip-neutral geometry; see _encodeLayoutRect.
        return {
            "type": "Ruler",
            "dfl1": (item.pos() + item.draftLine.p1()).toTuple(),
            "dfl2": (item.pos() + item.draftLine.p2()).toTuple(),
            "top": (item.pos() + item.transformOriginPoint()).toTuple(),
            "md": item.mode,
            "ang": item.angle,
            "fl": item.flipTuple,
        }

    def _encodePcell(self, item) -> Dict[str, Any]:
        argDict = {
            name: getattr(item, name)
            for name in _pcell_parameter_names(type(item))
            if hasattr(item, name)
        }
        return {
            "type": "Pcell",
            "lib": item.libraryName,
            "cell": item.cellName,
            "view": item.viewName,
            "nam": item.instanceName,
            "ic": item.counter,
            "loc": item.scenePos().toTuple(),
            "top": item.transformOriginPoint().toTuple(),
            "ang": item.angle,
            "fl": item.flipTuple,
            "params": argDict,
        }


class gdsImportEncoder(layoutEncoder):
    """Use the canonical layout encoder for GDS-imported JSON."""
