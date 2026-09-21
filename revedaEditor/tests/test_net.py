import pytest
from PySide6.QtCore import (QPoint, QLineF)
from PySide6.QtGui import QPen
from PySide6.QtWidgets import (QGraphicsScene, QGraphicsView)

import revedaEditor.common.net as snet
from revedaEditor.common.net import schematicNet, netNameStrengthEnum


@pytest.fixture
def setup_nets(qtbot):
    net1 = schematicNet(QPoint(0, 0), QPoint(10, 10))
    net2 = schematicNet(QPoint(10, 10), QPoint(20, 20))
    view = QGraphicsView()
    qtbot.addWidget(view)
    scene = QGraphicsScene()
    view.setScene(scene)
    scene.addItem(net1)
    scene.addItem(net2)
    return net1, net2, scene


def test_inheritNetName_set_to_noname(setup_nets):
    net1, net2, scene = setup_nets
    net1.nameStrength = netNameStrengthEnum.SET
    net1.name = "Net1"
    net2.nameStrength = netNameStrengthEnum.NONAME
    result = net1.inheritNetName(net2)
    assert result
    assert net2.name == "Net1"
    assert net2.nameStrength == netNameStrengthEnum.INHERIT


def test_inheritNetName_set_to_inherit(setup_nets):
    net1, net2, scene = setup_nets
    net1.nameStrength = netNameStrengthEnum.SET
    net1.name = "Net1"
    net2.nameStrength = netNameStrengthEnum.INHERIT
    result = net1.inheritNetName(net2)
    assert result
    assert net2.name == "Net1"
    assert net2.nameStrength == netNameStrengthEnum.INHERIT


def test_inheritNetName_set_to_set_conflict(setup_nets):
    net1, net2, scene = setup_nets
    net1.nameStrength = netNameStrengthEnum.SET
    net1.name = "Net1"
    net2.nameStrength = netNameStrengthEnum.SET
    net2.name = "Net2"
    result = net1.inheritNetName(net2)
    assert not result
    assert net1.nameConflict
    assert net2.nameConflict


def test_inheritNetName_inherit_to_noname(setup_nets):
    net1, net2, scene = setup_nets
    # Assigning .name forces SET strength; override strength afterwards.
    net1.name = "Net1"
    net1.nameStrength = netNameStrengthEnum.INHERIT
    net2.name = "Net2"
    net2.nameStrength = netNameStrengthEnum.NONAME
    result = net1.inheritNetName(net2)
    assert result
    assert net2.name == "Net1"
    assert net2.nameStrength == netNameStrengthEnum.INHERIT


def test_inheritNetName_inherit_to_weak(setup_nets):
    net1, net2, scene = setup_nets
    net1.name = "Net1"
    net1.nameStrength = netNameStrengthEnum.INHERIT
    net2.name = "Net2"
    net2.nameStrength = netNameStrengthEnum.WEAK
    result = net1.inheritNetName(net2)
    assert result
    assert net2.name == "Net1"
    assert net2.nameStrength == netNameStrengthEnum.INHERIT


def test_inheritNetName_inherit_to_inherit(setup_nets):
    net1, net2, scene = setup_nets
    net1.nameStrength = netNameStrengthEnum.INHERIT
    net1.name = "Net1"
    net2.nameStrength = netNameStrengthEnum.INHERIT
    net2.name = "Net2"
    result = net1.inheritNetName(net2)
    assert not result
    assert net1.nameConflict
    assert net2.nameConflict


def test_inheritNetName_inherit_to_set(setup_nets):
    net1, net2, scene = setup_nets
    net1.name = "Net1"
    net1.nameStrength = netNameStrengthEnum.INHERIT
    net2.name = "Net2"
    net2.nameStrength = netNameStrengthEnum.SET
    result = net1.inheritNetName(net2)
    assert result
    assert net1.name == "Net2"
    assert net1.nameStrength == netNameStrengthEnum.INHERIT


def test_inheritNetName_weak_to_noname(setup_nets):
    net1, net2, scene = setup_nets
    net1.name = "Net1"
    net1.nameStrength = netNameStrengthEnum.WEAK
    net2.nameStrength = netNameStrengthEnum.NONAME
    result = net1.inheritNetName(net2)
    assert result
    assert net2.name == "Net1"
    assert net2.nameStrength == netNameStrengthEnum.WEAK


def test_inheritNetName_weak_to_weak_different_name(setup_nets):
    net1, net2, scene = setup_nets
    net1.nameStrength = netNameStrengthEnum.WEAK
    net1.name = "Net1"
    net2.nameStrength = netNameStrengthEnum.WEAK
    net2.name = "Net2"
    result = net1.inheritNetName(net2)
    assert not result


