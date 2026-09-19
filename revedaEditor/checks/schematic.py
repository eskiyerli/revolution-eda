#
# Revolution EDA
#
# Copyright (c) 2026 Revolution Semiconductor
#
# This Source Code Form is subject to the terms of the
# Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
"""Schematic check rules.

Each entry in ``SCHEMATIC_RULES`` is a selectable check (id, display name,
severity, description) whose ``run`` function returns ``checkViolation``
objects carrying a log message and scene-coordinate marker rects. The scene
builds one shared ``schematicCheckContext`` per check run, so rules reuse a
single connectivity graph instead of rescanning the scene.
"""

import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from enum import IntEnum
from itertools import combinations
from typing import Callable, Dict, List, Optional, Set, Tuple

from PySide6.QtCore import QLineF, QPoint, QPointF, QRectF, Qt

import revedaEditor.common.net as snet
from revedaEditor.common.shapes import schematicSymbol


class checkSeverity(IntEnum):
    ERROR = 0
    WARNING = 1


@dataclass
class pinRecord:
    """One pin connection point on the schematic (instance or sheet pin)."""
    item: object  # shp.symbolPin or shp.schematicPin
    name: str
    direction: str  # "Input" | "Output" | "Inout"
    point: QPoint  # scene position of the pin connection point
    owner: str  # instance name for symbol pins, pin name for schematic pins


@dataclass
class checkViolation:
    ruleId: str
    severity: checkSeverity
    message: str
    markers: List[QRectF]


@dataclass
class schematicCheckContext:
    """Scene data collected once and shared by all rules."""
    scene: object  # schematicScene; untyped to keep checks importable standalone
    symbolSet: Set[schematicSymbol]
    netSet: Set[snet.schematicNet]
    pins: List[pinRecord]
    snapDist: int
    snapTuple: Tuple[int, int]
    netGroups: List[Set[snet.schematicNet]]
    netGroupOf: Dict[snet.schematicNet, int]
    pinGroupOf: Dict[object, Optional[int]]  # pin item -> group index or None


@dataclass
class schematicCheckRule:
    ruleId: str
    name: str
    description: str
    severity: checkSeverity
    run: Callable[[schematicCheckContext], List[checkViolation]]


def checkSymbolOverlaps(symbolSet: Set[schematicSymbol]):
    """
    Checks if any symbol overlaps with other symbols.
    """
    collisionRectSet = set()
    if symbolSet is None:
        return False, collisionRectSet
    symbolSetCombos = combinations(symbolSet, 2)
    if symbolSetCombos is None:
        return False, collisionRectSet
    for symbol1, symbol2 in symbolSetCombos:
        if symbol1.collidesWithItem(symbol2):
            path1 = symbol1.mapToScene(symbol1.shape())
            path2 = symbol2.mapToScene(symbol2.shape())
            collisionPath = path1.intersected(path2)
            if not collisionPath.isEmpty():
                collisionRectSet.add(collisionPath.boundingRect(
                ).toRect())
    return True, collisionRectSet


def checkUnconnectedNets(netSet: Set[snet.schematicNet],
                         pinPoints: Set[QPoint],
                         snapDist: int) -> Set[QPoint]:
    """
    Return dangling net endpoints: ends where no other net terminates and no
    pin sits within snap distance.
    """
    endCount = Counter()
    for netItem in netSet:
        endCount.update(netItem.sceneEndPoints)
    dangling = set()
    for point, count in endCount.items():
        if count > 1:
            continue
        if any((point - pinPoint).manhattanLength() <= snapDist
               for pinPoint in pinPoints):
            continue
        dangling.add(point)
    return dangling


def checkFloatingPins(pinPoints: Set[QPoint], netEndPoints: Set[QPoint],
                      snapDist: int) -> Set[QPoint]:
    """
    Return pin positions that are not within snap distance of any net
    endpoint.
    """
    return {pinPoint for pinPoint in pinPoints
            if all((pinPoint - endPoint).manhattanLength() > snapDist
                   for endPoint in netEndPoints)}


