# `revedaEditor/fileio/importlvsdb.py`

**Module:** `revedaEditor.fileio.importlvsdb`

## Purpose

KLayout LVS database (`.lvsdb`) parser producing error markers (`LVSErrorRect`) for the results browser.

## Classes

- `LVSErrorRect(QGraphicsRectItem)`
  - `cell()`
  - `cell()`
  - internals: `__repr__()`, `__str__()`
- `LVSDBParser` — Parses KLayout .lvsdb files into Python structures for Revolution EDA.
  - `tokenize()`
  - `parse_expression()`
  - `load()`
  - `get_all_layout_cells()`
  - `get_all_schematic_cells()`
  - `get_nets()`
  - `get_nets_with_schematic_names()`
  - `get_layout_devices()`
  - `get_schematic_devices()`
  - `get_schematic_nets()`
  - `get_extracted_schematic()`
  - `get_crossref()`
  - `get_all_crossrefs_formatted()`
  - `get_layout_cells_with_bbox()`
  - `get_connectivity()`
  - internals: `_find_section()`, `_process_units()`, `_process_crossrefs()`, `_parse_crossref_mapping()`, `_parse_crossref_diagnostics()`, `_extract_diagnostic_message()`, `_count_explicit_net_mismatches()`, `_is_internal_net_mismatch_message()`, `_normalize_device_type()`, `_normalize_param_value()`, `_device_param_signature()`, `_estimate_device_property_mismatches()` … (+16)

## Used by

- [[revedaEditor/gui/lvsResults|revedaEditor.gui.lvsResults]]
