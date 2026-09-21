"""Phase 3 tests — net expressions and inherited connections (netSet).

Covers the Qt-free ``connectivity.netexpr`` helpers, expression evaluation
inside ``connectivity.resolve``, ``nx``/``nst`` persistence, scene
integration (``nameSceneNets(netSet=...)``, ``collectNetExprNames``, the
resolved-name visibility toggle), and the end-to-end netlister path: a
``vdd!`` supply propagated through two hierarchy levels via netSet
overrides.
"""

import json
import pathlib
import types

import pytest
from PySide6.QtCore import QPoint

import revedaEditor.backend.libraryMethods as libm
import revedaEditor.backend.libraryModelView as lmview
import revedaEditor.common.labels as lbl
import revedaEditor.common.net as snet
import revedaEditor.common.shapes as shp
from revedaEditor.connectivity import (Port, Seg, checkRecords, netexpr,
                                       resolve, terminalBinds)
from revedaEditor.netlisting import exprSupport
from revedaEditor.netlisting.xyceNetlist import xyceNetlist
from revedaEditor.tests.sceneTestUtils import makeSchematicScene


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


# --- expression parsing ------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("[@vdd]", ("vdd", "")),
    ("[@vdd:vdd!]", ("vdd", "vdd!")),
    ("[@vdd : vdd! ]", ("vdd", "vdd!")),
    ("[@avss:0]", ("avss", "0")),
    ("[@data<0:3>]", ("data<0:3>", "")),
])
def test_parse_netexpr(text, expected):
    assert netexpr.parseNetExpr(text) == expected


@pytest.mark.parametrize("text", [
    "", "vdd", "vdd!", "[vdd]", "[@]", "[@vdd", "@vdd]", "[@@vdd]",
    None, 42,
])
def test_parse_netexpr_rejects(text):
    assert netexpr.parseNetExpr(text) is None


def test_eval_netexpr_binding_wins():
    binds = {"vdd": "AVDD"}
    assert netexpr.evalNetExpr("[@vdd:vdd!]", binds) == "AVDD"
    assert netexpr.evalNetExpr("[@vdd]", binds) == "AVDD"


def test_eval_netexpr_default_then_bare_name():
    assert netexpr.evalNetExpr("[@vdd:vdd!]", {}) == "vdd!"
    assert netexpr.evalNetExpr("[@vdd:vdd!]") == "vdd!"
    assert netexpr.evalNetExpr("[@vdd]") == "vdd"
    assert netexpr.evalNetExpr("not-an-expr") is None


@pytest.mark.parametrize("value,expected", [
    ({"vdd": "AVDD"}, {"vdd": "AVDD"}),
    ("vdd=AVDD;avss=AVSS", {"vdd": "AVDD", "avss": "AVSS"}),
    ("vdd=AVDD,avss=AVSS", {"vdd": "AVDD", "avss": "AVSS"}),
    ('{"vdd": "AVDD"}', {"vdd": "AVDD"}),
    ("", {}), (None, {}), (["vdd"], {}), ("noequals", {}),
])
def test_parse_netset(value, expected):
    assert netexpr.parseNetSet(value) == expected


def test_format_netset_roundtrip():
    text = netexpr.formatNetSet({"vdd": "AVDD", "avss": "0"})
    assert netexpr.parseNetSet(text) == {"vdd": "AVDD", "avss": "0"}


def test_terminal_binds_and_instance_nets():
    assert terminalBinds(["vdd"]) == {"vdd": "vdd"}
    defs = {"vdd": "vdd!", "avss": ""}
    # instanceExprNets: netSet override > default > bare name
    assert netexpr.instanceExprNets({"vdd": "AVDD"}, defs) == {
        "vdd": "AVDD", "avss": "avss"}
    assert netexpr.instanceExprNets({}, defs) == {
        "vdd": "vdd!", "avss": "avss"}


def test_expr_names_from_records():
    records = [
        {"type": "scn", "st": [0, 0], "end": [10, 0], "nam": "", "ns": 0,
         "nx": "[@vdd:vdd!]"},
        {"type": "scp", "st": [0, 0], "pn": "in", "pd": "Input",
         "pt": "Signal", "nx": "[@bias]"},
        {"type": "scn", "st": [20, 0], "end": [30, 0], "nam": "", "ns": 0},
    ]
    defs, problems = netexpr.exprNamesFromRecords(records)
    assert defs == {"vdd": "vdd!", "bias": ""}
    assert problems == []


