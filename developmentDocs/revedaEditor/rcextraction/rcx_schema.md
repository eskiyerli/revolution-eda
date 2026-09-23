# `revedaEditor/rcextraction/rcx_schema.py`

**Module:** `revedaEditor.rcextraction.rcx_schema`

## Purpose

RCX database schema definitions.

## Module docstring

RCX database schema — the contract between LVS and RC extraction.

The .rcx.json file is the extraction database that LVS produces and the
RC extractor consumes. It contains:
- Verified net connectivity with schematic net names
- Net geometry (shapes on routing layers for R/C computation)
- Device list with model names, parameters, and terminal-to-net mapping
- Port definitions (external interface of the cell)

This module defines the schema as dataclasses and provides load/save utilities.

## Classes

- `RcxShape` — A geometric shape belonging to a net on a specific layer.
- `RcxVia` — A via instance within a net.
- `RcxNet` — A verified net with schematic name and layout geometry.
- `RcxTerminal` — A device terminal connection.
- `RcxDevice` — A circuit device (transistor, resistor, capacitor, etc.).
- `RcxDatabase` — Complete extraction database — the .rcx.json content.
  - `get_net()`
  - `get_device()`

## Functions

- `save_rcx_database()` — Save an RCX database to a JSON file.
- `load_rcx_database()` — Load an RCX database from a JSON file.
