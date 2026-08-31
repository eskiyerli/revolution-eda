"""RCX database schema — the contract between LVS and RC extraction.

The .rcx.json file is the extraction database that LVS produces and the
RC extractor consumes. It contains:
- Verified net connectivity with schematic net names
- Net geometry (shapes on routing layers for R/C computation)
- Device list with model names, parameters, and terminal-to-net mapping
- Port definitions (external interface of the cell)

This module defines the schema as dataclasses and provides load/save utilities.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

RCX_SCHEMA_VERSION = "1.0"


@dataclass
class RcxShape:
    """A geometric shape belonging to a net on a specific layer."""

    layer: str  # Layer name (e.g. "Metal1") or GDS number as string
    layer_number: int  # GDS layer number for tech file lookup
    shape_type: str  # "rect", "path", "polygon"
    # For rect: [x1, y1, x2, y2]
    # For path: [x1, y1, x2, y2] + width
    # For polygon: [[x1,y1], [x2,y2], ...]
    coordinates: list[float] | list[list[float]]
    width: float = 0.0  # Only for path type


@dataclass
class RcxVia:
    """A via instance within a net."""

    via_type: str  # e.g. "via1", "Cont"
    x: float
    y: float
    width: float = 0.0
    height: float = 0.0
    nx: int = 1  # Array count X
    ny: int = 1  # Array count Y
    spacing_x: float = 0.0
    spacing_y: float = 0.0


@dataclass
class RcxNet:
    """A verified net with schematic name and layout geometry."""

    name: str  # Schematic net name (e.g. "Vout", "VDD")
    net_id: str  # Internal ID from LVS
    is_port: bool = False  # True if this net is an external port
    shapes: list[RcxShape] = field(default_factory=list)
    vias: list[RcxVia] = field(default_factory=list)


@dataclass
class RcxTerminal:
    """A device terminal connection."""

    name: str  # Terminal name (e.g. "D", "G", "S", "B")
    net: str  # Connected net name
    x: float | None = None
    y: float | None = None
    layer: str | None = None


@dataclass
class RcxDevice:
    """A circuit device (transistor, resistor, capacitor, etc.)."""

    name: str  # Instance name (e.g. "I0", "M1")
    model: str  # Model/subcircuit name (e.g. "sg13_lv_nmos")
    terminals: list[RcxTerminal] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)  # e.g. {"w": 8e-6, "l": 1.3e-7}


@dataclass
class RcxDatabase:
    """Complete extraction database — the .rcx.json content."""

    schema_version: str = RCX_SCHEMA_VERSION
    cell_name: str = ""
    lvs_equivalent: bool = False  # Whether LVS passed
    dbu: float = 1000.0  # Database units per micron
    nets: list[RcxNet] = field(default_factory=list)
    devices: list[RcxDevice] = field(default_factory=list)
    ports: list[str] = field(default_factory=list)  # Ordered port net names

    def get_net(self, name: str) -> RcxNet | None:
        """Look up a net by name."""
        for net in self.nets:
            if net.name == name:
                return net
        return None

    def get_device(self, name: str) -> RcxDevice | None:
        """Look up a device by instance name."""
        for dev in self.devices:
            if dev.name == name:
                return dev
        return None


def save_rcx_database(db: RcxDatabase, path: str | Path) -> None:
    """Save an RCX database to a JSON file.

    Args:
        db: The RcxDatabase to serialize.
        path: Output file path (.rcx.json).
    """
    path = Path(path)

    def serialize(obj):
        if hasattr(obj, '__dataclass_fields__'):
            return asdict(obj)
        return obj

    data = asdict(db)
    with path.open("w") as f:
        json.dump(data, f, indent=2, default=serialize)

    logger.info(f"Saved RCX database: {path} "
                f"({len(db.nets)} nets, {len(db.devices)} devices)")


def load_rcx_database(path: str | Path) -> RcxDatabase:
    """Load an RCX database from a JSON file.

    Args:
        path: Path to .rcx.json file.

    Returns:
        Populated RcxDatabase.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If the file format is invalid.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"RCX database not found: {path}\n"
            f"Run LVS with 'Export for PEX' enabled first, then re-run rcextract."
        )

    with path.open("r") as f:
        data = json.load(f)

    version = data.get("schema_version", "")
    if not version:
        raise ValueError(f"Invalid RCX file: missing schema_version in {path}")

    db = RcxDatabase(
        schema_version=version,
        cell_name=data.get("cell_name", ""),
        lvs_equivalent=data.get("lvs_equivalent", False),
        dbu=data.get("dbu", 1000.0),
        ports=data.get("ports", []),
    )

    # Load nets
    for net_data in data.get("nets", []):
        shapes = []
        for s in net_data.get("shapes", []):
            shapes.append(RcxShape(
                layer=s.get("layer", ""),
                layer_number=s.get("layer_number", 0),
                shape_type=s.get("shape_type", "rect"),
                coordinates=s.get("coordinates", []),
                width=s.get("width", 0.0),
            ))

        vias = []
        for v in net_data.get("vias", []):
            vias.append(RcxVia(
                via_type=v.get("via_type", ""),
                x=v.get("x", 0.0),
                y=v.get("y", 0.0),
                width=v.get("width", 0.0),
                height=v.get("height", 0.0),
                nx=v.get("nx", 1),
                ny=v.get("ny", 1),
                spacing_x=v.get("spacing_x", 0.0),
                spacing_y=v.get("spacing_y", 0.0),
            ))

        net = RcxNet(
            name=net_data.get("name", ""),
            net_id=net_data.get("net_id", ""),
            is_port=net_data.get("is_port", False),
            shapes=shapes,
            vias=vias,
        )
        db.nets.append(net)

    # Load devices
    for dev_data in data.get("devices", []):
        terminals = []
        for t in dev_data.get("terminals", []):
            terminals.append(RcxTerminal(
                name=t.get("name", ""),
                net=t.get("net", ""),
                x=t.get("x"),
                y=t.get("y"),
                layer=t.get("layer"),
            ))

        device = RcxDevice(
            name=dev_data.get("name", ""),
            model=dev_data.get("model", ""),
            terminals=terminals,
            params=dev_data.get("params", {}),
        )
        db.devices.append(device)

    logger.info(f"Loaded RCX database: {path} "
                f"({len(db.nets)} nets, {len(db.devices)} devices, "
                f"LVS={'PASS' if db.lvs_equivalent else 'FAIL'})")
    return db