def test_expr_names_from_records_via_pin_locator():
    def locator(lib, cell, view):
        return {"p": (0, 0), "pinExprs": {"bias": "[@bias:BIAS]"}}
    records = [{"type": "sys", "lib": "L", "cell": "C", "view": "symbol",
                "nam": "I0", "ld": {}, "loc": [0, 0]}]
    defs, problems = netexpr.exprNamesFromRecords(records, locator)
    assert defs == {"bias": "BIAS"}
    assert problems == []


def test_expr_names_conflicting_defaults():
    defs, problems = netexpr.exprNamesFromRecords([
        {"type": "scn", "st": [0, 0], "end": [10, 0], "nam": "", "ns": 0,
         "nx": "[@vdd:vdd!]"},
        {"type": "scn", "st": [0, 10], "end": [10, 10], "nam": "", "ns": 0,
         "nx": "[@vdd:AVDD]"},
    ])
    assert defs == {"vdd": "vdd!"}  # first default wins, deterministic
    assert any("conflicting defaults" in p for p in problems)


# --- resolve() integration ---------------------------------------------------

def _segs(*defs):
    """defs: (id, p1, p2, name, strength, expr)."""
    return [Seg(id=i, p1=p1, p2=p2, name=name, strength=strength, expr=expr)
            for i, p1, p2, name, strength, expr in defs]


def test_resolve_expr_default_names_group():
    """A wire carrying [@vdd:vdd!] resolves to the default global."""
    segs = _segs((0, (0, 0), (10, 0), "", 0, "[@vdd:vdd!]"))
    result = resolve(segs, [])
    assert result.exprNames == {"vdd": "vdd!"}
    assert result.segName[0] == ("vdd!", 3)  # SET — behaves like a global pin
    assert not result.conflicts


def test_resolve_expr_netset_override():
    """netSet binding beats the expression default."""
    segs = _segs((0, (0, 0), (10, 0), "", 0, "[@vdd:vdd!]"))
    result = resolve(segs, [], netSet={"vdd": "AVDD"})
    # plain (non-'!') result asserts a pin-tier name
    assert result.segName[0] == ("AVDD", 2)  # INHERIT
    assert result.exprNames == {"vdd": "vdd!"}


def test_resolve_expr_terminal_mode():
    """Identity binding (subcircuit definition context) names the net 'vdd'."""
    segs = _segs((0, (0, 0), (10, 0), "", 0, "[@vdd:vdd!]"))
    result = resolve(segs, [], netSet=terminalBinds(["vdd"]))
    assert result.segName[0] == ("vdd", 2)


def test_resolve_expr_bare_name_connect_by_name():
    segs = _segs((0, (0, 0), (10, 0), "", 0, "[@vdd]"))
    result = resolve(segs, [])
    assert result.segName[0] == ("vdd", 2)


def test_resolve_malformed_expr_diagnostic():
    segs = _segs((0, (0, 0), (10, 0), "", 0, "[vdd]"))
    result = resolve(segs, [])
    assert any(c.kind == "badNetExpr" for c in result.conflicts)
    # malformed expr contributes nothing — net falls back to auto naming
    assert result.segName[0][0].startswith("net")


def test_resolve_no_exprs_unchanged():
    """No-expression scenes behave exactly as before (auto net<N>)."""
    segs = _segs((0, (0, 0), (10, 0), "", 0, ""),
                 (1, (0, 10), (10, 10), "named", 3, ""))
    result = resolve(segs, [])
    assert result.exprNames == {}
    assert result.segName[0] == ("net0", 1)   # WEAK auto name
    assert result.segName[1] == ("named", 3)  # SET
    assert result.autoCount == 1


def test_resolve_expr_vs_set_conflict():
    """An expr resolving to a name different from a SET wire name shorts."""
    segs = _segs((0, (0, 0), (10, 0), "other", 3, ""),
                 (1, (10, 0), (20, 0), "", 0, "[@vdd:AVDD]"))
    result = resolve(segs, [])
    assert any(c.kind == "netNameConflict" for c in result.conflicts)


