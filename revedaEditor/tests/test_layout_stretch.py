import pytest
from PySide6.QtCore import QPoint, QPointF, QLineF
from PySide6.QtWidgets import QApplication, QGraphicsScene

import revedaEditor.backend.undoStack as us
from revedaEditor.common import layoutShapes as lshp
from defaultPDK.layoutLayers import odLayer_drw


@pytest.fixture(scope="module", autouse=True)
def init_qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def _makePath(mode: int = 0) -> lshp.layoutPath:
    return lshp.layoutPath(
        QLineF(QPointF(0, 0), QPointF(100, 0)),
        odLayer_drw,
        width=10.0,
        startExtend=5,
        endExtend=10,
        mode=mode,
    )


def test_path_nearest_end_pick():
    scene = QGraphicsScene()
    path = _makePath()
    scene.addItem(path)

    side, anchor = path._nearestStretchEnd(QPointF(90, 5))
    assert side == "p2"
    assert anchor == QPointF(0, 0)

    side, anchor = path._nearestStretchEnd(QPointF(10, 5))
    assert side == "p1"
    assert anchor == QPointF(100, 0)


def test_path_stretch_manhattan_end():
    scene = QGraphicsScene()
    path = _makePath(mode=0)
    scene.addItem(path)

    path._stretchSide, path._anchorScene = path._nearestStretchEnd(
        QPointF(90, 5)
    )
    path._stretchToScenePoint(QPointF(150, 30))

    # Anchor stays put; manhattan mode projects the end onto the x axis.
    assert path.sceneEndPoints[0] == QPoint(0, 0)
    assert path.sceneEndPoints[1] == QPoint(150, 0)


def test_path_stretch_p1_restores_orientation_and_extends():
    scene = QGraphicsScene()
    path = _makePath()
    scene.addItem(path)

    # Grab the p1 end: anchor becomes the original p2.
    path._stretchSide, path._anchorScene = path._nearestStretchEnd(
        QPointF(5, 0)
    )
    path._stretchToScenePoint(QPointF(-60, 0))
    assert path.sceneEndPoints[0] == QPoint(100, 0)
    assert path.sceneEndPoints[1] == QPoint(-60, 0)

    # On release the grabbed end becomes dfl1 again and the extends keep
    # their original physical ends.
    path._restoreStretchOrientation()
    assert path.sceneEndPoints[0] == QPoint(-60, 0)
    assert path.sceneEndPoints[1] == QPoint(100, 0)
    assert path.startExtend == 5
    assert path.endExtend == 10


def test_path_stretch_moved_item():
    scene = QGraphicsScene()
    path = _makePath()
    scene.addItem(path)
    path.setPos(50, 20)

    path._stretchSide, path._anchorScene = path._nearestStretchEnd(
        QPointF(140, 20)
    )
    assert path._stretchSide == "p2"
    path._stretchToScenePoint(QPointF(200, 20))

    assert path.sceneEndPoints[0] == QPoint(50, 20)
    assert path.sceneEndPoints[1] == QPoint(200, 20)


def test_path_capture_restore_geometry():
    scene = QGraphicsScene()
    path = _makePath()
    scene.addItem(path)

    state = path.captureGeometry()
    path._stretchSide, path._anchorScene = path._nearestStretchEnd(
        QPointF(90, 0)
    )
    path._stretchToScenePoint(QPointF(200, 0))
    assert path.sceneEndPoints[1] == QPoint(200, 0)

    path.restoreGeometry(state)
    assert path.sceneEndPoints[0] == QPoint(0, 0)
    assert path.sceneEndPoints[1] == QPoint(100, 0)


def test_path_stretch_undo_redo():
    scene = QGraphicsScene()
    scene.undoStack = us.undoStack()
    path = _makePath()
    scene.addItem(path)

    path._stretchOldGeometry = path.captureGeometry()
    path._stretchSide, path._anchorScene = path._nearestStretchEnd(
        QPointF(90, 0)
    )
    path._stretchToScenePoint(QPointF(160, 0))
    path._pushStretchUndo()

    assert path.sceneEndPoints[1] == QPoint(160, 0)
    scene.undoStack.undo()
    assert path.sceneEndPoints[1] == QPoint(100, 0)
    scene.undoStack.redo()
    assert path.sceneEndPoints[1] == QPoint(160, 0)


def test_path_cancel_stretch_restores_geometry():
    scene = QGraphicsScene()
    path = _makePath()
    scene.addItem(path)

    path._stretch = True
    path._stretchOldGeometry = path.captureGeometry()
    path._stretchSide, path._anchorScene = path._nearestStretchEnd(
        QPointF(90, 0)
    )
    path._stretchToScenePoint(QPointF(300, 0))

    path.cancelStretch()
    assert path.sceneEndPoints[1] == QPoint(100, 0)
    assert path.stretch is False
    assert path._stretchSide is None


def test_rect_capture_restore_geometry():
    scene = QGraphicsScene()
    rect = lshp.layoutRect(QPoint(0, 0), QPoint(100, 100), odLayer_drw)
    scene.addItem(rect)

    state = rect.captureGeometry()
    rect.rect.setRight(150)
    rect.restoreGeometry(state)
    assert rect.rect.right() == 100


def test_pin_capture_restore_geometry():
    scene = QGraphicsScene()
    pin = lshp.layoutPin(
        QPoint(0, 0), QPoint(100, 100), "p1", "Input", "Signal", odLayer_drw
    )
    scene.addItem(pin)

    state = pin.captureGeometry()
    pin.rect.setTop(50)
    pin.restoreGeometry(state)
    assert pin.rect.top() == 0


def test_polygon_capture_restore_geometry():
    scene = QGraphicsScene()
    points = [QPoint(0, 0), QPoint(100, 0), QPoint(100, 100), QPoint(0, 100)]
    poly = lshp.layoutPolygon(points, odLayer_drw)
    scene.addItem(poly)

    state = poly.captureGeometry()
    poly.points = [QPoint(0, 0), QPoint(50, 0), QPoint(100, 100), QPoint(0, 100)]
    poly.restoreGeometry(state)
    assert poly.points[1] == QPoint(100, 0)
