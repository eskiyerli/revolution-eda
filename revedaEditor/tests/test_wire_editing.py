import pytest
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication

import revedaEditor.common.net as snet
from revedaEditor.tests.sceneTestUtils import makeSchematicScene


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def scene(qapp):
    return makeSchematicScene()


def _nets(scene):
    return [item for item in scene.items()
            if isinstance(item, snet.schematicNet)
            and item.draftLine.length() >= 1]


def _endpoints(scene):
    return sorted(tuple(p.toTuple()) for net in _nets(scene)
                  for p in net.sceneEndPoints)


def _finishAt(scene, point):
    scene.mouseMoveLoc = point
    scene._finishWire()


def test_auto_route_l_and_single_undo_macro(scene):
    scene.editModes.setMode("drawWire")
    scene._handleDrawNet(QPoint(0, 0))
    scene._handleDrawNet(QPoint(100, 50))
    assert len(_nets(scene)) == 2
    assert (100, 0) in _endpoints(scene)  # horizontal-first corner
    _finishAt(scene, QPoint(100, 50))
    assert len(_nets(scene)) == 2
    assert scene.undoStack.count() == 1
    scene.undoStack.undo()
    assert len(_nets(scene)) == 0
    scene.undoStack.redo()
    assert len(_nets(scene)) == 2


@pytest.mark.parametrize("start,end", [
    (QPoint(110, 0), QPoint(210, 0)),
    (QPoint(0, 10), QPoint(100, 10)),
    (QPoint(100, 10), QPoint(100, 110)),
])
def test_drawing_near_existing_net_preserves_both_geometries(scene, start, end):
    scene.editModes.setMode("drawWire")
    scene._handleDrawNet(QPoint(0, 0))
    scene._handleDrawNet(QPoint(100, 0))
    _finishAt(scene, QPoint(100, 0))
    scene._handleDrawNet(start)
    scene._handleDrawNet(end)
    _finishAt(scene, end)
    assert {tuple(p.toTuple() for p in net.sceneEndPoints)
            for net in _nets(scene)} == {
        ((0, 0), (100, 0)), (start.toTuple(), end.toTuple())}


def test_drawing_truly_overlapping_net_still_merges(scene):
    scene.editModes.setMode("drawWire")
    scene._handleDrawNet(QPoint(0, 0))
    scene._handleDrawNet(QPoint(100, 0))
    _finishAt(scene, QPoint(100, 0))
    scene._handleDrawNet(QPoint(50, 0))
    scene._handleDrawNet(QPoint(150, 0))
    _finishAt(scene, QPoint(150, 0))
    assert _endpoints(scene) == [(0, 0), (150, 0)]


def test_drawing_net_at_existing_endpoint_merges(scene):
    scene.editModes.setMode("drawWire")
    scene._handleDrawNet(QPoint(0, 0))
    scene._handleDrawNet(QPoint(100, 0))
    _finishAt(scene, QPoint(100, 0))
    scene._handleDrawNet(QPoint(100, 0))
    scene._handleDrawNet(QPoint(200, 0))
    _finishAt(scene, QPoint(200, 0))
    assert _endpoints(scene) == [(0, 0), (200, 0)]


def test_t_junction_splits_and_auto_terminates(scene):
    scene.editModes.setMode("drawWire")
    scene._handleDrawNet(QPoint(0, 0))
    scene._handleDrawNet(QPoint(200, 0))
    _finishAt(scene, QPoint(200, 0))
    assert len(_nets(scene)) == 1
    scene._handleDrawNet(QPoint(100, 100))
    scene._handleDrawNet(QPoint(100, 0))  # lands on wire body
    assert scene._newNet is None
    assert len(_nets(scene)) == 3
    assert _endpoints(scene).count((100, 0)) == 3  # junction vertex


def test_pop_wire_vertex_resumes_chain(scene):
    scene.editModes.setMode("drawWire")
    scene._wireAutoRoute = False
    scene._handleDrawNet(QPoint(0, 300))
    scene._handleDrawNet(QPoint(100, 300))
    scene._handleDrawNet(QPoint(100, 400))
    assert len(_nets(scene)) == 2
    scene.popWireVertex()
    assert len(_nets(scene)) == 1
    assert (100, 400) not in _endpoints(scene)
    assert scene._newNet is not None
    assert scene._newNet.sceneEndPoints[0] == QPoint(100, 300)


def test_body_stretch_slides_segment(scene):
    body = snet.schematicNet(QPoint(0, 500), QPoint(200, 500))
    scene.addItem(body)
    scene.editModes.setMode("stretchItem")
    assert scene._initiateStretch(QPoint(100, 500))
    scene._updateBodyStretch(QPoint(100, 550))
    scene._completeStretch(QPoint(100, 550))
    assert len(_nets(scene)) == 1
    assert tuple(_nets(scene)[0].sceneEndPoints[0].toTuple()) == (0, 550)
    assert tuple(_nets(scene)[0].sceneEndPoints[1].toTuple()) == (200, 550)


