# SPDX-License-Identifier: MPL-2.0
#
# Copyright (c) 2024-2026 Revolution Semiconductor (Registered in the Netherlands)
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this file, You can obtain one at
# https://mozilla.org/MPL/2.0/.
#
# Add-ons and extensions developed for this software may be distributed
# under their own separate licenses.

"""SPICE netlist parsing utilities.

Provides functions to parse SPICE subcircuit netlists into a structured
representation that can be used for hierarchy tree views, schematic
generation, and other downstream tasks.
"""

from __future__ import annotations

import pathlib
import re
from typing import Any


def parse_spice_netlist(netlist_path: str | pathlib.Path | None) -> dict[str, dict[str, Any]]:
    """Parse a SPICE netlist and extract subcircuit definitions.

    Reads a SPICE netlist file, extracts all ``.SUBCKT`` / ``.ENDS`` blocks,
    and for each subcircuit records its pins and subcircuit-call (``X``)
    instances.

    Args:
        netlist_path: Path to the SPICE netlist file.  ``None`` or a
            non-existent path produces an empty dict.

    Returns:
        A dict keyed by casefolded subcircuit name.  Each value is::

            {
                "name": str,          # original subcircuit name
                "pins": list[str],    # pin names from .SUBCKT line
                "instances": dict[str, dict],  # instance_name -> info
            }

        Each instance info dict has keys ``name``, ``cell_name``, and
        ``connections`` (list of net names).
    """
    if netlist_path is None:
        return {}
    path = pathlib.Path(netlist_path)
    if not path.exists():
        return {}

    subckts: dict[str, dict[str, Any]] = {}
    current: dict[str, Any] | None = None

    with path.open("r", encoding="utf-8") as netlist_file:
        for raw_line in netlist_file:
            line = raw_line.strip()
            if not line or line.startswith("*"):
                continue

            upper_line = line.upper()
            if upper_line.startswith(".SUBCKT"):
                tokens = line.split()
                if len(tokens) < 2:
                    current = None
                    continue
                name = tokens[1]
                current = {
                    "name": name,
                    "pins": tokens[2:],
                    "instances": {},
                }
                subckts[name.casefold()] = current
                continue

            if upper_line.startswith(".ENDS"):
                current = None
                continue

            if current is None or line[:1].upper() != "X":
                continue

            tokens = line.split()
            if len(tokens) < 3:
                continue

            instance_name = tokens[0][1:]
            call_tokens = tokens[1:]
            cell_index = next(
                (
                    index
                    for index in range(len(call_tokens) - 1, -1, -1)
                    if "=" not in call_tokens[index]
                ),
                None,
            )
            if cell_index is None:
                continue

            cell_name = call_tokens[cell_index]
            connections = call_tokens[:cell_index]
            current["instances"][instance_name] = {
                "name": instance_name,
                "cell_name": cell_name,
                "connections": connections,
            }

    return subckts


def build_hierarchy_tree(
    subckts: dict[str, dict[str, Any]],
    top_cell_name: str,
    visited: set[str] | None = None,
) -> dict[str, Any] | None:
    """Build a recursive hierarchy tree from parsed SPICE subcircuits.

    Starting from *top_cell_name*, recursively walks the subcircuit
    instance calls to produce a nested dict representing the design
    hierarchy.

    Args:
        subckts: Result of :func:`parse_spice_netlist`.
        top_cell_name: Name of the top-level subcircuit (case-insensitive).
        visited: Internal set for cycle detection.

    Returns:
        A nested dict with keys ``name``, ``pins``, ``instances`` (list
        of child nodes), or ``None`` if the cell is not found or a cycle
        is detected.
    """
    key = top_cell_name.casefold()
    if visited is None:
        visited = set()
    if key in visited:
        return None
    visited = visited | {key}

    subckt = subckts.get(key)
    if subckt is None:
        return None

    node: dict[str, Any] = {
        "name": subckt["name"],
        "pins": list(subckt.get("pins", [])),
        "instances": [],
    }

    for inst_info in subckt.get("instances", {}).values():
        child_cell = inst_info.get("cell_name", "")
        if not child_cell:
            continue
        child_node = build_hierarchy_tree(subckts, child_cell, visited)
        if child_node is None:
            child_node = {"name": child_cell, "pins": [], "instances": []}
        child_node["instance_name"] = inst_info.get("name", "")
        child_node["connections"] = list(inst_info.get("connections", []))
        node["instances"].append(child_node)

    return node


