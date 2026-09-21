#
# Revolution EDA
#
# Copyright (c) 2026 Revolution Semiconductor
#
# This Source Code Form is subject to the terms of the
# Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
"""Schematic<->layout correspondence engine (XL-lite).

One correspondence model shared by GUI scenes, aiTerminal ops, and batch
tooling — Qt-free so it can run on decoded JSON records headlessly.

The persisted contract is the ``sdl`` field on ``Inst``/``Pcell`` layout
records, mirrored on the live item as ``layoutInstance._sdlSource``::

    {"lib": <schematic lib>, "cell": <schematic cell>,
     "view": <schematic view>, "inst": <schematic instance name>,
     "labels": {<labelName>: [<value>, <visible>]}}

``lib``/``cell``/``view`` identify the *source schematic cellview* (the cell
pair), ``inst`` the instance inside it. An instance whose ``sdl`` points at a
different source is foreign to a sync run and is never touched.

Legacy in-memory dicts written before the field was persisted used
``schematicLib``/``schematicCell``/``schematicInstance`` keys (the instance's
*referenced* cell, not the source); :func:`sdlInstName` normalizes both
shapes. Such dicts carry no source identity, so they only match by name.
"""

from __future__ import annotations

import inspect
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

import revedaEditor.connectivity as conn

# ---------------------------------------------------------------------------
# sdlSource helpers
# ---------------------------------------------------------------------------


def makeSdlSource(lib: str, cell: str, view: str, inst: str,
                  labels: dict) -> dict:
    """Canonical ``_sdlSource``/``sdl`` record shape."""
    return {
        "lib": lib,
        "cell": cell,
        "view": view,
        "inst": inst,
        "labels": dict(labels or {}),
    }


def sdlInstName(sdl: dict | None) -> str:
    """Schematic instance name, tolerant of the legacy key shape."""
    if not isinstance(sdl, dict):
        return ""
    return sdl.get("inst") or sdl.get("schematicInstance") or ""


def sdlSourceKey(sdl: dict | None) -> tuple | None:
    """(lib, cell, view) of the source schematic, or None when absent.

    Legacy dicts stored the referenced sub-cell under
    ``schematicLib``/``schematicCell`` — that is *not* a source identity, so
    they return None and can only match instances by name.
    """
    if not isinstance(sdl, dict):
        return None
    lib = sdl.get("lib")
    cell = sdl.get("cell")
    if lib is None or cell is None:
        return None
    return (lib, cell, sdl.get("view") or "")


def sdlLabels(sdl: dict | None) -> dict:
    if not isinstance(sdl, dict):
        return {}
    labels = sdl.get("labels")
    return labels if isinstance(labels, dict) else {}


def _labelValue(value) -> Any:
    """``ld`` entries are [value, visible]; live values may be plain."""
    if isinstance(value, (list, tuple)) and value:
        return value[0]
    return value


# ---------------------------------------------------------------------------
# Schematic record extraction
# ---------------------------------------------------------------------------


def schematicInstances(records: Iterable[dict]) -> dict:
    """{instName: sys-record} from a decoded schematic design array.

    Header entries and malformed records are skipped; the last record wins
    on duplicate names (renumbering is the scene's concern).
    """
    insts: dict = {}
    for rec in records:
        if isinstance(rec, dict) and rec.get("type") == "sys":
            name = rec.get("nam", "")
            if name:
                insts[name] = rec
    return insts


# ---------------------------------------------------------------------------
# Incremental sync
# ---------------------------------------------------------------------------


@dataclass
class SyncPlan:
    """Result of :func:`correspondenceDiff`.

    ``to_add`` holds schematic ``sys`` records needing a new layout
    instance. ``to_remove``/``to_update``/``adopted`` hold the caller's
    opaque descriptor dicts (``item`` references included verbatim).
    """

    to_add: list = field(default_factory=list)
    to_remove: list = field(default_factory=list)
    to_update: list = field(default_factory=list)   # (descriptor, record)
    adopted: list = field(default_factory=list)     # (descriptor, record)


def _labelsChanged(sdlLabelsDict: dict, recordLabels: dict) -> bool:
    """True when the stored sdl labels differ from the record's ``ld``."""
    if not sdlLabelsDict and not recordLabels:
        return False
    keys = set(sdlLabelsDict) | set(recordLabels)
    return any(
        _labelValue(sdlLabelsDict.get(k)) != _labelValue(recordLabels.get(k))
        for k in keys
    )


