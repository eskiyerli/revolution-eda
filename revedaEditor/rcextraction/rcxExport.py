#
# Copyright (c) 2024-2026 Revolution Semiconductor (Registered in the Netherlands)
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this file, You can obtain one at
# https://mozilla.org/MPL/2.0/.
#
# Add-ons and extensions developed for this software may be distributed
# under their own separate licenses.

"""Build an RCX extraction database (.rcx.json) from LVS results.

This bridges LVS and RC extraction (PEX). The parasitic geometry comes from
the Revolution EDA ``layout.json`` cellview (real drawn Paths/Rects/Vias on
real PDK layers with real widths) -- NOT from the KLayout ``.lvsdb``, whose
per-net shapes live on internal rule-deck layers with no physical dimensions
and would yield degenerate, identical R/C values.

Pipeline:
  1. Read geometry from ``layout.json`` (see :mod:`layoutGeometry`).
  2. Group shapes into nets by geometric connectivity (union-find over
     touching shapes; vias stitch metal layers; Pcell pins bridge terminals).
  3. Name each net:
       * top-level layout pins carry the port net name directly;
       * otherwise adopt the LVS/schematic net name whose LVSDB label position
         falls inside one of the group's shapes;
       * unnamed groups get a synthetic ``DNET<n>`` name.
  4. Emit devices from the KLayout-extracted netlist (real models, params,
     terminal-to-net connectivity).

The schema comes from :mod:`rcx_schema`, shared with the extractor.
"""

from __future__ import annotations

import json
import logging
import pathlib
from typing import Any, Optional

from .layoutGeometry import (
    LayoutGeometryReader,
    LayRect,
    NetGroup,
    buildConnectivity,
)
from .rcx_schema import (
    RcxDatabase,
    RcxDevice,
    RcxNet,
    RcxShape,
    RcxTerminal,
    RcxVia,
    save_rcx_database,
)

logger = logging.getLogger("reveda")


# ---------------------------------------------------------------------------
# Net naming
# ---------------------------------------------------------------------------


def _overlapArea(a: LayRect, b: LayRect) -> float:
    """Area of the intersection of two rectangles (0 if disjoint)."""
    ox = min(a.x2, b.x2) - max(a.x1, b.x1)
    oy = min(a.y2, b.y2) - max(a.y1, b.y1)
    if ox <= 0 or oy <= 0:
        return 0.0
    return ox * oy


def _bestAnchorNet(
    group: NetGroup,
    anchors: list[Any],
) -> Optional[str]:
    """Return the anchor net whose pin footprint overlaps the group the most.

    Only considers shapes and vias on matching conductor layers when layer is specified.
    """
    best: Optional[str] = None
    bestArea = 0.0
    for anchor in anchors:
        if len(anchor) >= 3:
            netId, pinRect, pinLayer = anchor[0], anchor[1], anchor[2]
        else:
            netId, pinRect = anchor[0], anchor[1]
            pinLayer = None

        pinLayerNorm = pinLayer.lower() if pinLayer else None
        area = 0.0
        for s in group.shapes:
            if pinLayerNorm is None or s.layer_name.lower() == pinLayerNorm:
                area += _overlapArea(s.footprint, pinRect)
        for v in group.vias:
            if (
                pinLayerNorm is None
                or v.lower_layer.lower() == pinLayerNorm
                or v.upper_layer.lower() == pinLayerNorm
            ):
                area += _overlapArea(v.footprint, pinRect)

        if area > bestArea:
            bestArea = area
            best = netId
    return best


def _nameGroups(
    groups: list[NetGroup],
    devicePinAnchors: list[tuple[str, LayRect]],
    portFootprints: list[tuple[str, LayRect]],
    tol: float,
) -> dict[int, tuple[str, bool]]:
    """Assign a (net_name, is_port) to each group index.

    Naming is driven by *pin overlap*, which is deterministic and precise:

      1. A top-level layout pin the group overlaps most -> that port's net
         name, and the group is flagged as a port.
      2. Otherwise the device (Pcell) terminal pin the group overlaps most ->
         that terminal's net id (from the extracted netlist). These are the
         exact net identifiers the device lines reference, so the parasitics
         connect to the right transistor terminals.
      3. Otherwise a synthetic ``DNET<n>`` name (internal routing that touches
         no pin).

    Matching by greatest overlap *area* (rather than first-hit containment)
    keeps a group assigned to the terminal it actually sits on when a large
    diffusion-metal pin from an adjacent terminal merely clips its edge.
    """
    result: dict[int, tuple[str, bool]] = {}
    usedNames: set[str] = set()

    for gi, group in enumerate(groups):
        isPort = False

        chosen = _bestAnchorNet(group, portFootprints)
        if chosen is not None:
            isPort = True
        else:
            chosen = _bestAnchorNet(group, devicePinAnchors)

        if chosen is None:
            # Synthetic name for internal routing touching no pin. Only these
            # must be unique; groups sharing a real net name are the same
            # electrical net and are merged by the caller.
            chosen = f"DNET{gi}"
            while chosen in usedNames:
                chosen = f"{chosen}_"

        usedNames.add(chosen)
        result[gi] = (chosen, isPort)

    return result


