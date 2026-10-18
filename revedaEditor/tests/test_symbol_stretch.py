"""Symbol-shape stretch regression: the snapped scene target must be
mapped back to item coordinates, or stretching an item whose pos() is
non-zero (moved, or loaded with a non-zero ``loc``) jumps the dragged
edge/endpoint by the item offset."""

import pytest
from PySide6.QtCore import QPoint, QPointF
from PySide6.QtWidgets import QApplication

import revedaEditor.common.shapes as shp
from revedaEditor.tests.sceneTestUtils import makeSchematicScene


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def scene(qapp):
    return makeSchematicScene()


class _FakeMouseEvent:
    """Stand-in for QGraphicsSceneMouseEvent: the stretch branches only
    read scenePos()/pos()."""

    def __init__(self, scenePos):
        self._scenePos = QPointF(scenePos)

    def scenePos(self):
        return self._scenePos

    def pos(self):
        return self._scenePos


def test_moved_line_stretch_end_lands_on_scene_point(scene):
    line = shp.symbolLine(QPoint(0, 0), QPoint(100, 0))
    scene.addItem(line)
    line.setPos(QPoint(50, 40))
    line._stretchSide = "end"
    line.mouseMoveEvent(_FakeMouseEvent(QPoint(200, 100)))
    assert line.mapToScene(line.end).toPoint() == QPoint(200, 100)


def test_moved_line_stretch_start_lands_on_scene_point(scene):
    line = shp.symbolLine(QPoint(50, 50), QPoint(150, 50))
    scene.addItem(line)
    line.setPos(QPoint(30, 20))
    line._stretchSide = "start"
    line.mouseMoveEvent(_FakeMouseEvent(QPoint(0, 0)))
    assert line.mapToScene(line.start).toPoint() == QPoint(0, 0)


def test_unmoved_line_stretch_end(scene):
    line = shp.symbolLine(QPoint(0, 0), QPoint(100, 0))
    scene.addItem(line)
    line._stretchSide = "end"
    line.mouseMoveEvent(_FakeMouseEvent(QPoint(230, 70)))
    assert line.end == QPoint(230, 70)


def test_moved_rect_stretch_edge_lands_on_scene_point(scene):
    rect = shp.symbolRectangle(QPoint(0, 0), QPoint(100, 50))
    scene.addItem(rect)
    rect.setPos(QPoint(40, 30))
    rect.stretch = True
    rect._stretchSide = shp.symbolRectangle.sides[1]  # "Right"
    rect.mouseMoveEvent(_FakeMouseEvent(QPoint(210, 77)))
    assert rect.rect.right() == 170
    assert rect.mapToScene(QPointF(rect.rect.right(), 0)).x() == 210


def test_moved_polygon_stretch_corner_lands_on_scene_point(scene):
    poly = shp.symbolPolygon(
        [QPoint(0, 0), QPoint(100, 0), QPoint(100, 100)])
    scene.addItem(poly)
    poly.setPos(QPoint(30, 20))
    poly.stretch = True
    poly._selectedCornerIndex = 2
    poly.mouseMoveEvent(_FakeMouseEvent(QPoint(160, 130)))
    assert poly.points[2] == QPoint(130, 110)
    assert poly.mapToScene(poly.points[2]).toPoint() == QPoint(160, 130)
