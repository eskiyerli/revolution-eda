"""Tests for schematic<->layout correspondence (backend/correspondence.py)
and the layoutScene SDL sync / flyline / cross-probe integration."""

import inspect

import orjson
import pytest
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication

import revedaEditor.backend.correspondence as corr
import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.backend.libBackEnd as libb
from defaultPDK.layoutLayers import m1Layer_drw, pdkAllLayers
from revedaEditor.common import layoutShapes as lshp
from revedaEditor.tests.sceneTestUtils import makeLayoutScene


@pytest.fixture(scope="module", autouse=True)
def init_qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


M1_LN = pdkAllLayers.index(m1Layer_drw)
SRC = ("mylib", "top", "schematic")


def _sysRecord(name, cell="sub", lib="mylib", labels=None, **kw):
    rec = {"type": "sys", "nam": name, "lib": lib, "cell": cell,
           "view": "symbol", "ic": 1, "loc": (0, 0), "ang": 0,
           "fl": (1, 1), "ld": labels or {}}
    rec.update(kw)
    return rec


def _desc(name, cell, sdl=None, tag=None):
    return {"item": tag if tag is not None else name,
            "name": name, "cell": cell, "sdl": sdl}


# --- pure record-level engine -----------------------------------------------


def test_schematicInstances_extracts_sys_records():
    records = [{"viewType": "schematic"}, {"snapGrid": [10, 10]},
               _sysRecord("M1"), _sysRecord("M2", cell="other"),
               {"type": "scn", "nam": "notaninst"}]
    insts = corr.schematicInstances(records)
    assert set(insts) == {"M1", "M2"}
    assert insts["M1"]["cell"] == "sub"


def test_sdl_source_canonical_and_legacy_shapes():
    sdl = corr.makeSdlSource(*SRC, "M1", {"w": ["1u", True]})
    assert corr.sdlInstName(sdl) == "M1"
    assert corr.sdlSourceKey(sdl) == SRC
    assert corr.sdlLabels(sdl) == {"w": ["1u", True]}
    # Pre-persistence in-memory shape: referenced-cell keys, no source.
    legacy = {"schematicLib": "mylib", "schematicCell": "sub",
              "schematicInstance": "M2"}
    assert corr.sdlInstName(legacy) == "M2"
    assert corr.sdlSourceKey(legacy) is None
    assert corr.sdlInstName(None) == ""
    assert corr.sdlSourceKey(None) is None
    assert corr.sdlLabels(None) == {}


def test_diff_adds_missing_and_keeps_matched():
    sch = {"M1": _sysRecord("M1"), "M2": _sysRecord("M2")}
    existing = [_desc("I1", "sub", corr.makeSdlSource(*SRC, "M1", {}))]
    plan = corr.correspondenceDiff(sch, existing, SRC)
    assert [r["nam"] for r in plan.to_add] == ["M2"]
    assert not plan.to_remove and not plan.to_update and not plan.adopted


def test_diff_removes_vanished_source_instances():
    gone = _desc("I1", "sub", corr.makeSdlSource(*SRC, "M1", {}))
    plan = corr.correspondenceDiff({}, [gone], SRC)
    assert plan.to_remove == [gone]
    assert not plan.to_add


def test_diff_flags_label_drift():
    sdl = corr.makeSdlSource(*SRC, "M1", {"w": ["1u", True]})
    sch = {"M1": _sysRecord("M1", labels={"w": ["2u", True]})}
    plan = corr.correspondenceDiff(sch, [_desc("I1", "sub", sdl)], SRC)
    assert len(plan.to_update) == 1
    assert plan.to_update[0][1] is sch["M1"]


def test_diff_adopts_matching_unsourced_and_skips_foreign():
    sch = {"M1": _sysRecord("M1", cell="sub")}
    orphan = _desc("M1", "sub")
    foreign = _desc("M2", "sub",
                    corr.makeSdlSource("other", "top2", "schematic",
                                       "M2", {}))
    stray = _desc("X9", "othercell")
    plan = corr.correspondenceDiff(sch, [orphan, foreign, stray], SRC)
    assert plan.adopted == [(orphan, sch["M1"])]
    assert not plan.to_remove
    # Adopted instance consumed the schematic record — nothing to add.
    assert not plan.to_add


