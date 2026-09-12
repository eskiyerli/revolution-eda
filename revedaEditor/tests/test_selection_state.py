import pytest
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsScene,
)

from revedaEditor.scenes.editorScene import editorScene


@pytest.fixture(scope="module", autouse=True)
def initQapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class selectionScene(QGraphicsScene):
    setSelectedItems = editorScene.setSelectedItems
    selectAll = editorScene.selectAll

    def __init__(self):
        super().__init__()
        self.selectedItemsSet = set()


def testSetSelectedItemsReplacesQtSelection():
    scene = selectionScene()
    first = QGraphicsRectItem(0, 0, 10, 10)
    second = QGraphicsRectItem(20, 0, 10, 10)
    first.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
    second.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
    scene.addItem(first)
    scene.addItem(second)

    scene.setSelectedItems({first})
    scene.setSelectedItems({second})

    assert set(scene.selectedItems()) == {second}
    assert scene.selectedItemsSet == {second}


def testSelectAllSynchronizesSelectionSet():
    scene = selectionScene()
    first = QGraphicsRectItem(0, 0, 10, 10)
    second = QGraphicsRectItem(20, 0, 10, 10)
    first.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
    second.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
    scene.addItem(first)
    scene.addItem(second)

    scene.selectAll()

    assert set(scene.selectedItems()) == {first, second}
    assert scene.selectedItemsSet == {first, second}