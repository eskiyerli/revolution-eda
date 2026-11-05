# SPDX-License-Identifier: MPL-2.0
#
# Revolution EDA
# Copyright (c) 2026 Revolution Semiconductor

"""Qt-free adapter: decoded schematic records → VACASK instance IR.

Bridges the connectivity engine's record path
(:func:`revedaEditor.connectivity.adapters.fromRecords` +
:func:`revedaEditor.connectivity.resolve.resolve`) into
:class:`revedaEditor.netlisting.vacaskFormat.InstanceIR` so a headless
caller can netlist a persisted ``schematic.json`` without instantiating
editors, scenes, or symbols.

The same code backs the parity test against the interactive
:class:`vacaskNetlist` — both directions must produce identical
instance lines.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass, field
from typing import Callable

import orjson

import revedaEditor.common.params as prm
from revedaEditor.connectivity.adapters import fromRecords
from revedaEditor.connectivity.resolve import resolve
from revedaEditor.netlisting import vacaskFormat


# ---------------------------------------------------------------------------
# Symbol manifest
# ---------------------------------------------------------------------------

@dataclass
class SymbolManifest:
    """Netlist-relevant content of one ``symbol.json`` file."""
    pins: dict = field(default_factory=dict)        # name -> (x, y), file order
    directions: dict = field(default_factory=dict)  # pinName -> direction
    paramDefs: list = field(default_factory=list)   # prm.ParamDef
    pinExprs: dict = field(default_factory=dict)    # pinName -> "[@x:net]"
    attrs: dict = field(default_factory=dict)       # attr nam -> def
    labelDefs: dict = field(default_factory=dict)   # @name -> "[@name:...]"

    def pin_map_for_locator(self) -> dict:
        """The dict shape ``connectivity.fromRecords`` expects from a pinLocator."""
        pin_map = dict(self.pins)
        pin_map["directions"] = self.directions
        pin_map["paramDefs"] = self.paramDefs
        pin_map["pinExprs"] = self.pinExprs
        return pin_map


def load_symbol_manifest(symbol_json: pathlib.Path
                         ) -> SymbolManifest | None:
    """Read one ``symbol.json`` into a :class:`SymbolManifest` (None on miss)."""
    path = pathlib.Path(symbol_json)
    if not path.is_file():
        return None
    try:
        records = orjson.loads(path.read_bytes())
    except (OSError, ValueError):
        return None
    manifest = SymbolManifest()
    for record in records[2:] if len(records) > 2 else []:
        if not isinstance(record, dict):
            continue
        kind = record.get("type")
        if kind == "pin":
            name = record.get("nam", "")
            loc = record.get("loc", (0, 0))
            st = record.get("st", (0, 0))
            manifest.pins[name] = (loc[0] + st[0], loc[1] + st[1])
            manifest.directions[name] = record.get("pd", "")
            if record.get("nx"):
                manifest.pinExprs[name] = record["nx"]
        elif kind == "attr":
            manifest.attrs[record.get("nam", "")] = record.get("def", "")
        elif kind == "label" and record.get("lt") == "NLPLabel":
            manifest.labelDefs[record.get("nam", "")] = record.get("def", "")
    manifest.paramDefs = prm.paramDefsFromSymattrs(manifest.attrs)
    return manifest


def make_manifest_loader(
        library_dict: dict[str, pathlib.Path]
) -> Callable[[str, str, str], SymbolManifest | None]:
    """``(lib, cell, view) -> SymbolManifest`` backed by a ``{lib: dir}`` map."""
    cache: dict = {}

    def loader(lib_name: str, cell_name: str, view_name: str
               ) -> SymbolManifest | None:
        key = (lib_name, cell_name, view_name)
        if key not in cache:
            lib_dir = library_dict.get(lib_name)
            cache[key] = (load_symbol_manifest(
                lib_dir / cell_name / f"{view_name}.json")
                if lib_dir is not None else None)
        return cache[key]

    return loader


def make_pin_locator(library_dict: dict[str, pathlib.Path]):
    """Qt-free twin of ``loadJSON.makeSymbolPinLocator``.

    Returns the ``pinLocator`` callable consumed by
    ``connectivity.fromRecords`` / ``analyzeRecords``.
    """
    loader = make_manifest_loader(library_dict)

    def locator(lib_name: str, cell_name: str, view_name: str):
        manifest = loader(lib_name, cell_name, view_name)
        return manifest.pin_map_for_locator() if manifest else None

    locator.manifest_for = loader
    return locator


# ---------------------------------------------------------------------------
# Records -> InstanceIR
# ---------------------------------------------------------------------------

# Predefined NLP labels resolved from the instance/symbol itself.
_PREDEFINED_LABELS = ("@instName", "@cellName", "@libName", "@viewName",
                     "@modelName", "@elementNum")


def _instance_records(records) -> list[dict]:
    """Every ``sys`` record, expanding ``Group`` containers like fromRecords."""
    out: list[dict] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        kind = record.get("type")
        if kind == "sys":
            out.append(record)
        elif kind == "Group":
            out.extend(child for child in record.get("items", [])
                       if isinstance(child, dict)
                       and child.get("type") == "sys")
    return out


def _stored_label_values(record: dict) -> dict[str, str]:
    """``{bareName: value}`` from the record's ``ld`` label dict."""
    out: dict[str, str] = {}
    for name, entry in (record.get("ld") or {}).items():
        if isinstance(entry, (list, tuple)) and entry:
            out[str(name)] = str(entry[0] if entry[0] is not None else "")
        elif entry is not None and not isinstance(entry, dict):
            out[str(name)] = str(entry)
    return out


