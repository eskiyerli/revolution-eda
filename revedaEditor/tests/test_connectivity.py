"""Tests for the unified connectivity engine (revedaEditor.connectivity).

Covers geometric joins (endpoint coincidence, endpoint-on-body T contacts,
non-joining crossings), name resolution priority (global pins, sheet pins,
SET names, auto names), conflict reporting, the records adapter, and parity
with schematicScene.nameSceneNets on geometry both implementations agree on.
"""

import pytest
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication

import revedaEditor.common.net as snet
import revedaEditor.common.shapes as shp
from revedaEditor.connectivity import (INHERIT, NONAME, SET, WEAK, Port, Seg,
                                       analyzeItems, analyzeRecords, resolve)
from revedaEditor.connectivity.adapters import fromRecords
from revedaEditor.tests.sceneTestUtils import makeSchematicScene


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


def seg(id, x1, y1, x2, y2, name="", strength=0):
    return Seg(id=id, p1=(x1, y1), p2=(x2, y2), name=name, strength=strength)


def port(id, name, x, y, direction="Inout", kind="schemPin", owner=""):
    return Port(id=id, name=name, direction=direction, point=(x, y),
                kind=kind, owner=owner or name)


# --- geometric grouping ----------------------------------------------------

def test_endpoint_coincidence_joins():
    result = resolve([seg(0, 0, 0, 100, 0), seg(1, 100, 0, 200, 0)], [])
    assert len(result.groups) == 1


def test_t_contact_joins():
    # Endpoint of seg 1 lands on the body of seg 0 (legacy T contact).
    result = resolve([seg(0, 0, 0, 200, 0), seg(1, 100, 0, 100, 100)], [])
    assert len(result.groups) == 1


def test_crossing_without_endpoint_does_not_join():
    # Interior crossing, no endpoint on the other segment's body.
    result = resolve([seg(0, 0, 0, 200, 0), seg(1, 100, -50, 100, 50)], [])
    assert len(result.groups) == 2


def test_disjoint_segments_stay_separate():
    result = resolve([seg(0, 0, 0, 100, 0), seg(1, 0, 50, 100, 50)], [])
    assert len(result.groups) == 2


# --- name resolution ---------------------------------------------------------

def test_set_name_propagates():
    result = resolve([seg(0, 0, 0, 100, 0, name="vdd", strength=SET),
                      seg(1, 100, 0, 200, 0)], [])
    assert len(result.groups) == 1
    group = result.groups[0]
    assert group.name == "vdd"
    assert result.segName[0] == ("vdd", SET)
    assert result.segName[1] == ("vdd", INHERIT)


def test_schematic_pin_names_net_inherit():
    result = resolve([seg(0, 0, 0, 100, 0), seg(1, 100, 0, 200, 0)],
                     [port(0, "in", 0, 0, direction="Input")])
    group = result.groups[0]
    assert group.name == "in"
    assert result.segName[0][1] == INHERIT
    assert result.segName[1][1] == INHERIT


def test_global_pin_names_net_set():
    result = resolve([seg(0, 0, 0, 100, 0), seg(1, 100, 0, 200, 0)],
                     [port(0, "gnd!", 0, 0, kind="symbolPin", owner="I0")])
    group = result.groups[0]
    assert group.name == "gnd!"
    assert result.segName[0] == ("gnd!", SET)  # directly under pin
    assert result.segName[1] == ("gnd!", INHERIT)


def test_auto_naming_is_deterministic():
    segs = [seg(0, 0, 0, 100, 0), seg(1, 0, 50, 100, 50),
            seg(2, 0, 90, 100, 90)]
    result = resolve(segs, [])
    names = sorted(result.segName[i][0] for i in (0, 1, 2))
    assert names == ["net0", "net1", "net2"]
    # origin member (smallest id) is WEAK, others INHERIT
    result2 = resolve(list(reversed(segs)), [])
    assert [result2.segName[i][0] for i in (0, 1, 2)] == [
        result.segName[i][0] for i in (0, 1, 2)]


def test_set_name_conflict_flagged():
    result = resolve([seg(0, 0, 0, 100, 0, name="a", strength=SET),
                      seg(1, 100, 0, 200, 0, name="b", strength=SET)], [])
    assert result.conflicts
    assert result.conflicts[0].kind == "netNameConflict"
    assert result.segConflicts == {0, 1}


def test_bus_member_name_compatible_with_bus():
    # 'a<3>' on a wire inside bus 'a<7:0>' is not a conflict.
    result = resolve([seg(0, 0, 0, 100, 0, name="a<7:0>", strength=SET),
                      seg(1, 100, 0, 200, 0, name="a<3>", strength=SET)], [])
    assert not result.conflicts