# ---------------------------------------------------------------------------
# Shape/via conversion
# ---------------------------------------------------------------------------


def _toRcxShapes(group: NetGroup) -> list[RcxShape]:
    """Convert a group's geometry into RcxShapes for the extractor."""
    shapes: list[RcxShape] = []
    for s in group.shapes:
        if s.kind == "path" and s.centerline is not None:
            x1, y1, x2, y2 = s.centerline
            shapes.append(RcxShape(
                layer=s.layer_name,
                layer_number=s.gds_layer,
                shape_type="path",
                coordinates=[x1, y1, x2, y2],
                width=s.width,
            ))
        else:  # rect
            fp = s.footprint
            shapes.append(RcxShape(
                layer=s.layer_name,
                layer_number=s.gds_layer,
                shape_type="rect",
                coordinates=[fp.x1, fp.y1, fp.x2, fp.y2],
            ))
    return shapes


def _toRcxVias(group: NetGroup) -> list[RcxVia]:
    vias: list[RcxVia] = []
    for v in group.vias:
        fp = v.footprint
        vias.append(RcxVia(
            via_type=v.via_type,
            x=fp.x1,
            y=fp.y1,
            width=v.width,
            height=v.height,
            nx=v.nx,
            ny=v.ny,
            spacing_x=v.spacing_x,
            spacing_y=v.spacing_y,
        ))
    return vias


