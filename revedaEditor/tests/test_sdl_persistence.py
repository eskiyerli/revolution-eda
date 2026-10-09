"""Persistence compatibility for RevSDL metadata owned by the free core."""

import json

import orjson
import pytest
from PySide6.QtCore import QLineF, QPointF
from PySide6.QtWidgets import QApplication

import revedaEditor.fileio.layoutEncoder as layenc
import revedaEditor.fileio.loadJSON as lj
from defaultPDK import pcells
from revedaEditor.common import layoutShapes as lshp
from revedaEditor.fileio import schemaValidation as sv
from revedaEditor.tests.sceneTestUtils import makeLayoutScene


@pytest.fixture(scope="module", autouse=True)
def initQapp():
    app = QApplication.instance() or QApplication([])
    yield app


SDL = {
    "lib": "mylib",
    "cell": "top",
    "view": "schematic",
    "inst": "M1",
    "labels": {"w": ["6u", True]},
}


def _layoutRecord(recordType="Inst", sdl=SDL):
    record = {
        "type": recordType,
        "lib": "mylib",
        "cell": "sub" if recordType == "Inst" else "mos",
        "view": "layout" if recordType == "Inst" else "pcell",
        "nam": "M1",
        "ic": 1,
        "loc": [0, 0],
        "ang": 0,
        "fl": [1, 1],
    }
    if recordType == "Pcell":
        record["params"] = {"width": 4.0, "length": 0.13, "nf": 1}
    if sdl is not None:
        record["sdl"] = sdl
    return record


def _layoutData(record, version="1.0"):
    return [
        {"viewType": "layout", "schemaVersion": version},
        {"snapGrid": [10, 10]},
        record,
    ]


def _writeReferencedViews(tmp_path):
    libDir = tmp_path / "mylib"
    (libDir / "sub").mkdir(parents=True)
    (libDir / "mos").mkdir()
    (libDir / "sub" / "layout.json").write_bytes(orjson.dumps([
        {"viewType": "layout", "schemaVersion": "1.0"},
        {"snapGrid": [10, 10]},
    ]))
    (libDir / "mos" / "pcell.json").write_bytes(orjson.dumps([
        {"cellView": "pcell"},
        {"reference": "nmos"},
    ]))
    return libDir


def _instance():
    instance = lshp.layoutInstance([])
    instance.libraryName = "mylib"
    instance.cellName = "sub"
    instance.viewName = "layout"
    instance.instanceName = "M1"
    instance.counter = 1
    return instance


def _pcell():
    instance = pcells.nmos()
    instance.libraryName = "mylib"
    instance.cellName = "mos"
    instance.viewName = "pcell"
    instance.instanceName = "M1"
    instance.counter = 1
    return instance


@pytest.mark.parametrize("recordType", ("Inst", "Pcell"))
def test_strict_schema_accepts_canonical_sdl(recordType):
    isValid, errors = sv.validate_design_data(
        _layoutData(_layoutRecord(recordType)), strict=True)
    assert isValid, errors


@pytest.mark.parametrize(
    "sdl",
    (
        {"lib": "mylib", "cell": "top", "inst": "M1", "labels": {}},
        {"lib": "mylib", "cell": "top", "view": "schematic", "inst": "M1"},
        {"lib": "mylib", "cell": "top", "view": "schematic",
         "inst": "M1", "labels": []},
        {"schematicLib": "mylib", "schematicCell": "sub",
         "schematicInstance": "M1", "labels": {}},
        "not-a-source",
    ),
)
def test_strict_schema_rejects_noncanonical_sdl(sdl):
    isValid, errors = sv.validate_design_data(
        _layoutData(_layoutRecord(sdl=sdl)), strict=True)
    assert not isValid
    assert errors


@pytest.mark.parametrize("makeItem", (_instance, _pcell))
def test_encoder_writes_only_canonical_sdl(makeItem):
    item = makeItem()
    item._sdlSource = dict(SDL)
    record = json.loads(json.dumps(item, cls=layenc.layoutEncoder))
    assert record["sdl"] == SDL

    item._sdlSource = {
        "schematicLib": "mylib",
        "schematicCell": "sub",
        "schematicInstance": "M1",
        "labels": {},
    }
    record = json.loads(json.dumps(item, cls=layenc.layoutEncoder))
    assert "sdl" not in record


@pytest.mark.parametrize("recordType", ("Inst", "Pcell"))
def test_plugin_absent_load_save_preserves_canonical_sdl(
        recordType, tmp_path, monkeypatch):
    libDir = _writeReferencedViews(tmp_path)
    if recordType == "Pcell":
        monkeypatch.setattr(
            lj.PCellCache, "getPCellClass", lambda *_: pcells.nmos)
    scene = makeLayoutScene()
    scene.libraryDict = {"mylib": libDir}
    factory = lj.layoutItems(scene)

    restored = factory.create(_layoutRecord(recordType))

    assert restored is not None
    assert restored._sdlSource == SDL
    encoded = json.loads(json.dumps(restored, cls=layenc.layoutEncoder))
    assert encoded["sdl"] == SDL


@pytest.mark.parametrize("recordType", ("Inst", "Pcell"))
def test_absent_sdl_remains_absent_across_load_save(
        recordType, tmp_path, monkeypatch):
    libDir = _writeReferencedViews(tmp_path)
    if recordType == "Pcell":
        monkeypatch.setattr(
            lj.PCellCache, "getPCellClass", lambda *_: pcells.nmos)
    scene = makeLayoutScene()
    scene.libraryDict = {"mylib": libDir}

    restored = lj.layoutItems(scene).create(
        _layoutRecord(recordType, sdl=None))

    assert restored is not None
    assert getattr(restored, "_sdlSource", None) is None
    encoded = json.loads(json.dumps(restored, cls=layenc.layoutEncoder))
    assert "sdl" not in encoded


@pytest.mark.parametrize(
    "metadata",
    (
        {
            "schematicLib": "mylib",
            "schematicCell": "sub",
            "schematicInstance": "M1",
            "labels": {},
        },
        {
            "lib": "mylib",
            "cell": "top",
            "view": "schematic",
            "inst": "M1",
            "labels": [],
        },
    ),
)
def test_loader_ignores_noncanonical_persisted_sdl(
        metadata, tmp_path, caplog):
    libDir = _writeReferencedViews(tmp_path)
    scene = makeLayoutScene()
    scene.libraryDict = {"mylib": libDir}

    restored = lj.layoutItems(scene).create(_layoutRecord(sdl=metadata))

    assert restored is not None
    assert getattr(restored, "_sdlSource", None) is None
    assert "Ignoring noncanonical sdl metadata" in caplog.text


def test_layout_with_sdl_rejects_unsupported_future_schema():
    with pytest.raises(sv.DesignFileValidationError):
        sv.prepare_design_data(
            _layoutData(_layoutRecord(), version="99.0"), "layout")


def test_flyline_overlay_is_excluded_from_saved_layout(tmp_path):
    scene = makeLayoutScene()
    scene.editorWindow.cellName = "top"
    scene.editorWindow.viewName = "layout"
    scene.editorWindow.lodThreshold = 0.02
    scene.addItem(lshp.layoutFlightLine(
        QLineF(QPointF(0, 0), QPointF(100, 100)), "sig"))
    output = tmp_path / "layout.json"

    scene.saveLayoutCell(output)

    records = orjson.loads(output.read_bytes())
    assert len(records) == 2
    assert all(record.get("type") != "FlightLine" for record in records)
