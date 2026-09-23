"""Tests for persistent layout item groups (layoutGroup + Group records)."""

import json

import pytest
from PySide6.QtCore import QPoint, QPointF
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QGraphicsItem

from defaultPDK.layoutLayers import m1Layer_drw, m1layer_txt
from defaultPDK import layoutLayers as laylyr
from defaultPDK import process as fabproc
from revedaEditor.common import layoutShapes as lshp
from revedaEditor.fileio import layoutEncoder as layenc
from revedaEditor.fileio import loadJSON as lj
import revedaEditor.connectivity as conn

from revedaEditor.tests.sceneTestUtils import makeLayoutScene


@pytest.fixture(scope="module", autouse=True)
def init_qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def _rect(x1, y1, x2, y2, layer=m1Layer_drw):
    return lshp.layoutRect(QPoint(x1, y1), QPoint(x2, y2), layer)


def _group_two(scene):
    """Group two fresh rects; return (group, r1, r2)."""
    r1 = _rect(0, 0, 100, 100)
    r2 = _rect(200, 0, 300, 100)
    scene.addItem(r1)
    scene.addItem(r2)
    scene.setSelectedItems({r1, r2})
    scene.groupSelectedItems()
    groups = [
        item for item in scene.items()
        if isinstance(item, lshp.layoutGroup)
    ]
    assert len(groups) == 1
    return groups[0], r1, r2


def _top_lefts(item):
    """Scene position of a layoutRect's drawn top-left corner."""
    p = item.mapToScene(item.rect.topLeft())
    return (round(p.x()), round(p.y()))


def test_group_selected_items_creates_container():
    scene = makeLayoutScene()
    group, r1, r2 = _group_two(scene)
    assert group.parentItem() is None
    assert set(group.shapes) == {r1, r2}
    assert r1.parentItem() is group
    assert r2.parentItem() is group
    # The group is the selected unit; members are not independently
    # selectable while grouped.
    assert scene.selectedItems() == [group]
    assert not r1.flags() & QGraphicsItem.ItemIsSelectable
    assert not r2.flags() & QGraphicsItem.ItemIsSelectable
    # Grouping does not move geometry: local coords stay scene coords.
    assert _top_lefts(r1) == (0, 0)
    assert _top_lefts(r2) == (200, 0)


def test_group_requires_two_items():
    scene = makeLayoutScene()
    r1 = _rect(0, 0, 10, 10)
    scene.addItem(r1)
    scene.setSelectedItems({r1})
    scene.groupSelectedItems()
    assert not [
        item for item in scene.items()
        if isinstance(item, lshp.layoutGroup)
    ]
    assert r1.parentItem() is None


def test_group_moves_members_as_unit():
    scene = makeLayoutScene()
    group, r1, r2 = _group_two(scene)
    group.moveBy(50, 25)
    assert _top_lefts(r1) == (50, 25)
    assert _top_lefts(r2) == (250, 25)


def test_ungroup_restores_toplevel_items():
    scene = makeLayoutScene()
    group, r1, r2 = _group_two(scene)
    scene.setSelectedItems({group})
    scene.ungroupSelectedItems()
    assert group.scene() is None
    assert r1.parentItem() is None and r2.parentItem() is None
    assert r1.flags() & QGraphicsItem.ItemIsSelectable
    assert r2.flags() & QGraphicsItem.ItemIsSelectable
    assert set(scene.selectedItems()) == {r1, r2}
    assert _top_lefts(r1) == (0, 0)
    assert _top_lefts(r2) == (200, 0)


def test_ungroup_after_move_preserves_positions():
    scene = makeLayoutScene()
    group, r1, r2 = _group_two(scene)
    group.moveBy(40, 60)
    scene.setSelectedItems({group})
    scene.ungroupSelectedItems()
    assert _top_lefts(r1) == (40, 60)
    assert _top_lefts(r2) == (240, 60)


def test_rotated_group_ungroup_composes_member_transforms():
    scene = makeLayoutScene()
    group, r1, _r2 = _group_two(scene)
    # Rotate the group 90 degrees about the scene origin.
    group.setTransformOriginPoint(QPointF(0, 0))
    group.angle = 90
    scene.setSelectedItems({group})
    scene.ungroupSelectedItems()
    # Qt rotation is clockwise in scene coords: (x, y) -> (-y, x), so
    # r1's rect (0,0)-(100,100) lands at (-100,0)-(0,100).
    mapped = [
        r1.mapToScene(r1.rect.topLeft()),
        r1.mapToScene(r1.rect.bottomRight()),
    ]
    xs = sorted(p.x() for p in mapped)
    ys = sorted(p.y() for p in mapped)
    assert xs == pytest.approx([-100, 0], abs=0.5)
    assert ys == pytest.approx([0, 100], abs=0.5)


