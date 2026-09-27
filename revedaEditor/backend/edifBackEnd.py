# SPDX-License-Identifier: MPL-2.0
#
# Copyright (c) 2024-2026 Revolution Semiconductor (Registered in the Netherlands)
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this file, You can obtain one at
# https://mozilla.org/MPL/2.0/.
#
# Add-ons and extensions developed for this software may be distributed
# under their own separate licenses.

"""EDIF 2 0 0 reader.

Parses an EDIF file into a Qt-free intermediate model (libraries, cells,
views, ports, instances, nets, wire figures) consumed by
``revedaEditor.fileio.importEDIF``.  The parser is intentionally generic: it
tokenizes the s-expression file and walks the tree by keyword rather than
enforcing the strict EDIF grammar, so dialect quirks (page/section wrappers,
vendor property bags, level>0 forms) degrade gracefully instead of failing.

EDIF is not case sensitive for keywords; name tokens may carry ``&`` escape
toggles (``&`` switches between identifier and extended-character modes) and
``(rename id "display")`` pairs a legal name with the original display name.
"""

import pathlib
from collections.abc import Iterator
from dataclasses import dataclass, field


class EdifError(ValueError):
    """Raised for unreadable or unsupported EDIF input."""


class EdifStr(str):
    """A double-quoted string token (vs a bare EDIF name atom)."""


# ---------------------------------------------------------------------------
# tokenizer / s-expression layer
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list:
    """Split EDIF text into '(' ')' atoms and EdifStr string tokens.

    An ``&`` inside an atom toggles extended-name mode, so whitespace and
    other specials between two ``&`` markers belong to the token.
    """
    tokens: list = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if ch in "()":
            tokens.append(ch)
            i += 1
            continue
        if ch == '"':
            j = text.find('"', i + 1)
            if j == -1:
                raise EdifError("Unterminated string in EDIF file")
            tokens.append(EdifStr(text[i + 1:j]))
            i = j + 1
            continue
        if ch == ";":
            # ;-style comment to end of line (writers emit them although
            # the spec only defines (comment …) forms).
            j = text.find("\n", i)
            i = n if j == -1 else j + 1
            continue
        # atom; consume until delimiter, honoring & extended-name toggles
        j = i
        extended = False
        while j < n:
            c = text[j]
            if c == "&":
                extended = not extended
                j += 1
                continue
            if not extended and (c.isspace() or c in "()"):
                break
            if c == '"':
                break
            j += 1
        tokens.append(text[i:j])
        i = j
    return tokens


def _parseSexpr(tokens: list) -> list:
    """Build nested lists from tokens. Returns the top-level form list."""
    root: list = []
    stack = [root]
    for token in tokens:
        if token == "(":
            node: list = []
            stack[-1].append(node)
            stack.append(node)
        elif token == ")":
            if len(stack) < 2:
                raise EdifError("Unbalanced parentheses in EDIF file")
            stack.pop()
        else:
            stack[-1].append(token)
    if len(stack) != 1:
        raise EdifError("Unbalanced parentheses in EDIF file")
    return root


def _head(form) -> str:
    """Lower-cased head keyword of a form, or '' for atoms/empty lists."""
    if isinstance(form, list) and form and isinstance(form[0], str):
        return form[0].casefold()
    return ""


def _unescape(name) -> str:
    """Strip EDIF ``&`` extended-name toggles from a name token."""
    return str(name).replace("&", "")


def _asInt(value) -> int:
    return int(float(str(value)))


def _nameOf(node) -> str:
    """EDIF name of a name/rename form, preferring the display name."""
    if isinstance(node, list):
        if _head(node) == "rename" and len(node) >= 3:
            return _unescape(node[2])
        for child in node:
            if isinstance(child, EdifStr):
                return _unescape(child)
        for child in node:
            if not isinstance(child, list):
                return _unescape(child)
        return ""
    return _unescape(node)


def _legalNameOf(node) -> str:
    """EDIF legal name of a name/rename form (identifier before rename)."""
    if isinstance(node, list):
        if _head(node) == "rename" and len(node) >= 2:
            return _unescape(node[1])
        return _nameOf(node)
    return _unescape(node)


def _points(form) -> list[tuple[float, float]]:
    """Collect (x, y) pairs from a pointList/pt form or a bare x y pair."""
    pts = []
    for node in form[1:]:
        if isinstance(node, list) and _head(node) == "pt" and len(node) >= 3:
            try:
                pts.append((float(str(node[1])), float(str(node[2]))))
            except ValueError:
                continue
    return pts


