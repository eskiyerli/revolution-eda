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

"""Geometric union-find over wire segments.

Canonical join semantics (adopted from ``checks.schematic.buildCheckContext``,
which supersedes the endpoint-only ``checkNetConnect``):

- endpoint coincidence: any endpoint of A within ``endpointTol`` Manhattan
  distance of any endpoint of B;
- endpoint-on-body (T contact): any endpoint of A within ``bodyTol`` of
  segment B's interior, or vice versa.

Interior crossings with no endpoint involvement are *not* joins — they stay
``crossoverNoJunction`` warnings, as before.
"""

from __future__ import annotations

import math

from .primitives import Point, Seg


def _pointSegDist(p: Point, a: Point, b: Point) -> float:
    """Euclidean distance from point p to segment a-b."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    lenSq = dx * dx + dy * dy
    if lenSq < 1e-9:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / lenSq
    t = max(0.0, min(1.0, t))
    return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))


def _manhattan(p: Point, q: Point) -> float:
    return abs(p[0] - q[0]) + abs(p[1] - q[1])


def segmentsJoin(a: Seg, b: Seg, endpointTol: float, bodyTol: float) -> bool:
    """True when A and B electrically touch per the canonical rules."""
    endsA = (a.p1, a.p2)
    endsB = (b.p1, b.p2)
    for p in endsA:
        for q in endsB:
            if _manhattan(p, q) <= endpointTol:
                return True
    for p in endsA:
        if _pointSegDist(p, b.p1, b.p2) <= bodyTol:
            return True
    for q in endsB:
        if _pointSegDist(q, a.p1, a.p2) <= bodyTol:
            return True
    return False


class _UnionFind:
    def __init__(self, ids):
        self._parent = {i: i for i in ids}

    def find(self, item):
        parent = self._parent
        root = item
        while parent[root] != root:
            root = parent[root]
        while parent[item] != item:
            parent[item], item = root, parent[item]
        return root

    def union(self, a, b):
        rootA, rootB = self.find(a), self.find(b)
        if rootA != rootB:
            # deterministic: smaller id is the root
            if rootB < rootA:
                rootA, rootB = rootB, rootA
            self._parent[rootB] = rootA


def buildGroups(segs: list[Seg], endpointTol: float = 1.0,
                bodyTol: float = 5.0) -> tuple[list[set[int]], dict[int, int]]:
    """Union segments into physically connected groups.

    Returns (groups, segGroup) where groups is a list of seg-id sets ordered
    deterministically by smallest member id, and segGroup maps seg id ->
    group index.
    """
    uf = _UnionFind(seg.id for seg in segs)
    ordered = sorted(segs, key=lambda s: s.id)
    # Spatial index on segment bounding boxes (inflated by bodyTol) so pair
    # checks stay near-linear instead of O(n^2) over the whole sheet.
    grid: dict[tuple[int, int], list[int]] = {}
    cellSize = max(bodyTol * 4, endpointTol * 4, 40)
    bounds: dict[int, tuple[float, float, float, float]] = {}
    for seg in ordered:
        x0, x1 = sorted((seg.p1[0], seg.p2[0]))
        y0, y1 = sorted((seg.p1[1], seg.p2[1]))
        bounds[seg.id] = (x0 - bodyTol - endpointTol, y0 - bodyTol - endpointTol,
                          x1 + bodyTol + endpointTol, y1 + bodyTol + endpointTol)
        bx0, by0, bx1, by1 = bounds[seg.id]
        for gx in range(int(bx0 // cellSize), int(bx1 // cellSize) + 1):
            for gy in range(int(by0 // cellSize), int(by1 // cellSize) + 1):
                grid.setdefault((gx, gy), []).append(seg.id)

    seenPairs: set[frozenset[int]] = set()
    byId = {seg.id: seg for seg in ordered}
    for seg in ordered:
        bx0, by0, bx1, by1 = bounds[seg.id]
        candidates = set()
        for gx in range(int(bx0 // cellSize), int(bx1 // cellSize) + 1):
            for gy in range(int(by0 // cellSize), int(by1 // cellSize) + 1):
                candidates.update(grid.get((gx, gy), ()))
        for otherId in candidates:
            if otherId == seg.id:
                continue
            pairKey = frozenset((seg.id, otherId))
            if pairKey in seenPairs:
                continue
            seenPairs.add(pairKey)
            other = byId[otherId]
            ox0, oy0, ox1, oy1 = bounds[otherId]
            if bx1 < ox0 or ox1 < bx0 or by1 < oy0 or oy1 < by0:
                continue
            if segmentsJoin(seg, other, endpointTol, bodyTol):
                uf.union(seg.id, otherId)

    grouped: dict[int, set[int]] = {}
    for seg in ordered:
        grouped.setdefault(uf.find(seg.id), set()).add(seg.id)
    groups = [grouped[k] for k in sorted(grouped, key=lambda r: min(grouped[r]))]
    segGroup = {segId: index for index, members in enumerate(groups)
                for segId in members}
    return groups, segGroup
