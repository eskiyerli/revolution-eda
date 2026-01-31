import pytest
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import (QGraphicsScene, QGraphicsView)

from revedaEditor.common.shapes import schematicSymbol, symbolPin


@pytest.fixture
def setup_shape(qtbot):
    pin1 = symbolPin(QPoint(0, 0), "pin1", "Input", "Signal")
    pin2 = symbolPin(QPoint(0, 10), "pin2", "Output", "Signal")
    pin3 = symbolPin(QPoint(0, 20), "pin3", "Input", "Signal")
    symattrs = {"pinOrder": "pin1, pin2, pin3"}
    shapes = [pin1, pin2, pin3]
    shape = schematicSymbol(shapes, symattrs)
    view = QGraphicsView()
    qtbot.addWidget(view)
    scene = QGraphicsScene()
    view.setScene(scene)
    scene.addItem(shape)
    return (shape, scene, pin1, pin2, pin3)


def test_pins_without_pin_order(setup_shape):
    shape, scene, pin1, pin2, pin3 = setup_shape
    shape.symattrs = {}
    assert shape.pins == {
        "pin1": pin1,
        "pin2": pin2,
        "pin3": pin3}


def test_pins_with_pin_order(setup_shape):
    shape, scene, pin1, pin2, pin3 = setup_shape
    shape.symattrs = {"pinOrder": "pin1, pin2, pin3"}
    assert shape.pins == {
        "pin1": pin1,
        "pin2": pin2,
        "pin3": pin3}


def test_pins_with_changed_order(setup_shape):
    shape, scene, pin1, pin2, pin3 = setup_shape
    shape.symattrs = {"pinOrder": "pin2, pin1, pin3"}
    assert shape.pins == {"pin2": pin2, "pin1": pin1, "pin3": pin3}


def test_pins_with_partial_order(setup_shape):
    shape, scene, pin1, pin2, pin3 = setup_shape
    shape.symattrs = {"pinOrder": "pin2, pin3"}
    assert shape.pins == {"pin2": pin2, "pin3": pin3}


def test_pins_with_invalid_order(setup_shape):
    shape, scene, pin1, pin2, pin3 = setup_shape
    shape.symattrs = {"pinOrder": "pin2, invalidPin, pin3"}
    assert shape.pins == {"pin2": pin2, "pin3": pin3}
