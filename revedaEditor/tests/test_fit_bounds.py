"""Regression test: fitItemsInView must not feed back through items whose
boundingRect depends on the current view zoom (layoutRuler's inverse-scaled
label margin). Each 'f' press used to zoom out further."""

import pytest
from PySide6.QtCore import QLineF, QPoint
from PySide6.QtGui import QFont, QTransform
from PySide6.QtWidgets import QApplication, QGraphicsView

from defaultPDK.layoutLayers import m1Layer_drw
import revedaEditor.common.layoutShapes as lshp
from revedaEditor.tests.sceneTestUtils import makeLayoutScene


@pytest.fixture(scope="module", autouse=True)
def init_qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_fit_items_in_view_stable_with_ruler():
    scene = makeLayoutScene()
    scene.addItem(lshp.layoutRect(QPoint(0, 0), QPoint(100, 100), m1Layer_drw))
    ruler = lshp.layoutRuler(QLineF(0, 0, 500, 0), width=2,
                             tickFont=QFont("Arial", 12))
    scene.addItem(ruler)

    view = QGraphicsView(scene)
    view.resize(800, 600)

    # Start zoomed in; repeated fits must converge (the first press can
    # shift once as Qt settles scrollbars — that predates this fix), but
    # must never zoom out further on each press.
    view.setTransform(QTransform().scale(10.0, 10.0))
    scales = []
    for _ in range(3):
        scene.fitItemsInView()
        QApplication.processEvents()
        t = view.transform()
        scales.append((t.m11() ** 2 + t.m12() ** 2) ** 0.5)

    assert scales[0] > 0
    assert scales[2] == pytest.approx(scales[1])
    assert scales[2] >= scales[1]
    # The ruler's shape bound (line + ticks + fixed margin) is covered, so
    # a sane fit includes the design, not a huge label margin.
    assert scene.sceneRect().width() < 50000