def test_group_undo_redo():
    scene = makeLayoutScene()
    group, r1, r2 = _group_two(scene)
    scene.undoStack.undo()
    assert group.scene() is None
    assert r1.parentItem() is None and r2.parentItem() is None
    scene.undoStack.redo()
    assert group.scene() is scene
    assert r1.parentItem() is group and r2.parentItem() is group


def test_ungroup_undo_regroups_members():
    scene = makeLayoutScene()
    group, r1, r2 = _group_two(scene)
    scene.setSelectedItems({group})
    scene.ungroupSelectedItems()
    scene.undoStack.undo()
    assert group.scene() is scene
    assert r1.parentItem() is group and r2.parentItem() is group


def test_ungroup_undo_on_moved_group_restores_children():
    scene = makeLayoutScene()
    group, r1, r2 = _group_two(scene)
    group.moveBy(40, 60)
    scene.setSelectedItems({group})
    scene.ungroupSelectedItems()
    scene.undoStack.undo()
    # Re-attaching under the moved group must re-express member transforms
    # in group-local coordinates — children keep their released positions.
    assert r1.parentItem() is group
    assert _top_lefts(r1) == (40, 60)
    assert _top_lefts(r2) == (240, 60)


def test_group_encodes_and_recreates():
    scene = makeLayoutScene()
    group, _r1, _r2 = _group_two(scene)
    record = json.loads(json.dumps(group, cls=layenc.layoutEncoder))
    assert record["type"] == "Group"
    assert len(record["items"]) == 2
    assert all(i["type"] == "Rect" for i in record["items"])
    factory = lj.layoutItems(scene)
    clone = factory.create(record)
    assert isinstance(clone, lshp.layoutGroup)
    assert len(clone.shapes) == 2
    assert all(isinstance(s, lshp.layoutRect) for s in clone.shapes)
    # Members are group-local: with loc (0,0) their coords are unchanged.
    child_tl = sorted(
        (s.pos() + s.rect.topLeft()).toTuple() for s in clone.shapes)
    assert child_tl == [(0.0, 0.0), (200.0, 0.0)]


def test_moved_group_record_preserves_transform():
    scene = makeLayoutScene()
    group, _r1, _r2 = _group_two(scene)
    group.moveBy(30, 40)
    record = json.loads(json.dumps(group, cls=layenc.layoutEncoder))
    assert tuple(record["loc"]) == (30.0, 40.0)
    clone = lj.layoutItems(scene).create(record)
    assert clone.pos().toTuple() == (30.0, 40.0)
    scene2 = makeLayoutScene()
    scene2.addItem(clone)
    assert sorted(_top_lefts(s) for s in clone.shapes) == [
        (30, 40), (230, 40)]


def test_grouped_pin_still_anchors_net():
    scene = makeLayoutScene()
    pin = lshp.layoutPin(QPoint(0, 0), QPoint(100, 100), "vdd",
                         "Input", "Signal", m1Layer_drw)
    rect = _rect(50, 50, 300, 150)
    scene.addItem(pin)
    scene.addItem(rect)
    scene.setSelectedItems({pin, rect})
    scene.groupSelectedItems()
    group = next(
        item for item in scene.items()
        if isinstance(item, lshp.layoutGroup))
    shapes, vias, anchors, *_ = conn.fromLayoutItems([group])
    assert [a[0] for a in anchors] == ["vdd"]
    groups = conn.buildConnectivity(shapes, vias)
    assert len(groups) == 1
    names, conflicts, _auto = conn.assignNetNames(groups, anchors)
    assert names == ["vdd"]
    assert not conflicts


def test_grouped_label_still_anchors_net():
    scene = makeLayoutScene()
    rect = _rect(0, 0, 100, 100)
    label = lshp.layoutLabel(QPoint(50, 50), "vss", "Arial", "Regular",
                             "1.0", "Left", "R0", m1layer_txt)
    scene.addItem(rect)
    scene.addItem(label)
    scene.setSelectedItems({rect, label})
    scene.groupSelectedItems()
    group = next(
        item for item in scene.items()
        if isinstance(item, lshp.layoutGroup))
    _shapes, _vias, anchors, *_ = conn.fromLayoutItems([group])
    assert [a[0] for a in anchors] == ["vss"]


def test_group_copies_to_clipboard_as_group():
    scene = makeLayoutScene()
    group, _r1, _r2 = _group_two(scene)
    scene.setSelectedItems({group})
    assert scene.copySelectionToClipboard() == 1
    records = json.loads(QGuiApplication.clipboard().text())
    assert len(records) == 1
    assert records[0]["type"] == "Group"
    assert len(records[0]["items"]) == 2


def test_paste_recreates_group(qapp):
    scene = makeLayoutScene()
    group, _r1, _r2 = _group_two(scene)
    scene.setSelectedItems({group})
    scene.copySelectionToClipboard()
    pasted = scene.pasteClipboard(QPoint(500, 500))
    groups = [
        item for item in scene.items()
        if isinstance(item, lshp.layoutGroup)
    ]
    assert len(groups) == 2  # original + pasted copy
    pasted_group = next(g for g in groups if g is not group)
    assert len(pasted_group.shapes) == 2


