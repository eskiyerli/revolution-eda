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

"""Unified connectivity engine — one implementation for GUI scenes, decoded
JSON records (aiTerminal ops, importers, batch tooling), and tests.

Public API:
    analyzeItems(netItems, pinItems, ...)  — live scene/duck-typed items
    analyzeRecords(records, pinLocator, ...) — decoded design arrays
    resolve(segs, ports, ...)              — primitives-level entry point
"""

from .adapters import fromLayoutItems, fromRecords, fromSceneItems
from .diagnostics import RecordDiagnostic, checkLayoutRecords, checkRecords
from .layout import (LayRect, LayShape, LayVia, LayoutGeometryReader,
                     PcellBridge, assignNetNames, buildConnectivity)
from .layout import NetGroup as LayoutNetGroup
from .netexpr import (evalNetExpr, exprNamesFromItems,
                      exprNamesFromRecords, formatNetSet, instanceExprNets,
                      isNetExpr, parseNetExpr, parseNetSet, terminalBinds)
from .primitives import (INHERIT, NONAME, SET, WEAK, Conflict,
                         ConnectivityResult, NetGroup, Port, Seg, busWidth,
                         namesMatch, parseArrayNotation)
from .resolve import resolve


def analyzeItems(netItems, pinItems, **kwargs):
    """Resolve connectivity for live (duck-typed) scene items.

    Returns (ConnectivityResult, segItemById, portItemById) so callers can
    map resolved names and conflicts back onto items.
    """
    segs, ports, segItemById, portItemById = fromSceneItems(netItems,
                                                          pinItems)
    result = resolve(segs, ports, **kwargs)
    return result, segItemById, portItemById


def analyzeRecords(records, pinLocator=None, **kwargs):
    """Resolve connectivity for a decoded schematic JSON design array.

    Returns (ConnectivityResult, diagnostics).
    """
    segs, ports, diagnostics = fromRecords(records, pinLocator=pinLocator)
    result = resolve(segs, ports, **kwargs)
    return result, diagnostics


def analyzeLayoutItems(items, touchTolerance=1.0, **kwargs):
    """Group live layout items into named nets.

    Returns (groups, names, conflicts, shapeItemByIdx, viaItemByIdx,
    anchorItemByIdx) — ``groups`` is a list of LayoutNetGroup with ``name``
    filled in by assignNetNames.
    """
    shapes, vias, anchors, shapeByIdx, viaByIdx, anchorByIdx = \
        fromLayoutItems(items)
    groups = buildConnectivity(shapes, vias, touchTolerance=touchTolerance,
                               **kwargs)
    names, conflicts, _auto = assignNetNames(groups, anchors,
                                             touchTolerance=touchTolerance)
    return groups, names, conflicts, shapeByIdx, viaByIdx, anchorByIdx


__all__ = [
    "INHERIT", "NONAME", "SET", "WEAK",
    "Conflict", "ConnectivityResult", "LayRect", "LayShape", "LayVia",
    "LayoutGeometryReader", "LayoutNetGroup", "NetGroup", "PcellBridge",
    "Port", "RecordDiagnostic", "Seg",
    "analyzeItems", "analyzeLayoutItems", "analyzeRecords", "assignNetNames",
    "buildConnectivity", "busWidth", "checkLayoutRecords", "checkRecords",
    "evalNetExpr", "exprNamesFromItems", "exprNamesFromRecords",
    "formatNetSet", "fromLayoutItems", "fromRecords", "fromSceneItems",
    "instanceExprNets", "isNetExpr", "namesMatch", "parseArrayNotation",
    "parseNetExpr", "parseNetSet", "resolve", "terminalBinds",
]