def _coerceParam(value: Any) -> Any:
    if isinstance(value, (int, float)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def _buildDevices(extractedNetlist: Optional[dict]) -> list[RcxDevice]:
    """Devices from the KLayout-extracted netlist (models/params/net names)."""
    devices: list[RcxDevice] = []
    if not extractedNetlist:
        return devices
    for dev in extractedNetlist.get("devices", []):
        term_locs = dev.get("terminal_locations", {})
        pos = dev.get("position", {})
        dev_x = pos.get("x") if isinstance(pos, dict) else None
        dev_y = pos.get("y") if isinstance(pos, dict) else None
        terminals = []
        for termName, netName in dev.get("terminals", {}).items():
            loc = term_locs.get(termName.upper(), term_locs.get(termName, {}))
            tx = loc.get("x") if loc else dev_x
            ty = loc.get("y") if loc else dev_y
            tlayer = loc.get("layer") if loc else None
            terminals.append(RcxTerminal(
                name=termName,
                net=str(netName),
                x=tx,
                y=ty,
                layer=tlayer,
            ))
        params = {k: _coerceParam(v) for k, v in dev.get("params", {}).items()}
        devices.append(RcxDevice(
            name=dev.get("name", ""),
            model=dev.get("type", ""),
            terminals=terminals,
            params=params,
        ))
    return devices


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def buildRcxDatabase(
    layoutCellName: str,
    layoutElements: list[dict],
    extractedNetlist: Optional[dict],
    layoutLayers: Any,
    processModule: Any,
    dbu: float,
    lvsEquivalent: bool,
    devicePinAnchors: Optional[list[tuple[str, LayRect]]] = None,
    portFootprints: Optional[list[tuple[str, LayRect]]] = None,
    touchTolerance: float = 1.0,
) -> RcxDatabase:
    """Assemble the :class:`RcxDatabase` for ``layoutCellName``.

    Args:
        layoutCellName: top layout cell name.
        layoutElements: the ``layout.json`` element list (including the two
            header entries; they are skipped internally).
        extractedNetlist: ``parse_extracted_netlist`` result (device source).
        layoutLayers: PDK ``layoutLayers`` module.
        processModule: PDK ``process`` module (via definitions).
        dbu: database units per micron.
        lvsEquivalent: whether LVS passed.
        devicePinAnchors: (net_id, LayRect) list built from device (Pcell)
            terminal pins in the scene; the net_id is the terminal's net from
            the extracted netlist. Drives net naming so parasitics connect to
            the correct device terminals.
        portFootprints: optional (portName, LayRect) list from top-level pins.
        touchTolerance: overlap slack in dbu for the connectivity test.
    """
    reader = LayoutGeometryReader(layoutLayers, processModule)
    elements = layoutElements[2:] if len(layoutElements) > 2 else []
    shapes, vias = reader.read(elements)

    # Connectivity uses only physical geometry (touching metal + vias). Pcell
    # pins are deliberately NOT used to merge groups: a device pin footprint
    # can overlap several of the device's own terminals' routing, which would
    # falsely short drain/gate/source together. Instead, device pins are used
    # only to *name* groups (below); routing pieces that share a terminal get
    # the same net name and are merged by name afterwards.
    groups = buildConnectivity(
        shapes, vias, touchTolerance=touchTolerance
    )

    naming = _nameGroups(
        groups, devicePinAnchors or [], portFootprints or [], touchTolerance
    )

    # Diagnostics: log the geometry, anchors, and resulting names so a real
    # in-app run can be inspected in reveda.log.
    if logger.isEnabledFor(logging.INFO):
        logger.info(
            f"RCX export {layoutCellName}: {len(groups)} geometric groups, "
            f"{len(devicePinAnchors or [])} device-pin anchors, "
            f"{len(portFootprints or [])} port pins"
        )
        for netId, r in (devicePinAnchors or []):
            logger.info(
                f"  device-pin anchor net={netId} "
                f"rect=[{r.x1:.0f},{r.y1:.0f},{r.x2:.0f},{r.y2:.0f}]"
            )
        for gi, group in enumerate(groups):
            fps = [s.footprint for s in group.shapes]
            if fps:
                bx1 = min(f.x1 for f in fps); by1 = min(f.y1 for f in fps)
                bx2 = max(f.x2 for f in fps); by2 = max(f.y2 for f in fps)
            else:
                bx1 = by1 = bx2 = by2 = 0
            layers = sorted({s.layer_name for s in group.shapes})
            logger.info(
                f"  group {gi} -> net '{naming[gi][0]}' "
                f"layers={layers} nvias={len(group.vias)} "
                f"bbox=[{bx1:.0f},{by1:.0f},{bx2:.0f},{by2:.0f}]"
            )

    # Merge all geometric groups that resolved to the same net name into one
    # RcxNet. Disjoint pieces of the same electrical net (e.g. routing that
    # reconnects through a device) must share a single node, and merging also
    # keeps per-net shape indices unique so parasitic node names don't collide.
    byName: dict[str, RcxNet] = {}
    ports: list[str] = []
    for gi, group in enumerate(groups):
        name, isPort = naming[gi]
        rcxNet = byName.get(name)
        if rcxNet is None:
            rcxNet = RcxNet(name=name, net_id=name, is_port=isPort)
            byName[name] = rcxNet
        rcxNet.is_port = rcxNet.is_port or isPort
        rcxNet.shapes.extend(_toRcxShapes(group))
        rcxNet.vias.extend(_toRcxVias(group))
    for name, rcxNet in byName.items():
        if rcxNet.is_port:
            ports.append(name)
    nets = list(byName.values())

    # If no top-level layout pins were found, fall back to the extracted
    # netlist's .SUBCKT header pins for port declarations.
    if not ports and extractedNetlist:
        for pin in extractedNetlist.get("pins", []):
            if pin not in ports:
                ports.append(pin)

    return RcxDatabase(
        cell_name=layoutCellName,
        lvs_equivalent=bool(lvsEquivalent),
        dbu=float(dbu),
        ports=ports,
        nets=nets,
        devices=_buildDevices(extractedNetlist),
    )


def exportRcxDatabase(
    layoutCellName: str,
    layoutElements: list[dict],
    extractedNetlist: Optional[dict],
    layoutLayers: Any,
    processModule: Any,
    outputPath: str | pathlib.Path,
    dbu: float,
    lvsEquivalent: bool,
    devicePinAnchors: Optional[list[tuple[str, LayRect]]] = None,
    portFootprints: Optional[list[tuple[str, LayRect]]] = None,
    touchTolerance: float = 1.0,
) -> pathlib.Path:
    """Build and write the ``.rcx.json`` extraction database.

    Returns the path written. Raises ``OSError`` on write failure.
    """
    outputPath = pathlib.Path(outputPath)
    database = buildRcxDatabase(
        layoutCellName,
        layoutElements,
        extractedNetlist,
        layoutLayers,
        processModule,
        dbu,
        lvsEquivalent,
        devicePinAnchors=devicePinAnchors,
        portFootprints=portFootprints,
        touchTolerance=touchTolerance,
    )
    outputPath.parent.mkdir(parents=True, exist_ok=True)
    save_rcx_database(database, outputPath)
    return outputPath
