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

"""Net name resolution — single implementation of nameSceneNets semantics.

Priority order (mirroring ``schematicScene.nameSceneNets``):

1. global symbol pins (name ends with ``!``) — name applied SET;
2. schematic (sheet) pins — name applied INHERIT, with SET-name conflict and
   bus-width checks;
3. SET-named segments — name propagates through the group;
4. everything else — auto ``net<N>`` names, WEAK.

Differences from the legacy implementation, by design:

- traversal order is deterministic (sorted by id / position), so auto net
  numbering is stable across runs;
- conflicts are collected as data instead of aborting the whole pass on the
  first one;
- two different pin names on one group are flagged ``pinNameConflict``
  (legacy code silently let the last pin win).
"""

from __future__ import annotations

from typing import Optional

from .graph import _pointSegDist, buildGroups
from .netexpr import parseNetExpr
from .primitives import (INHERIT, NONAME, SET, WEAK, Conflict,
                         ConnectivityResult, NetGroup, Port, Seg,
                         busWidth, namesMatch)


def _attachPorts(ports: list[Port], segs: dict[int, Seg],
                 segGroup: dict[int, int], portTol: float,
                 ) -> dict[int, Optional[int]]:
    """Map each port to the group containing a segment within portTol.

    A port attaches when its connection point lies within ``portTol`` of a
    segment (endpoint proximity and pin-on-body are both covered by
    point-to-segment distance — the union of the legacy bounding-rect and
    endpoint-snap rules).
    """
    portGroup: dict[int, Optional[int]] = {}
    for port in ports:
        groupIndex = None
        bestDist = None
        for segId, seg in segs.items():
            dist = _pointSegDist(port.point, seg.p1, seg.p2)
            if dist <= portTol and (bestDist is None or dist < bestDist):
                bestDist = dist
                groupIndex = segGroup[segId]
        portGroup[port.id] = groupIndex
    return portGroup


