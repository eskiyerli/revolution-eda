# `revedaEditor/connectivity/graph.py`

**Module:** `revedaEditor.connectivity.graph`

## Purpose

Union-find connectivity graph: merges shapes through geometric touch and via-stack rules into net groups.

## Module docstring

Geometric union-find over wire segments.

Canonical join semantics (adopted from `checks.schematic.buildCheckContext`,
which supersedes the endpoint-only `checkNetConnect`):

- endpoint coincidence: any endpoint of A within `endpointTol` Manhattan
  distance of any endpoint of B;
- endpoint-on-body (T contact): any endpoint of A within `bodyTol` of
  segment B's interior, or vice versa.

Interior crossings with no endpoint involvement are *not* joins — they stay
`crossoverNoJunction` warnings, as before.

## Classes

- `_UnionFind`
  - `find()`
  - `union()`

## Functions

- `_pointSegDist()` — Euclidean distance from point p to segment a-b.
- `_manhattan()`
- `segmentsJoin()` — True when A and B electrically touch per the canonical rules.
- `buildGroups()` — Union segments into physically connected groups.