def _find(form, keyword: str) -> list | None:
    """First direct child form of *form* whose head is *keyword*."""
    folded = keyword.casefold()
    for node in form[1:]:
        if _head(node) == folded:
            return node
    return None


def _findAll(form, keyword: str) -> Iterator[list]:
    folded = keyword.casefold()
    for node in form[1:]:
        if _head(node) == folded:
            yield node


def _findDeep(form, keyword: str) -> Iterator[list]:
    """All descendant forms (any depth) whose head is *keyword*."""
    if not isinstance(form, list):
        return
    folded = keyword.casefold()
    for node in form[1:]:
        if isinstance(node, list):
            if _head(node) == folded:
                yield node
            yield from _findDeep(node, keyword)


def _properties(form) -> dict[str, str]:
    """(property name (string|integer|number|boolean v)) → {name: str(v)}."""
    props: dict[str, str] = {}
    for node in _findAll(form, "property"):
        if len(node) < 3:
            continue
        name = _nameOf(node[1])
        valueForm = node[2]
        value = ""
        if isinstance(valueForm, list) and len(valueForm) >= 2:
            # (string "v") / (integer 5) / (number 1.5) / (boolean (true))
            inner = valueForm[-1]
            value = (
                str(inner[-1]) if isinstance(inner, list) and inner
                else str(inner)
            )
        elif not isinstance(valueForm, list):
            value = str(valueForm)
        props[name] = value
    return props


# ---------------------------------------------------------------------------
# EDIF orientation → reveda (angle, flipTuple)
# ---------------------------------------------------------------------------

# reveda applies rotate(angle)·scale(flip) so a mirrored-rotated orientation
# maps cleanly: EDIF MX flips y, MY flips x, suffix R90 adds +90 rotation.
_ORIENTATION_MAP = {
    "r0": (0.0, (1, 1)),
    "r90": (90.0, (1, 1)),
    "r180": (180.0, (1, 1)),
    "r270": (270.0, (1, 1)),
    "mx": (0.0, (1, -1)),
    "my": (0.0, (-1, 1)),
    "mxr90": (90.0, (1, -1)),
    "myr90": (90.0, (-1, 1)),
}

_DIRECTION_MAP = {
    "input": "Input",
    "output": "Output",
    "inout": "Inout",
}


# ---------------------------------------------------------------------------
# model
# ---------------------------------------------------------------------------

@dataclass
class EdifPort:
    """A flattened scalar port member (array/bundle ports expand to these)."""
    name: str
    direction: str = "Inout"  # Input | Output | Inout
    pinType: str = "Signal"   # Signal | Power | Ground


@dataclass
class EdifPortRef:
    """One endpoint of a net join. ``instance`` is None for interface ports
    and global port refs."""
    port: str
    instance: str | None = None


@dataclass
class EdifInstance:
    name: str
    cellName: str
    libName: str | None = None       # None → same library as owner cell
    viewName: str | None = None
    pos: tuple[float, float] | None = None
    angle: float = 0.0
    flip: tuple[int, int] = (1, 1)
    properties: dict = field(default_factory=dict)
    page: int = 0


@dataclass
class EdifNet:
    name: str
    refs: list[EdifPortRef] = field(default_factory=list)
    segments: list[list[tuple[float, float]]] = field(default_factory=list)
    properties: dict = field(default_factory=dict)
    page: int = 0


@dataclass
class EdifView:
    name: str
    viewType: str = ""
    ports: list[EdifPort] = field(default_factory=list)
    instances: list[EdifInstance] = field(default_factory=list)
    nets: list[EdifNet] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)
    pageCount: int = 1


@dataclass
class EdifCell:
    name: str
    libName: str
    views: dict[str, EdifView] = field(default_factory=dict)
    cellType: str = "GENERIC"

    def bestView(self) -> EdifView | None:
        """Prefer a SCHEMATIC view, then NETLIST, then the first view."""
        views = list(self.views.values())
        for preferred in ("schematic", "netlist"):
            for view in views:
                if view.viewType.casefold() == preferred:
                    return view
        return views[0] if views else None


@dataclass
class EdifLib:
    name: str
    cells: dict[str, EdifCell] = field(default_factory=dict)
    external: bool = False
    distanceUnit: float | None = None  # meters per EDIF distance unit


# ---------------------------------------------------------------------------
# semantic pass
# ---------------------------------------------------------------------------