def _resolveGroup(group: NetGroup, segs: dict[int, Seg],
                  ports: dict[int, Port], autoName: Optional[str],
                  portTol: float,
                  segName: dict[int, tuple[str, int]],
                  segConflicts: set[int], conflicts: list[Conflict],
                  portExprNet: dict[int, str],
                  segExprNet: dict[int, str]) -> None:
    members = sorted(group.members)
    memberSegs = [segs[segId] for segId in members]
    groupPorts = sorted((ports[p] for p in group.ports),
                        key=lambda p: (p.point, p.id))
    globalPorts = [p for p in groupPorts if p.isGlobal]
    # Only sheet pins name nets; non-global symbol pins merely attach.
    schemPorts = [p for p in groupPorts if p.kind == "schemPin"]
    setSegs = [s for s in memberSegs if s.strength == SET and s.name]

    # Resolved net expressions on this group. A "!" result behaves like a
    # global pin; a plain result is a pin-tier name assertion (connect by
    # name), weaker than an explicit SET wire name.
    exprPorts = [(p, portExprNet[p.id]) for p in groupPorts
                 if p.id in portExprNet]
    exprSegs = [(s, segExprNet[s.id]) for s in memberSegs
                if s.id in segExprNet]
    globalExprPorts = [(p, n) for p, n in exprPorts if n.endswith("!")]
    globalExprSegs = [(s, n) for s, n in exprSegs if n.endswith("!")]

    def flag(kind: str, message: str, segIds=(), portIds=()):
        conflicts.append(Conflict(kind, message, tuple(segIds),
                                  tuple(portIds)))
        segConflicts.update(segIds)

    globalNames = sorted(
        {p.name for p in globalPorts}
        | {n for _, n in globalExprPorts}
        | {n for _, n in globalExprSegs})
    pinNames = sorted(
        {p.name for p in schemPorts}
        | {n for _, n in (*exprPorts, *exprSegs)
           if not n.endswith("!")})
    setNames = sorted({s.name for s in setSegs})

    winner = None
    if globalNames:
        winner = globalNames[0]
        if len(globalNames) > 1:
            flag("netNameConflict",
                 f"Conflicting global pins on one node: "
                 f"{', '.join(globalNames)}.",
                 # segConflicts drives wire highlighting, so it must carry
                 # actual segment IDs rather than the independently numbered
                 # global-port IDs.
                 segIds=members,
                 portIds=[p.id for p in globalPorts])
        for name in setNames:
            if not namesMatch(winner, name):
                flag("netNameConflict",
                     f"Net name conflict at global pin '{winner}' vs "
                     f"SET name '{name}'.",
                     segIds=[s.id for s in setSegs if s.name == name],
                     portIds=[p.id for p in globalPorts
                              if p.name == winner])
    elif setNames:
        winner = setNames[0]
        conflicting = [n for n in setNames[1:] if not namesMatch(winner, n)]
        if conflicting:
            flag("netNameConflict",
                 f"Shorted net names on one node: "
                 f"{', '.join(setNames)}.",
                 segIds=[s.id for s in setSegs])
    elif pinNames:
        winner = pinNames[0]
        if len(pinNames) > 1:
            flag("pinNameConflict",
                 f"Conflicting pin names on one node: "
                 f"{', '.join(pinNames)}.",
                 portIds=[p.id for p in schemPorts])
    elif autoName is not None:
        winner = autoName

    # Pin-side checks apply even when a stronger name wins.
    for pin in schemPorts:
        pinWidth = busWidth(pin.name)
        for seg in setSegs:
            if not namesMatch(pin.name, seg.name):
                flag("netNameConflict",
                     f"Net name conflict: net '{seg.name}' vs pin "
                     f"'{pin.name}'.",
                     segIds=[seg.id], portIds=[pin.id])
            elif (pinWidth is not None and busWidth(seg.name) is not None
                  and busWidth(seg.name) != pinWidth):
                flag("busWidthMismatch",
                     f"Incompatible bus sizes: {pin.name} <-> {seg.name}.",
                     segIds=[seg.id], portIds=[pin.id])
    # Expression assertions vs SET names: mismatch is a genuine short.
    for carrier, exprName in (*exprPorts, *exprSegs):
        if exprName.endswith("!"):
            continue  # handled by the global-name conflict loop above
        carrierIsPort = isinstance(carrier, Port)
        for seg in setSegs:
            if not namesMatch(exprName, seg.name):
                flag("netNameConflict",
                     f"Net name conflict: net '{seg.name}' vs net "
                     f"expression '{carrier.expr}' (resolved "
                     f"'{exprName}').",
                     segIds=[seg.id]
                     + ([] if carrierIsPort else [carrier.id]),
                     portIds=[carrier.id] if carrierIsPort else [])

    if winner is None:
        return
    group.name = winner
    group.strength = (SET if globalNames else
                      (INHERIT if pinNames and not setNames else SET))

    attachedToGlobal = [p for p in globalPorts if p.name == winner]
    globalPoints = [p.point for p in attachedToGlobal]
    globalPoints += [p.point for p, n in globalExprPorts if n == winner]
    globalExprSegIds = {s.id for s, n in globalExprSegs if n == winner}
    for seg in memberSegs:
        if seg.strength == SET and seg.name and namesMatch(seg.name, winner):
            segName[seg.id] = (seg.name, SET)
        elif (seg.id in globalExprSegIds
              or any(_pointSegDist(point, seg.p1, seg.p2) <= portTol
                     for point in globalPoints)):
            # Segments directly under a global pin (or carrying a
            # global-resolving expression) keep SET strength, matching
            # findGlobalNets which SETs colliding nets.
            segName[seg.id] = (winner, SET)
        else:
            segName[seg.id] = (winner, INHERIT)