def test_resolve_expr_on_port():
    """Expression on a symbol pin resolves even when the pin is floating."""
    ports = [Port(id=0, name="bias", direction="Input", point=(5, 5),
                  kind="symbolPin", owner="I0", expr="[@bias:BIAS_NET]")]
    result = resolve(_segs((0, (0, 0), (10, 0), "", 0, "")), ports)
    assert result.portExprNet[0] == "BIAS_NET"
    assert result.segName[0] == ("BIAS_NET", 2)


def test_resolve_expr_port_overrides_set_global():
    ports = [Port(id=0, name="x", direction="Input", point=(5, 5),
                  kind="symbolPin", owner="I0", expr="[@vdd:vdd!]")]
    result = resolve([], ports, netSet={"vdd": "vdd!"})
    assert result.portExprNet[0] == "vdd!"


def test_resolve_symbol_pin_expr_uses_instance_netset():
    """A floating pin's [@vdd] resolves via its owning instance's netSet;
    the sheet-level binding cascades underneath as fallback."""
    port = Port(id=0, name="bias", direction="Input", point=(5, 5),
                kind="symbolPin", owner="I0", expr="[@vdd:vdd!]",
                netSet={"vdd": "LOCAL_VDD"})
    # Instance netSet wins over both the default and the sheet binding.
    assert resolve([], [port]).portExprNet[0] == "LOCAL_VDD"
    assert resolve([], [port],
                   netSet={"vdd": "SHEET_VDD"}).portExprNet[0] == "LOCAL_VDD"
    # Without an instance override the sheet binding cascades through.
    portNoSet = Port(id=0, name="bias", direction="Input", point=(5, 5),
                     kind="symbolPin", owner="I0", expr="[@vdd:vdd!]")
    assert resolve([], [portNoSet],
                   netSet={"vdd": "SHEET_VDD"}).portExprNet[0] == "SHEET_VDD"


# --- record adapter (nx/nst) -------------------------------------------------

def test_from_records_expr_fields():
    records = [
        {"type": "scn", "st": [0, 0], "end": [100, 0], "nam": "", "ns": 0,
         "nx": "[@vdd:vdd!]"},
        {"type": "scp", "st": [0, 0], "pn": "in", "pd": "Input",
         "pt": "Signal", "nx": "[@bias]"},
    ]
    result, _diags = checkRecords(records)
    assert result.exprNames == {"vdd": "vdd!", "bias": ""}
    # scp pin is at (0,0) — attaches to the same group as the wire;
    # the !-resolved expression names it vdd!
    names = {name for name, _s in result.segName.values()}
    assert "vdd!" in names


def test_from_records_netset_override():
    records = [
        {"type": "scn", "st": [0, 0], "end": [100, 0], "nam": "", "ns": 0,
         "nx": "[@vdd:vdd!]"},
    ]
    result, _diags = checkRecords(records, netSet={"vdd": "AVDD"})
    assert result.segName[0] == ("AVDD", 2)


def test_check_records_expr_diagnostics():
    records = [
        {"type": "scn", "st": [0, 0], "end": [10, 0], "nam": "", "ns": 0,
         "nx": "[bad]"},
    ]
    _result, diags = checkRecords(records)
    assert any("Malformed net expression" in d.message for d in diags)


# --- persistence round trip ---------------------------------------------------

def test_schematic_encoder_expr_fields(qapp):
    from revedaEditor.fileio.schematicEncoder import schematicEncoder
    scene = makeSchematicScene()
    netItem = snet.schematicNet(QPoint(0, 0), QPoint(100, 0))
    netItem.netExpr = "[@vdd:vdd!]"
    pinItem = shp.schematicPin(QPoint(0, 0), "in", "Input", "Signal")
    pinItem.netExpr = "[@bias:BIAS]"
    symItem = shp.schematicSymbol([], {})
    symItem.libraryName = "L"
    symItem.cellName = "C"
    symItem.viewName = "symbol"
    symItem.instanceName = "I0"
    symItem.netSet = {"vdd": "AVDD"}
    for item in (netItem, pinItem, symItem):
        scene.addItem(item)
    netRec = json.loads(json.dumps(netItem, cls=schematicEncoder))
    pinRec = json.loads(json.dumps(pinItem, cls=schematicEncoder))
    symRec = json.loads(json.dumps(symItem, cls=schematicEncoder))
    assert netRec["nx"] == "[@vdd:vdd!]"
    assert pinRec["nx"] == "[@bias:BIAS]"
    assert symRec["nst"] == {"vdd": "AVDD"}