def test_reader_expands_group_records():
    reader = conn.LayoutGeometryReader(laylyr, fabproc)
    ln = laylyr.pdkAllLayers.index(m1Layer_drw)
    records = [{
        "type": "Group", "loc": (100, 50), "ang": 0, "fl": (1, 1),
        "items": [
            {"type": "Rect", "ln": ln, "tl": (0, 0), "br": (10, 10)},
        ],
    }]
    shapes, vias = reader.read(records)
    assert len(shapes) == 1
    f = shapes[0].footprint
    assert (f.x1, f.y1, f.x2, f.y2) == (100, 50, 110, 60)


def test_reader_shifts_grouped_anchors():
    reader = conn.LayoutGeometryReader(laylyr, fabproc)
    ln = laylyr.pdkAllLayers.index(m1Layer_drw)
    anchors = reader.readAnchors([{
        "type": "Group", "loc": (10, 20), "items": [
            {"type": "Pin", "pn": "x", "ln": ln,
             "tl": (5, 5), "br": (6, 6)},
        ],
    }])
    assert anchors == [("x", 15.0, 25.0)]


def test_nested_groups_ungroup_one_level():
    scene = makeLayoutScene()
    inner, r1, r2 = _group_two(scene)
    r3 = _rect(500, 0, 600, 100)
    scene.addItem(r3)
    scene.setSelectedItems({inner, r3})
    scene.groupSelectedItems()
    outer = next(
        item for item in scene.items()
        if isinstance(item, lshp.layoutGroup) and item is not inner)
    assert set(outer.shapes) == {inner, r3}
    scene.setSelectedItems({outer})
    scene.ungroupSelectedItems()
    assert outer.scene() is None
    # The inner group survives intact one level down.
    assert inner.scene() is scene
    assert inner.parentItem() is None
    assert set(inner.shapes) == {r1, r2}
    assert r3.parentItem() is None


def test_pcell_placement_options_retained_for_repeats(monkeypatch):
    """Accepted PCell/mosaic options are reused on later clicks; the
    parameter form opens only for the first placement."""
    from PySide6.QtWidgets import (
        QDialog, QFormLayout, QGroupBox, QLineEdit)
    import revedaEditor.gui.layoutDialogues as ldlg

    class _FakePcell(lshp.layoutPcell):
        def __init__(self):
            super().__init__([])
            self.applied = []

        def __call__(self, *values):
            self.applied.append(values)
            return self

    class _FakeDialogue(QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.instanceLibName = QLineEdit()
            self.instanceCellName = QLineEdit()
            self.instanceViewName = QLineEdit()
            self.arrayGroup = QGroupBox()
            self.rowsEdit = QLineEdit()
            self.colsEdit = QLineEdit()
            self.rowPitchEdit = QLineEdit()
            self.colPitchEdit = QLineEdit()
            self.pcellParamsGroup = QGroupBox()
            self.pcellParamsLayout = QFormLayout()
            self.pcellParamsGroup.setLayout(self.pcellParamsLayout)

        def exec(self):
            return QDialog.DialogCode.Accepted

        def arraySpec(self):
            return (2, 3, 5, 7)

    scene = makeLayoutScene()
    scene.layoutInstanceTuple = None
    produced = []
    monkeypatch.setattr(
        scene, "instLayout",
        lambda _tuple: produced.append(_FakePcell()) or produced[-1])
    monkeypatch.setattr(
        scene, "extractPcellInstanceParameters",
        lambda _inst: {"w": QLineEdit("2u")})
    dialogues = []
    monkeypatch.setattr(
        ldlg, "layoutInstanceDialogue",
        lambda _parent: dialogues.append(_FakeDialogue()) or dialogues[-1])
    mosaics = []
    monkeypatch.setattr(
        scene, "_makeLayoutMosaicGroup",
        lambda base, spec, values=None: mosaics.append(
            (base, spec, values)) or mosaics[-1])

    first = scene.addNewInstance()
    expectedSpec = (2, 3, 5 * fabproc.dbu, 7 * fabproc.dbu)
    # First placement: one dialogue, options retained in dbu units.
    assert len(dialogues) == 1
    assert scene.pendingInstanceOptions == {
        "pcellValues": {"w": "2u"}, "arraySpec": expectedSpec}
    assert first == (produced[0], expectedSpec, {"w": "2u"})

    second = scene.addNewInstance()
    # Second placement reuses the retained options; no new dialogue.
    assert len(dialogues) == 1
    assert second == (produced[1], expectedSpec, {"w": "2u"})
    assert [call[1:] for call in mosaics] == [
        (expectedSpec, {"w": "2u"})] * 2
    assert produced[0].applied == [("2u",)]
    assert produced[1].applied == [("2u",)]