def test_diff_wrong_cell_does_not_adopt():
    sch = {"M1": _sysRecord("M1", cell="sub")}
    wrongCell = _desc("M1", "othercell")
    plan = corr.correspondenceDiff(sch, [wrongCell], SRC)
    assert not plan.adopted
    assert [r["nam"] for r in plan.to_add] == ["M1"]


def test_pcellParamsFor_maps_labels_and_reports_missing():
    def fakeCall(w, l, extra=5):
        pass

    params = inspect.signature(fakeCall).parameters
    pmap = {"w": "w", "l": "length"}
    labels = {"w": ["2u", True], "length": ["0.5u", True]}
    kwargs, missing = corr.pcellParamsFor(params, pmap, labels)
    assert kwargs == {"w": "2u", "l": "0.5u"}
    assert not missing
    # Missing required label -> reported; defaulted param never is.
    kwargs, missing = corr.pcellParamsFor(
        params, pmap, {"w": ["2u", True]})
    assert missing == ["l"]


def test_flyline_endpoints_resolve_pin_nets():
    # I1.A (50,0) --- scn "sig" (50,0)->(150,0) --- I2.B (150,0),
    # sheet pin "IN" at (100,0) rides the same net.
    records = [
        _sysRecord("I1", loc=(0, 0)),
        _sysRecord("I2", loc=(200, 0)),
        {"type": "scn", "st": (50, 0), "end": (150, 0), "nam": "sig",
         "ns": 3},
        {"type": "scp", "st": (100, 0), "pn": "IN", "pd": "Input"},
    ]
    pinLocator = lambda lib, cell, view: {"A": (50, 0), "B": (-50, 0)}
    endpoints, _diags = corr.flylineEndpoints(records, pinLocator)
    # SET wire name anchors the group; sheet pin rides along.
    sig = set(endpoints["sig"])
    assert ("I1", "A") in sig
    assert ("I2", "B") in sig
    assert ("", "IN") in sig


def test_flyline_endpoints_skip_dangling_pins():
    records = [
        _sysRecord("I1", loc=(0, 0)),
        {"type": "scn", "st": (50, 0), "end": (150, 0), "nam": "sig",
         "ns": 3},
    ]
    # Symbol has two pins; only A touches the wire — B is dangling.
    pinLocator = lambda lib, cell, view: {"A": (50, 0), "B": (500, 500)}
    endpoints, _diags = corr.flylineEndpoints(records, pinLocator)
    assert ("I1", "A") in endpoints["sig"]
    assert all(pin != "B" for eps in endpoints.values()
               for _inst, pin in eps)


# --- scene-level sync --------------------------------------------------------


def _writeLibrary(tmp_path):
    """Minimal library: mylib/top/schematic.json + mylib/sub views."""
    libDir = tmp_path / "mylib"
    (libDir / "sub").mkdir(parents=True)
    (libDir / "top").mkdir(parents=True)
    (libDir / "sub" / "layout.json").write_bytes(orjson.dumps([
        {"viewType": "layout"},
        {"snapGrid": [10, 10]},
        {"type": "Pin", "tl": [0, 0], "br": [40, 40], "pn": "A",
         "pd": "Input", "pt": "Signal", "ln": M1_LN},
    ]))
    (libDir / "sub" / "symbol.json").write_bytes(orjson.dumps([
        {"viewType": "symbol"},
        {},
        {"type": "pin", "nam": "A", "loc": [0, 0], "st": [50, 0],
         "pd": "Input"},
    ]))
    return libDir


def _writeSchematic(libDir, insts, extra=()):
    records = [{"viewType": "schematic"}, {"snapGrid": [10, 10]}]
    records += list(insts) + list(extra)
    (libDir / "top" / "schematic.json").write_bytes(orjson.dumps(records))


def _schematicTuple(libDir):
    return ddef.viewItemTuple(
        libb.libraryItem(libDir), libb.cellItem(libDir / "top"),
        libb.viewItem(libDir / "top" / "schematic.json"))


def _sceneFor(libDir):
    scene = makeLayoutScene()
    scene.libraryDict = {"mylib": libDir}
    return scene


