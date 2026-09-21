"""Phase 4 schematic UX: find/replace, marker persistence, bus ripper,
clipboard paste, and descend edit-in-place."""

import json

import orjson
import pytest
from PySide6.QtCore import QPoint, QRectF
from PySide6.QtGui import QGuiApplication

import revedaEditor.checks.schematic as schk
import revedaEditor.common.net as snet
import revedaEditor.common.shapes as shp
from revedaEditor.tests.sceneTestUtils import makeSchematicScene


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def _net(scene, p1, p2, name="", width=0):
    item = snet.schematicNet(p1, p2, width, snet.NetMode.ORTHOGONAL)
    scene.addItem(item)
    if name:
        item.name = name
    return item


def _symbol(scene, name="I1", pos=None, libName="lib",
            cellName="cell"):
    item = shp.schematicSymbol([], {"instName": "[@instName]"})
    item.libraryName = libName
    item.cellName = cellName
    item.viewName = "symbol"
    item.instanceName = name
    item.setPos(pos if pos is not None else QPoint(0, 0))
    scene.addItem(item)
    return item


# --------------------------------------------------------------------------
# find / replace
# --------------------------------------------------------------------------

def test_find_nets_by_resolved_name(qapp):
    scene = makeSchematicScene()
    _net(scene, QPoint(0, 0), QPoint(100, 0), "sig_a")
    _net(scene, QPoint(100, 0), QPoint(100, 100))  # joined, same net
    _net(scene, QPoint(0, 50), QPoint(50, 50), "sig_b")
    hits = scene.findItems("net", "sig_*")
    byName = {h.name: h for h in hits}
    assert set(byName) == {"sig_a", "sig_b"}
    assert len(byName["sig_a"].items) == 2  # both member segments


def test_find_instances_and_prop_filter(qapp):
    scene = makeSchematicScene()
    # Keep Python refs: an unreferenced wrapper may be GC'd, removing the
    # item from the scene mid-test.
    _i1 = _symbol(scene, "I1")
    _i2 = _symbol(scene, "I2")
    _x1 = _symbol(scene, "X1")
    hits = scene.findItems("instance", "I*")
    assert {h.name for h in hits} == {"I1", "I2"}
    # property filter on cell name
    hits = scene.findItems("instance", "*", "cell=cell")
    assert len(hits) == 3
    hits = scene.findItems("instance", "*", "cell=other")
    assert hits == []


def test_find_pins(qapp):
    scene = makeSchematicScene()
    pin = shp.schematicPin(QPoint(0, 0), "data<0:3>", "Input", "Signal")
    scene.addItem(pin)
    assert [h.name for h in scene.findItems("pin", "data*")] == ["data<0:3>"]
    assert scene.findItems("pin", "clk*") == []


def test_replace_hit_renames_all_net_segments(qapp):
    scene = makeSchematicScene()
    n1 = _net(scene, QPoint(0, 0), QPoint(100, 0), "old")
    n2 = _net(scene, QPoint(100, 0), QPoint(100, 100))
    hit = next(iter(scene.findItems("net", "old")))
    new = scene.replaceHitName(hit, "old", "new_net")
    assert new == "new_net"
    assert n1.name == "new_net" and n2.name == "new_net"


def test_replace_instance_and_pin(qapp):
    scene = makeSchematicScene()
    inst = _symbol(scene, "I1")
    pin = shp.schematicPin(QPoint(0, 0), "in", "Input", "Signal")
    scene.addItem(pin)
    hit = next(iter(scene.findItems("instance", "I1")))
    assert scene.replaceHitName(hit, "I", "X") == "X1"
    assert inst.instanceName == "X1"
    hit = next(iter(scene.findItems("pin", "in")))
    assert scene.replaceHitName(hit, "in", "clk") == "clk"
    assert pin.pinName == "clk"


# --------------------------------------------------------------------------
# marker persistence
# --------------------------------------------------------------------------

def test_marker_records_roundtrip(qapp, tmp_path):
    scene = makeSchematicScene()
    _net(scene, QPoint(0, 0), QPoint(100, 0))
    scene.lastCheckViolations = [schk.checkViolation(
        ruleId="danglingWireEnd", severity=schk.checkSeverity.WARNING,
        message="wire end dangling", markers=[QRectF(95, -5, 10, 10)])]
    file = tmp_path / "schematic.json"
    scene.saveSchematic(file)
    records = json.loads(file.read_text())
    mrk = [r for r in records if r.get("type") == "mrk"]
    assert len(mrk) == 1
    assert mrk[0]["rule"] == "danglingWireEnd"
    assert mrk[0]["sev"] == "warning"

    scene2 = makeSchematicScene()
    scene2.editorWindow.configureGridSettings = lambda *a: None
    scene2.loadDesign(file)
    assert len(scene2.lastCheckViolations) == 1
    assert scene2.lastCheckViolations[0].ruleId == "danglingWireEnd"
    assert len(scene2.overlapRectSet) == 1