def _pointMarker(point: QPoint, halfSize: int = 4) -> QRectF:
    return QRectF(point.x() - halfSize, point.y() - halfSize,
                  2 * halfSize, 2 * halfSize)


def _pinOwnerName(pinItem) -> str:
    parentItem = pinItem.parentItem()
    if parentItem is not None:
        instanceName = getattr(parentItem, "instanceName", "")
        if instanceName:
            return f"{instanceName}/{pinItem.pinName}"
    return pinItem.pinName


def _netSceneRect(netItem: snet.schematicNet) -> QRectF:
    return netItem.mapToScene(netItem.boundingRect()).boundingRect()


def _pinNetGroup(pinItem, pinPoint: QPoint, netSet, netGroupOf,
                 snapDist: int) -> Optional[int]:
    """Net group a pin attaches to: any net the pin shape touches, or any
    net endpoint within snap distance of the pin point."""
    for item in pinItem.collidingItems(Qt.IntersectsItemShape):
        if isinstance(item, snet.schematicNet) and item in netGroupOf:
            return netGroupOf[item]
    for netItem in netSet:
        if any((pinPoint - endPoint).manhattanLength() <= snapDist
               for endPoint in netItem.sceneEndPoints):
            return netGroupOf[netItem]
    return None


def _disjointFind(parent: Dict, item):
    root = item
    while parent[root] != root:
        root = parent[root]
    while parent[item] != item:
        parent[item], item = root, parent[item]
    return root


def buildCheckContext(scene) -> schematicCheckContext:
    """Collect scene data shared by all check rules and build the net
    connectivity graph: nets joined by coincident endpoints or by an endpoint
    landing on another net's body (unsplit T contacts in legacy schematics)."""
    symbolSet = scene.findSceneSymbolSet()
    netSet = scene.findSceneNetsSet()
    snapDist = min(scene.snapTuple)

    pins = []
    pinSources = [pinItem for symbolItem in symbolSet
                  for pinItem in symbolItem.pins.values()]
    pinSources.extend(scene.findSceneSchemPinsSet())
    for pinItem in pinSources:
        pins.append(pinRecord(
            pinItem, pinItem.pinName, pinItem.pinDir,
            pinItem.mapToScene(pinItem.start).toPoint(),
            _pinOwnerName(pinItem)))

    # Union nets that electrically touch.
    parent = {netItem: netItem for netItem in netSet}
    for netItem in netSet:
        for endPoint in netItem.sceneEndPoints:
            probe = QRectF(endPoint.x() - 1, endPoint.y() - 1, 2, 2)
            for item in scene.items(probe):
                if (not isinstance(item, snet.schematicNet)
                        or item is netItem or item not in parent):
                    continue
                touches = any(
                    (endPoint - otherEnd).manhattanLength() <= 1
                    for otherEnd in item.sceneEndPoints)
                if touches or item.sceneShapeRect.contains(endPoint):
                    rootA = _disjointFind(parent, netItem)
                    rootB = _disjointFind(parent, item)
                    if rootA != rootB:
                        parent[rootB] = rootA

    grouped = defaultdict(set)
    for netItem in netSet:
        grouped[_disjointFind(parent, netItem)].add(netItem)
    netGroups = list(grouped.values())
    netGroupOf = {netItem: index for index, group in enumerate(netGroups)
                  for netItem in group}

    pinGroupOf = {
        pin.item: _pinNetGroup(pin.item, pin.point, netSet, netGroupOf,
                               snapDist)
        for pin in pins}

    return schematicCheckContext(scene, symbolSet, netSet, pins, snapDist,
                                 scene.snapTuple, netGroups, netGroupOf,
                                 pinGroupOf)


# --- Rule implementations ------------------------------------------------

def _ruleSymbolOverlap(context: schematicCheckContext) -> List[checkViolation]:
    _, collisionRects = checkSymbolOverlaps(context.symbolSet)
    return [checkViolation(
        "symbolOverlap", checkSeverity.ERROR,
        f"Overlapping symbols at {rect.center().toTuple()}.",
        [QRectF(rect)]) for rect in collisionRects]