def test_updateFromSchematic_places_and_stamps(tmp_path):
    libDir = _writeLibrary(tmp_path)
    _writeSchematic(libDir, [_sysRecord("M1"), _sysRecord("M2")])
    scene = _sceneFor(libDir)
    stats = scene.updateFromSchematic(_schematicTuple(libDir))
    assert stats["added"] == 2
    insts = [i for i in scene.items()
             if isinstance(i, lshp.layoutInstance)]
    assert len(insts) == 2
    sdl = insts[0]._sdlSource
    assert corr.sdlSourceKey(sdl) == SRC
    assert corr.sdlInstName(sdl) in {"M1", "M2"}
    # Undoable as one macro.
    scene.undoStack.undo()
    assert not [i for i in scene.items()
                if isinstance(i, lshp.layoutInstance)]
    scene.undoStack.redo()


def test_updateFromSchematic_is_incremental(tmp_path):
    libDir = _writeLibrary(tmp_path)
    _writeSchematic(libDir, [_sysRecord("M1")])
    scene = _sceneFor(libDir)
    scene.updateFromSchematic(_schematicTuple(libDir))
    # User geometry survives a re-sync; no duplicates for M1.
    userRect = lshp.layoutRect(QPoint(500, 500), QPoint(600, 600),
                               m1Layer_drw)
    scene.addItem(userRect)
    _writeSchematic(libDir, [_sysRecord("M1"), _sysRecord("M2")])
    stats = scene.updateFromSchematic(_schematicTuple(libDir))
    assert stats["added"] == 1
    assert stats["removed"] == 0
    insts = [i for i in scene.items()
             if isinstance(i, lshp.layoutInstance)]
    assert len(insts) == 2
    assert userRect.scene() is scene


def test_updateFromSchematic_removes_and_adopts(tmp_path):
    libDir = _writeLibrary(tmp_path)
    _writeSchematic(libDir, [_sysRecord("M1"), _sysRecord("M2")])
    scene = _sceneFor(libDir)
    scene.updateFromSchematic(_schematicTuple(libDir))
    # Schematic drops M2, renames M1 -> M3 (orphan M3 placed by hand).
    orphan = lshp.layoutInstance([])
    orphan.libraryName = "mylib"
    orphan.cellName = "sub"
    orphan.viewName = "layout"
    orphan.instanceName = "M3"
    orphan.counter = 9
    scene.addItem(orphan)
    _writeSchematic(libDir, [_sysRecord("M3")])
    stats = scene.updateFromSchematic(_schematicTuple(libDir))
    assert stats["removed"] == 2      # M1 + M2 sources vanished
    assert stats["adopted"] == 1      # orphan M3 matched by name+cell
    assert stats["added"] == 0        # adopted consumed the record
    insts = [i for i in scene.items()
             if isinstance(i, lshp.layoutInstance)]
    assert insts == [orphan]
    assert corr.sdlInstName(orphan._sdlSource) == "M3"
    assert corr.sdlSourceKey(orphan._sdlSource) == SRC


def test_sdl_field_persists_round_trip(tmp_path):
    libDir = _writeLibrary(tmp_path)
    _writeSchematic(libDir, [_sysRecord("M1")])
    scene = _sceneFor(libDir)
    scene.updateFromSchematic(_schematicTuple(libDir))
    inst = next(i for i in scene.items()
                if isinstance(i, lshp.layoutInstance))
    # Encoder writes sdl; loader restores _sdlSource.
    import revedaEditor.fileio.layoutEncoder as layenc
    import revedaEditor.fileio.loadJSON as lj
    encoder = layenc.layoutEncoder()
    record = encoder._encodeLayoutInstance(inst)
    assert record["sdl"]["inst"] == "M1"
    assert record["sdl"]["lib"] == "mylib"
    assert record["sdl"]["cell"] == "top"
    loader = lj.layoutItems(scene)
    restored = loader.create(record)
    assert corr.sdlInstName(restored._sdlSource) == "M1"
    assert corr.sdlSourceKey(restored._sdlSource) == SRC