# --------------------------------------------------------------------------
# bus ripper
# --------------------------------------------------------------------------

def test_bus_rip_off_trunk(qapp):
    scene = makeSchematicScene()
    _net(scene, QPoint(0, 0), QPoint(200, 0), "d<0:3>", width=1)
    scene.editModes.setMode("drawWire")
    scene._busRipIndex = 2
    scene._handleDrawNet(QPoint(50, 0), width=0)
    assert scene._wirePendingName == "d<2>"
    scene._handleDrawNet(QPoint(50, 80), width=0)
    scene._finishWire()
    names = sorted(n.name for n in scene.findSceneNetsSet())
    assert names.count("d<0:3>") == 2  # pierced trunk halves keep bus name
    assert "d<2>" in names


def test_bus_rip_off_bus_pin(qapp):
    scene = makeSchematicScene()
    pin = shp.schematicPin(QPoint(0, 0), "q<0:1>", "Input", "Signal")
    pin.setPos(QPoint(300, 0))
    scene.addItem(pin)
    scene.editModes.setMode("drawWire")
    scene._busRipIndex = 0
    scene._handleDrawNet(QPoint(300, 0), width=0)
    assert scene._wirePendingName == "q<0>"
    scene._finishWire()


def test_no_rip_on_plain_net(qapp):
    scene = makeSchematicScene()
    _net(scene, QPoint(0, 0), QPoint(200, 0), "plain")
    scene.editModes.setMode("drawWire")
    scene._handleDrawNet(QPoint(50, 0), width=0)
    assert scene._wirePendingName == ""
    scene._finishWire()


def test_bus_rip_descending_trunk(qapp):
    """Buses like d<7:0> must rip the same way ascending ones do."""
    scene = makeSchematicScene()
    _net(scene, QPoint(0, 0), QPoint(200, 0), "d<7:0>", width=1)
    scene.editModes.setMode("drawWire")
    scene._busRipIndex = 2
    scene._handleDrawNet(QPoint(50, 0), width=0)
    assert scene._wirePendingName == "d<2>"
    scene._handleDrawNet(QPoint(50, 80), width=0)
    scene._finishWire()
    names = sorted(n.name for n in scene.findSceneNetsSet())
    assert names.count("d<7:0>") == 2
    assert "d<2>" in names


def test_bus_rip_descending_index_bounds(qapp):
    """The one-shot index is validated against min/max, not lo<=x<=hi."""
    scene = makeSchematicScene()
    scene._busRipIndex = 5
    assert scene._busMemberIndex("d", 7, 0) == 5
    scene._busRipIndex = 9
    assert scene._busMemberIndex("d", 7, 0) is None


def test_bus_rip_member_connects_to_bus(qapp):
    """A ripped member wire must resolve onto the bus by namesMatch."""
    scene = makeSchematicScene()
    _net(scene, QPoint(0, 0), QPoint(200, 0), "d<0:3>", width=1)
    member = _net(scene, QPoint(50, 0), QPoint(50, 80), "d<2>")
    result = scene.rebuildConnectivity()
    segId = scene._connectivitySegIdByItem[member]
    name, _ = result.segName[segId]
    assert name == "d<2>"


# --------------------------------------------------------------------------
# clipboard copy/paste
# --------------------------------------------------------------------------

def test_clipboard_copy_paste_roundtrip(qapp):
    scene = makeSchematicScene()
    net = _net(scene, QPoint(0, 0), QPoint(100, 0), "sig")
    net.setSelected(True)
    pin = shp.schematicPin(QPoint(0, 0), "in1", "Input", "Signal")
    pin.setPos(QPoint(50, 50))
    scene.addItem(pin)
    pin.setSelected(True)

    assert scene.copySelectionToClipboard() == 2
    records = json.loads(QGuiApplication.clipboard().text())
    assert {r["type"] for r in records} == {"scn", "scp"}

    scene2 = makeSchematicScene()
    assert scene2.pasteClipboard(QPoint(500, 500)) == 2
    nets = scene2.findSceneNetsSet()
    assert len(nets) == 1
    assert nets.pop().name == "sig"
    pins = scene2.findSceneSchemPinsSet()
    assert len(pins) == 1


