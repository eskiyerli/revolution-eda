# `revedaEditor/rcextraction/layoutGeometry.py`

**Module:** `revedaEditor.rcextraction.layoutGeometry`

## Purpose

Record-driven layout geometry reader feeding the extractor — independent of the live scene.

## Module docstring

Backwards-compatible shim: the layout connectivity engine and the
`layout.json` record reader now live in
:mod:`revedaEditor.connectivity.layout`, shared by the live
`layoutScene` (net highlighting), RCX, and batch tooling.

Why this path exists: the KLayout `.lvsdb` is a *connectivity* database
whose per-net shapes live on internal rule-deck layers with no GDS mapping;
`layout.json` holds the real drawn interconnect. Net *names* are attached
separately (see :mod:`rcxExport`) using label positions from the LVSDB.

## Depends on

- [[revedaEditor/connectivity/layout|revedaEditor.connectivity.layout]]