def test_schematic_encoder_omits_empty_expr(qapp):
    """No nx/nst keys when expressions are unset — old readers unaffected."""
    from revedaEditor.fileio.schematicEncoder import schematicEncoder
    scene = makeSchematicScene()
    netItem = snet.schematicNet(QPoint(0, 0), QPoint(100, 0))
    scene.addItem(netItem)
    record = json.loads(json.dumps(netItem, cls=schematicEncoder))
    assert "nx" not in record


def test_symbol_encoder_pin_nx(qapp):
    from revedaEditor.fileio.symbolEncoder import symbolEncoder
    scene = makeSchematicScene()
    pin = shp.symbolPin(QPoint(0, 0), "vdd", "Inout", "Signal")
    pin.netExpr = "[@vdd:vdd!]"
    scene.addItem(pin)
    record = json.loads(json.dumps(pin, cls=symbolEncoder))
    assert record["nx"] == "[@vdd:vdd!]"


def test_loadjson_decodes_expr_fields(qapp):
    """nx on scn/scp records and nst on sys records reach live items."""
    from revedaEditor.fileio.loadJSON import schematicItems
    scene = makeSchematicScene()
    loader = schematicItems(scene)
    netItem = loader._createNet(
        {"type": "scn", "st": [0, 0], "end": [100, 0], "nam": "", "ns": 0,
         "nx": "[@vdd:vdd!]"})
    assert netItem.netExpr == "[@vdd:vdd!]"
    pinItem = loader._createPin(
        {"type": "scp", "st": [0, 0], "pn": "in", "pd": "Input",
         "pt": "Signal", "nx": "[@bias]"})
    assert pinItem.netExpr == "[@bias]"
    symItem = loader._createSymbolShape(
        {"type": "sys", "lib": "missing", "cell": "C", "view": "symbol",
         "nam": "I0", "ic": 0, "ld": {}, "loc": [0, 0], "br": [0, 0, 50, 50],
         "nst": {"vdd": "AVDD"}})
    assert symItem.netSet == {"vdd": "AVDD"}


def test_loadjson_legacy_records_no_expr(qapp):
    """Records without nx/nst decode with empty expression state."""
    from revedaEditor.fileio.loadJSON import schematicItems
    scene = makeSchematicScene()
    loader = schematicItems(scene)
    netItem = loader._createNet(
        {"type": "scn", "st": [0, 0], "end": [100, 0], "nam": "", "ns": 0})
    assert netItem.netExpr == ""
    pinItem = loader._createPin(
        {"type": "scp", "st": [0, 0], "pn": "in", "pd": "Input",
         "pt": "Signal"})
    assert pinItem.netExpr == ""
    symItem = loader._createSymbolShape(
        {"type": "sys", "lib": "missing", "cell": "C", "view": "symbol",
         "nam": "I0", "ic": 0, "ld": {}, "loc": [0, 0], "br": [0, 0, 50, 50]})
    assert symItem.netSet == {}


# --- scene integration ---------------------------------------------------------

def _addNet(scene, x1, y1, x2, y2, expr=""):
    netItem = snet.schematicNet(QPoint(x1, y1), QPoint(x2, y2))
    netItem.netExpr = expr
    scene.addItem(netItem)
    return netItem


def test_scene_collect_net_expr_names(qapp):
    scene = makeSchematicScene()
    _addNet(scene, 0, 0, 100, 0, "[@vdd:vdd!]")
    pin = shp.schematicPin(QPoint(0, 50), "in", "Input", "Signal")
    pin.netExpr = "[@bias]"
    scene.addItem(pin)
    assert scene.collectNetExprNames() == {"vdd": "vdd!", "bias": ""}