def records_to_ir(records, manifest_for=None, pin_locator=None,
                  ) -> tuple[list[vacaskFormat.InstanceIR], list[str],
                             list[str]]:
    """Adapt a decoded schematic design array into :class:`InstanceIR`s.

    ``manifest_for`` is ``(lib, cell, view) -> SymbolManifest``; when only a
    ``pin_locator`` is given its ``manifest_for`` attribute (installed by
    :func:`make_pin_locator`) supplies manifests.

    Returns ``(instances, warnings, diagnostics)`` — *diagnostics* come
    straight out of the connectivity engine (malformed records, missing
    symbols), *warnings* cover netlist-level anomalies (unresolved pins,
    missing manifests).
    """
    if manifest_for is None:
        manifest_for = getattr(pin_locator, "manifest_for", None)
    if manifest_for is None:
        raise ValueError("records_to_ir needs manifest_for or a pin_locator "
                         "created by make_pin_locator")

    segs, ports, diagnostics = fromRecords(records, pinLocator=pin_locator)
    result = resolve(segs, ports)

    def port_net(port) -> str:
        group_id = result.portGroup.get(port.id)
        if group_id is None:
            return ""
        return result.groups[group_id].name

    ports_by_owner: dict[str, list] = {}
    for port in ports:
        if port.kind == "symbolPin":
            ports_by_owner.setdefault(port.owner, []).append(port)

    warnings: list[str] = []
    instances: list[vacaskFormat.InstanceIR] = []
    for record in _instance_records(records):
        inst_name = str(record.get("nam", "") or "")
        manifest = manifest_for(record.get("lib", ""),
                                record.get("cell", ""),
                                record.get("view", "symbol"))
        if manifest is None:
            warnings.append(f"{inst_name}: no manifest for "
                            f"{record.get('lib')}/{record.get('cell')}/"
                            f"{record.get('view', 'symbol')}")
            continue
        if str(manifest.attrs.get("NetlistIgnore", "")) == "1" or \
                record.get("ign"):
            continue

        owned = {p.name: p for p in ports_by_owner.get(inst_name, [])}
        pin_nets: list[tuple[str, str]] = []
        for pin_name in manifest.pins:
            port = owned.get(pin_name)
            if port is None:
                warnings.append(
                    f"{inst_name}: pin {pin_name!r} has no connectivity "
                    "port")
                continue
            net = port_net(port)
            if not net:
                warnings.append(
                    f"{inst_name}.{pin_name}: floating pin — empty net")
            pin_nets.append((pin_name, net))

        stored = _stored_label_values(record)
        typed = prm.applyDefaults(manifest.paramDefs, stored)
        labels = vacaskFormat.resolve_label_values(
            manifest.labelDefs,
            instance_values=stored,
            typed_defaults=typed)
        labels.setdefault("@instName", inst_name)
        labels.setdefault("@cellName", str(record.get("cell", "")))
        labels.setdefault("@libName", str(record.get("lib", "")))
        labels.setdefault("@viewName", str(record.get("view", "symbol")))
        if manifest.attrs.get("modelName"):
            labels.setdefault("@modelName", manifest.attrs["modelName"])

        instances.append(vacaskFormat.InstanceIR(
            name=inst_name,
            attrs=dict(manifest.attrs),
            labels=labels,
            pinNets=pin_nets,
        ))
    return instances, warnings, diagnostics