def resolve(segs: list[Seg], ports: list[Port], *, endpointTol: float = 1.0,
            bodyTol: float = 5.0, portTol: float = 10.0,
            netSet: Optional[dict] = None,
            ) -> ConnectivityResult:
    """Build connectivity for one sheet and resolve all net names.

    ``netSet`` maps net-expression names to local net names (inherited
    connections). An expression ``[@name:default]`` resolves to the bound
    net when present, else its default, else the bare name; a ``!``-suffixed
    result behaves like a global pin, a plain result asserts a pin-tier
    name. ``None`` evaluates every expression to its default — the
    top-level/canvas context.
    """
    binds = netSet or {}
    segSets, segGroup = buildGroups(segs, endpointTol=endpointTol,
                                  bodyTol=bodyTol)
    segById = {s.id: s for s in segs}
    portById = {p.id: p for p in ports}
    portGroup = _attachPorts(ports, segById, segGroup, portTol)

    groups: list[NetGroup] = []
    for index, members in enumerate(segSets):
        groups.append(NetGroup(id=index, members=set(members)))
    for port in ports:
        index = portGroup[port.id]
        if index is not None:
            groups[index].ports.add(port.id)

    segName: dict[int, tuple[str, int]] = {}
    segConflicts: set[int] = set()
    conflicts: list[Conflict] = []

    # Evaluate net expressions once — the single evaluation point shared by
    # GUI, record checks, and netlisting.
    exprNames: dict[str, str] = {}
    portExprNet: dict[int, str] = {}
    segExprNet: dict[int, str] = {}
    for carrier in (*ports, *segs):
        if not carrier.expr:
            continue
        parsed = parseNetExpr(carrier.expr)
        isPort = isinstance(carrier, Port)
        ids = {"portIds": (carrier.id,)} if isPort else {
            "segIds": (carrier.id,)}
        if parsed is None:
            conflicts.append(Conflict(
                "badNetExpr",
                f"Malformed net expression {carrier.expr!r} on "
                f"'{carrier.name or '?'}'.", **ids))
            continue
        name, default = parsed
        if name in exprNames:
            if default and exprNames[name] and exprNames[name] != default:
                conflicts.append(Conflict(
                    "exprDefaultConflict",
                    f"Net expression '{name}' has conflicting defaults "
                    f"'{exprNames[name]}' and '{default}'.", **ids))
        else:
            exprNames[name] = default
        # Symbol-pin exprs evaluate against their owning instance's netSet
        # (inherited-connection overrides), shadowed onto the sheet-level
        # bindings so unbound names still propagate upward. Sheet pins and
        # wire exprs use the sheet bindings directly.
        portBinds = binds
        if isPort and carrier.kind == "symbolPin" and carrier.netSet:
            portBinds = {**binds, **carrier.netSet}
        resolved = portBinds.get(name) or default or name
        if isPort:
            portExprNet[carrier.id] = resolved
        else:
            segExprNet[carrier.id] = resolved

    # Deterministic auto-numbering: unnamed groups ordered by smallest seg id.
    autoCounter = 0
    for group in groups:
        needsAuto = (
            not any(p.isGlobal for p in
                    (portById[i] for i in group.ports))
            and not any(portById[i].kind == "schemPin"
                        for i in group.ports)
            and not any(segById[s].strength == SET and segById[s].name
                        for s in group.members)
            and not any(i in portExprNet for i in group.ports)
            and not any(s in segExprNet for s in group.members))
        autoName = f"net{autoCounter}" if needsAuto else None
        if needsAuto:
            autoCounter += 1
        _resolveGroup(group, segById, portById, autoName, portTol, segName,
                      segConflicts, conflicts, portExprNet, segExprNet)
        if needsAuto:
            group.strength = WEAK

    # Auto-named groups: origin member (smallest id) keeps WEAK, the rest
    # inherit — matching the legacy mergeNetName propagation result.
    for group in groups:
        if group.name and group.strength == WEAK:
            origin = min(group.members)
            for segId in group.members:
                segName[segId] = (group.name,
                                  WEAK if segId == origin else INHERIT)

    # Unnamed segments (empty-name auto groups can't occur; this covers segs
    # in groups resolved above that were never assigned) get NONAME.
    for seg in segs:
        segName.setdefault(seg.id, (seg.name if seg.strength == SET else "",
                                    seg.strength if seg.strength == SET
                                    else NONAME))

    return ConnectivityResult(groups=groups, segGroup=segGroup,
                              portGroup=portGroup, segName=segName,
                              segConflicts=segConflicts, conflicts=conflicts,
                              autoCount=autoCounter, exprNames=exprNames,
                              portExprNet=portExprNet)