def correspondenceDiff(
    schInsts: dict,
    layoutDescriptors: Iterable[dict],
    sourceKey: tuple,
) -> SyncPlan:
    """Diff schematic instances against layout instance descriptors.

    Args:
        schInsts: ``{name: sys-record}`` from :func:`schematicInstances`.
        layoutDescriptors: one dict per candidate layout instance:
            ``{"item", "name", "cell", "sdl"}`` where ``item`` is opaque
            (returned verbatim), ``name``/``cell`` mirror the instance's
            instanceName/cellName, ``sdl`` is its ``_sdlSource`` or None.
        sourceKey: ``(lib, cell, view)`` of the source schematic — only
            instances whose sdl names this source are managed.

    Match rules (Virtuoso-style name correspondence):
        * sdl pointing at ``sourceKey``: inst in schematic -> keep (and
          ``to_update`` when labels drifted); inst gone -> ``to_remove``.
        * no sdl / foreign sdl: adopted when ``name``+``cell`` match a
          schematic instance (caller stamps the sdl field).
        * everything else is user geometry — never touched.
    """
    plan = SyncPlan()
    matched: set[str] = set()

    for desc in layoutDescriptors:
        sdl = desc.get("sdl")
        sdlKey = sdlSourceKey(sdl)
        sdlInst = sdlInstName(sdl)
        if sdlKey == sourceKey and sdlInst:
            record = schInsts.get(sdlInst)
            if record is None:
                plan.to_remove.append(desc)
            else:
                matched.add(sdlInst)
                if _labelsChanged(sdlLabels(sdl), record.get("ld", {})):
                    plan.to_update.append((desc, record))
        elif not sdlKey:
            # Unsourced (or legacy-sourced) instance: adopt on name+cell.
            record = schInsts.get(desc.get("name") or "")
            if record is not None and desc.get("cell") == record.get("cell"):
                plan.adopted.append((desc, record))
                matched.add(record.get("nam", ""))
        # Foreign-source instances and non-matching user geometry: skip.

    plan.to_add = [
        rec for name, rec in sorted(schInsts.items()) if name not in matched
    ]
    return plan


# ---------------------------------------------------------------------------
# Schematic label -> pcell parameter mapping
# ---------------------------------------------------------------------------


def pcellParamsFor(callParameters, parameterMap: dict, labels: dict):
    """Map schematic labels to pcell call parameters.

    Args:
        callParameters: ``inspect.signature(inst.__call__).parameters``.
        parameterMap: ``{pcellParamName: schematicLabelName}`` from the PDK's
            ``pcellParameterMap.json`` entry for the cell.
        labels: schematic ``ld`` dict (``name -> [value, visible]``; plain
            ``name -> value`` also accepted).

    Returns:
        ``(params, missing)`` — kwargs for ``inst(**params)`` plus the names
        of required parameters no label supplied.
    """
    params: dict = {}
    missing: list = []
    for name, parameter in callParameters.items():
        if parameter.kind not in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY):
            continue
        labelName = parameterMap.get(name)
        if labelName is not None and labelName in labels:
            params[name] = _labelValue(labels[labelName])
        elif parameter.default is inspect.Parameter.empty:
            missing.append(name)
    return params, missing


# ---------------------------------------------------------------------------
# Flyline endpoints (schematic pin -> net for layout rat's nest)
# ---------------------------------------------------------------------------


def flylineEndpoints(records: list, pinLocator) -> tuple[dict, list]:
    """Resolve ``{netName: [(instName, pinName), ...]}`` from schematic records.

    Uses the shared connectivity engine on records — the same resolution the
    scene performs — so net identity is identical between the two. Only
    ports that actually joined a group (or carry a net expression) become
    endpoints; dangling pins produce no flyline.

    Endpoint shape: ``(instName, pinName)`` for symbol pins; ``("", pinName)``
    for sheet-level schematic pins, which the layout side resolves against
    its top-level ``layoutPin`` items.

    Args:
        records: decoded schematic design array.
        pinLocator: ``(lib, cell, view) -> {pinName: (x, y), ...}`` callable,
            e.g. ``loadJSON.makeSymbolPinLocator(libraryDict)``.

    Returns:
        ``(endpoints, diagnostics)`` — endpoints keyed by resolved net name
        (auto ``net<N>``/``dnet`` names included; a nameless group falls
        back to ``_grp<i>``), diagnostics from the adapter.
    """
    segs, ports, diagnostics = conn.fromRecords(records, pinLocator=pinLocator)
    result = conn.resolve(segs, ports)
    endpoints: dict[str, list] = {}
    for port in ports:
        if port.kind == "symbolPin":
            if not port.owner:
                continue
            endpoint = (port.owner, port.name)
        elif port.kind == "schemPin":
            endpoint = ("", port.name)
        else:
            continue
        groupIndex = result.portGroup.get(port.id)
        if groupIndex is not None:
            name = result.groups[groupIndex].name or f"_grp{groupIndex}"
        else:
            name = result.portExprNet.get(port.id)
            if not name:
                continue
        endpoints.setdefault(name, []).append(endpoint)
    return endpoints, diagnostics
