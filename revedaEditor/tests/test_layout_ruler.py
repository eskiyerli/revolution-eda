import pytest
from PySide6.QtCore import QPoint, QPointF, QRectF, QLineF, Qt
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import QApplication, QGraphicsScene

from revedaEditor.common import layoutShapes as lshp
from defaultPDK.layoutLayers import odLayer_drw


@pytest.fixture(scope="module", autouse=True)
def init_qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


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

    ruler = lshp.layoutRuler(
        draftLine=QLineF(QPointF(0, 0), QPointF(50, 50)),
        width=1.0,
        tickGap=10.0,
        tickLength=5,
        tickFont=QFont("Arial", 10),
    )
    scene.addItem(ruler)

    query_qpoint = QPoint(150, 95)
    snapped = ruler.snapPointToClosestEdge(query_qpoint, maxDistance=20.0)
    assert snapped == QPointF(150, 100)

    far_query = QPoint(0, 0)
    snapped_far = ruler.snapPointToClosestEdge(far_query, maxDistance=20.0)
    assert snapped_far == QPointF(0, 0)


def test_ruler_ticks_calculation():
    ruler = lshp.layoutRuler(
        draftLine=QLineF(QPointF(0, 0), QPointF(100, 0)),
        width=1.0,
        tickGap=25.0,
        tickLength=5,
        tickFont=QFont("Arial", 10),
    )
    labels = [t.text for t in ruler._tickTuples if t.text]
    assert "0" in labels
    assert "100" in labels
    # Verify labels aren't crowded
    assert len(labels) <= 10


def test_ruler_large_distance_uncrowded_labels():
    ruler = lshp.layoutRuler(
        draftLine=QLineF(QPointF(0, 0), QPointF(5000, 0)),
        width=1.0,
        tickGap=1.0,
        tickLength=5,
        tickFont=QFont("Arial", 10),
    )
    text_labels = [t.text for t in ruler._tickTuples if t.text]
    # For a distance of 5000 units, text labels should be limited to ~5-10 clean intervals
    assert len(text_labels) <= 12
    assert "0" in text_labels
    assert "5000" in text_labels


def test_ruler_text_angle_upright():
    scene = QGraphicsScene()
    r1 = lshp.layoutRuler(QLineF(0, 0, 100, 0), 1.0, 10.0, 5, QFont())
    scene.addItem(r1)
    p1 = r1.mapToScene(r1._draftLine.p1())
    p2 = r1.mapToScene(r1._draftLine.p2())
    assert QLineF(p1, p2).angle() == 0.0

    r2 = lshp.layoutRuler(QLineF(100, 0, 0, 0), 1.0, 10.0, 5, QFont())
    scene.addItem(r2)
    p1_2 = r2.mapToScene(r2._draftLine.p1())
    p2_2 = r2.mapToScene(r2._draftLine.p2())
    assert QLineF(p1_2, p2_2).angle() == 180.0