def test_scene_names_nets_with_expr_default(qapp):
    """[@vdd:vdd!] on a wire resolves to the vdd! global, SET strength."""
    scene = makeSchematicScene()
    netItem = _addNet(scene, 0, 0, 100, 0, "[@vdd:vdd!]")
    scene.nameSceneNets()
    assert netItem.name == "vdd!"
    assert netItem.nameStrength == snet.netNameStrengthEnum.SET


def test_scene_names_nets_with_netset(qapp):
    scene = makeSchematicScene()
    netItem = _addNet(scene, 0, 0, 100, 0, "[@vdd:vdd!]")
    scene.nameSceneNets(netSet={"vdd": "AVDD"})
    assert netItem.name == "AVDD"


def test_scene_names_nets_terminal_mode(qapp):
    scene = makeSchematicScene()
    netItem = _addNet(scene, 0, 0, 100, 0, "[@vdd:vdd!]")
    scene.nameSceneNets(netSet=terminalBinds(["vdd"]))
    assert netItem.name == "vdd"


def test_scene_no_exprs_unchanged(qapp):
    """nameSceneNets output is identical when no expressions are present."""
    scene = makeSchematicScene()
    auto = _addNet(scene, 0, 0, 100, 0)
    named = _addNet(scene, 0, 100, 100, 100)
    named.name = "mysig"
    named.nameStrength = snet.netNameStrengthEnum.SET
    scene.nameSceneNets()
    assert auto.name == "net0"
    assert named.name == "mysig"


def test_toggle_resolved_names_visibility(qapp):
    scene = makeSchematicScene()
    auto = _addNet(scene, 0, 0, 100, 0)
    scene.nameSceneNets()
    assert not auto.nameItem.isVisible()  # auto name hidden by default
    scene.toggleResolvedNames(True)
    assert auto.nameItem.isVisible()
    scene.toggleResolvedNames(False)
    assert not auto.nameItem.isVisible()


# --- netlister: two-level netSet acceptance ---------------------------------

def _writeJson(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(records).encode())


def _symbolJson(pins, pinOrder, cellName):
    """Minimal symbol view: pins + instName label + pinOrder/line attrs.

    Emits the netlist-line template for all three backends so one fixture
    exercises xyce, spectre and vacask identically.
    """
    records = [
        {"viewType": "symbol", "schemaVersion": "1.0"},
        {},
        {"type": "label", "st": [0, 0], "nam": "@instName",
         "def": "[@instName]",
         "txt": "?", "val": "I0", "vis": True, "lt": "NLPLabel", "ht": 12,
         "al": "Left", "or": "R0", "use": "Normal", "loc": [0, 0],
         "fl": [1, 1]},
        {"type": "attr", "nam": "pinOrder", "def": pinOrder},
        {"type": "attr", "nam": "SpiceNetlistLine",
         "def": f"X@instName %pinOrder {cellName}"},
        {"type": "attr", "nam": "SpectreNetlistLine",
         "def": f"X@instName (%pinOrder) {cellName}"},
        {"type": "attr", "nam": "VacaskNetlistLine",
         "def": f"X@instName (%pinOrder) {cellName}"},
    ]
    for name, x, y in pins:
        records.append({"type": "pin", "st": [0, 0], "nam": name,
                        "pd": "Inout", "pt": "Signal", "loc": [x, y],
                        "ang": 0, "fl": [1, 1]})
    return records


def _schematicPinRecord(name, x, y):
    return {"type": "scp", "st": [x, y], "pn": name, "pd": "Inout",
            "pt": "Signal", "ang": 0, "fl": [1, 1]}


def _wireRecord(x1, y1, x2, y2, nx=None):
    rec = {"type": "scn", "st": [x1, y1], "end": [x2, y2], "nam": "",
           "ns": 0}
    if nx:
        rec["nx"] = nx
    return rec


def _sysRecord(lib, cell, instName, x, y, nst=None, ld=None):
    rec = {"type": "sys", "lib": lib, "cell": cell, "view": "symbol",
           "nam": instName, "ic": 0, "ld": ld or {"@instName": [instName, True]},
           "loc": [x, y], "ang": 0, "ign": 0, "br": [0, 0, 100, 100],
           "fl": [1, 1]}
    if nst:
        rec["nst"] = nst
    return rec


