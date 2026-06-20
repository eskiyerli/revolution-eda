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