def test_body_stretch_rubber_bands_neighbours(scene):
    scene.addItem(snet.schematicNet(QPoint(0, 600), QPoint(200, 600)))
    scene.addItem(snet.schematicNet(QPoint(200, 600), QPoint(200, 700)))
    scene.editModes.setMode("stretchItem")
    assert scene._initiateStretch(QPoint(100, 600))
    scene._completeStretch(QPoint(100, 650))
    ends = _endpoints(scene)
    assert (0, 650) in ends and (200, 650) in ends
    assert (200, 700) in ends  # attached net still reaches moved end


def test_net_name_auto_increment(scene):
    scene.netNameString = "n<0:2>"
    scene._netNameAuto = None
    assert scene._nextNetName() == "n<0>"
    assert scene._nextNetName() == "n<1>"
    assert scene._nextNetName() == "n<2>"
    assert scene.netNameString is None
    scene.netNameString = "x<5>"
    scene._netNameAuto = None
    assert scene._nextNetName() == "x<5>"
    assert scene._nextNetName() == "x<6>"
    scene.netNameString = "plain"
    scene._netNameAuto = None
    assert scene._nextNetName() == "plain"
    assert scene._nextNetName() == "plain"


def test_add_stretch_wires_l_route_orientation(scene):
    segs = scene.addStretchWires(QPoint(0, 0), QPoint(100, 50), True)
    assert len(segs) == 2
    assert tuple(segs[0].sceneEndPoints[0].toTuple()) == (0, 0)
    assert tuple(segs[0].sceneEndPoints[1].toTuple()) == (100, 0)
    segs = scene.addStretchWires(QPoint(0, 0), QPoint(100, 50), False)
    assert tuple(segs[0].sceneEndPoints[1].toTuple()) == (0, 50)


def test_uncommitted_wire_leaves_no_undo_entry(scene):
    # Click once then finish at the same point: the draft is dropped and the
    # empty "Draw Wire" macro must not linger on the undo stack.
    scene.editModes.setMode("drawWire")
    scene._handleDrawNet(QPoint(0, 0))
    _finishAt(scene, QPoint(0, 0))
    assert len(_nets(scene)) == 0
    assert not scene.undoStack.canUndo()


def test_wire_draw_mode_cycling(scene):
    assert scene._wireDrawMode == snet.NetMode.ORTHOGONAL
    scene.cycleWireDrawMode()
    assert scene._wireDrawMode == snet.NetMode.DIAGONAL
    scene.cycleWireDrawMode()
    assert scene._wireDrawMode == snet.NetMode.FREE
    scene.cycleWireDrawMode()
    assert scene._wireDrawMode == snet.NetMode.ORTHOGONAL


def test_wire_body_snap(scene):
    scene.addItem(snet.schematicNet(QPoint(0, 800), QPoint(200, 800)))
    point, isConn = scene.findSnapTarget(QPoint(103, 803), set())
    assert isConn and point == QPoint(100, 800)


def test_snap_does_not_jump_a_grid(scene):
    # A pin one grid row above the cursor must not pull the wire end away
    # from the plain grid point: snapping never relocates the endpoint by a
    # snap distance or more.
    pin = snet.schematicNet(QPoint(100, 0), QPoint(100, 0))
    scene.addItem(pin)
    # cursor 8px below the pin: grid point (100, 10) wins, no jump.
    point, isConn = scene.findSnapTarget(QPoint(98, 8), set())
    assert point == QPoint(100, 10) and not isConn
    # cursor essentially on the pin: snap engages.
    point, isConn = scene.findSnapTarget(QPoint(98, 3), set())
    assert isConn and point == QPoint(100, 0)


def test_snap_terminates_on_grid_coincidence(scene):
    # Grid point coincides with a connection point: wire must terminate even
    # though the raw cursor is outside the snap radius.
    pin = snet.schematicNet(QPoint(100, 0), QPoint(100, 0))
    scene.addItem(pin)
    point, isConn = scene.findSnapTarget(QPoint(96, 4), set())
    assert point == QPoint(100, 0) and isConn


def test_parallel_wire_not_welded_at_one_grid(scene):
    # A wire body one grid below the cursor's row must not capture the end.
    scene.addItem(snet.schematicNet(QPoint(0, 0), QPoint(200, 0)))
    point, isConn = scene.findSnapTarget(QPoint(103, 8), set())
    assert point == QPoint(100, 10) and not isConn


if __name__ == "__main__":
    pytest.main()
