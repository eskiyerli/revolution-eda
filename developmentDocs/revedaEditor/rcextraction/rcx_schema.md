# `revedaEditor\rcextraction\rcx_schema.py`

**Module:** `revedaEditor.rcextraction.rcx_schema`

## Purpose

RCX database schema — the contract between LVS and RC extraction.

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
