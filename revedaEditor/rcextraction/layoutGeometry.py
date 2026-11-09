# SPDX-License-Identifier: MPL-2.0
#
# Revolution EDA
# Copyright (c) 2024-2026 Revolution Semiconductor

"""Backwards-compatible shim: the layout connectivity engine and the
``layout.json`` record reader now live in
:mod:`revedaEditor.connectivity.layout`, shared by the live
``layoutScene`` (net highlighting), RCX, and batch tooling.

Why this path exists: the KLayout ``.lvsdb`` is a *connectivity* database
whose per-net shapes live on internal rule-deck layers with no GDS mapping;
``layout.json`` holds the real drawn interconnect. Net *names* are attached
separately (see :mod:`rcxExport`) using label positions from the LVSDB.
"""

from __future__ import annotations

import logging

from revedaEditor.connectivity.layout import (  # noqa: F401  (re-exports)
    LayRect,
    LayShape,
    LayVia,
    LayoutGeometryReader,
    NetGroup,
    PcellBridge,
    _pathFootprint,
    buildConnectivity,
)

logger = logging.getLogger("reveda")

__all__ = [
    "LayRect", "LayShape", "LayVia", "LayoutGeometryReader", "NetGroup",
    "PcellBridge", "buildConnectivity",
]