def test_inheritNetName_weak_to_same_name(setup_nets):
    net1, net2, scene = setup_nets
    net1.name = "Net1"
    net1.nameStrength = netNameStrengthEnum.WEAK
    net2.name = "Net1"
    net2.nameStrength = netNameStrengthEnum.WEAK
    result = net1.inheritNetName(net2)
    assert result
    assert net2.name == "Net1"
    assert net2.nameStrength == netNameStrengthEnum.WEAK


def test_inheritNetName_weak_to_inherit(setup_nets):
    net1, net2, scene = setup_nets
    net1.name = "Net1"
    net1.nameStrength = netNameStrengthEnum.WEAK
    net2.name = "Net2"
    net2.nameStrength = netNameStrengthEnum.INHERIT
    result = net1.inheritNetName(net2)
    assert result
    assert net1.name == "Net2"
    assert net1.nameStrength == netNameStrengthEnum.INHERIT


def test_inheritNetName_weak_to_set(setup_nets):
    net1, net2, scene = setup_nets
    net1.name = "Net1"
    net1.nameStrength = netNameStrengthEnum.WEAK
    net2.name = "Net2"
    net2.nameStrength = netNameStrengthEnum.SET
    result = net1.inheritNetName(net2)
    assert result
    assert net1.name == "Net2"
    assert net1.nameStrength == netNameStrengthEnum.INHERIT


def test_inheritNetName_noname_to_inherit(setup_nets):
    net1, net2, scene = setup_nets
    net1.nameStrength = netNameStrengthEnum.NONAME
    net1.name = ""
    net2.nameStrength = netNameStrengthEnum.INHERIT
    net2.name = "Net2"
    result = net1.inheritNetName(net2)
    assert result
    assert net1.name == "Net2"
    assert net1.nameStrength == netNameStrengthEnum.INHERIT


def test_inheritNetName_noname_to_set(setup_nets):
    net1, net2, scene = setup_nets
    net1.nameStrength = netNameStrengthEnum.NONAME
    net1.name = ""
    net2.nameStrength = netNameStrengthEnum.SET
    net2.name = "Net2"
    result = net1.inheritNetName(net2)
    assert result
    assert net1.name == "Net2"
    assert net1.nameStrength == netNameStrengthEnum.INHERIT


def test_inheritNetName_noname_to_noname(setup_nets):
    net1, net2, scene = setup_nets
    net1.nameStrength = netNameStrengthEnum.NONAME
    net1.name = ""
    net2.nameStrength = netNameStrengthEnum.NONAME
    net2.name = ""
    result = net1.inheritNetName(net2)
    assert result


def test_findOverlapNets_no_overlap(setup_nets):
    net1, net2, scene = setup_nets
    # collidingItems() uses shape() inflated by _clickMargin on both nets,
    # so the gap between endpoints must exceed twice the margin.
    net1.draftLine = QLineF(QPoint(0, 0), QPoint(0, 10))
    net2.draftLine = QLineF(QPoint(0, 40), QPoint(0, 50))
    overlap_nets = net1.findOverlapNets()
    assert len(overlap_nets) == 0


def test_findOverlapNets_with_overlap(setup_nets):
    net1, net2, scene = setup_nets
    net1.draftLine = QLineF(QPoint(0, 0), QPoint(20, 0))
    net2.draftLine = QLineF(QPoint(10, 0), QPoint(60, 0))
    overlap_nets = net1.findOverlapNets()
    assert len(overlap_nets) == 1
    assert net2 in overlap_nets


def test_schlyr_deferred_until_access(qapp):
    """schlyr must be a lazy proxy, not an eager top-level import.

    PDK layer modules (e.g. ihp_pdk.schLayers) import common.net while
    common.net is itself importing the PDK — an eager importPDKModule()
    at module top returns None inside a partially-initialized cycle.
    """
    assert type(snet.schlyr).__name__ == "_LazyPDKModule"
    # First access resolves and caches the real module.
    layer = snet.schlyr.wireHilightLayer
    assert layer.pcolor.isValid()


def test_netFlightLine_highlight_pen_resolves_pdk_layer(qapp):
    pen = snet.netFlightLine.wireHighlightPen()
    layer = snet.schlyr.wireHilightLayer
    assert isinstance(pen, QPen)
    assert pen.color() == layer.pcolor
    assert pen.widthF() == layer.pwidth


def test_findOverlapNets_multiple_overlaps(setup_nets):
    net1, net2, scene = setup_nets
    net3 = schematicNet(QPoint(5, 5), QPoint(15, 15))
    scene.addItem(net3)
    net1.draftLine = QLineF(QPoint(0, 0), QPoint(0, 20))
    net2.draftLine = QLineF(QPoint(0, 10), QPoint(0, 30))
    net3.draftLine = QLineF(QPoint(-10, 10), QPoint(10, 10))
    overlap_nets = net1.findOverlapNets()
    assert len(overlap_nets) == 2
    assert net2 in overlap_nets
    assert net3 in overlap_nets


if __name__ == "__main__":
    pytest.main()
