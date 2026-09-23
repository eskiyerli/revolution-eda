# `revedaEditor/fileio/spiceNetlist.py`

**Module:** `revedaEditor.fileio.spiceNetlist`

## Purpose

SPICE/extracted-netlist parsing utilities: subcircuit hierarchy trees, device-line parsing.

## Module docstring

SPICE netlist parsing utilities.

Provides functions to parse SPICE subcircuit netlists into a structured
representation that can be used for hierarchy tree views, schematic
generation, and other downstream tasks.

## Functions

- `parse_spice_netlist()` — Parse a SPICE netlist and extract subcircuit definitions.
- `build_hierarchy_tree()` — Build a recursive hierarchy tree from parsed SPICE subcircuits.
- `get_top_level_subcircuit()` — Return the name of the top-level subcircuit in a parsed netlist.
- `_terminal_names_for()` — Return terminal names for *net_count* nets of a device with *prefix*.
- `_join_continuation_lines()` — Join SPICE continuation lines (starting with +) into logical lines.
- `_parse_device_line()` — Parse a single SPICE primitive device line into a device dict.
- `parse_extracted_netlist()` — Parse a KLayout extracted SPICE netlist into the format needed by generateSchematic.

## Used by

- [[revedaEditor/tests/test_spiceNetlist|revedaEditor.tests.test_spiceNetlist]]
