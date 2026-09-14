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
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Pre-build a type -> encoder map for the common concrete shape classes.
        # Exact-type lookup is faster than an isinstance chain for large layouts.
        self._encoders = {
            lshp.layoutPcell: self._encodePcell,
            lshp.layoutInstance: self._encodeLayoutInstance,
            lshp.layoutRect: self._encodeLayoutRect,
            lshp.layoutPath: self._encodeLayoutPath,
            lshp.layoutViaArray: self._encodeLayoutViaArray,
            lshp.layoutPin: self._encodeLayoutPin,
            lshp.layoutLabel: self._encodeLayoutLabel,
            lshp.layoutPolygon: self._encodeLayoutPolygon,
            lshp.layoutRuler: self._encodeLayoutRuler,
        }
        # Resolve the layer list at encode time and key it by
        # (name, purpose) rather than object id: after a runtime PDK switch
        # the layoutLayers module is re-imported, so shapes may hold layLayer
        # objects from a different module instance than the one bound here.
        layers = importPDKModule("layoutLayers").pdkAllLayers
        self._layerIndex = {
            (layer.name, layer.purpose): i for i, layer in enumerate(layers)
        }

    def _layerIndexFor(self, layer) -> int:
        return self._layerIndex[(layer.name, layer.purpose)]

    def default(self, item: Any) -> Dict[str, Any]:
        encoder = self._encoders.get(type(item))
        if encoder is not None:
            return encoder(item)
        # layoutPcell is a subclass of layoutInstance; handle subclasses that
        # are not in the exact-type map.
        if isinstance(item, lshp.layoutPcell):
            return self._encodePcell(item)
        if isinstance(item, lshp.layoutInstance):
            return self._encodeLayoutInstance(item)
        return super().default(item)

    def _encodeLayoutInstance(self, item: lshp.layoutInstance) -> Dict[str, Any]:
        # ``bbox`` is the children bounds in item-local coordinates; the loader
        # uses it to defer child construction until the instance is viewed.
        bounds = item._childrenBounds()
        return {
            "type": "Inst",
            "lib": item.libraryName,
            "cell": item.cellName,
            "view": item.viewName,
            "nam": item.instanceName,
            "ic": item.counter,
            # ``pos`` is the parent-coordinate translation consumed by
            # the instance/PCell loaders.  ``scenePos`` includes this item's
            # rotation/flip about ``top`` and would be applied a second time
            # after reload, moving the instance on every save/load cycle.
            "loc": item.pos().toTuple(),
            "top": item.transformOriginPoint().toTuple(),
            "ang": item.angle,
            "fl": item.flipTuple,
            "bbox": (bounds.x(), bounds.y(), bounds.width(), bounds.height()),
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
        pos = item.pos()
        return {
            "type": "Rect",
            "tl": (pos + item.rect.topLeft()).toTuple(),
            "br": (pos + item.rect.bottomRight()).toTuple(),
            "top": (pos + item.transformOriginPoint()).toTuple(),
            "ang": item.angle,
            "ln": self._layerIndexFor(item.layer),
            "fl": item.flipTuple,
        }

    def _encodeLayoutPath(self, item: lshp.layoutPath) -> Dict[str, Any]:
        # Rotation/flip-neutral geometry; see _encodeLayoutRect.
        pos = item.pos()
        return {
            "type": "Path",
            "dfl1": (pos + item.draftLine.p1()).toTuple(),
            "dfl2": (pos + item.draftLine.p2()).toTuple(),
            "top": (pos + item.transformOriginPoint()).toTuple(),
            "ln": self._layerIndexFor(item.layer),
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
            # Keep the custom local pivot so rotation/flip continue to use the
            # same center after the array is rebuilt from its canonical origin.
            "top": item.transformOriginPoint().toTuple(),
            "ang": item.angle,
            "fl": item.flipTuple,
        }

    def _encodeLayoutPin(self, item: lshp.layoutPin) -> Dict[str, Any]:
        # Rotation/flip-neutral geometry; see _encodeLayoutRect.
        pos = item.pos()
        return {
            "type": "Pin",
            "tl": (pos + item.rect.topLeft()).toTuple(),
            "br": (pos + item.rect.bottomRight()).toTuple(),
            "top": (pos + item.transformOriginPoint()).toTuple(),
            "pn": item.pinName,
            "pd": item.pinDir,
            "pt": item.pinType,
            "ln": self._layerIndexFor(item.layer),
            "ang": item.angle,
            "fl": item.flipTuple,
        }

    def _encodeLayoutLabel(self, item: lshp.layoutLabel) -> Dict[str, Any]:
        # Labels derive their orientation from labelOrient (see setOrient), not
        # the generic rotate path, so only the anchor is stored pos-folded; the
        # loader recreates orientation from labelOrient instead of re-applying
        # generic ang/fl.
        pos = item.pos()
        return {
            "type": "Label",
            "st": (pos + item.start).toTuple(),
            "lt": item.labelText,
            "ff": item.fontFamily,
            "fs": item.fontStyle,
            "fh": item.fontHeight,
            "la": item.labelAlign,
            "lo": item.labelOrient,
            "ang": item.angle,
            "fl": item.flipTuple,
            "ln": self._layerIndexFor(item.layer),
        }

    def _encodeLayoutPolygon(self, item: lshp.layoutPolygon) -> Dict[str, Any]:
        # Rotation/flip-neutral geometry; see _encodeLayoutRect.
        pos = item.pos()
        return {
            "type": "Polygon",
            "ps": [(pos + point).toTuple() for point in item.points],
            "top": (pos + item.transformOriginPoint()).toTuple(),
            "ln": self._layerIndexFor(item.layer),
            "ang": item.angle,
            "fl": item.flipTuple,
        }

    def _encodeLayoutRuler(self, item: lshp.layoutRuler) -> Dict[str, Any]:
        # Rotation/flip-neutral geometry; see _encodeLayoutRect.
        pos = item.pos()
        return {
            "type": "Ruler",
            "dfl1": (pos + item.draftLine.p1()).toTuple(),
            "dfl2": (pos + item.draftLine.p2()).toTuple(),
            "top": (pos + item.transformOriginPoint()).toTuple(),
            "md": item.mode,
            "ang": item.angle,
            "fl": item.flipTuple,
        }

    def _encodePcell(self, item) -> Dict[str, Any]:
        # A deferred pcell's ctor-param attributes still hold defaults, so read
        # the pending params dict instead of getattr on the instance.
        pending = getattr(item, "deferredParams", None)
        if pending is not None:
            argDict = dict(pending)
        else:
            argDict = {
                name: getattr(item, name)
                for name in _pcell_parameter_names(type(item))
                if hasattr(item, name)
            }
        bounds = item._childrenBounds()
        return {
            "type": "Pcell",
            "lib": item.libraryName,
            "cell": item.cellName,
            "view": item.viewName,
            "nam": item.instanceName,
            "ic": item.counter,
            # ``pos`` is the parent-coordinate translation consumed by
            # the instance/PCell loaders.  ``scenePos`` includes this item's
            # rotation/flip about ``top`` and would be applied a second time
            # after reload, moving the instance on every save/load cycle.
            "loc": item.pos().toTuple(),
            "top": item.transformOriginPoint().toTuple(),
            "ang": item.angle,
            "fl": item.flipTuple,
            "params": argDict,
            "bbox": (bounds.x(), bounds.y(), bounds.width(), bounds.height()),
        }


class gdsImportEncoder(layoutEncoder):
    """Use the canonical layout encoder for GDS-imported JSON."""