def test_pin_vs_set_name_conflict():
    result = resolve([seg(0, 0, 0, 100, 0, name="vdd", strength=SET)],
                     [port(0, "in", 50, 0)])
    kinds = {c.kind for c in result.conflicts}
    assert "netNameConflict" in kinds


def test_bus_width_mismatch_flagged():
    result = resolve([seg(0, 0, 0, 100, 0, name="a<0:7>", strength=SET)],
                     [port(0, "a<0:3>", 0, 0)])
    kinds = {c.kind for c in result.conflicts}
    assert "busWidthMismatch" in kinds


def test_conflicting_pin_names_flagged():
    result = resolve([seg(0, 0, 0, 100, 0)],
                     [port(0, "in", 0, 0), port(1, "out", 100, 0)])
    kinds = {c.kind for c in result.conflicts}
    assert "pinNameConflict" in kinds


def test_floating_port_gets_no_group():
    result = resolve([seg(0, 0, 0, 100, 0)], [port(0, "in", 500, 500)])
    assert result.portGroup[0] is None


def test_connect_by_name_signal_key():
    # Disjoint groups with the same SET name share a signal key.
    result = resolve([seg(0, 0, 0, 100, 0, name="sig", strength=SET),
                      seg(1, 0, 50, 100, 50, name="sig", strength=SET)], [])
    assert len(result.groups) == 2
    assert result.signalKey(0) == result.signalKey(1) == "sig"


# --- records adapter ---------------------------------------------------------

def test_from_records_basic():
    records = [
        {"type": "scn", "st": (0, 0), "end": (100, 0), "nam": "", "ns": 0},
        {"type": "scn", "st": (100, 0), "end": (200, 0), "nam": "out",
         "ns": 3},
        {"type": "scp", "st": (0, 0), "pn": "in", "pd": "Input",
         "pt": "Signal"},
    ]
    result, diagnostics = analyzeRecords(records)
    assert diagnostics == []
    assert len(result.groups) == 1
    assert result.groups[0].name == "out"
    assert result.portGroup[0] == 0


def test_from_records_instance_ports_via_pin_locator():
    records = [
        {"type": "scn", "st": (-100, 0), "end": (0, 0), "nam": "", "ns": 0},
        {"type": "sys", "lib": "lib", "cell": "res", "view": "symbol",
         "nam": "I0", "loc": (0, 0), "ang": 0, "fl": (1, 1), "ld": {}},
    ]
    pinLocator = lambda lib, cell, view: {"plus": (0, 0), "minus": (60, 0),
                                          "directions": {"plus": "Inout",
                                                         "minus": "Inout"}}
    result, diagnostics = analyzeRecords(records, pinLocator=pinLocator)
    assert diagnostics == []
    assert len(result.portGroup) == 2
    assert result.portGroup[0] == 0  # 'plus' sits on the wire end
    assert result.portGroup[1] is None  # 'minus' is floating


def test_from_records_missing_locator_is_diagnostic_not_crash():
    records = [{"type": "sys", "lib": "lib", "cell": "res", "view": "symbol",
                "nam": "I0", "loc": (0, 0)}]
    result, diagnostics = analyzeRecords(records)
    assert diagnostics
    assert result.portGroup == {}


def test_from_records_malformed_record_is_diagnostic():
    records = [{"type": "scn", "st": (0, 0)}]  # missing 'end'
    result, diagnostics = analyzeRecords(records)
    assert diagnostics
    assert result.groups == []


# --- parity with schematicScene.nameSceneNets ---------------------------------

def _addNet(scene, x1, y1, x2, y2):
    netItem = snet.schematicNet(QPoint(x1, y1), QPoint(x2, y2))
    scene.addItem(netItem)
    return netItem


def _addSchemPin(scene, x, y, name, direction="Input"):
    pinItem = shp.schematicPin(QPoint(x, y), name, direction, "Signal")
    scene.addItem(pinItem)
    return pinItem


def _scenePinItems(scene):
    pins = [item for item in scene.items()
            if isinstance(item, shp.schematicPin)]
    for symbolItem in scene.findSceneSymbolSet():
        pins.extend(symbolItem.pins.values())
    return pins


def test_parity_with_nameSceneNets_simple(qapp):
    """Engine and legacy naming agree on geometry without T contacts."""
    scene = makeSchematicScene()
    netA = _addNet(scene, 0, 0, 100, 0)
    netB = _addNet(scene, 100, 0, 200, 0)  # joins netA at endpoint
    netC = _addNet(scene, 0, 50, 100, 50)  # disjoint
    _addSchemPin(scene, 0, 0, "in")
    scene.nameSceneNets()
    legacy = {item: item.name for item in (netA, netB, netC)}

    pins = _scenePinItems(scene)
    result, segMap, _ = analyzeItems([netA, netB, netC], pins,
                                     portTol=min(scene.snapTuple))
    for netItem in (netA, netB, netC):
        segId = next(i for i, item in segMap.items() if item is netItem)
        assert result.segName[segId][0] == legacy[netItem]
    assert legacy[netA] == legacy[netB] == "in"
    assert legacy[netC].startswith("net")


