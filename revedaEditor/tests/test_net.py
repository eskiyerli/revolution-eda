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


# NOTE: the former ``test_inheritNetName_*`` matrix was removed together with
# the dead ``schematicNet.inheritNetName`` pairwise resolver. The strength
# resolution it exercised (SET/INHERIT/WEAK/NONAME propagation and conflict
# flagging) is owned by the single connectivity engine and is covered by
# ``test_connectivity.py`` (e.g. ``test_set_name_propagates``,
# ``test_schematic_pin_names_net_inherit``, ``test_set_name_conflict_flagged``
# and the ``test_parity_*`` cases against ``nameSceneNets``).


def test_mergeNetName_higher_strength_wins(setup_nets):
    net1, net2, scene = setup_nets
    net1.name = "weakNet"
    net1.nameStrength = netNameStrengthEnum.WEAK
    net2.name = "setNet"
    net2.nameStrength = netNameStrengthEnum.SET
    result = net1.mergeNetName(net2)
    assert result
    assert net1.name == "setNet"
    assert net1.nameStrength == netNameStrengthEnum.INHERIT


def test_mergeNetName_equal_strength_conflict(setup_nets):
    net1, net2, scene = setup_nets
    net1.name = "a"
    net1.nameStrength = netNameStrengthEnum.SET
    net2.name = "b"
    net2.nameStrength = netNameStrengthEnum.SET
    result = net1.mergeNetName(net2)
    assert not result
    assert net1.nameConflict
    assert net2.nameConflict


def test_mergeNetName_self_higher_strength_kept(setup_nets):
    net1, net2, scene = setup_nets
    net1.name = "keepMe"
    net1.nameStrength = netNameStrengthEnum.SET
    net2.name = "weak"
    net2.nameStrength = netNameStrengthEnum.WEAK
    result = net1.mergeNetName(net2)
    assert result
    assert net1.name == "keepMe"


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