def test_paste_rejects_non_fragment_clipboard(qapp):
    scene = makeSchematicScene()
    QGuiApplication.clipboard().setText("not a fragment")
    assert scene.pasteClipboard() == 0
    QGuiApplication.clipboard().setText('[{"type": "unknown"}]')
    assert scene.pasteClipboard() == 0


# --------------------------------------------------------------------------
# descend edit-in-place
# --------------------------------------------------------------------------

def _childLibrary(tmp_path):
    lib = tmp_path / "mylib"
    cell = lib / "child"
    cell.mkdir(parents=True)
    (cell / "schematic.json").write_bytes(orjson.dumps([
        {"viewType": "schematic", "schemaVersion": "1.0"},
        {"snapGrid": [50, 10]},
        {"type": "scn", "st": [0, 0], "end": [100, 0], "nam": "in", "ns": 3},
        {"type": "scp", "st": [0, 0], "pn": "in", "pd": "Input",
         "pt": "Signal"},
    ]))
    (cell / "symbol.json").write_bytes(orjson.dumps([
        {"viewType": "symbol", "schemaVersion": "1.0"},
        {"snapGrid": [50, 10]},
        {"type": "pin", "st": [0, 0], "pn": "in", "pd": "Input",
         "pt": "Signal"},
        {"type": "attr", "nam": "instName", "def": "[@instName]"},
    ]))
    return lib, cell


def test_descend_in_place_ghost_transform(qapp, tmp_path):
    lib, _cell = _childLibrary(tmp_path)
    scene = makeSchematicScene()
    scene.libraryDict = {"mylib": lib}
    inst = _symbol(scene, "I1", QPoint(500, 500), libName="mylib", cellName="child")
    group = scene.descendInPlace(inst)
    assert group is not None
    assert len(group.childItems()) == 2
    # ghost children render at the instance position
    rect = group.childItems()[0].sceneBoundingRect()
    assert rect.left() >= 480 and rect.top() >= 480
    # ghosts are excluded from the parent connectivity and item sets
    assert len(scene.findSceneNetsSet()) == 0
    assert len(scene.findSceneSchemPinsSet()) == 0


def test_descend_in_place_writeback(qapp, tmp_path):
    lib, cell = _childLibrary(tmp_path)
    scene = makeSchematicScene()
    scene.libraryDict = {"mylib": lib}
    inst = _symbol(scene, "I1", QPoint(500, 500), libName="mylib", cellName="child")
    group = scene.descendInPlace(inst)
    childNet = next(c for c in group.childItems()
                    if type(c).__name__ == "schematicNet")
    childNet.name = "renamed_in"
    assert scene.saveInPlaceEdits() == 1
    data = json.loads((cell / "schematic.json").read_text())
    scn = next(r for r in data if r.get("type") == "scn")
    assert scn["nam"] == "renamed_in"
    # child-frame coords are preserved (inverse transform applied)
    assert scn["st"] == [0, 0] and scn["end"] == [100, 0]


def test_ascend_in_place_removes_ghosts(qapp, tmp_path):
    lib, _cell = _childLibrary(tmp_path)
    scene = makeSchematicScene()
    scene.libraryDict = {"mylib": lib}
    inst = _symbol(scene, "I1", QPoint(500, 500), libName="mylib", cellName="child")
    scene.descendInPlace(inst)
    assert len(scene._eipGroups) == 1
    assert scene.ascendInPlace() == 1
    assert len(scene._eipGroups) == 0


# --------------------------------------------------------------------------
# path snap-mode cycling (layout counterpart of wire draw mode)
# --------------------------------------------------------------------------

def test_cycle_path_mode(qapp):
    import revedaEditor.backend.dataDefinitions as ddef
    from revedaEditor.tests.sceneTestUtils import makeLayoutScene
    scene = makeLayoutScene()
    from defaultPDK import layoutLayers as laylyr
    scene.newPathTuple = ddef.layoutPathTuple(
        "p", laylyr.m1Layer_drw, 0, 10.0, 0.0, 0.0)
    scene.cyclePathMode()
    assert scene.newPathTuple.pathMode == 1
    scene.cyclePathMode()
    assert scene.newPathTuple.pathMode == 2
    scene.cyclePathMode()
    assert scene.newPathTuple.pathMode == 0
