#
# Revolution EDA
#
# Copyright (c) 2026 Revolution Semiconductor
#
# This Source Code Form is subject to the terms of the
# Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
##

"""Inherited-connection (netSet / net expression) support for netlisters.

Each distinct net-expression name used inside a cell becomes an implicit
subcircuit terminal — appended after the cell's explicit pins. Inside the
subcircuit definition the expression resolves to the terminal name
(identity binding); at instantiation the instance supplies its netSet
override, the expression default, or the bare name.

The helpers here are shared by xyceNetlist, spectreNetlist and
vacaskNetlist so all backends emit identical semantics.
"""

from __future__ import annotations

import pathlib

import orjson

import revedaEditor.backend.libraryMethods as libm
from revedaEditor.connectivity import netexpr
from revedaEditor.fileio import loadJSON


def exprDefsForSchematicView(cellItem, netlistView: str,
                             libraryDict: dict) -> dict[str, str]:
    """{exprName: default} for a cell's schematic view, from its JSON file.

    Reads the design array directly (no scene/editor needed) so instance
    lines can be emitted before the child editor is loaded.
    """
    viewItem = libm.getViewItem(cellItem, netlistView)
    viewPath = getattr(viewItem, "viewPath", None)
    if viewPath is None or not pathlib.Path(viewPath).exists():
        return {}
    try:
        records = orjson.loads(pathlib.Path(viewPath).read_bytes())
    except (orjson.JSONDecodeError, OSError):
        return {}
    pinLocator = loadJSON.makeSymbolPinLocator(libraryDict)
    defs, _problems = netexpr.exprNamesFromRecords(records, pinLocator)
    return defs


def exprNetsForInstance(elementSymbol, exprDefs: dict[str, str]
                        ) -> list[str]:
    """Ordered parent-level nets for an instance's implicit terminals.

    Terminal order is the sorted expression-name order, matching
    ``exprTerminals`` on the subckt header.
    """
    binds = netexpr.instanceExprNets(
        getattr(elementSymbol, "netSet", {}), exprDefs)
    return [binds[name] for name in sorted(exprDefs)]


def exprTerminals(exprDefs: dict[str, str]) -> list[str]:
    """Implicit terminal names for a subckt header (sorted)."""
    return sorted(exprDefs)


def terminalNetSet(exprDefs: dict[str, str]) -> dict[str, str]:
    """Identity bindings for collecting a subcircuit's internals."""
    return netexpr.terminalBinds(exprDefs)


def globalNets(exprDefs: dict[str, str], netSet) -> set[str]:
    """Resolved ``!`` nets contributed by an instance's expr bindings."""
    binds = netexpr.instanceExprNets(netSet, exprDefs)
    return {net for net in binds.values() if net.endswith("!")}
