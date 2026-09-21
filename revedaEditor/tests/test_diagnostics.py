"""Tests for connectivity.diagnostics — headless record-level checks
(checkRecords / checkLayoutRecords) and the loadJSON pin locator."""

import json

import pytest
from PySide6.QtWidgets import QApplication

import revedaEditor.connectivity as conn
from revedaEditor.connectivity import checkLayoutRecords, checkRecords
from revedaEditor.fileio.loadJSON import makeSymbolPinLocator
import defaultPDK.layoutLayers as laylyr
import defaultPDK.process as fabproc


@pytest.fixture(scope="module", autouse=True)
def init_qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


# --- schematic records ------------------------------------------------------


def test_checkRecords_clean():
    records = [
        {"type": "scn", "st": (0, 0), "end": (100, 0), "nam": "", "ns": 0},
        {"type": "scn", "st": (100, 0), "end": (200, 0), "nam": "out",
         "ns": 3},
        # Schematic pin asserts the net name: pin "out" agrees with the
        # SET-named wire, so no conflict.
        {"type": "scp", "st": (0, 0), "pn": "out", "pd": "Output",
         "pt": "Signal"},
    ]
    result, diagnostics = checkRecords(records, portTol=10)
    errors = [d for d in diagnostics if d.severity == "error"]
    assert not errors
    assert result.groups[0].name == "out"


def test_checkRecords_floating_pin():
    records = [
        {"type": "scn", "st": (0, 0), "end": (100, 0), "nam": "", "ns": 0},
        {"type": "scp", "st": (500, 500), "pn": "far", "pd": "Input",
         "pt": "Signal"},
    ]
    _result, diagnostics = checkRecords(records, portTol=10)
    floating = [d for d in diagnostics if d.kind == "floatingPin"]
    assert len(floating) == 1
    assert "far" in floating[0].message


def test_checkRecords_dangling_end():
    records = [
        {"type": "scn", "st": (0, 0), "end": (100, 0), "nam": "", "ns": 0},
    ]
    _result, diagnostics = checkRecords(records, portTol=10)
    dangling = [d for d in diagnostics if d.kind == "danglingEnd"]
    assert len(dangling) == 2  # both ends unterminated


def test_checkRecords_dangling_suppressed_by_junction():
    # T-contact: (50,0) lands on body of the vertical wire.
    records = [
        {"type": "scn", "st": (0, 0), "end": (100, 0), "nam": "", "ns": 0},
        {"type": "scn", "st": (50, 0), "end": (50, -100), "nam": "",
         "ns": 0},
        {"type": "scp", "st": (0, 0), "pn": "a", "pd": "Input",
         "pt": "Signal"},
        {"type": "scp", "st": (100, 0), "pn": "b", "pd": "Output",
         "pt": "Signal"},
        {"type": "scp", "st": (50, -100), "pn": "c", "pd": "Output",
         "pt": "Signal"},
    ]
    _result, diagnostics = checkRecords(records, bodyTol=5, portTol=10)
    assert not [d for d in diagnostics if d.kind == "danglingEnd"]


def test_checkRecords_name_conflict_is_error():
    records = [
        {"type": "scn", "st": (0, 0), "end": (100, 0), "nam": "a", "ns": 3},
        {"type": "scn", "st": (100, 0), "end": (200, 0), "nam": "b",
         "ns": 3},
    ]
    _result, diagnostics = checkRecords(records)
    conflicts = [d for d in diagnostics if d.kind == "netNameConflict"]
    assert conflicts and all(d.severity == "error" for d in conflicts)


def test_checkRecords_malformed_and_unresolved():
    records = [
        {"type": "scn", "st": (0, 0)},  # missing 'end'
        {"type": "sys", "lib": "lib", "cell": "res", "view": "symbol",
         "nam": "I0", "loc": (0, 0)},
    ]
    _result, diagnostics = checkRecords(records)  # no pinLocator
    kinds = {d.kind for d in diagnostics}
    assert "malformedRecord" in kinds
    assert "unresolvedInstance" in kinds


