"""Array copy options: rows×columns clipboard paste with X/Y pitch
(Virtuoso-style copy options driven by scene.copyOptions)."""

import pytest
from PySide6.QtCore import QPoint
from PySide6.QtGui import QGuiApplication

import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.common.net as snet
import revedaEditor.common.shapes as shp
from revedaEditor.tests.sceneTestUtils import (
    makeLayoutScene,
    makeSchematicScene,
)


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def _net(scene, p1, p2, name=""):
    item = snet.schematicNet(p1, p2, 0, snet.NetMode.ORTHOGONAL)
    scene.addItem(item)
    if name:
        item.name = name
    return item


def _symbol(scene, pos=None, name="I1"):
    item = shp.schematicSymbol([], {"instName": "[@instName]"})
    item.libraryName = "lib"
    item.cellName = "cell"
    item.viewName = "symbol"
    item.instanceName = name
    item.setPos(pos if pos is not None else QPoint(0, 0))
    scene.addItem(item)
    return item


def _symbols(scene):
    return [i for i in scene.items() if isinstance(i, shp.schematicSymbol)]


def _nets(scene):
    return [i for i in scene.items() if isinstance(i, snet.schematicNet)]


def test_array_paste_count_and_offsets(qapp):
    scene = makeSchematicScene()
    n = _net(scene, QPoint(0, 0), QPoint(100, 0))
    s = _symbol(scene, QPoint(200, 200))
    scene.setSelectedItems({n, s})
    assert scene.copySelectionToClipboard() == 2
    scene.copyOptions = ddef.copyOptions(
        rows=2, columns=3, xOffset=100, yOffset=50)
    assert scene.pasteClipboard(QPoint(1000, 1000)) == 12
    assert len(_nets(scene)) == 7  # original + 6 copies
    assert len(_symbols(scene)) == 7
    # Six distinct element positions, each offset by (c*dx, r*dy)
    # plus the common paste delta.
    positions = {(round(i.pos().x()), round(i.pos().y()))
                 for i in _symbols(scene)}
    positions.discard((200, 200))  # the original
    assert len(positions) == 6
    xs = sorted({p[0] for p in positions})
    ys = sorted({p[1] for p in positions})
    assert len(xs) == 3 and xs[1] - xs[0] == 100 and xs[2] - xs[1] == 100
    assert len(ys) == 2 and ys[1] - ys[0] == 50


def test_array_paste_unique_instance_names(qapp):
    scene = makeSchematicScene()
    s = _symbol(scene, QPoint(0, 0))
    scene.setSelectedItems({s})
    scene.copySelectionToClipboard()
    scene.copyOptions = ddef.copyOptions(
        rows=2, columns=2, xOffset=100, yOffset=100)
    scene.pasteClipboard(QPoint(500, 500))
    names = [i.instanceName for i in _symbols(scene)]
    assert len(names) == len(set(names)) == 5


def test_array_single_undo(qapp):
    scene = makeSchematicScene()
    s = _symbol(scene, QPoint(0, 0))
    scene.setSelectedItems({s})
    scene.copySelectionToClipboard()
    scene.copyOptions = ddef.copyOptions(
        rows=2, columns=2, xOffset=10, yOffset=10)
    scene.pasteClipboard(QPoint(500, 500))
    assert len(_symbols(scene)) == 5
    scene.undoStack.undo()
    assert _symbols(scene) == [s]


def test_rearm_rebuilds_group(qapp):
    scene = makeSchematicScene()
    s = _symbol(scene, QPoint(0, 0))
    scene.setSelectedItems({s})
    scene.copySelectionToClipboard()
    assert scene.beginClipboardPaste(QPoint(100, 100)) == 1
    assert len(scene.selectedItemGroup.childItems()) == 1
    scene.copyOptions = ddef.copyOptions(
        rows=2, columns=2, xOffset=10, yOffset=10)
    assert scene.rearmClipboardPaste() == 4
    assert len(scene.selectedItemGroup.childItems()) == 4
    # Cancel removes the whole armed array — no orphans.
    assert scene.cancelArmedCopy()
    assert _symbols(scene) == [s]


def test_rearm_without_armed_copy_is_noop(qapp):
    scene = makeSchematicScene()
    assert scene.rearmClipboardPaste() == 0


def test_zero_offset_uses_bbox_pitch(qapp):
    scene = makeSchematicScene()
    n = _net(scene, QPoint(0, 0), QPoint(80, 0))
    scene.setSelectedItems({n})
    scene.copySelectionToClipboard()
    scene.copyOptions = ddef.copyOptions(rows=1, columns=2)
    scene.pasteClipboard(QPoint(500, 500))
    nets = _nets(scene)
    assert len(nets) == 3  # original + 2 copies
    copies = [i for i in nets if i is not n]
    copies.sort(key=lambda i: i.pos().x())
    expected_dx = scene.snapToBase(
        n.sceneBoundingRect().width(), scene.snapTuple[0]) \
        or scene.snapTuple[0]
    # The two copies are separated by exactly one column pitch.
    diff = copies[1].pos() - copies[0].pos()
    assert diff == QPoint(expected_dx, 0)


def test_layout_array_paste(qapp):
    import revedaEditor.common.layoutShapes as lshp
    from defaultPDK.layoutLayers import m1Layer_drw

    scene = makeLayoutScene()
    rect = lshp.layoutRect(
        QPoint(0, 0), QPoint(100, 100), m1Layer_drw)
    scene.addItem(rect)
    scene.setSelectedItems({rect})
    assert scene.copySelectionToClipboard() == 1
    scene.copyOptions = ddef.copyOptions(
        rows=2, columns=2, xOffset=200, yOffset=300)
    assert scene.pasteClipboard(QPoint(1000, 1000)) == 4
    rects = [i for i in scene.items() if isinstance(i, lshp.layoutRect)]
    assert len(rects) == 5
    positions = {(round(i.pos().x()), round(i.pos().y())) for i in rects}
    positions.discard((0, 0))  # the original
    assert len(positions) == 4
    xs = sorted({p[0] for p in positions})
    ys = sorted({p[1] for p in positions})
    assert len(xs) == 2 and xs[1] - xs[0] == 200
    assert len(ys) == 2 and ys[1] - ys[0] == 300