def test_parity_set_name_propagation(qapp):
    scene = makeSchematicScene()
    netA = _addNet(scene, 0, 0, 100, 0)
    netB = _addNet(scene, 100, 0, 200, 0)
    netA.name = "vdd"
    netA.nameStrength = snet.netNameStrengthEnum.SET
    scene.nameSceneNets()
    assert netB.name == "vdd"

    result, segMap, _ = analyzeItems([netA, netB], [])
    segId = next(i for i, item in segMap.items() if item is netB)
    assert result.segName[segId][0] == "vdd"


def test_parity_t_contact_difference_is_deliberate(qapp):
    """Endpoint-on-body T contacts join — the adopted check-context
    semantic. The retired endpoint-only checkNetConnect auto-named the
    T-contacted wire instead; this was the deliberate correctness fix."""
    scene = makeSchematicScene()
    netA = _addNet(scene, 0, 0, 200, 0)
    netB = _addNet(scene, 100, 0, 100, 100)  # T contact at (100,0)
    netA.name = "bus"
    netA.nameStrength = snet.netNameStrengthEnum.SET
    scene.nameSceneNets()
    assert netB.name == "bus"  # joined via T contact

    result, segMap, _ = analyzeItems([netA, netB], [])
    segIdB = next(i for i, item in segMap.items() if item is netB)
    assert result.segName[segIdB][0] == "bus"


def test_parity_global_pin(qapp):
    scene = makeSchematicScene()
    pin = shp.symbolPin(QPoint(0, 0), "gnd!", "Inout", "Signal")
    symbolItem = shp.schematicSymbol([pin], {})
    symbolItem.instanceName = "I0"
    scene.addItem(symbolItem)
    netA = _addNet(scene, -100, 0, 0, 0)
    netB = _addNet(scene, 0, 0, 200, 0)
    scene.nameSceneNets()
    assert netA.name == "gnd!"
    assert netB.name == "gnd!"

    pins = _scenePinItems(scene)
    result, segMap, _ = analyzeItems([netA, netB], pins,
                                     portTol=min(scene.snapTuple))
    for netItem in (netA, netB):
        segId = next(i for i, item in segMap.items() if item is netItem)
        assert result.segName[segId][0] == "gnd!"


if __name__ == "__main__":
    pytest.main()


def test_from_records_rotated_instance_pin_positions(qapp):
    """``ang`` on a sys record is the item's Qt rotation (CCW-positive).

    A pin at symbol-space (10,0) under ang=90 lands at loc + (0,10), not
    loc + (0,-10); a flip composes *outside* the rotation (Qt's manual
    transform matrix is outermost).
    """
    pinLocator = lambda lib, cell, view: {"p": (10, 0),
                                          "directions": {"p": "Inout"}}

    def pinEndpoint(ang, fl):
        records = [
            {"type": "sys", "lib": "lib", "cell": "c", "view": "symbol",
             "nam": "I0", "loc": (100, 0), "ang": ang, "fl": fl, "ld": {}},
        ]
        _, ports, _ = fromRecords(records, pinLocator=pinLocator)
        assert len(ports) == 1
        return ports[0].point

    def assertPt(ang, fl, expected):
        x, y = pinEndpoint(ang, fl)
        assert (x, y) == pytest.approx(expected, abs=1e-6)

    assertPt(0, (1, 1), (110, 0))
    assertPt(90, (1, 1), (100, 10))
    assertPt(-90, (1, 1), (100, -10))
    assertPt(180, (1, 1), (90, 0))
    assertPt(0, (-1, 1), (90, 0))
    # rotate first, then flip: rotate(10,0,90)=(0,10) -> flipx -> (0,10)
    assertPt(90, (-1, 1), (100, 10))
    # rotate(10,0,270)=(0,-10) -> flipy -> (0,10)
    assertPt(270, (1, -1), (100, 10))


def test_from_records_rotated_instance_connects(qapp):
    """A wire ending at the rotated pin's true position must join."""
    pinLocator = lambda lib, cell, view: {"p": (10, 0),
                                          "directions": {"p": "Inout"}}
    records = [
        {"type": "scn", "st": (100, 10), "end": (100, 60), "nam": "n",
         "ns": 3},
        {"type": "sys", "lib": "lib", "cell": "c", "view": "symbol",
         "nam": "I0", "loc": (100, 0), "ang": 90, "fl": (1, 1), "ld": {}},
    ]
    result, diagnostics = analyzeRecords(records, pinLocator=pinLocator)
    assert diagnostics == []
    assert result.portGroup[0] == 0  # pin joins the wire's group