def test_makeSymbolPinLocator(tmp_path):
    libDir = tmp_path / "mylib"
    cellDir = libDir / "res"
    cellDir.mkdir(parents=True)
    (cellDir / "symbol.json").write_text(json.dumps([
        {"viewType": "symbol"}, {},
        {"type": "pin", "nam": "plus", "pd": "Inout", "pt": "Signal",
         "st": (0, 0), "loc": (10, 20), "ang": 0, "fl": (1, 1)},
        {"type": "pin", "nam": "minus", "pd": "Inout", "pt": "Signal",
         "st": (0, 0), "loc": (60, 20), "ang": 0, "fl": (1, 1)},
    ]))
    locator = makeSymbolPinLocator({"mylib": libDir})
    pinMap = locator("mylib", "res", "symbol")
    assert pinMap["plus"] == (10, 20)
    assert pinMap["minus"] == (60, 20)
    assert pinMap["directions"]["plus"] == "Inout"
    assert locator("mylib", "res", "nosuchview") is None
    assert locator("badlib", "res", "symbol") is None


def test_checkRecords_with_locator_resolves_instance_pins(tmp_path):
    libDir = tmp_path / "mylib"
    cellDir = libDir / "res"
    cellDir.mkdir(parents=True)
    (cellDir / "symbol.json").write_text(json.dumps([
        {"viewType": "symbol"}, {},
        {"type": "pin", "nam": "plus", "pd": "Inout", "pt": "Signal",
         "st": (0, 0), "loc": (0, 0), "ang": 0, "fl": (1, 1)},
    ]))
    records = [
        {"type": "scn", "st": (-100, 0), "end": (0, 0), "nam": "", "ns": 0},
        {"type": "sys", "lib": "mylib", "cell": "res", "view": "symbol",
         "nam": "I0", "loc": (0, 0), "ang": 0, "fl": (1, 1), "ld": {}},
    ]
    locator = makeSymbolPinLocator({"mylib": libDir})
    result, diagnostics = checkRecords(records, pinLocator=locator,
                                       portTol=10)
    assert not [d for d in diagnostics if d.kind == "floatingPin"]
    assert result.portGroup[0] == 0


# --- layout records ---------------------------------------------------------


def _m1Index():
    return laylyr.pdkAllLayers.index(laylyr.m1Layer_drw)


def _m2Index():
    return laylyr.pdkAllLayers.index(laylyr.m2Layer_drw)


def test_checkLayoutRecords_via_bridge_and_label_name():
    records = [
        {"viewType": "layout"}, {},
        {"type": "Rect", "tl": (0, 0), "br": (100, 100), "ln": _m1Index()},
        {"type": "Rect", "tl": (0, 100), "br": (100, 300),
         "ln": _m2Index()},
        {"type": "Via", "st": (25, 50),
         "via": {"vdt": "v1", "w": 50, "h": 60}},
        {"type": "Label", "st": (10, 10), "lt": "vdd", "ln": _m1Index()},
    ]
    groups, names, diagnostics = checkLayoutRecords(records, laylyr,
                                                  fabproc)
    assert len(groups) == 1
    assert names == ["vdd"]
    assert not diagnostics


def test_checkLayoutRecords_pin_names_net_and_is_metal():
    records = [
        {"viewType": "layout"}, {},
        {"type": "Pin", "tl": (0, 0), "br": (50, 50), "pn": "vss",
         "ln": _m1Index()},
        {"type": "Rect", "tl": (40, 10), "br": (200, 60),
         "ln": _m1Index()},
    ]
    groups, names, diagnostics = checkLayoutRecords(records, laylyr,
                                                  fabproc)
    assert len(groups) == 1  # pin metal joins the rect
    assert names == ["vss"]


def test_checkLayoutRecords_label_conflict():
    records = [
        {"viewType": "layout"}, {},
        {"type": "Rect", "tl": (0, 0), "br": (100, 100), "ln": _m1Index()},
        {"type": "Label", "st": (20, 20), "lt": "vdd", "ln": _m1Index()},
        {"type": "Label", "st": (80, 80), "lt": "vss", "ln": _m1Index()},
    ]
    groups, names, diagnostics = checkLayoutRecords(records, laylyr,
                                                  fabproc)
    assert names == ["vdd"]
    assert len(diagnostics) == 1
    assert diagnostics[0].kind == "netNameConflict"
