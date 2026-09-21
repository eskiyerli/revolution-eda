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

"""Headless semantic checks on decoded design arrays.

These are the record-level counterparts of the scene check rules: they run
the *same* connectivity engine on raw JSON records, so aiTerminal design
ops, importers, and batch tooling validate against identical semantics to
the GUI.

    checkRecords(records, pinLocator)        -> schematic diagnostics
    checkLayoutRecords(records, layers, ...) -> layout diagnostics

A schematic ``pinLocator`` maps (lib, cell, view) -> {pinName: (x, y),
"directions": {pinName: dir}} in symbol coordinates; build one from a
library dict with ``loadJSON.makeSymbolPinLocator`` or supply your own.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Iterable, Optional

from .adapters import fromRecords
from .layout import (LayoutGeometryReader, assignNetNames, buildConnectivity)
from .primitives import Port, Seg
from .resolve import resolve
from ..common import params as prm


@dataclass(frozen=True)
class RecordDiagnostic:
    """One semantic finding on a decoded design array."""
    kind: str       # "malformedRecord" | "unresolvedInstance" |
                    # "floatingPin" | "danglingEnd" | conflict kinds |
                    # "unresolvedLayoutRecord"
    severity: str   # "error" | "warning"
    message: str


def _adapterDiagnostic(message: str) -> RecordDiagnostic:
    if message.startswith("Malformed"):
        return RecordDiagnostic("malformedRecord", "error", message)
    return RecordDiagnostic("unresolvedInstance", "warning", message)


def _manhattan(p, q) -> float:
    return abs(p[0] - q[0]) + abs(p[1] - q[1])


def _pointSegDist(p, a, b) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    lenSq = dx * dx + dy * dy
    if lenSq < 1e-9:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / lenSq
    t = max(0.0, min(1.0, t))
    return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))


def _danglingEnds(segs: list[Seg], ports: list[Port],
                  endpointTol: float, bodyTol: float,
                  portTol: float) -> list[RecordDiagnostic]:
    """Seg endpoints joined to nothing: no coincident endpoint, no T-contact
    on another seg body, and no pin within portTol."""
    diagnostics: list[RecordDiagnostic] = []
    for seg in segs:
        for point in (seg.p1, seg.p2):
            joined = False
            for other in segs:
                if other is seg:
                    continue
                if any(_manhattan(point, q) <= endpointTol
                       for q in (other.p1, other.p2)):
                    joined = True
                    break
                if _pointSegDist(point, other.p1, other.p2) <= bodyTol:
                    joined = True
                    break
            if not joined:
                joined = any(
                    _manhattan(point, port.point) <= portTol
                    for port in ports)
            if not joined:
                diagnostics.append(RecordDiagnostic(
                    "danglingEnd", "warning",
                    f"Dangling wire end at "
                    f"({point[0]:.0f}, {point[1]:.0f}) on net "
                    f"'{seg.name or '?'}'"))
    return diagnostics


def checkRecords(records: Iterable[dict],
                 pinLocator: Optional[Callable] = None,
                 endpointTol: float = 1.0, bodyTol: float = 5.0,
                 portTol: float = 10.0, netSet: Optional[dict] = None):
    """Semantic check of a decoded schematic design array.

    Returns ``(ConnectivityResult, list[RecordDiagnostic])``. Diagnostics
    cover malformed records, unresolved instances, engine-reported name
    conflicts (net name conflicts, bus-width mismatches, pin name
    conflicts, malformed/conflicting net expressions), floating pins, and
    dangling wire ends.

    ``netSet`` optionally supplies {exprName: localNet} bindings so a
    design array can be checked under an inherited-connection context;
    ``None`` evaluates expressions to their defaults.
    """
    records = list(records)  # materialize: consumed twice (adapter + params)
    segs, ports, adapterDiags = fromRecords(records, pinLocator=pinLocator)
    result = resolve(segs, ports, endpointTol=endpointTol,
                     bodyTol=bodyTol, portTol=portTol, netSet=netSet)

    diagnostics = [_adapterDiagnostic(msg) for msg in adapterDiags]
    diagnostics.extend(
        RecordDiagnostic(conflict.kind, "error", conflict.message)
        for conflict in result.conflicts)
    diagnostics.extend(
        RecordDiagnostic(
            "floatingPin", "warning",
            f"Unconnected pin '{port.name}'"
            + (f" on instance '{port.owner}'" if port.owner != port.name
               else "")
            + f" at ({port.point[0]:.0f}, {port.point[1]:.0f})")
        for port in ports
        if result.portGroup.get(port.id) is None
        # A floating pin carrying a net expression is an intentional
        # inherited connection, not a dangling pin.
        and port.id not in result.portExprNet)
    diagnostics.extend(_danglingEnds(segs, ports, endpointTol, bodyTol,
                                     portTol))
    diagnostics.extend(_paramDiagnostics(records, pinLocator))
    return result, diagnostics


def _paramDiagnostics(records: Iterable[dict],
                      pinLocator: Optional[Callable]
                      ) -> list[RecordDiagnostic]:
    """Validate ``sys.ld`` values against symbol paramDefs (CDF-lite).

    The pin locator doubles as the symbol-attribute source: when its
    result carries a ``"paramDefs"`` entry (as produced by
    ``loadJSON.makeSymbolPinLocator``), each instance's persisted label
    values are checked against the typed definitions."""
    if pinLocator is None:
        return []
    diagnostics: list[RecordDiagnostic] = []
    for record in records:
        if not isinstance(record, dict) or record.get("type") != "sys":
            continue
        pinMap = pinLocator(record.get("lib", ""), record.get("cell", ""),
                            record.get("view", "symbol"))
        if not pinMap:
            continue
        paramDefs = pinMap.get("paramDefs") or []
        labelDict = record.get("ld", {})
        if not paramDefs or not isinstance(labelDict, dict):
            continue
        for err in prm.validateInstanceValues(
                paramDefs, labelDict, owner=record.get("nam", "")):
            diagnostics.append(
                RecordDiagnostic("paramValueError", "warning", err))
    return diagnostics


def checkLayoutRecords(records: Iterable[dict], layoutLayers,
                       processModule, touchTolerance: float = 1.0):
    """Semantic check of a decoded layout design array.

    Returns ``(groups, names, list[RecordDiagnostic])`` — net groups from
    the shared layout engine, their resolved names, and diagnostics for
    unreadable records plus net-name conflicts.
    """
    elements = list(records)
    reader = LayoutGeometryReader(layoutLayers, processModule)
    # Skip the two header entries when present (view header + settings have
    # no "type" key and are ignored by read() anyway).
    body = elements[2:] if len(elements) > 2 and "type" not in elements[0] \
        else elements
    shapes, vias = reader.read(body)
    anchors = reader.readAnchors(body)
    groups = buildConnectivity(shapes, vias, touchTolerance=touchTolerance)
    names, conflicts, _auto = assignNetNames(groups, anchors,
                                             touchTolerance=touchTolerance)
    diagnostics = [
        RecordDiagnostic("netNameConflict", "error", msg)
        for msg in conflicts
    ]
    return groups, names, diagnostics