def test_flylines_draw_for_unrouted_and_clear_when_routed(tmp_path):
    libDir = _writeLibrary(tmp_path)
    # I1.A --- "sig" --- I2.A ; symbol pin A at (50,0) -> scene (50,0).
    _writeSchematic(
        libDir,
        [_sysRecord("I1", loc=(0, 0)), _sysRecord("I2", loc=(200, 0))],
        extra=[{"type": "scn", "st": (50, 0), "end": (250, 0),
                "nam": "sig", "ns": 3}])
    scene = _sceneFor(libDir)
    scene.updateFromSchematic(_schematicTuple(libDir))
    # Two pins on one net, no routing -> one flyline.
    assert len(scene._flylines) == 1
    assert scene._flylines[0].netName == "sig"
    # Route the two pins together -> the flyline disappears on rebuild.
    p1 = scene._layoutPinForEndpoint("I1", "A")
    p2 = scene._layoutPinForEndpoint("I2", "A")
    r1, r2 = p1.sceneBoundingRect(), p2.sceneBoundingRect()
    wire = lshp.layoutRect(
        r1.center().toPoint(), r2.center().toPoint(), m1Layer_drw)
    scene.addItem(wire)
    assert scene.rebuildFlylines() == 0
    assert not scene._flylines


def test_flylines_resolve_via_pcell_pin_map(tmp_path):
    """Symbol pins named differently from layout pins (rsil 'P' vs 'PLUS')
    resolve through the cell's pinMappings entry in pcellParameterMap.json."""
    libDir = _writeLibrary(tmp_path)
    # Layout pin carries the pcell's LVS terminal name, not the symbol's.
    (libDir / "sub" / "layout.json").write_bytes(orjson.dumps([
        {"viewType": "layout"},
        {"snapGrid": [10, 10]},
        {"type": "Pin", "tl": [0, 0], "br": [40, 40], "pn": "PLUS",
         "pd": "Input", "pt": "Signal", "ln": M1_LN},
    ]))
    _writeSchematic(
        libDir,
        [_sysRecord("I1", loc=(0, 0)), _sysRecord("I2", loc=(200, 0))],
        extra=[{"type": "scn", "st": (50, 0), "end": (250, 0),
                "nam": "sig", "ns": 3}])
    scene = _sceneFor(libDir)
    scene.updateFromSchematic(_schematicTuple(libDir))
    # Unmapped names resolve nothing -> no flylines.
    assert not scene._flylines
    # With the cell's pinMappings entry, 'A' resolves to layout pin 'PLUS'.
    scene._getPcellPinMap = lambda cellName: {"A": "PLUS"}
    assert scene.rebuildFlylines() == 1
    pin = scene._layoutPinForEndpoint("I1", "A")
    assert pin is not None and pin.pinName == "PLUS"


def test_updateFromSchematic_rebuilds_flylines_when_unchanged(tmp_path):
    """A no-op sync (layout already matches) still refreshes the rat's
    nest and records the schematic as the flyline source."""
    libDir = _writeLibrary(tmp_path)
    _writeSchematic(
        libDir,
        [_sysRecord("I1", loc=(0, 0)), _sysRecord("I2", loc=(200, 0))],
        extra=[{"type": "scn", "st": (50, 0), "end": (250, 0),
                "nam": "sig", "ns": 3}])
    scene = _sceneFor(libDir)
    scene.updateFromSchematic(_schematicTuple(libDir))
    assert len(scene._flylines) == 1
    scene.clearFlylines()
    stats = scene.updateFromSchematic(_schematicTuple(libDir))
    assert stats["added"] == 0 and stats["updated"] == 0
    assert len(scene._flylines) == 1


def test_flylines_track_instance_moves(tmp_path):
    """Flylines re-anchor to pin positions on move and drop when the
    islands they bridge merge (checked via the connectivity rebuild
    hook, not just an explicit rebuildFlylines)."""
    libDir = _writeLibrary(tmp_path)
    _writeSchematic(
        libDir,
        [_sysRecord("I1", loc=(0, 0)), _sysRecord("I2", loc=(200, 0))],
        extra=[{"type": "scn", "st": (50, 0), "end": (250, 0),
                "nam": "sig", "ns": 3}])
    scene = _sceneFor(libDir)
    scene.updateFromSchematic(_schematicTuple(libDir))
    assert len(scene._flylines) == 1
    flyline = scene._flylines[0]
    before = flyline.line()

    inst2 = next(i for i in scene.items()
                 if isinstance(i, lshp.layoutInstance)
                 and i.instanceName == "I2")
    inst2.setPos(inst2.pos() + QPoint(500, 300))
    # Headless scenes emit no changed() without a view; the real editor's
    # setPos->changed->markConnectivityDirty chain is simulated directly.
    scene.markConnectivityDirty()
    after = flyline.line()
    assert after != before
    assert after.p2() == scene._layoutPinForEndpoint(
        "I2", "A").sceneBoundingRect().center()

    # Slide I2 so its pin overlaps I1's pin: islands merge and the
    # connectivity rebuild drops the flyline.
    inst1 = next(i for i in scene.items()
                 if isinstance(i, lshp.layoutInstance)
                 and i.instanceName == "I1")
    inst2.setPos(inst1.pos())
    scene.rebuildConnectivity()
    assert not scene._flylines


