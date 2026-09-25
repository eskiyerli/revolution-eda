# `revedaEditor\connectivity\graph.py`

**Module:** `revedaEditor.connectivity.graph`

## Purpose

Geometric union-find over wire segments.

## Classes

- `_UnionFind`
  - `find()`
  - `union()`

## Functions

- `_pointSegDist()` — Euclidean distance from point p to segment a-b.
- `_manhattan()`
- `segmentsJoin()` — True when A and B electrically touch per the canonical rules.
- `buildGroups()` — Union segments into physically connected groups.
