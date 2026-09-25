# `revedaEditor\rcextraction\netlist.py`

**Module:** `revedaEditor.rcextraction.netlist`

## Purpose

Netlist writers for parasitic extraction results.

## Classes

- `NetlistWriter(ABC)` — Base class for netlist output writers.
  - `write()`
- `SpiceWriter(NetlistWriter)` — Write parasitic netlist in SPICE format.
  - `write()`
- `SpefWriter(NetlistWriter)` — Write parasitic netlist in SPEF (Standard Parasitic Exchange Format).
  - `write()`
- `SpectreWriter(NetlistWriter)` — Write parasitic netlist in Cadence Spectre format.
  - `write()`
- `VacaskWriter(NetlistWriter)` — Write parasitic netlist in VACASK format.
  - `write()`

## Functions

- `_format_spice_device()` — Format a device instance as a SPICE subcircuit call.
- `_format_spectre_device()` — Format a device instance in Spectre syntax.
- `_format_vacask_device()` — Format a device instance in VACASK syntax.
- `_get_terminal_order()` — Get standard terminal order for a device model.
- `_format_param()` — Format a parameter value for netlist output.
- `_sanitize_node()` — Sanitize a node name for netlist output.
- `_spef_node()` — Get SPEF node reference.
- `get_writer()` — Get a netlist writer by format name.