@pytest.fixture
def exprLibrary(tmp_path):
    """Two-level library: top -> mid -> diffpair, vdd bound via netSet.

    - diffpair schematic carries wire ``[@vdd:vdd!]`` — implicit terminal
      ``vdd`` defaulting to the ``vdd!`` global.
    - mid schematic wires instance I2 of diffpair between its in/out pins,
      declares its own ``[@vdd]`` terminal, and binds I2's ``vdd`` to it.
    - top wires instance I1 of mid between tin/tout and binds ``vdd`` to
      ``vdd!``.
    """
    libPath = tmp_path / "exprLib"
    libPath.joinpath("reveda.lib").parent.mkdir(parents=True, exist_ok=True)
    libPath.joinpath("reveda.lib").write_text("")

    # diffpair: symbol pins p (0,0) / n (0,100); schematic declares vdd expr.
    _writeJson(libPath / "diffpair" / "symbol.json",
               _symbolJson((("p", 0, 0), ("n", 0, 100)), "p,n",
                           "diffpair"))
    _writeJson(libPath / "diffpair" / "schematic.json", [
        {"viewType": "schematic", "schemaVersion": "1.0"}, {},
        _schematicPinRecord("p", 0, 0), _schematicPinRecord("n", 0, 100),
        _wireRecord(0, 0, 100, 0), _wireRecord(0, 100, 100, 100),
        _wireRecord(50, 50, 50, 150, nx="[@vdd:vdd!]"),
    ])

    # mid: symbol pins in/out; schematic instantiates diffpair bound to its
    # own [@vdd] terminal.
    _writeJson(libPath / "mid" / "symbol.json",
               _symbolJson((("in", 0, 0), ("out", 0, 100)), "in,out",
                           "mid"))
    _writeJson(libPath / "mid" / "schematic.json", [
        {"viewType": "schematic", "schemaVersion": "1.0"}, {},
        _schematicPinRecord("in", 0, 0), _schematicPinRecord("out", 0, 100),
        _wireRecord(0, 0, 100, 0), _wireRecord(0, 100, 100, 100),
        _wireRecord(50, 150, 50, 250, nx="[@vdd]"),
        _sysRecord("exprLib", "diffpair", "I2", 100, 0, nst={"vdd": "vdd"}),
    ])

    # top: I1 of mid, vdd bound to the vdd! global.
    _writeJson(libPath / "top" / "schematic.json", [
        {"viewType": "schematic", "schemaVersion": "1.0"}, {},
        _schematicPinRecord("tin", 0, 0), _schematicPinRecord("tout", 0, 100),
        _wireRecord(0, 0, 100, 0), _wireRecord(0, 100, 100, 100),
        _sysRecord("exprLib", "mid", "I1", 100, 0, nst={"vdd": "vdd!"}),
    ])
    return {"exprLib": libPath}


class _MiniSchematicEditor:
    """Duck-typed schematicEditor: real scene + real loadDesign, no window."""

    def __init__(self, viewItem, libraryDict, libraryView):
        self.viewItem = viewItem
        self.libraryDict = libraryDict
        self.libraryView = libraryView
        self.libName = viewItem.parent().parent().libraryName
        self.cellName = viewItem.parent().cellName
        self.viewName = viewItem.viewName
        self.file = pathlib.Path(viewItem.viewPath)
        self.centralW = types.SimpleNamespace(scene=None)

    def loadSchematic(self, register: bool = True):
        scene = makeSchematicScene()
        scene.libraryDict = self.libraryDict
        scene.loadDesign(self.file)
        self.centralW.scene = scene


def _miniEditorFactory(libraryDict, libraryView):
    def factory(viewItem, _ld, _lv):
        return _MiniSchematicEditor(viewItem, libraryDict, libraryView)
    return factory


def test_expr_defs_for_schematic_view(qapp, exprLibrary):
    model = lmview.designLibrariesModel(exprLibrary)
    libItem = libm.getLibItem(model, "exprLib")
    diffpair = libm.getCellItem(libItem, "diffpair")
    defs = exprSupport.exprDefsForSchematicView(
        diffpair, "schematic", exprLibrary)
    assert defs == {"vdd": "vdd!"}
    mid = libm.getCellItem(libItem, "mid")
    assert exprSupport.exprDefsForSchematicView(
        mid, "schematic", exprLibrary) == {"vdd": ""}


