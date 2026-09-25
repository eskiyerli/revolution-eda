# `revedaEditor\fileio\spiceNetlist.py`

**Module:** `revedaEditor.fileio.spiceNetlist`

## Purpose

SPICE netlist parsing utilities.

## Functions

- `parse_spice_netlist()` — Parse a SPICE netlist and extract subcircuit definitions.
- `build_hierarchy_tree()` — Build a recursive hierarchy tree from parsed SPICE subcircuits.
- `get_top_level_subcircuit()` — Return the name of the top-level subcircuit in a parsed netlist.
- `_terminal_names_for()` — Return terminal names for *net_count* nets of a device with *prefix*.
- `_join_continuation_lines()` — Join SPICE continuation lines (starting with +) into logical lines.
- `_parse_device_line()` — Parse a single SPICE primitive device line into a device dict.
- `parse_extracted_netlist()` — Parse a KLayout extracted SPICE netlist into the format needed by generateSchematic.

## Used by

- [[revedaEditor\tests\test_spiceNetlist|revedaEditor.tests.test_spiceNetlist]]