def _ruleDanglingWireEnd(context: schematicCheckContext) -> List[
    checkViolation]:
    pinPoints = {pin.point for pin in context.pins}
    dangling = checkUnconnectedNets(context.netSet, pinPoints,
                                    context.snapDist)
    return [checkViolation(
        "danglingWireEnd", checkSeverity.WARNING,
        f"Dangling wire end at {point.toTuple()}.",
        [_pointMarker(point)]) for point in dangling]


def _ruleFloatingPin(context: schematicCheckContext) -> List[checkViolation]:
    return [checkViolation(
        "floatingPin", checkSeverity.WARNING,
        f"Unconnected pin {pin.owner} at {pin.point.toTuple()}.",
        [_pointMarker(pin.point)])
        for pin in context.pins
        if pin.direction != "Input"
        and context.pinGroupOf.get(pin.item) is None]


def _ruleFloatingInputPin(context: schematicCheckContext) -> List[
    checkViolation]:
    return [checkViolation(
        "floatingInputPin", checkSeverity.WARNING,
        f"Unconnected input pin {pin.owner} at {pin.point.toTuple()}.",
        [_pointMarker(pin.point)])
        for pin in context.pins
        if pin.direction == "Input"
        and context.pinGroupOf.get(pin.item) is None]


def _ruleShortedOutputs(context: schematicCheckContext) -> List[checkViolation]:
    outputsByGroup = defaultdict(list)
    for pin in context.pins:
        group = context.pinGroupOf.get(pin.item)
        if group is not None and pin.direction == "Output":
            outputsByGroup[group].append(pin)
    violations = []
    for pins in outputsByGroup.values():
        if len(pins) < 2:
            continue
        names = ", ".join(pin.owner for pin in pins)
        violations.append(checkViolation(
            "shortedOutputs", checkSeverity.ERROR,
            f"Shorted output pins: {names}.",
            [_pointMarker(pin.point) for pin in pins]))
    return violations


def _ruleNetNameConflict(context: schematicCheckContext) -> List[
    checkViolation]:
    violations = []
    flaggedNets = set()
    for group in context.netGroups:
        strongNames = {netItem.name for netItem in group
                       if netItem.name
                       and netItem.nameStrength ==
                       snet.netNameStrengthEnum.SET}
        if len(strongNames) > 1 and any(
                not snet.schematicNet._namesMatch(nameA, nameB)
                for nameA, nameB in combinations(strongNames, 2)):
            groupNets = [netItem for netItem in group
                         if netItem.nameStrength ==
                         snet.netNameStrengthEnum.SET]
            flaggedNets.update(groupNets)
            violations.append(checkViolation(
                "netNameConflict", checkSeverity.ERROR,
                f"Shorted net names on one node: "
                f"{', '.join(sorted(strongNames))}.",
                [_netSceneRect(netItem) for netItem in groupNets]))
    for netItem in context.netSet:
        if netItem.nameConflict and netItem not in flaggedNets:
            violations.append(checkViolation(
                "netNameConflict", checkSeverity.ERROR,
                f"Net name conflict on '{netItem.name}'.",
                [_netSceneRect(netItem)]))
    return violations


def _overlappingNetPairs(context: schematicCheckContext):
    """Yield (netA, netB) pairs whose bodies geometrically overlap."""
    seen = set()
    for netItem in context.netSet:
        for otherNet in netItem.findOverlapNets():
            if otherNet not in context.netSet:
                continue
            key = frozenset((id(netItem), id(otherNet)))
            if key in seen:
                continue
            seen.add(key)
            yield netItem, otherNet


def _collinearOverlapLength(netA: snet.schematicNet,
                            netB: snet.schematicNet,
                            snapDist: int) -> float:
    """Length of the interval two parallel nets share when they lie on the
    same line (perpendicular offset within snap distance); 0 otherwise."""
    p1, p2 = (QPointF(point) for point in netA.sceneEndPoints)
    q1, q2 = (QPointF(point) for point in netB.sceneEndPoints)
    direction = p2 - p1
    lengthSq = QPointF.dotProduct(direction, direction)
    if lengthSq < 1.0:
        return 0.0
    lengthA = math.sqrt(lengthSq)
    unit = direction / lengthA
    relQ1 = q1 - p1
    # Perpendicular distance from q1 to netA's line.
    perpDist = abs(relQ1.x() * unit.y() - relQ1.y() * unit.x())
    if perpDist > snapDist:
        return 0.0
    t1 = QPointF.dotProduct(relQ1, unit)
    t2 = QPointF.dotProduct(q2 - p1, unit)
    lo, hi = min(t1, t2), max(t1, t2)
    return max(0.0, min(lengthA, hi) - max(0.0, lo))


