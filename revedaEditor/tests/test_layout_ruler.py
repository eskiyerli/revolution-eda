import math

import pytest
from PySide6.QtCore import QPoint, QPointF, QRectF, QLineF, Qt
from PySide6.QtGui import QFont, QColor, QTransform
from PySide6.QtWidgets import QApplication, QGraphicsScene

from revedaEditor.common import layoutShapes as lshp
from defaultPDK.layoutLayers import odLayer_drw
from defaultPDK import process as fabproc

DBU = fabproc.dbu


@pytest.fixture(scope="module", autouse=True)
def init_qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def _ruler(line, mode=0):
    return lshp.layoutRuler(QLineF(line), width=1.0,
                            tickFont=QFont("Arial", 10), mode=mode)


def test_closest_point_on_segment():
    a = QPointF(0, 0)
    b = QPointF(100, 0)
    p = QPoint(50, 10)
    res = lshp.layoutRuler._closestPointOnSegment(p, a, b)
    assert res == QPointF(50, 0)

    p_off = QPoint(150, 20)
    res_off = lshp.layoutRuler._closestPointOnSegment(p_off, a, b)
    assert res_off == QPointF(100, 0)


def test_ruler_snap_to_closest_edge_qpoint():
    scene = QGraphicsScene()
    rect = lshp.layoutRect(QPoint(100, 100), QPoint(300, 250), odLayer_drw)
    scene.addItem(rect)

    ruler = _ruler(QLineF(QPointF(0, 0), QPointF(50, 50)), mode=2)
    scene.addItem(ruler)

    query_qpoint = QPoint(150, 95)
    snapped = ruler.snapPointToClosestEdge(query_qpoint, maxDistance=20.0)
    assert snapped == QPointF(150, 100)

    far_query = QPoint(0, 0)
    snapped_far = ruler.snapPointToClosestEdge(far_query, maxDistance=20.0)
    assert snapped_far == QPointF(0, 0)


def test_ruler_orthogonal_constraint():
    # Default mode (0) snaps to the dominant axis.
    ruler = _ruler(QLineF(0, 0, 3000, 500))
    assert ruler.draftLine.p2() == QPointF(3000, 0)

    ruler.draftLine = QLineF(QPointF(0, 0), QPointF(500, 3000))
    assert ruler.draftLine.p2() == QPointF(0, 3000)


def test_ruler_diagonal_and_any_angle():
    diag = _ruler(QLineF(0, 0, 1000, 700), mode=1)
    p2 = diag.draftLine.p2()
    # Nearest 45-degree direction for a ~35-degree drag is 45 deg (down-right).
    assert p2.x() == pytest.approx(p2.y())
    assert QLineF(QPointF(0, 0), p2).length() == pytest.approx(
        math.hypot(1000, 700))

    anyAngle = _ruler(QLineF(0, 0, 1000, 700), mode=2)
    assert anyAngle.draftLine.p2() == QPointF(1000, 700)


def test_ruler_no_item_rotation():
    # The rewrite stores real endpoints: no residual item rotation.
    for line in (QLineF(0, 0, 3000, 0), QLineF(3000, 0, 0, 0),
                 QLineF(0, 0, 0, -3000), QLineF(0, 0, 2000, 2000)):
        ruler = _ruler(line, mode=2)
        assert ruler.rotation() == 0.0
        assert ruler.angle == 0
        ends = ruler.sceneEndPoints
        assert ends[0] == line.p1()
        assert ends[1] == line.p2()


def test_tick_marks_progressive_and_positive():
    ruler = _ruler(QLineF(0, 0, 3000, 0))  # 3 um at dbu=1000
    marks = ruler._tickMarks(scale=10.0)
    labels = [m[2] for m in marks if m[2]]
    assert labels[0] == "0"
    # End label is the total length in um.
    assert labels[-1] == "3"
    # All labels parse as non-negative, strictly ascending distances.
    values = [float(v) for v in labels]
    assert all(v >= 0 for v in values)
    assert values == sorted(values)


def test_tick_marks_right_to_left_positive():
    # Drawn right-to-left: geometry keeps direction, labels stay positive.
    ruler = _ruler(QLineF(3000, 0, 0, 0))
    marks = ruler._tickMarks(scale=10.0)
    labels = [m[2] for m in marks if m[2]]
    assert labels[0] == "0"
    assert labels[-1] == "3"
    assert all(float(v) >= 0 for v in labels)


def test_tick_density_adapts_to_zoom():
    ruler = _ruler(QLineF(0, 0, 5000, 0))  # 5 um
    zoomed_out = ruler._tickMarks(scale=0.5)
    zoomed_in = ruler._tickMarks(scale=20.0)
    out_labels = [m[2] for m in zoomed_out if m[2]]
    in_labels = [m[2] for m in zoomed_in if m[2]]
    assert out_labels[0] == "0" and out_labels[-1] == "5"
    assert in_labels[0] == "0" and in_labels[-1] == "5"
    # The same ruler shows more graduations when zoomed in.
    assert len(in_labels) >= len(out_labels)
    # Labeled marks never get closer than ~30 px on screen at any zoom.
    for marks, scale in ((zoomed_out, 0.5), (zoomed_in, 20.0)):
        labeled = [m[0] for m in marks if m[2]]
        for a, b in zip(labeled, labeled[1:]):
            assert (b - a) * scale >= 30.0
    # Minor ticks are hidden once they would render too close together.
    _, minor_out = ruler._tickSpacing(scale=0.5)
    assert minor_out == 0 or (
        minor_out * 0.5 >= lshp.layoutRuler._MINOR_TICK_PX)
    _, minor_in = ruler._tickSpacing(scale=20.0)
    assert minor_in > 0


def test_ruler_endpoint_stretch():
    scene = QGraphicsScene()
    ruler = _ruler(QLineF(0, 0, 3000, 0))
    scene.addItem(ruler)
    ruler._stretchSide = "p2"
    ruler._anchorScene = QPointF(0, 0)
    ruler._stretchToScenePoint(QPointF(4500, 20))
    assert ruler.sceneEndPoints[1] == QPointF(4500, 0)  # orthogonal snap

    # Stretching the p1 end keeps p2 anchored.
    ruler._stretchSide = "p1"
    ruler._anchorScene = QPointF(4500, 0)
    ruler._stretchToScenePoint(QPointF(1500, 900))
    assert ruler.sceneEndPoints[0] == QPointF(1500, 0)
    assert ruler.sceneEndPoints[1] == QPointF(4500, 0)


def test_ruler_stretch_geometry_undo_roundtrip():
    ruler = _ruler(QLineF(0, 0, 3000, 0))
    old = ruler.captureGeometry()
    ruler.draftLine = QLineF(QPointF(0, 0), QPointF(9000, 0))
    ruler.restoreGeometry(old)
    assert ruler.draftLine == QLineF(0, 0, 3000, 0)


def test_ruler_mode_switch_reconstrains_draft():
    ruler = _ruler(QLineF(0, 0, 1000, 700), mode=2)
    ruler.mode = 0
    p2 = ruler.draftLine.p2()
    assert p2 == QPointF(1000, 0) or p2 == QPointF(0, 700)