def get_top_level_subcircuit(subckts: dict[str, dict[str, Any]]) -> str | None:
    """Return the name of the top-level subcircuit in a parsed netlist.

    The top-level subcircuit is the one that is never instantiated by
    any other subcircuit in the netlist.

    Args:
        subckts: Result of :func:`parse_spice_netlist`.

    Returns:
        The original (non-casefolded) name of the top-level subcircuit,
        or ``None`` if the netlist is empty.
    """
    if not subckts:
        return None

    instantiated: set[str] = set()
    for subckt in subckts.values():
        for inst_info in subckt.get("instances", {}).values():
            child_cell = inst_info.get("cell_name", "")
            if child_cell:
                instantiated.add(child_cell.casefold())

    top_candidates = [
        subckt["name"]
        for key, subckt in subckts.items()
        if key not in instantiated
    ]

    if top_candidates:
        return top_candidates[0]

    return next(iter(subckts.values()))["name"]


# SPICE primitive device terminal orders (standard SPICE convention)
_DEVICE_TERMINALS: dict[str, list[str]] = {
    "M": ["D", "G", "S", "B"],        # MOSFET: drain, gate, source, bulk
    "Q": ["C", "B", "E"],             # BJT: collector, base, emitter (+ optional substrate)
    "R": ["PLUS", "MINUS"],           # Resistor: plus, minus
    "C": ["PLUS", "MINUS"],           # Capacitor: plus, minus
    "D": ["PLUS", "MINUS"],           # Diode: anode, cathode
    "L": ["PLUS", "MINUS"],           # Inductor: plus, minus
}


def _join_continuation_lines(lines: list[str]) -> list[str]:
    """Join SPICE continuation lines (starting with +) into logical lines.

    Also preserves *device instance comments that contain position data.
    """
    joined: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Preserve device-instance comments for position extraction
        if stripped.startswith("*device instance") or stripped.startswith("* device instance"):
            joined.append(stripped)
            continue
        if stripped.startswith("*"):
            continue
        if stripped.startswith("+") and joined:
            # Find last non-comment line to append to
            for i in range(len(joined) - 1, -1, -1):
                if not joined[i].startswith("*"):
                    joined[i] += " " + stripped[1:].strip()
                    break
        else:
            joined.append(stripped)
    return joined


def _parse_device_line(line: str) -> dict[str, Any] | None:
    """Parse a single SPICE primitive device line into a device dict.

    Handles M (MOSFET), Q (BJT), R (Resistor), C (Capacitor), D (Diode),
    and X (subcircuit instance) lines.

    Returns a dict with keys: id, name, type, params, terminals.
    """
    tokens = line.split()
    if not tokens:
        return None

    prefix = tokens[0][0].upper()
    inst_name = tokens[0]

    if prefix == "X":
        # Subcircuit instance: X<name> <nets...> <cell_name> [params...]
        # Find the cell name: last token before key=value params
        call_tokens = tokens[1:]
        cell_index = next(
            (i for i in range(len(call_tokens) - 1, -1, -1)
             if "=" not in call_tokens[i]),
            None,
        )
        if cell_index is None:
            return None

        cell_name = call_tokens[cell_index]
        connections = call_tokens[:cell_index]
        params = {}
        for tok in call_tokens[cell_index + 1:]:
            if "=" in tok:
                k, _, v = tok.partition("=")
                params[k] = v

        # For X instances, we don't know the pin names without the subckt def,
        # so use generic numbered terminal names
        terminals = {f"net{i}": net for i, net in enumerate(connections)}

        return {
            "id": inst_name,
            "name": inst_name,
            "type": cell_name,
            "params": params,
            "terminals": terminals,
        }

    terminal_names = _DEVICE_TERMINALS.get(prefix)
    if terminal_names is None:
        return None

    # Standard device: <prefix><name> <nets...> <model_or_value> [params...]
    rest = tokens[1:]

    # Separate nets, model, and parameters.
    # Nets come first, then model name (no '='), then key=value params.
    # Number of nets is defined by terminal_names length.
    num_terminals = len(terminal_names)

    # For BJTs, there might be a 4th terminal (substrate)
    if prefix == "Q" and len(rest) > 4 and "=" not in rest[3]:
        terminal_names = ["C", "B", "E", "S"]
        num_terminals = 4

    if len(rest) < num_terminals + 1:
        # Not enough tokens for terminals + model
        return None

    net_tokens = rest[:num_terminals]
    model_name = rest[num_terminals]
    param_tokens = rest[num_terminals + 1:]

    terminals = dict(zip(terminal_names, net_tokens))
    params = {}
    for tok in param_tokens:
        if "=" in tok:
            k, _, v = tok.partition("=")
            params[k] = v

    return {
        "id": inst_name,
        "name": inst_name,
        "type": model_name,
        "params": params,
        "terminals": terminals,
    }