def _ruleOverlappingNets(context: schematicCheckContext) -> List[
    checkViolation]:
    """Collinear wire bodies sharing more than an endpoint's worth of
    overlap — duplicated wires and silent shorts."""
    violations = []
    for netA, netB in _overlappingNetPairs(context):
        if not netA.isParallel(netB):
            continue
        if _collinearOverlapLength(netA, netB,
                                   context.snapDist) <= context.snapDist:
            continue
        overlapRect = netA.sceneShapeRect.intersected(netB.sceneShapeRect)
        if not overlapRect.isEmpty():
            violations.append(checkViolation(
                "overlappingNets", checkSeverity.ERROR,
                f"Overlapping wires at "
                f"{overlapRect.center().toTuple()}.",
                [overlapRect]))
    return violations


def _ruleCrossoverNoJunction(context: schematicCheckContext) -> List[
    checkViolation]:
    """Perpendicular wire bodies crossing interior-to-interior with no
    vertex at the crossing — visually connected but electrically open."""
    violations = []
    for netA, netB in _overlappingNetPairs(context):
        if netA.isParallel(netB):
            continue
        if context.netGroupOf.get(netA) == context.netGroupOf.get(netB):
            continue
        lineA = QLineF(QPointF(netA.sceneEndPoints[0]),
                       QPointF(netA.sceneEndPoints[1]))
        lineB = QLineF(QPointF(netB.sceneEndPoints[0]),
                       QPointF(netB.sceneEndPoints[1]))
        intersectType, crossing = lineA.intersects(lineB)
        if intersectType != QLineF.IntersectionType.BoundedIntersection:
            continue
        crossingPoint = crossing.toPoint()
        endPoints = (netA.sceneEndPoints + netB.sceneEndPoints)
        if any((crossingPoint - endPoint).manhattanLength()
               <= context.snapDist for endPoint in endPoints):
            continue
        violations.append(checkViolation(
            "crossoverNoJunction", checkSeverity.WARNING,
            f"Wires cross without a junction at "
            f"{crossingPoint.toTuple()}.",
            [_pointMarker(crossingPoint)]))
    return violations


def _ruleDuplicateInstName(context: schematicCheckContext) -> List[
    checkViolation]:
    nameCounts = Counter(
        symbolItem.instanceName for symbolItem in context.symbolSet)
    violations = []
    for symbolItem in context.symbolSet:
        if nameCounts[symbolItem.instanceName] > 1:
            violations.append(checkViolation(
                "duplicateInstName", checkSeverity.ERROR,
                f"Duplicate instance name '{symbolItem.instanceName}'.",
                [symbolItem.mapToScene(
                    symbolItem.boundingRect()).boundingRect()]))
    return violations


def _ruleOffGridItems(context: schematicCheckContext) -> List[checkViolation]:
    snap = context.scene.snapToGrid
    offGridPoints = set()
    for netItem in context.netSet:
        for endPoint in netItem.sceneEndPoints:
            if snap(endPoint) != endPoint:
                offGridPoints.add(endPoint)
    for pin in context.pins:
        if snap(pin.point) != pin.point:
            offGridPoints.add(pin.point)
    for symbolItem in context.symbolSet:
        origin = symbolItem.scenePos().toPoint()
        if snap(origin) != origin:
            offGridPoints.add(origin)
    return [checkViolation(
        "offGridItems", checkSeverity.WARNING,
        f"Off-grid item at {point.toTuple()}.",
        [_pointMarker(point)]) for point in offGridPoints]


