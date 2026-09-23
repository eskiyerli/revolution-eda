"""Repro: explicit copy-array pitch vs committed geometry."""

import pytest
from PySide6.QtCore import QPoint, QPointF

import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.common.shapes as shp
from revedaEditor.tests.sceneTestUtils import makeSchematicScene


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def _symbol(scene, pos, name="I1"):
    # A symbol with real geometry: 40x40 body rect offset from origin,
    # plus an instName label sitting above the body.
    body = shp.symbolRectangle(QPoint(-20, -20), QPoint(20, 20))
    item = shp.schematicSymbol([body], {"instName": "[@instName]"})
    item.libraryName = "lib"
    item.cellName = "cell"
    item.viewName = "symbol"
    item.instanceName = name
    item.setPos(pos)
    scene.addItem(item)
    return item


def _symbols(scene):
    return [i for i in scene.items() if isinstance(i, shp.schematicSymbol)]


def test_pitch_immediate_paste(qapp):
    scene = makeSchematicScene()
    s = _symbol(scene, QPoint(200, 200))
    scene.setSelectedItems({s})
    scene.copySelectionToClipboard()
    scene.copyOptions = ddef.copyOptions(
        rows=1, columns=3, xOffset=20, yOffset=0)
    scene.pasteClipboard(QPoint(500, 500))
    copies = [i for i in _symbols(scene) if i is not s]
    copies.sort(key=lambda i: i.pos().x())
    for i in copies:
        print("\npos:", i.pos(), "bbox:", i.sceneBoundingRect())
    diffs = [copies[k + 1].pos() - copies[k].pos()
             for k in range(len(copies) - 1)]
    print("\npos diffs:", diffs)


def test_pitch_armed_commit(qapp):
    scene = makeSchematicScene()
    s = _symbol(scene, QPoint(200, 200))
    scene.setSelectedItems({s})
    scene.copySelectionToClipboard()
    scene.copyOptions = ddef.copyOptions(
        rows=1, columns=3, xOffset=20, yOffset=0)
    scene.mouseMoveLoc = QPoint(600, 600)
    assert scene.beginClipboardPaste(QPoint(600, 600)) == 3
    group = scene.selectedItemGroup
    scene.mouseMoveLoc = QPoint(800, 700)
    group.setPos(QPointF(scene.mouseMoveLoc) - scene._copyAnchor)
    scene._commitCopyGroup()
    copies = [i for i in _symbols(scene) if i is not s]
    copies.sort(key=lambda i: i.pos().x())
    for i in copies:
        print("\npos:", i.pos(), "bbox:", i.sceneBoundingRect())
    diffs = [copies[k + 1].pos() - copies[k].pos()
             for k in range(len(copies) - 1)]
    print("\npos diffs:", diffs)