def test_cross_probe_targets_for_selected_instance(tmp_path):
    libDir = _writeLibrary(tmp_path)
    _writeSchematic(libDir, [_sysRecord("M1")])
    scene = _sceneFor(libDir)
    scene.updateFromSchematic(_schematicTuple(libDir))
    inst = next(i for i in scene.items()
                if isinstance(i, lshp.layoutInstance))
    inst.setSelected(True)
    instances, netEndpoints = scene._probeTargets()
    assert instances == ["M1"]
    # A selected member of the pin's net probes via endpoints. (Instance
    # children are unselectable; top-level members carry the selection.)
    inst.setSelected(False)
    wire = lshp.layoutRect(QPoint(30, 10), QPoint(200, 30), m1Layer_drw)
    scene.addItem(wire)
    wire.setSelected(True)
    instances, netEndpoints = scene._probeTargets()
    assert not instances
    assert ("M1", "A") in netEndpoints


def test_selectProbeTargets_selects_and_highlights(tmp_path):
    libDir = _writeLibrary(tmp_path)
    _writeSchematic(libDir, [_sysRecord("M1")])
    scene = _sceneFor(libDir)
    scene.updateFromSchematic(_schematicTuple(libDir))
    inst = next(i for i in scene.items()
                if isinstance(i, lshp.layoutInstance))
    assert scene.selectProbeTargets(instances=["M1"]) == 1
    assert inst.isSelected()
    inst.setSelected(False)
    # Endpoint probe highlights the pin's net group.
    assert scene.highlightNetGroupsForEndpoints([("M1", "A")]) == 1
    pin = scene._layoutPinForEndpoint("M1", "A")
    assert pin in scene._netHighlightItems


def test_probe_source_key_prefers_cache_then_majority(tmp_path):
    libDir = _writeLibrary(tmp_path)
    _writeSchematic(libDir, [_sysRecord("M1"), _sysRecord("M2"),
                            _sysRecord("M3")])
    # A second, valid source schematic in the same library.
    (libDir / "top2").mkdir()
    (libDir / "top2" / "schematic.json").write_bytes(orjson.dumps(
        [{"viewType": "schematic"}, {"snapGrid": [10, 10]}]))
    scene = _sceneFor(libDir)
    scene.updateFromSchematic(_schematicTuple(libDir))
    other = ("mylib", "top2", "schematic")
    byInst = {corr.sdlInstName(i._sdlSource): i
              for i in scene.items()
              if isinstance(i, lshp.layoutInstance)}
    byInst["M1"]._sdlSource = corr.makeSdlSource(*other, "X1", {})
    byInst["M2"]._sdlSource = corr.makeSdlSource(*other, "X2", {})
    # Session cache wins even as the minority stamp.
    assert scene._sdlSourceKeyForScene() == SRC
    # Reload path (no cache): majority stamp decides.
    scene._flylineSource = None
    assert scene._sdlSourceKeyForScene() == other


def test_probe_source_key_skips_stale_stamps(tmp_path):
    libDir = _writeLibrary(tmp_path)
    _writeSchematic(libDir, [_sysRecord("M1"), _sysRecord("M2")])
    scene = _sceneFor(libDir)
    scene.updateFromSchematic(_schematicTuple(libDir))
    insts = [i for i in scene.items()
             if isinstance(i, lshp.layoutInstance)]
    insts[0]._sdlSource = corr.makeSdlSource(
        "ghostlib", "ghostcell", "schematic", "G1", {})
    scene._flylineSource = None
    # The dead stamp is skipped in favour of the surviving source.
    assert scene._sdlSourceKeyForScene() == SRC
    # Only dead stamps left -> no probe source at all.
    insts[1]._sdlSource = insts[0]._sdlSource
    assert scene._sdlSourceKeyForScene() is None