def _ruleBusWidthMismatch(context: schematicCheckContext) -> List[
    checkViolation]:
    violations = []
    for pin in context.pins:
        groupIndex = context.pinGroupOf.get(pin.item)
        if groupIndex is None:
            continue
        pinBase, pinIndices = snet.schematicNet.parseArrayNotation(pin.name)
        if pinIndices[0] == -1:
            continue  # pin is not bussed
        pinWidth = abs(pinIndices[0] - pinIndices[1])
        for netItem in context.netGroups[groupIndex]:
            if netItem.nameStrength != snet.netNameStrengthEnum.SET:
                continue
            netBase, netIndices = snet.schematicNet.parseArrayNotation(
                netItem.name)
            if netBase != pinBase or netIndices[0] == -1:
                continue  # different name is netNameConflict's job
            if abs(netIndices[0] - netIndices[1]) != pinWidth:
                violations.append(checkViolation(
                    "busWidthMismatch", checkSeverity.ERROR,
                    f"Bus width mismatch: pin {pin.owner} "
                    f"'{pin.name}' vs net '{netItem.name}'.",
                    [_pointMarker(pin.point), _netSceneRect(netItem)]))
    return violations


SCHEMATIC_RULES: List[schematicCheckRule] = [
    schematicCheckRule(
        "symbolOverlap", "Overlapping symbols",
        "Flags symbol instances whose drawn shapes overlap.",
        checkSeverity.ERROR, _ruleSymbolOverlap),
    schematicCheckRule(
        "danglingWireEnd", "Dangling wire ends",
        "Flags wire endpoints not connected to another wire or pin.",
        checkSeverity.WARNING, _ruleDanglingWireEnd),
    schematicCheckRule(
        "floatingPin", "Floating pins",
        "Flags pins that touch no wire (input pins are covered by a "
        "separate rule).",
        checkSeverity.WARNING, _ruleFloatingPin),
    schematicCheckRule(
        "floatingInputPin", "Floating input pins",
        "Flags Input-direction pins with no connected net.",
        checkSeverity.WARNING, _ruleFloatingInputPin),
    schematicCheckRule(
        "shortedOutputs", "Shorted output pins",
        "Flags two or more Output pins driving the same net.",
        checkSeverity.ERROR, _ruleShortedOutputs),
    schematicCheckRule(
        "netNameConflict", "Net name conflicts",
        "Flags electrically joined nets carrying different strong (SET) "
        "names, and nets already marked with a name conflict.",
        checkSeverity.ERROR, _ruleNetNameConflict),
    schematicCheckRule(
        "overlappingNets", "Overlapping wires",
        "Flags parallel wire segments drawn on top of each other "
        "(silent shorts).",
        checkSeverity.ERROR, _ruleOverlappingNets),
    schematicCheckRule(
        "crossoverNoJunction", "Crossing wires without junction",
        "Flags wires crossing interior-to-interior with no vertex at the "
        "crossing — looks connected but is not.",
        checkSeverity.WARNING, _ruleCrossoverNoJunction),
    schematicCheckRule(
        "duplicateInstName", "Duplicate instance names",
        "Flags symbol instances sharing the same instance name.",
        checkSeverity.ERROR, _ruleDuplicateInstName),
    schematicCheckRule(
        "offGridItems", "Off-grid items",
        "Flags net endpoints, pin origins, and symbol origins not on the "
        "snap grid.",
        checkSeverity.WARNING, _ruleOffGridItems),
    schematicCheckRule(
        "busWidthMismatch", "Bus width mismatch",
        "Flags bussed pins connected to like-named nets of a different "
        "bus width.",
        checkSeverity.ERROR, _ruleBusWidthMismatch),
]

_RULES_BY_ID = {rule.ruleId: rule for rule in SCHEMATIC_RULES}


def runChecks(context: schematicCheckContext,
              enabledIds: Optional[Set[str]] = None) -> List[checkViolation]:
    """Run every registered rule (or only ``enabledIds``) over the shared
    context and return all violations."""
    violations = []
    for rule in SCHEMATIC_RULES:
        if enabledIds is not None and rule.ruleId not in enabledIds:
            continue
        violations.extend(rule.run(context))
    return violations
