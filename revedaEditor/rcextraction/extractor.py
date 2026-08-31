"""Unified RC extractor that consumes an RCX database.

This is the main extraction engine. It reads a pre-solved .rcx.json
(produced by the LVS export step) and computes parasitic R and C for
each net. It then outputs a complete netlist with both the original
devices and parasitic elements.

The extractor builds a connected spatial graph of resistors and capacitors
for each net, linking wire segments, vias, ports, and transistor terminals.
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Optional

from .rcx_schema import RcxDatabase, RcxDevice, RcxNet, RcxShape, RcxVia
from .tech import LayerInfo, TechFile, ViaInfo

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result data structures
# ---------------------------------------------------------------------------


@dataclass
class ParasiticResistor:
    """An extracted parasitic resistor within a net."""

    net: str
    node1: str
    node2: str
    value: float  # Ohms
    layer: str


@dataclass
class ParasiticCapacitor:
    """An extracted parasitic capacitor."""

    node1: str
    node2: str  # "0" for substrate
    value: float  # fF
    cap_type: str  # "substrate", "coupling"
    net1: str = ""
    net2: str = ""  # empty or "GND" for substrate


@dataclass
class DeviceInstance:
    """A device to include in the output netlist."""

    name: str
    model: str
    terminals: dict[str, str]  # terminal_name -> node_name
    params: dict[str, Any]


@dataclass
class ExtractionResult:
    """Complete extraction output: devices + parasitics."""

    cell_name: str
    ports: list[str]
    devices: list[DeviceInstance] = field(default_factory=list)
    resistors: list[ParasiticResistor] = field(default_factory=list)
    capacitors: list[ParasiticCapacitor] = field(default_factory=list)

    @property
    def total_r(self) -> int:
        return len(self.resistors)

    @property
    def total_c(self) -> int:
        return len(self.capacitors)


# ---------------------------------------------------------------------------
# NetGraph: spatial electrical node manager per net
# ---------------------------------------------------------------------------


class NetGraph:
    """Manages electrical nodes in physical space (x, y, layer) for a single net."""

    def __init__(self, net_name: str, dbu: float, tol: float = 25.0):
        self.net_name = net_name
        self.dbu = dbu
        self.tol = tol  # tolerance in dbu (e.g. 25 dbu = 25nm)
        # List of (x, y, layer, node_name)
        self._nodes: list[tuple[float, float, str, str]] = []
        self._node_counter = 0

    def has_nodes(self) -> bool:
        return len(self._nodes) > 0

    def get_or_create_node(
        self, x: float, y: float, layer: str, preferred_name: Optional[str] = None
    ) -> str:
        """Find an existing node within tolerance on the same layer, or create a new one."""
        layer_norm = layer.lower()
        tol_sq = self.tol ** 2
        for nx, ny, nlayer, nname in self._nodes:
            if nlayer.lower() == layer_norm:
                if (nx - x) ** 2 + (ny - y) ** 2 <= tol_sq:
                    return nname

        self._node_counter += 1
        if preferred_name:
            node_name = preferred_name
        else:
            node_name = f"{self.net_name}_{layer}_{self._node_counter}"

        self._nodes.append((x, y, layer, node_name))
        return node_name

    def find_nearest_node(
        self, x: Optional[float], y: Optional[float], layer: Optional[str] = None
    ) -> str:
        """Find the closest existing node on the specified layer (or any layer)."""
        if not self._nodes:
            return self.net_name

        if x is None or y is None:
            return self._nodes[0][3]

        best_name = None
        best_dist = float("inf")
        layer_norm = layer.lower() if layer else None

        if layer_norm is not None:
            for nx, ny, nlayer, nname in self._nodes:
                if nlayer.lower() == layer_norm:
                    dist = (nx - x) ** 2 + (ny - y) ** 2
                    if dist < best_dist:
                        best_dist = dist
                        best_name = nname

        if best_name is None:
            for nx, ny, nlayer, nname in self._nodes:
                dist = (nx - x) ** 2 + (ny - y) ** 2
                if dist < best_dist:
                    best_dist = dist
                    best_name = nname

        return best_name if best_name is not None else self.net_name

    def get_port_node(self) -> Optional[str]:
        """Return the best node to represent the external port.

        Prefers the node on the highest-numbered routing layer, which is
        typically the top metal where external connections land."""
        if not self._nodes:
            return None
        return self._nodes[-1][3]

    def get_port_node_by_layer(
        self, layer_numbers: dict[str, int]
    ) -> Optional[str]:
        """Return the node on the highest layer number, falling back to the
        last node if layer numbers are unavailable.

        Args:
            layer_numbers: mapping of layer name -> layer number.
        """
        if not self._nodes:
            return None
        best_name = None
        best_ln = -1
        for _x, _y, nlayer, nname in self._nodes:
            ln = layer_numbers.get(nlayer, -1)
            if ln > best_ln:
                best_ln = ln
                best_name = nname
        return best_name if best_name is not None else self._nodes[-1][3]

    def alias_node(self, old_name: str, new_name: str) -> None:
        """Replace all occurrences of old_name with new_name in stored nodes."""
        for i, (nx, ny, nlayer, nname) in enumerate(self._nodes):
            if nname == old_name:
                self._nodes[i] = (nx, ny, nlayer, new_name)


# ---------------------------------------------------------------------------
# Main extraction function
# ---------------------------------------------------------------------------


def extract(rcx_db: RcxDatabase, tech: TechFile, coupling: bool = True) -> ExtractionResult:
    """Run parasitic RC extraction on an RCX database.

    Args:
        rcx_db: Pre-solved RCX database from LVS.
        tech: Technology file with R/C models.
        coupling: Whether to extract inter-net coupling capacitance.

    Returns:
        ExtractionResult containing devices and parasitic elements.
    """
    result = ExtractionResult(
        cell_name=rcx_db.cell_name,
        ports=list(rcx_db.ports),
    )

    dbu = rcx_db.dbu
    net_graphs: dict[str, NetGraph] = {}
    node_sub_caps: dict[str, float] = defaultdict(float)  # node -> fF

    # --- Step 1: Extract R and substrate C per net ---
    for net in rcx_db.nets:
        net_graph = NetGraph(net.name, dbu=dbu, tol=25.0)
        net_graphs[net.name] = net_graph
        _extract_net_parasitics(net, tech, dbu, net_graph, result, node_sub_caps)

    # --- Step 1b: Merge same-layer nodes on layers with no routing shapes ---
    # PCell-internal metal (e.g. Metal1 source/drain contacts) is not in the
    # RCX database as routing shapes, but via cuts landing on it create
    # separate nodes that are electrically shorted inside the device.
    for net in rcx_db.nets:
        net_graph = net_graphs.get(net.name)
        if not net_graph or not net_graph.has_nodes():
            continue
        _merge_pcell_internal_nodes(net, net_graph, result, node_sub_caps)

    # --- Step 2: Extract coupling C between nets ---
    if coupling:
        net_list = rcx_db.nets
        for i in range(len(net_list)):
            for j in range(i + 1, len(net_list)):
                _extract_coupling(
                    net_list[i], net_list[j], tech, dbu, net_graphs, result
                )

    # --- Step 3: Connect Ports ---
    # Ensure external ports map to actual nodes in the network.
    # Build a layer-name -> layer-number map so port selection can prefer
    # the highest metal (where external pins land) rather than the
    # last-created node.
    layer_numbers: dict[str, int] = {}
    for lname, linfo in tech.layers.items():
        layer_numbers[lname] = linfo.layer_number

    for port_name in result.ports:
        net_graph = net_graphs.get(port_name)
        if net_graph and net_graph.has_nodes():
            port_node = net_graph.get_port_node_by_layer(layer_numbers)
            if port_node and port_node != port_name:
                # Rename the internal port node to the port name throughout result
                _rename_node_in_result(result, node_sub_caps, port_node, port_name)
                net_graph.alias_node(port_node, port_name)

    # --- Step 4: Emit consolidated substrate capacitors ---
    # Build a reverse lookup from node name -> net name so we don't rely
    # on fragile string parsing of node names that may contain underscores.
    node_to_net: dict[str, str] = {}
    for net_name, ng in net_graphs.items():
        for _x, _y, _layer, nname in ng._nodes:
            node_to_net[nname] = net_name

    for node_name, cap_val in node_sub_caps.items():
        if cap_val > 1e-6:
            net_name = node_to_net.get(node_name, "")
            result.capacitors.append(
                ParasiticCapacitor(
                    node1=node_name,
                    node2="0",
                    value=cap_val,
                    cap_type="substrate",
                    net1=net_name,
                    net2="GND",
                )
            )

    # --- Step 5: Connect Devices to the extracted network ---
    _connect_devices(rcx_db, net_graphs, result)

    logger.info(
        f"Extraction complete: {result.total_r} resistors, "
        f"{result.total_c} capacitors, {len(result.devices)} devices"
    )
    return result


def _merge_pcell_internal_nodes(
    net: RcxNet,
    net_graph: NetGraph,
    result: ExtractionResult,
    node_sub_caps: dict[str, float],
) -> None:
    """Merge nodes on layers that have no routing shapes in the net.

    Via cuts landing on PCell-internal metal (e.g. Metal1 source/drain contacts)
    create isolated nodes. Inside the device these are electrically shorted,
    so we alias them to a single canonical node.
    """
    # Collect layers that have routing shapes
    layers_with_shapes: set[str] = set()
    for shape in net.shapes:
        layers_with_shapes.add(shape.layer.lower())

    # Group nodes by layer
    nodes_by_layer: dict[str, list[str]] = {}
    for _x, _y, nlayer, nname in net_graph._nodes:
        ln = nlayer.lower()
        nodes_by_layer.setdefault(ln, []).append(nname)

    for layer_name, node_names in nodes_by_layer.items():
        if layer_name in layers_with_shapes:
            continue
        if len(node_names) <= 1:
            continue
        # Alias all nodes to the first one
        canonical = node_names[0]
        for alias in node_names[1:]:
            _rename_node_in_result(result, node_sub_caps, alias, canonical)
            net_graph.alias_node(alias, canonical)


def _rename_node_in_result(
    result: ExtractionResult,
    node_sub_caps: dict[str, float],
    old_node: str,
    new_node: str,
) -> None:
    """Rename a node across all resistors, capacitors, and caps dict."""
    if old_node == new_node:
        return

    for r in result.resistors:
        if r.node1 == old_node:
            r.node1 = new_node
        if r.node2 == old_node:
            r.node2 = new_node

    for c in result.capacitors:
        if c.node1 == old_node:
            c.node1 = new_node
        if c.node2 == old_node:
            c.node2 = new_node

    if old_node in node_sub_caps:
        val = node_sub_caps.pop(old_node)
        node_sub_caps[new_node] += val


# ---------------------------------------------------------------------------
# Per-net R and substrate C extraction
# ---------------------------------------------------------------------------


def _extract_net_parasitics(
    net: RcxNet,
    tech: TechFile,
    dbu: float,
    net_graph: NetGraph,
    result: ExtractionResult,
    node_sub_caps: dict[str, float],
) -> None:
    """Extract connected R and substrate C for a single net."""
    # 1) Collect potential interior tap / connection points on each layer
    # Tap points come from via centers and shape endpoints
    taps_by_layer: dict[str, list[tuple[float, float]]] = defaultdict(list)

    for via in net.vias:
        via_info = tech.via_by_name(via.via_type)
        step_x = via.spacing_x + via.width
        step_y = via.spacing_y + via.height
        for iy in range(via.ny):
            for ix in range(via.nx):
                cx = via.x + ix * step_x + via.width / 2.0
                cy = via.y + iy * step_y + via.height / 2.0
                if via_info:
                    taps_by_layer[via_info.lower_layer.lower()].append((cx, cy))
                    taps_by_layer[via_info.upper_layer.lower()].append((cx, cy))
                else:
                    taps_by_layer["metal1"].append((cx, cy))
                    taps_by_layer["metal2"].append((cx, cy))

    # 2) Process wire paths
    for shape in net.shapes:
        layer_info = tech.layer_by_number(shape.layer_number)
        if layer_info is None:
            layer_info = tech.layer_by_name(shape.layer)
        if layer_info is None or layer_info.purpose not in ("routing", "gate", "diffusion"):
            continue

        layer_name = layer_info.name
        layer_norm = layer_name.lower()
        taps = taps_by_layer.get(layer_norm, [])

        if shape.shape_type == "path":
            coords = shape.coordinates
            if len(coords) < 4 or not isinstance(coords[0], (int, float)):
                continue
            x1 = float(coords[0])
            y1 = float(coords[1])
            x2 = float(coords[2])
            y2 = float(coords[3])
            width_dbu = float(shape.width)
            width_um = max(width_dbu / dbu, 0.001)

            dx = x2 - x1
            dy = y2 - y1
            path_len_sq = dx * dx + dy * dy

            if path_len_sq == 0:
                n = net_graph.get_or_create_node(x1, y1, layer_name)
                c_sub = layer_info.area_cap * (width_um * width_um)
                node_sub_caps[n] += c_sub
                continue

            # Find tap points along the path centerline
            t_values = [0.0, 1.0]
            hw_tol = (width_dbu / 2.0) + net_graph.tol

            for tx, ty in taps:
                # Project (tx, ty) onto segment (x1, y1) -> (x2, y2)
                t = ((tx - x1) * dx + (ty - y1) * dy) / path_len_sq
                if 0.0 < t < 1.0:
                    px = x1 + t * dx
                    py = y1 + t * dy
                    dist_perp = math.hypot(tx - px, ty - py)
                    if dist_perp <= hw_tol:
                        t_values.append(t)

            # Sort and deduplicate t_values
            t_values = sorted(set(t_values))
            clean_t = [t_values[0]]
            min_t_delta = (net_graph.tol / math.sqrt(path_len_sq)) if path_len_sq > 0 else 1.0
            for t in t_values[1:]:
                if t - clean_t[-1] >= min_t_delta or t == 1.0:
                    clean_t.append(t)
            t_values = clean_t

            # Create sub-segment resistors and capacitors
            for k in range(len(t_values) - 1):
                t_a, t_b = t_values[k], t_values[k + 1]
                ax, ay = x1 + t_a * dx, y1 + t_a * dy
                bx, by = x1 + t_b * dx, y1 + t_b * dy

                seg_len_dbu = math.hypot(bx - ax, by - ay)
                seg_len_um = seg_len_dbu / dbu
                if seg_len_um <= 0:
                    continue

                node_a = net_graph.get_or_create_node(ax, ay, layer_name)
                node_b = net_graph.get_or_create_node(bx, by, layer_name)

                # Resistance
                r_val = layer_info.sheet_resistance * seg_len_um / width_um
                if node_a != node_b and r_val > 1e-6:
                    result.resistors.append(
                        ParasiticResistor(
                            net=net.name,
                            node1=node_a,
                            node2=node_b,
                            value=r_val,
                            layer=layer_name,
                        )
                    )

                # Substrate capacitance (split equally between node_a and node_b)
                area_um2 = seg_len_um * width_um
                perim_um = 2.0 * (seg_len_um + width_um)
                c_sub = (layer_info.area_cap * area_um2) + (layer_info.fringe_cap * perim_um)
                if c_sub > 1e-6:
                    node_sub_caps[node_a] += c_sub / 2.0
                    node_sub_caps[node_b] += c_sub / 2.0

        elif shape.shape_type == "rect":
            coords = shape.coordinates
            if len(coords) < 4 or not isinstance(coords[0], (int, float)):
                continue
            rx1 = float(coords[0])
            ry1 = float(coords[1])
            rx2 = float(coords[2])
            ry2 = float(coords[3])
            w_um = abs(rx2 - rx1) / dbu
            h_um = abs(ry2 - ry1) / dbu
            area_um2 = w_um * h_um
            perim_um = 2.0 * (w_um + h_um)

            cx = (rx1 + rx2) / 2.0
            cy = (ry1 + ry2) / 2.0

            if w_um >= h_um:
                p1x, p1y = min(rx1, rx2), cy
                p2x, p2y = max(rx1, rx2), cy
                length_um, width_um = max(w_um, 0.001), max(h_um, 0.001)
            else:
                p1x, p1y = cx, min(ry1, ry2)
                p2x, p2y = cx, max(ry1, ry2)
                length_um, width_um = max(h_um, 0.001), max(w_um, 0.001)

            node_a = net_graph.get_or_create_node(p1x, p1y, layer_name)
            node_b = net_graph.get_or_create_node(p2x, p2y, layer_name)

            r_val = layer_info.sheet_resistance * length_um / width_um
            if node_a != node_b and r_val > 1e-6:
                result.resistors.append(
                    ParasiticResistor(
                        net=net.name,
                        node1=node_a,
                        node2=node_b,
                        value=r_val,
                        layer=layer_name,
                    )
                )

            c_sub = (layer_info.area_cap * area_um2) + (layer_info.fringe_cap * perim_um)
            if c_sub > 1e-6:
                node_sub_caps[node_a] += c_sub / 2.0
                node_sub_caps[node_b] += c_sub / 2.0

    # 3) Process vias — one resistor per cut
    for via in net.vias:
        via_info = tech.via_by_name(via.via_type)
        if via_info is None:
            continue

        num_cuts = max(via.nx * via.ny, 1)
        r_per_cut = via_info.resistance / num_cuts
        step_x = via.spacing_x + via.width
        step_y = via.spacing_y + via.height

        for iy in range(via.ny):
            for ix in range(via.nx):
                cx = via.x + ix * step_x + via.width / 2.0
                cy = via.y + iy * step_y + via.height / 2.0

                # Project cut center onto nearby path centerlines on each
                # layer so the via node merges with the path tap node.
                # If no shape is found (e.g. Metal1 inside PCell), fall back
                # to the cut center so the via resistor is still created.
                lo_proj = _projectOntoShapes(
                    cx, cy, via_info.lower_layer, net.shapes, tech,
                    via.width, via.height,
                )
                hi_proj = _projectOntoShapes(
                    cx, cy, via_info.upper_layer, net.shapes, tech,
                    via.width, via.height,
                )
                if lo_proj is None and hi_proj is None:
                    continue
                lo_x, lo_y = lo_proj if lo_proj is not None else (cx, cy)
                hi_x, hi_y = hi_proj if hi_proj is not None else (cx, cy)

                node_lower = net_graph.get_or_create_node(
                    lo_x, lo_y, via_info.lower_layer
                )
                node_upper = net_graph.get_or_create_node(
                    hi_x, hi_y, via_info.upper_layer
                )
                if node_lower != node_upper and r_per_cut > 1e-6:
                    result.resistors.append(
                        ParasiticResistor(
                            net=net.name,
                            node1=node_lower,
                            node2=node_upper,
                            value=r_per_cut,
                            layer=via.via_type,
                        )
                    )


# ---------------------------------------------------------------------------
# Inter-net coupling capacitance
# ---------------------------------------------------------------------------


def _projectOntoShapes(
    cx: float, cy: float, layer_name: str, shapes: list[RcxShape], tech: TechFile,
    via_w: float = 0.0, via_h: float = 0.0,
) -> Optional[tuple[float, float]]:
    """Project a via cut center onto the centerline of the nearest overlapping shape on the given layer.

    The via cut footprint (cx±w/2, cy±h/2) is tested against shape bboxes
    so cuts that straddle a wide path are still matched.
    """
    layer_info = tech.layer_by_name(layer_name)
    if layer_info is not None:
        ln = layer_info.layer_number
    else:
        ln = -1

    hw = via_w / 2.0 if via_w > 0 else 50.0
    hh = via_h / 2.0 if via_h > 0 else 50.0

    best_dist = float("inf")
    best_px: float = 0.0
    best_py: float = 0.0
    found = False

    for shape in shapes:
        if shape.layer_number != ln and shape.layer.lower() != layer_name.lower():
            continue
        bbox = _get_bbox(shape)
        if bbox is None:
            continue
        bx1, by1, bx2, by2 = bbox
        # Check if via cut footprint overlaps shape bbox
        if cx + hw < bx1 or cx - hw > bx2 or cy + hh < by1 or cy - hh > by2:
            continue

        if shape.shape_type == "path":
            coords = shape.coordinates
            if len(coords) >= 4 and isinstance(coords[0], (int, float)):
                x1, y1, x2, y2 = float(coords[0]), float(coords[1]), float(coords[2]), float(coords[3])
                dx, dy = x2 - x1, y2 - y1
                path_len_sq = dx * dx + dy * dy
                if path_len_sq > 0:
                    t = ((cx - x1) * dx + (cy - y1) * dy) / path_len_sq
                    t = max(0.0, min(1.0, t))
                    px = x1 + t * dx
                    py = y1 + t * dy
                    dist = math.hypot(cx - px, cy - py)
                    if dist < best_dist:
                        best_dist = dist
                        best_px, best_py = px, py
                        found = True
        elif shape.shape_type == "rect":
            # Use the center of the rect on the longer axis
            rx_c = (bx1 + bx2) / 2.0
            ry_c = (by1 + by2) / 2.0
            dist = math.hypot(cx - rx_c, cy - ry_c)
            if dist < best_dist:
                best_dist = dist
                best_px, best_py = rx_c, ry_c
                found = True

    if not found:
        return None
    return best_px, best_py


def _extract_coupling(
    net1: RcxNet,
    net2: RcxNet,
    tech: TechFile,
    dbu: float,
    net_graphs: dict[str, NetGraph],
    result: ExtractionResult,
) -> None:
    """Extract coupling capacitance between two nets."""
    g1 = net_graphs.get(net1.name)
    g2 = net_graphs.get(net2.name)
    if not g1 or not g2:
        return

    # Check interlayer overlap
    for coupling_model in tech.coupling:
        l1_info = tech.layer_by_name(coupling_model.layer1)
        l2_info = tech.layer_by_name(coupling_model.layer2)
        if l1_info is None or l2_info is None:
            continue

        ln1 = l1_info.layer_number
        ln2 = l2_info.layer_number

        shapes_n1_l1 = [s for s in net1.shapes if s.layer_number == ln1]
        shapes_n2_l2 = [s for s in net2.shapes if s.layer_number == ln2]
        shapes_n1_l2 = [s for s in net1.shapes if s.layer_number == ln2]
        shapes_n2_l1 = [s for s in net2.shapes if s.layer_number == ln1]

        # net1 on layer1 overlapping net2 on layer2
        for s1 in shapes_n1_l1:
            for s2 in shapes_n2_l2:
                overlap, cx, cy = _overlap_info(s1, s2, dbu)
                if overlap > 0:
                    c_val = coupling_model.area_cap * overlap
                    if c_val > 1e-6:
                        n1 = g1.find_nearest_node(cx, cy, coupling_model.layer1)
                        n2 = g2.find_nearest_node(cx, cy, coupling_model.layer2)
                        result.capacitors.append(
                            ParasiticCapacitor(
                                node1=n1,
                                node2=n2,
                                value=c_val,
                                cap_type="coupling",
                                net1=net1.name,
                                net2=net2.name,
                            )
                        )

        # net1 on layer2 overlapping net2 on layer1
        for s1 in shapes_n1_l2:
            for s2 in shapes_n2_l1:
                overlap, cx, cy = _overlap_info(s1, s2, dbu)
                if overlap > 0:
                    c_val = coupling_model.area_cap * overlap
                    if c_val > 1e-6:
                        n1 = g1.find_nearest_node(cx, cy, coupling_model.layer2)
                        n2 = g2.find_nearest_node(cx, cy, coupling_model.layer1)
                        result.capacitors.append(
                            ParasiticCapacitor(
                                node1=n1,
                                node2=n2,
                                value=c_val,
                                cap_type="coupling",
                                net1=net1.name,
                                net2=net2.name,
                            )
                        )

    # Same-layer lateral coupling
    for layer_name, layer_info in tech.layers.items():
        if layer_info.purpose != "routing":
            continue
        ln = layer_info.layer_number
        shapes_n1 = [s for s in net1.shapes if s.layer_number == ln]
        shapes_n2 = [s for s in net2.shapes if s.layer_number == ln]

        for s1 in shapes_n1:
            for s2 in shapes_n2:
                c_lateral, cx, cy = _lateral_coupling_info(s1, s2, layer_info, dbu)
                if c_lateral > 1e-6:
                    n1 = g1.find_nearest_node(cx, cy, layer_name)
                    n2 = g2.find_nearest_node(cx, cy, layer_name)
                    result.capacitors.append(
                        ParasiticCapacitor(
                            node1=n1,
                            node2=n2,
                            value=c_lateral,
                            cap_type="coupling",
                            net1=net1.name,
                            net2=net2.name,
                        )
                    )


# ---------------------------------------------------------------------------
# Device connection
# ---------------------------------------------------------------------------


def _connect_devices(
    rcx_db: RcxDatabase,
    net_graphs: dict[str, NetGraph],
    result: ExtractionResult,
) -> None:
    """Connect devices directly to their corresponding nodes in the parasitic network."""
    for dev in rcx_db.devices:
        terminals: dict[str, str] = {}

        for term in dev.terminals:
            net_name = term.net
            net_graph = net_graphs.get(net_name)

            if net_graph and net_graph.has_nodes():
                # Connect to the nearest node on this net
                term_node = net_graph.find_nearest_node(term.x, term.y, term.layer)
            else:
                # No parasitics drawn for this net, connect directly to net name
                term_node = net_name

            terminals[term.name] = term_node

        result.devices.append(
            DeviceInstance(
                name=dev.name,
                model=dev.model,
                terminals=terminals,
                params=dev.params,
            )
        )


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------


def _get_bbox(shape: RcxShape) -> Optional[tuple[float, float, float, float]]:
    """Get bounding box of a shape as (x1, y1, x2, y2)."""
    if shape.shape_type == "rect":
        coords = shape.coordinates
        if len(coords) >= 4:
            return (
                min(coords[0], coords[2]),
                min(coords[1], coords[3]),
                max(coords[0], coords[2]),
                max(coords[1], coords[3]),
            )
    elif shape.shape_type == "path":
        coords = shape.coordinates
        if len(coords) >= 4:
            hw = shape.width / 2.0
            x1, y1, x2, y2 = coords[0], coords[1], coords[2], coords[3]
            return (
                min(x1, x2) - hw,
                min(y1, y2) - hw,
                max(x1, x2) + hw,
                max(y1, y2) + hw,
            )
    return None


def _overlap_info(
    s1: RcxShape, s2: RcxShape, dbu: float
) -> tuple[float, float, float]:
    """Compute overlap area in um^2 and center (cx, cy) in dbu."""
    bb1 = _get_bbox(s1)
    bb2 = _get_bbox(s2)
    if bb1 is None or bb2 is None:
        return 0.0, 0.0, 0.0

    ox1 = max(bb1[0], bb2[0])
    oy1 = max(bb1[1], bb2[1])
    ox2 = min(bb1[2], bb2[2])
    oy2 = min(bb1[3], bb2[3])

    if ox2 <= ox1 or oy2 <= oy1:
        return 0.0, 0.0, 0.0

    area_um2 = ((ox2 - ox1) / dbu) * ((oy2 - oy1) / dbu)
    cx = (ox1 + ox2) / 2.0
    cy = (oy1 + oy2) / 2.0
    return area_um2, cx, cy


def _lateral_coupling_info(
    s1: RcxShape,
    s2: RcxShape,
    layer_info: LayerInfo,
    dbu: float,
) -> tuple[float, float, float]:
    """Estimate lateral coupling and return (cap_fF, cx, cy)."""
    bb1 = _get_bbox(s1)
    bb2 = _get_bbox(s2)
    if bb1 is None or bb2 is None:
        return 0.0, 0.0, 0.0

    # Overlap in Y direction
    y_start = max(bb1[1], bb2[1])
    y_end = min(bb1[3], bb2[3])
    y_run = y_end - y_start

    # Overlap in X direction
    x_start = max(bb1[0], bb2[0])
    x_end = min(bb1[2], bb2[2])
    x_run = x_end - x_start

    if y_run > 0 and x_run <= 0:
        spacing = max(bb2[0] - bb1[2], bb1[0] - bb2[2])
        if spacing <= 0:
            return 0.0, 0.0, 0.0
        run_length = y_run / dbu
        spacing_um = spacing / dbu
        if bb2[0] >= bb1[2]:
            cx = (bb1[2] + bb2[0]) / 2.0
        else:
            cx = (bb2[2] + bb1[0]) / 2.0
        cy = (y_start + y_end) / 2.0
    elif x_run > 0 and y_run <= 0:
        spacing = max(bb2[1] - bb1[3], bb1[1] - bb2[3])
        if spacing <= 0:
            return 0.0, 0.0, 0.0
        run_length = x_run / dbu
        spacing_um = spacing / dbu
        cx = (x_start + x_end) / 2.0
        if bb2[1] >= bb1[3]:
            cy = (bb1[3] + bb2[1]) / 2.0
        else:
            cy = (bb2[3] + bb1[1]) / 2.0
    else:
        return 0.0, 0.0, 0.0

    if spacing_um <= 0 or run_length <= 0:
        return 0.0, 0.0, 0.0

    epsilon_r = 3.9  # SiO2
    epsilon_0 = 8.854e-3  # fF/um
    thickness_um = layer_info.thickness
    c_val = epsilon_0 * epsilon_r * thickness_um * run_length / spacing_um
    return c_val, cx, cy
