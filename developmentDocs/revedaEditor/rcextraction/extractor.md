# `revedaEditor/rcextraction/extractor.py`

**Module:** `revedaEditor.rcextraction.extractor`

## Purpose

Unified RC extractor consuming the RCX database: parasitic R/C modeling, device pin anchoring, coupling capacitance.

## Module docstring

Unified RC extractor that consumes an RCX database.

This is the main extraction engine. It reads a pre-solved .rcx.json
(produced by the LVS export step) and computes parasitic R and C for
each net. It then outputs a complete netlist with both the original
devices and parasitic elements.

The extractor builds a connected spatial graph of resistors and capacitors
for each net, linking wire segments, vias, ports, and transistor terminals.

## Classes

- `ParasiticResistor` — An extracted parasitic resistor within a net.
- `ParasiticCapacitor` — An extracted parasitic capacitor.
- `DeviceInstance` — A device to include in the output netlist.
- `ExtractionResult` — Complete extraction output: devices + parasitics.
  - `total_r()`
  - `total_c()`
- `NetGraph` — Manages electrical nodes in physical space (x, y, layer) for a single net.
  - `has_nodes()`
  - `get_or_create_node()`
  - `find_nearest_node()`
  - `get_port_node()`
  - `get_port_node_by_layer()`
  - `alias_node()`

## Functions

- `extract()` — Run parasitic RC extraction on an RCX database.
- `_merge_pcell_internal_nodes()` — Merge nodes on layers that have no routing shapes in the net.
- `_rename_node_in_result()` — Rename a node across all resistors, capacitors, and caps dict.
- `_extract_net_parasitics()` — Extract connected R and substrate C for a single net.
- `_extract_net_capacitance()` — Lump a net's total substrate capacitance onto its net-name node.
- `_projectOntoShapes()` — Project a via cut center onto the centerline of the nearest overlapping shape on the given layer.
- `_extract_coupling()` — Extract coupling capacitance between two nets.
- `_connect_devices()` — Connect devices directly to their corresponding nodes in the parasitic network.
- `_get_bbox()` — Get bounding box of a shape as (x1, y1, x2, y2).
- `_overlap_info()` — Compute overlap area in um^2 and center (cx, cy) in dbu.
- `_lateral_coupling_info()` — Estimate lateral coupling and return (cap_fF, cx, cy).
