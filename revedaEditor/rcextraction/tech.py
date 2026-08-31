"""Technology file loader and layer stackup definitions.

A tech file defines the physical properties of each layer needed for
parasitic extraction: sheet resistance, thickness, height above substrate,
dielectric constants, and via resistance.

Supports process corners (nom, hrhc, lrhc, hrlc, lrlc) where R and C
values vary while physical geometry (thickness, height) stays the same.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

VALID_CORNERS = ("nom", "hrhc", "lrhc", "hrlc", "lrlc")


@dataclass
class LayerInfo:
    """Physical properties of a single routing layer."""

    name: str
    layer_number: int
    purpose: str  # "routing", "cut", "diffusion", "gate"
    sheet_resistance: float  # Ohms/square
    thickness: float  # um
    height: float  # um above substrate
    min_width: float  # um
    min_spacing: float  # um
    # Capacitance model parameters (to substrate)
    area_cap: float = 0.0  # fF/um^2
    fringe_cap: float = 0.0  # fF/um perimeter
    sidewall_cap: float = 0.0  # fF/um same-layer sidewall coupling


@dataclass
class ViaInfo:
    """Physical properties of a via type."""

    name: str
    resistance: float  # Ohms per via cut
    lower_layer: str
    upper_layer: str
    width: float  # um
    height: float  # um


@dataclass
class CouplingModel:
    """Interlayer coupling capacitance model."""

    layer1: str  # upper layer
    layer2: str  # lower layer
    area_cap: float = 0.0  # fF/um^2 overlap capacitance
    fringe_cap: float = 0.0  # fF/um fringe (legacy, single value)
    fringe_cap_upper: float = 0.0  # fF/um fringe from upper layer edge
    fringe_cap_lower: float = 0.0  # fF/um fringe from lower layer edge


@dataclass
class TechFile:
    """Complete technology definition for RC extraction."""

    name: str
    corner: str  # active process corner
    dbu: float  # database units per um (e.g. 1000 means 1 dbu = 1nm)
    layers: dict[str, LayerInfo] = field(default_factory=dict)
    vias: dict[str, ViaInfo] = field(default_factory=dict)
    coupling: list[CouplingModel] = field(default_factory=list)
    available_corners: list[str] = field(default_factory=list)
    # Layer number to name lookup
    _layer_map: dict[int, str] = field(default_factory=dict, repr=False)

    def layer_by_number(self, num: int) -> LayerInfo | None:
        """Look up layer info by its GDS/RevEDA layer number."""
        name = self._layer_map.get(num)
        if name is None:
            return None
        return self.layers.get(name)

    def layer_by_name(self, name: str) -> LayerInfo | None:
        """Look up layer info by name (case-insensitive)."""
        if not name:
            return None
        if name in self.layers:
            return self.layers[name]
        name_lower = name.lower()
        for k, v in self.layers.items():
            if k.lower() == name_lower:
                return v
        return None

    def via_by_name(self, name: str) -> ViaInfo | None:
        """Look up via info by name (case-insensitive)."""
        if not name:
            return None
        if name in self.vias:
            return self.vias[name]
        name_lower = name.lower()
        for k, v in self.vias.items():
            if k.lower() == name_lower:
                return v
        return None

    def via_between(self, lower: str, upper: str) -> ViaInfo | None:
        """Find via definition connecting two layers."""
        for via in self.vias.values():
            if via.lower_layer == lower and via.upper_layer == upper:
                return via
            if via.lower_layer == upper and via.upper_layer == lower:
                return via
        return None


def load_tech_file(path: str | Path, corner: str = "nom") -> TechFile:
    """Load a technology definition from a JSON file.

    Args:
        path: Path to the tech JSON file.
        corner: Process corner to use. One of: nom, hrhc, lrhc, hrlc, lrlc.

    Returns:
        Populated TechFile instance with corner-specific R/C values.
    """
    path = Path(path)
    with path.open("r") as f:
        data: dict[str, Any] = json.load(f)

    if corner not in VALID_CORNERS:
        raise ValueError(f"Invalid corner '{corner}'. Valid: {VALID_CORNERS}")

    # Check if this is a corner-based or flat tech file
    has_corners = "corners" in data
    if has_corners and corner not in data["corners"]:
        available = list(data["corners"].keys())
        raise ValueError(f"Corner '{corner}' not in tech file. Available: {available}")

    tech = TechFile(
        name=data["name"],
        corner=corner,
        dbu=data.get("dbu", 1000.0),
        available_corners=list(data["corners"].keys()) if has_corners else ["nom"],
    )

    if has_corners:
        corner_data = data["corners"][corner]
        _load_with_corners(tech, data, corner_data)
    else:
        _load_flat(tech, data)

    return tech


def _load_with_corners(tech: TechFile, data: dict, corner_data: dict) -> None:
    """Load tech file using corner-specific R/C overlaid on base geometry."""
    r_values = corner_data.get("resistance", {})
    via_r_values = corner_data.get("via_resistance", {})
    cap_values = corner_data.get("capacitance", {})
    coupling_values = corner_data.get("coupling", {})

    # Load layers (geometry from base, R/C from corner)
    for layer_data in data.get("layers", []):
        name = layer_data["name"]
        cap_data = cap_values.get(name, {})

        layer = LayerInfo(
            name=name,
            layer_number=layer_data["layer_number"],
            purpose=layer_data.get("purpose", "routing"),
            sheet_resistance=r_values.get(name, 0.0),
            thickness=layer_data["thickness"],
            height=layer_data["height"],
            min_width=layer_data.get("min_width", 0.0),
            min_spacing=layer_data.get("min_spacing", 0.0),
            area_cap=cap_data.get("area_cap", 0.0),
            fringe_cap=cap_data.get("fringe_cap", 0.0),
            sidewall_cap=cap_data.get("sidewall_cap", 0.0),
        )
        tech.layers[layer.name] = layer
        tech._layer_map[layer.layer_number] = layer.name

    # Load vias (geometry from base, resistance from corner)
    for via_data in data.get("vias", []):
        name = via_data["name"]
        via = ViaInfo(
            name=name,
            resistance=via_r_values.get(name, 0.0),
            lower_layer=via_data["lower_layer"],
            upper_layer=via_data["upper_layer"],
            width=via_data.get("width", 0.0),
            height=via_data.get("height", 0.0),
        )
        tech.vias[via.name] = via

    # Load coupling models from corner
    for key, coup_data in coupling_values.items():
        # Key format: "Metal2_Metal1" (upper_lower)
        parts = key.split("_", 1)
        if len(parts) == 2:
            layer1, layer2 = parts[0], parts[1]
        else:
            continue

        coupling = CouplingModel(
            layer1=layer1,
            layer2=layer2,
            area_cap=coup_data.get("area_cap", 0.0),
            fringe_cap=coup_data.get("fringe_cap", 0.0),
            fringe_cap_upper=coup_data.get("fringe_cap_upper", 0.0),
            fringe_cap_lower=coup_data.get("fringe_cap_lower", 0.0),
        )
        tech.coupling.append(coupling)


def _load_flat(tech: TechFile, data: dict) -> None:
    """Load legacy flat tech file (no corners, all values inline)."""
    for layer_data in data.get("layers", []):
        layer = LayerInfo(
            name=layer_data["name"],
            layer_number=layer_data["layer_number"],
            purpose=layer_data.get("purpose", "routing"),
            sheet_resistance=layer_data.get("sheet_resistance", 0.0),
            thickness=layer_data["thickness"],
            height=layer_data["height"],
            min_width=layer_data.get("min_width", 0.0),
            min_spacing=layer_data.get("min_spacing", 0.0),
            area_cap=layer_data.get("area_cap", 0.0),
            fringe_cap=layer_data.get("fringe_cap", 0.0),
            sidewall_cap=layer_data.get("sidewall_cap", 0.0),
        )
        tech.layers[layer.name] = layer
        tech._layer_map[layer.layer_number] = layer.name

    for via_data in data.get("vias", []):
        via = ViaInfo(
            name=via_data["name"],
            resistance=via_data.get("resistance", 0.0),
            lower_layer=via_data["lower_layer"],
            upper_layer=via_data["upper_layer"],
            width=via_data.get("width", 0.0),
            height=via_data.get("height", 0.0),
        )
        tech.vias[via.name] = via

    for coup_data in data.get("coupling", []):
        coupling = CouplingModel(
            layer1=coup_data["layer1"],
            layer2=coup_data["layer2"],
            area_cap=coup_data.get("area_cap", 0.0),
            fringe_cap=coup_data.get("fringe_cap", 0.0),
            fringe_cap_upper=coup_data.get("fringe_cap_upper", 0.0),
            fringe_cap_lower=coup_data.get("fringe_cap_lower", 0.0),
        )
        tech.coupling.append(coupling)
