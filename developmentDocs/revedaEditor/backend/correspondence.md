# `revedaEditor/backend/correspondence.py`

**Module:** `revedaEditor.backend.correspondence`

## Purpose

Schematic↔layout correspondence engine (Phase 6): canonical `sdl` record accessors, name-correspondence diff → `SyncPlan`, `pcellParamsFor` label→kwarg mapping, `flylineEndpoints`.

## Module docstring

Schematic<->layout correspondence engine (XL-lite).

One correspondence model shared by GUI scenes, aiTerminal ops, and batch
tooling — Qt-free so it can run on decoded JSON records headlessly.

The persisted contract is the `sdl` field on `Inst`/`Pcell` layout
records, mirrored on the live item as `layoutInstance._sdlSource`::

    {"lib": <schematic lib>, "cell": <schematic cell>,
     "view": <schematic view>, "inst": <schematic instance name>,
     "labels": {<labelName>: [<value>, <visible>]}}

`lib`/`cell`/`view` identify the *source schematic cellview* (the cell
pair), `inst` the instance inside it. An instance whose `sdl` points at a
different source is foreign to a sync run and is never touched.

Legacy in-memory dicts written before the field was persisted used
`schematicLib`/`schematicCell`/`schematicInstance` keys (the instance's
*referenced* cell, not the source); :func:`sdlInstName` normalizes both
shapes. Such dicts carry no source identity, so they only match by name.

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

- [[revedaEditor/connectivity/__init__|revedaEditor.connectivity.__init__]]

## Used by

- [[revedaEditor/scenes/layoutScene|revedaEditor.scenes.layoutScene]]
- [[revedaEditor/tests/test_correspondence|revedaEditor.tests.test_correspondence]]
