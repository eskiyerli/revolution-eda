# `revedaEditor\backend\correspondence.py`

**Module:** `revedaEditor.backend.correspondence`

## Purpose

Schematic<->layout correspondence engine (XL-lite).

## Classes

- `SyncPlan` — Result of :func:`correspondenceDiff`.

## Functions

- `makeSdlSource()` — Canonical `_sdlSource`/`sdl` record shape.
- `sdlInstName()` — Schematic instance name, tolerant of the legacy key shape.
- `sdlSourceKey()` — (lib, cell, view) of the source schematic, or None when absent.
- `sdlLabels()`
- `_labelValue()` — `ld` entries are [value, visible]; live values may be plain.
- `schematicInstances()` — {instName: sys-record} from a decoded schematic design array.
- `_labelsChanged()` — True when the stored sdl labels differ from the record's `ld`.
- `correspondenceDiff()` — Diff schematic instances against layout instance descriptors.
- `pcellParamsFor()` — Map schematic labels to pcell call parameters.
- `flylineEndpoints()` — Resolve `{netName: [(instName, pinName), ...]}` from schematic records.

## Depends on

- [[revedaEditor\connectivity\__init__|revedaEditor.connectivity.__init__]]

## Used by

- [[revedaEditor\scenes\layoutScene|revedaEditor.scenes.layoutScene]]
- [[revedaEditor\tests\test_correspondence|revedaEditor.tests.test_correspondence]]