class edifC:
    """Parse an EDIF 2 0 0 file into libraries/cells/views.

    Mirrors the ``hdlBackEnd`` parser classes (``spiceC`` etc.): constructed
    from a ``pathlib.Path`` and exposes parsed data as attributes.
    """

    def __init__(self, pathObj: pathlib.Path):
        self._pathObj = pathlib.Path(pathObj)
        self.designName = ""
        self.topLibName = ""
        self.topCellName = ""
        self.libraries: dict[str, EdifLib] = {}
        self.messages: list[str] = []

        text = self._pathObj.read_text(encoding="utf-8", errors="replace")
        roots = _parseSexpr(_tokenize(text))
        edifForm = next(
            (form for form in roots if _head(form) == "edif"), None)
        if edifForm is None:
            raise EdifError("Not an EDIF file: missing top-level (edif …) form")
        self._checkVersion(edifForm)
        for node in edifForm[1:]:
            if not isinstance(node, list):
                continue
            head = _head(node)
            if head in ("library", "external"):
                self._parseLibrary(node, external=(head == "external"))
            elif head == "design":
                self._parseDesign(node)
            elif head == "comment":
                self.messages.append(
                    f"top-level comment: {' '.join(map(str, node[1:]))}")
        if not self.designName and len(edifForm) > 1:
            self.designName = _legalNameOf(edifForm[1])

    def _checkVersion(self, edifForm: list):
        version = _find(edifForm, "edifVersion")
        if version is None or len(version) < 2:
            raise EdifError("EDIF file has no edifVersion")
        try:
            major = _asInt(version[1])
        except (ValueError, IndexError):
            raise EdifError(f"Unreadable edifVersion: {version[1:]}")
        if major != 2:
            raise EdifError(
                f"Unsupported EDIF version "
                f"{' '.join(map(str, version[1:]))}; only EDIF 2 0 0 "
                "is supported")

    @property
    def pathObj(self):
        return self._pathObj

    # -- library / cell / view ----------------------------------------------

    def _parseLibrary(self, form: list, external: bool):
        if len(form) < 2:
            return
        lib = EdifLib(name=_nameOf(form[1]), external=external)
        lib.distanceUnit = self._distanceUnit(form)
        self.libraries[lib.name] = lib
        for node in form[1:]:
            if _head(node) == "cell":
                self._parseCell(node, lib)

    @staticmethod
    def _distanceUnit(libForm: list) -> float | None:
        """Meters per EDIF distance unit from
        ``(scale N (e m e) (unit DISTANCE))`` — also tolerates the
        ``(scale distance N (e m e))`` keyword-first dialect."""
        for scale in _findDeep(libForm, "scale"):
            numbers = []
            factor = 1.0
            for node in scale[1:]:
                if isinstance(node, list):
                    if _head(node) == "e" and len(node) >= 3:
                        try:
                            factor = float(str(node[1])) * 10.0 ** float(
                                str(node[2]))
                        except ValueError:
                            factor = 1.0
                    continue
                try:
                    numbers.append(float(str(node)))
                except ValueError:
                    continue
            if numbers:
                return numbers[0] * factor
        return None

    def _parseCell(self, form: list, lib: EdifLib):
        if len(form) < 2:
            return
        cell = EdifCell(name=_nameOf(form[1]), libName=lib.name)
        for node in form[1:]:
            head = _head(node)
            if head == "celltype" and len(node) > 1:
                cell.cellType = str(node[1])
            elif head == "view":
                view = self._parseView(node, lib)
                if view is not None:
                    cell.views[view.name] = view
        # Some writers omit the (view …) wrapper and hang interface/contents
        # directly on the cell — treat them as one implicit view.
        implicit = self._implicitView(form)
        if implicit is not None:
            cell.views.setdefault(implicit.name, implicit)
        lib.cells[cell.name] = cell

    def _implicitView(self, cellForm: list) -> EdifView | None:
        """Synthesize a view from cell-level (interface)/(contents) forms."""
        interface = _find(cellForm, "interface")
        contents = _find(cellForm, "contents")
        if interface is None and contents is None:
            return None
        view = EdifView(
            name=f"{_nameOf(cellForm[1])}_view",
            viewType="SCHEMATIC" if contents is not None else "NETLIST")
        if interface is not None:
            self._parseInterface(interface, view)
        if contents is not None:
            self._parseContents(contents, view)
        return view

    def _parseView(self, form: list, lib: EdifLib) -> EdifView | None:
        if len(form) < 2:
            return None
        view = EdifView(name=_nameOf(form[1]))
        for node in form[1:]:
            head = _head(node)
            if head == "viewtype" and len(node) > 1:
                view.viewType = str(node[1])
            elif head == "interface":
                self._parseInterface(node, view)
            elif head == "contents":
                self._parseContents(node, view)
        return view

    # -- interface -----------------------------------------------------------

    def _parseInterface(self, form: list, view: EdifView):
        for node in form[1:]:
            if _head(node) == "port":
                view.ports.extend(self._parsePort(node))

    def _parsePort(self, form: list) -> list[EdifPort]:
        if len(form) < 2:
            return []
        direction = "Inout"
        dirForm = _find(form, "direction")
        if dirForm is not None and len(dirForm) > 1:
            direction = _DIRECTION_MAP.get(str(dirForm[1]).casefold(), "Inout")
        pinType = self._portPinType(_properties(form))

        nameNode = form[1]
        members: list[str] = []
        head = _head(nameNode)
        if head == "array":
            # (array name size) → name<0> … name<size-1>
            if len(nameNode) >= 3:
                base = _nameOf(nameNode[1])
                try:
                    size = _asInt(nameNode[2])
                except (ValueError, IndexError):
                    size = 0
                members = [f"{base}<{i}>" for i in range(size)]
        elif head == "bundle":
            # (bundle (listOf p1 p2 …) ) → each member by name
            listOf = _find(nameNode, "listof") or _find(nameNode, "list")
            if listOf is not None:
                members = [_nameOf(m) for m in listOf[1:]]
            else:
                members = [_nameOf(m) for m in nameNode[1:]
                           if not isinstance(m, list)]
        else:
            members = [_nameOf(nameNode)]
        return [EdifPort(name=m, direction=direction, pinType=pinType)
                for m in members if m]

    @staticmethod
    def _portPinType(props: dict[str, str]) -> str:
        folded = {key.casefold(): value.casefold()
                  for key, value in props.items()}
        isSupply = (
            any("power" in folded.get(key, "")
                for key in ("type", "porttype", "usetype"))
            or folded.get("porttype") in ("power", "supply")
        )
        if not isSupply:
            return "Signal"
        supplyType = folded.get("supplytype", "")
        if any(tag in supplyType for tag in ("gnd", "ground")):
            return "Ground"
        return "Power"

    # -- contents ------------------------------------------------------------

    def _parseContents(self, form: list, view: EdifView):
        """Walk contents, descending into page/section/portGroup wrappers."""
        self._walkContents(list(form[1:]), view)

    def _walkContents(self, nodes: list, view: EdifView, pageIndex: int = 0):
        for node in nodes:
            head = _head(node)
            if head == "instance":
                for inst in self._parseInstance(node):
                    inst.page = pageIndex
                    view.instances.append(inst)
            elif head == "net":
                net = self._parseNet(node)
                net.page = pageIndex
                view.nets.append(net)
            elif head in ("page", "section", "portgroup"):
                nextPage = pageIndex
                if head == "page":
                    pageIndex += 1
                    view.pageCount = max(view.pageCount, pageIndex + 1)
                    nextPage = pageIndex
                self._walkContents(list(node[1:]), view, nextPage)
            elif head == "comment":
                text = " ".join(str(n) for n in node[1:])
                if text:
                    view.comments.append(text)
            elif head == "offpageconnector":
                # merged pages already share names; nothing to emit
                continue

    # -- instances -----------------------------------------------------------

    def _parseInstance(self, form: list) -> list[EdifInstance]:
        if len(form) < 2:
            return []
        ref = self._instanceRef(form)
        props = _properties(form)
        angle, flip, pos = self._instanceTransform(form)
        base = EdifInstance(
            name="", cellName=ref[0], libName=ref[1], viewName=ref[2],
            pos=pos, angle=angle, flip=flip, properties=props)

        nameNode = form[1]
        if _head(nameNode) == "array" and len(nameNode) >= 3:
            # (instance (array I 4) …) → scalar instances I<0>…I<3>
            try:
                size = _asInt(nameNode[2])
            except (ValueError, IndexError):
                size = 1
            baseName = _nameOf(nameNode[1])
            result = []
            for i in range(size):
                member = EdifInstance(
                    name=f"{baseName}<{i}>", cellName=base.cellName,
                    libName=base.libName, viewName=base.viewName,
                    pos=base.pos, angle=base.angle, flip=base.flip,
                    properties=dict(base.properties))
                result.append(member)
            return result
        base.name = _nameOf(nameNode)
        return [base]

    @staticmethod
    def _instanceRef(form: list) -> tuple[str, str | None, str | None]:
        """(viewRef v (cellRef c [(libraryRef l)])) → (cell, lib, view)."""
        cellName = libName = viewName = None
        viewRef = _find(form, "viewref")
        if viewRef is None:
            # tolerate (instance i (cellRef c …)) without a viewRef
            cellRef = _find(form, "cellref")
            viewRef = form
        else:
            if len(viewRef) > 1:
                viewName = _nameOf(viewRef[1])
            cellRef = _find(viewRef, "cellref")
        if cellRef is not None and len(cellRef) > 1:
            cellName = _nameOf(cellRef[1])
            libRef = _find(cellRef, "libraryref")
            if libRef is not None and len(libRef) > 1:
                libName = _nameOf(libRef[1])
        return cellName or "", libName, viewName

    @staticmethod
    def _instanceTransform(form: list) -> tuple[float, tuple[int, int],
                                              tuple[float, float] | None]:
        angle, flip, pos = 0.0, (1, 1), None
        for transform in _findAll(form, "transform"):
            for node in transform[1:]:
                head = _head(node)
                if head == "orientation" and len(node) > 1:
                    angle, flip = _ORIENTATION_MAP.get(
                        str(node[1]).casefold(), (0.0, (1, 1)))
                elif head in ("origin", "translation", "offset"):
                    if len(node) >= 3 and not isinstance(node[1], list):
                        try:
                            pos = (float(str(node[1])),
                                   float(str(node[2])))
                        except ValueError:
                            pos = None
                    else:
                        pts = _points(node) or _points(
                            _find(node, "pt") or [])
                        if pts:
                            pos = pts[0]
        return angle, flip, pos

    # -- nets ----------------------------------------------------------------

    def _parseNet(self, form: list) -> EdifNet:
        net = EdifNet(name=_nameOf(form[1]) if len(form) > 1 else "")
        net.properties = _properties(form)
        for node in form[1:]:
            head = _head(node)
            if head == "joined":
                for ref in node[1:]:
                    portRef = self._parsePortRef(ref)
                    if portRef is not None:
                        net.refs.append(portRef)
            elif head == "figure" or head in ("figuregroup", "figuregroupoverride"):
                net.segments.extend(self._figureSegments(node))
        return net

    def _parsePortRef(self, form) -> EdifPortRef | None:
        """(portRef p [(instanceRef i)|(member p i)|…]) → EdifPortRef."""
        head = _head(form)
        if head == "globalportref":
            if len(form) >= 2:
                return EdifPortRef(port=_nameOf(form[1]), instance=None)
            return None
        if head == "member":
            # bare (member p i) inside joined → interface member port
            if len(form) >= 3:
                return EdifPortRef(
                    port=f"{_nameOf(form[1])}<{_nameOf(form[2])}>")
            return None
        if head not in ("portinst", "portref"):
            return None
        if len(form) < 2:
            return None
        portNode = form[1]
        if _head(portNode) == "member" and len(portNode) >= 3:
            port = f"{_nameOf(portNode[1])}<{_nameOf(portNode[2])}>"
        else:
            port = _nameOf(portNode)
        instance = None
        instRef = _find(form, "instanceref")
        if instRef is not None and len(instRef) > 1:
            instNode = instRef[1]
            if _head(instNode) == "member" and len(instNode) >= 3:
                instance = (f"{_nameOf(instNode[1])}"
                            f"<{_nameOf(instNode[2])}>")
            else:
                instance = _nameOf(instNode)
        return EdifPortRef(port=port, instance=instance)

    def _figureSegments(self, form) -> list[list[tuple[float, float]]]:
        """Wire geometry inside a figure: path/polyline/line polylines and
        openShape curves. Dots mark junctions — connectivity is geometric in
        reveda so they need no representation."""
        segments: list[list[tuple[float, float]]] = []
        for keyword in ("path", "polyline", "line", "arc"):
            for node in _findDeep(form, keyword):
                pts = _points(node)
                if not pts:
                    pointList = _find(node, "pointlist")
                    if pointList is not None:
                        pts = _points(pointList)
                if len(pts) >= 2:
                    segments.append(pts)
        return segments

    # -- design directive ----------------------------------------------------

    def _parseDesign(self, form: list):
        if len(form) < 2:
            return
        self.designName = _nameOf(form[1])
        cellRef = _find(form, "cellref")
        if cellRef is not None and len(cellRef) > 1:
            self.topCellName = _nameOf(cellRef[1])
            libRef = _find(cellRef, "libraryref")
            if libRef is not None and len(libRef) > 1:
                self.topLibName = _nameOf(libRef[1])

    # -- convenience -----------------------------------------------------------

    def cells(self) -> Iterator[EdifCell]:
        for lib in self.libraries.values():
            yield from lib.cells.values()

    def topCell(self) -> EdifCell | None:
        lib = self.libraries.get(self.topLibName)
        if lib is not None:
            return lib.cells.get(self.topCellName)
        return None