def parse_extracted_netlist(
    netlist_path: str | pathlib.Path | None,
    top_cell_name: str | None = None,
) -> dict[str, Any] | None:
    """Parse a KLayout extracted SPICE netlist into the format needed by generateSchematic.

    Reads the extracted .cir file and returns a dict suitable for direct use
    by klayoutSchematicGenerator.generateSchematic(). This uses the extracted
    netlist as the single source of truth for what the layout extraction found.

    Args:
        netlist_path: Path to the extracted .cir netlist file.
        top_cell_name: Name of the top cell to extract. If None, uses the
            top-level subcircuit (one not instantiated by others).

    Returns:
        A dict with keys::

            {
                "name": str,          # subcircuit/cell name
                "devices": list,      # list of device dicts
                "nets": list,         # list of net dicts
            }

        Each device dict has: id, name, type, params, terminals.
        Each net dict has: id, name, layout_net_id.
        Returns None if the file doesn't exist or can't be parsed.
    """
    if netlist_path is None:
        return None
    path = pathlib.Path(netlist_path)
    if not path.exists():
        return None

    # Read and join continuation lines
    with path.open("r", encoding="utf-8") as f:
        raw_lines = f.readlines()
    logical_lines = _join_continuation_lines(raw_lines)

    # Parse subcircuit structure
    subckts: dict[str, dict[str, Any]] = {}
    current_name: str | None = None
    current_devices: list[dict] = []
    current_pins: list[str] = []
    pending_positions: dict[str, dict] = {}

    for line in logical_lines:
        upper = line.upper()

        if upper.startswith(".SUBCKT"):
            tokens = line.split()
            if len(tokens) >= 2:
                current_name = tokens[1]
                # Pins might have params mixed in on .SUBCKT line
                current_pins = [t for t in tokens[2:] if "=" not in t]
                current_devices = []
            continue

        if upper.startswith(".ENDS"):
            if current_name is not None:
                subckts[current_name] = {
                    "name": current_name,
                    "pins": current_pins,
                    "devices": current_devices,
                }
            current_name = None
            current_devices = []
            current_pins = []
            continue

        # Skip non-device lines
        if upper.startswith("."):
            continue

        # Parse position from *device instance comments
        # Format: *device instance $<id> <orient> <mirror> <x>,<y> <type>
        if line.startswith("*device instance") or line.startswith("* device instance"):
            if current_name is not None:
                match = re.search(
                    r"\$(\S+)\s+\S+\s+\S+\s+([-\d.]+),([-\d.]+)", line
                )
                if match:
                    dev_idx = match.group(1)
                    x_pos = float(match.group(2))
                    y_pos = float(match.group(3))
                    pending_positions[dev_idx] = {"x": x_pos, "y": y_pos}
            continue

        # Parse device lines (only inside subcircuit blocks)
        if current_name is not None:
            device = _parse_device_line(line)
            if device is not None:
                # Try to attach position from preceding comment
                dev_name = device.get("name", "")
                dev_idx = dev_name.split("$")[-1] if "$" in dev_name else None
                if dev_idx and dev_idx in pending_positions:
                    device["position"] = pending_positions.pop(dev_idx)
                current_devices.append(device)

    if not subckts:
        return None

    # Determine target subcircuit
    if top_cell_name:
        # Try exact match first, then casefold
        target = subckts.get(top_cell_name) or subckts.get(top_cell_name.casefold())
        # Try case-insensitive lookup
        if target is None:
            for name, subckt in subckts.items():
                if name.casefold() == top_cell_name.casefold():
                    target = subckt
                    break
    else:
        # Find top-level subcircuit (not instantiated by others)
        instantiated: set[str] = set()
        for subckt in subckts.values():
            for dev in subckt.get("devices", []):
                if dev.get("name", "")[:1].upper() == "X":
                    instantiated.add(dev.get("type", "").casefold())
        top_candidates = [
            s for name, s in subckts.items()
            if name.casefold() not in instantiated
        ]
        target = top_candidates[0] if top_candidates else next(iter(subckts.values()))

    if target is None:
        return None

    devices = target.get("devices", [])

    # Collect all unique net names from device terminals and subckt pins
    net_names: set[str] = set()
    for dev in devices:
        for net_name in dev.get("terminals", {}).values():
            net_names.add(net_name)
    for pin in target.get("pins", []):
        net_names.add(pin)

    nets = [
        {"id": name, "name": name, "layout_net_id": name}
        for name in sorted(net_names)
    ]

    return {
        "name": target["name"],
        "pins": target.get("pins", []),
        "devices": devices,
        "nets": nets,
    }
