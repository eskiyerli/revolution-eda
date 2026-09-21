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

"""Qt-free connectivity primitives.

The connectivity engine works on plain data records so the same code path
serves live scenes (GUI), decoded JSON design arrays (aiTerminal ops,
importers, batch netlisting) and unit tests. Scenes and records are mapped
into these primitives by ``adapters.py``.

Name strengths mirror ``netNameStrengthEnum`` in ``common/net.py``; they are
plain ints here so this module stays importable without Qt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# Net name strengths, mirroring netNameStrengthEnum (NONAME < WEAK < INHERIT < SET).
NONAME = 0
WEAK = 1
INHERIT = 2
SET = 3

Point = tuple[float, float]


def parseArrayNotation(name: str) -> tuple[str, tuple[int, int]]:
    """Parse 'name<start:end>' / 'name<i>' into (baseName, (start, end)).

    Scalar names return (name, (-1, -1)). Mirrors
    ``schematicNet.parseArrayNotation``.
    """
    if "<" not in name or ">" not in name:
        return name, (-1, -1)
    baseName = name.split("<")[0]
    indexRange = name.split("<")[1].split(">")[0]
    if ":" not in indexRange:
        singleIndex = int(indexRange)
        return baseName, (singleIndex, singleIndex)
    start, end = map(int, indexRange.split(":"))
    return baseName, (start, end)


def namesMatch(name1: str, name2: str) -> bool:
    """Bus-aware name equality, mirroring ``schematicNet._namesMatch``:
    'inp<7>' matches 'inp<7:0>' (index inside range)."""
    if name1 == name2:
        return True
    base1, (start1, end1) = parseArrayNotation(name1)
    base2, (start2, end2) = parseArrayNotation(name2)
    if base1 != base2:
        return False
    if (start1 == -1) or (start2 == -1):
        return False
    min1, max1 = min(start1, end1), max(start1, end1)
    min2, max2 = min(start2, end2), max(start2, end2)
    return not (max1 < min2 or max2 < min1)


def busWidth(name: str) -> Optional[int]:
    """Bus width of an array-notation name, or None for scalars."""
    _, (start, end) = parseArrayNotation(name)
    if start == -1:
        return None
    return abs(start - end)


@dataclass(frozen=True)
class Seg:
    """One wire segment: endpoints in scene/sheet coordinates."""
    id: int
    p1: Point
    p2: Point
    name: str = ""
    strength: int = NONAME
    expr: str = ""  # optional net expression "[@name[:default]]" (scn nx)


@dataclass(frozen=True)
class Port:
    """A pin attachment point (symbol pin or schematic pin)."""
    id: int
    name: str
    direction: str  # "Input" | "Output" | "Inout"
    point: Point
    kind: str  # "symbolPin" | "schemPin"
    owner: str = ""  # instance name for symbol pins, pin name for sheet pins
    expr: str = ""  # optional net expression "[@name[:default]]"
    # Owning instance's netSet ({exprName: localNet}) for symbolPin ports;
    # shadows sheet-level bindings when evaluating this pin's expr.
    netSet: dict = field(default_factory=dict)

    @property
    def isGlobal(self) -> bool:
        """Only symbol pins carry global (!) semantics, matching
        findGlobalNets which iterates symbol pins only."""
        return self.kind == "symbolPin" and self.name.endswith("!")


@dataclass
class NetGroup:
    """A physically joined set of segments plus attached ports."""
    id: int
    members: set[int] = field(default_factory=set)  # seg ids
    ports: set[int] = field(default_factory=set)  # port ids
    name: str = ""
    strength: int = NONAME


@dataclass(frozen=True)
class Conflict:
    """A semantic conflict discovered during name resolution."""
    kind: str  # "netNameConflict" | "busWidthMismatch" | "pinNameConflict"
    message: str
    segIds: tuple[int, ...] = ()
    portIds: tuple[int, ...] = ()


@dataclass
class ConnectivityResult:
    """Output of the connectivity engine for one sheet."""
    groups: list[NetGroup]
    segGroup: dict[int, int]  # seg id -> group index into groups
    portGroup: dict[int, Optional[int]]  # port id -> group index or None
    segName: dict[int, tuple[str, int]]  # seg id -> (resolved name, strength)
    segConflicts: set[int] = field(default_factory=set)
    conflicts: list[Conflict] = field(default_factory=list)
    autoCount: int = 0  # number of auto-assigned net<N> names
    # Net-expression results (Phase 3): exprName -> declared default, and
    # resolved net name for each expr-bearing port (floating pins included).
    exprNames: dict[str, str] = field(default_factory=dict)
    portExprNet: dict[int, str] = field(default_factory=dict)

    def groupOf(self, segId: int) -> Optional[NetGroup]:
        index = self.segGroup.get(segId)
        return self.groups[index] if index is not None else None

    def signalKey(self, groupId: int) -> str:
        """Logical signal identity: resolved group name. Disjoint groups
        sharing a SET name connect-by-name to the same signal."""
        return self.groups[groupId].name