def test_expr_support_instance_nets():
    symbol = types.SimpleNamespace(netSet={"vdd": "vdd!"})
    assert exprSupport.exprNetsForInstance(symbol, {"vdd": ""}) == ["vdd!"]
    assert exprSupport.exprTerminals({"vdd": "", "avss": "gnd!"}) == [
        "avss", "vdd"]
    assert exprSupport.terminalNetSet({"vdd": ""}) == {"vdd": "vdd"}
    assert exprSupport.globalNets({"vdd": ""}, {"vdd": "vdd!"}) == {"vdd!"}
    assert exprSupport.globalNets({"vdd": ""}, {"vdd": "vdd"}) == set()


def _runNetlister(nlClass, exprLibrary, tmp_path, monkeypatch, name):
    """Run a netlister over the exprLibrary top cell; return output text."""
    import revedaEditor.gui.schematicEditor as schEditorModule

    model = lmview.designLibrariesModel(exprLibrary)
    libraryView = types.SimpleNamespace(libraryModel=model)
    monkeypatch.setattr(schEditorModule, "schematicEditor",
                        _miniEditorFactory(exprLibrary, libraryView))

    # Top-level scene loaded for real from the on-disk top cell.
    topScene = makeSchematicScene()
    topScene.libraryDict = exprLibrary
    topScene.loadDesign(exprLibrary["exprLib"] / "top" / "schematic.json")

    topEditor = types.SimpleNamespace(
        centralW=types.SimpleNamespace(scene=topScene),
        libraryDict=exprLibrary, libraryView=libraryView,
        libName="exprLib", cellName="top", viewName="schematic",
        switchViewList=["schematic", "symbol"], stopViewList=["symbol"])

    outFile = tmp_path / name
    nlClass(topEditor, outFile).writeNetlist()
    return outFile.read_text()


def test_two_level_netset_netlist_xyce(qapp, exprLibrary, tmp_path,
                                       monkeypatch):
    """Acceptance: vdd! reaches diffpair's implicit terminal through two
    hierarchy levels — top binds mid's vdd->vdd!, mid binds diffpair's
    vdd->vdd (its own terminal)."""
    text = _runNetlister(xyceNetlist, exprLibrary, tmp_path, monkeypatch,
                         "top.cir")

    # I1 supplies mid's implicit vdd terminal with the vdd! global.
    assert "XI1 tin tout vdd! mid" in text
    # mid's subckt declares the vdd implicit terminal.
    assert ".SUBCKT mid in out vdd" in text
    # Inside mid, I2's vdd terminal binds to mid's local 'vdd' net.
    assert "XI2 in out vdd diffpair" in text
    # diffpair's subckt declares its own vdd implicit terminal.
    assert ".SUBCKT diffpair p n vdd" in text
    # The vdd! global resolved from the netSet binding is declared.
    assert ".GLOBAL vdd!" in text


def test_two_level_netset_netlist_spectre(qapp, exprLibrary, tmp_path,
                                          monkeypatch):
    from revedaEditor.netlisting.spectreNetlist import spectreNetlist
    text = _runNetlister(spectreNetlist, exprLibrary, tmp_path, monkeypatch,
                         "top.scs")

    # Spectre instance syntax: instName (nets) cellName; '!' nets are
    # global by convention (no declaration needed).
    assert "XI1 (tin tout vdd!) mid" in text
    assert "subckt mid in out vdd" in text
    assert "XI2 (in out vdd) diffpair" in text
    assert "subckt diffpair p n vdd" in text


def test_two_level_netset_netlist_vacask(qapp, exprLibrary, tmp_path,
                                         monkeypatch):
    from revedaEditor.netlisting.vacaskNetlist import vacaskNetlist
    text = _runNetlister(vacaskNetlist, exprLibrary, tmp_path, monkeypatch,
                         "top.va")

    # VACASK strips '!' and declares globals explicitly: vdd! -> vdd.
    assert "XI1 (tin tout vdd) mid" in text
    assert "global vdd" in text
    assert "subckt mid ( in out vdd )" in text
    assert "XI2 (in out vdd) diffpair" in text
    assert "subckt diffpair ( p n vdd )" in text
