"""Hierarchy display level and per-instance collapse tests (layout editor)."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QTransform
from PySide6.QtWidgets import QStyleOptionGraphicsItem

from revedaEditor.common import layoutShapes as lshp
from revedaEditor.fileio.loadJSON import layoutItems
from revedaEditor.tests.sceneTestUtils import makeLayoutScene


def _writeLayoutCell(tmp_path, lib, cell, records):
    cellDir = tmp_path / lib / cell
    cellDir.mkdir(parents=True)
    (cellDir / "layout.json").write_text(
        '[{"viewType":"layout"},{"snapGrid":[10,10]},' + ",".join(records) + "]"
    )
    return tmp_path / lib


def _sceneWithLibrary(libPath):
    scene = makeLayoutScene()
    scene.libraryDict = {"library": str(libPath)}
    return scene


def _paintItem(item, scale=1.0):
    """Paint one item at a full-detail level of detail."""
    image = QImage(800, 600, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setWorldTransform(QTransform().scale(scale, scale))
    item.paint(painter, QStyleOptionGraphicsItem(), None)
    painter.end()


def _nestedInstanceScene(tmp_path):
    """grandchild(rect) -> child(inst) -> top-level instance; all deferred."""
    _writeLayoutCell(tmp_path, "library", "grandchild", [
        '{"type":"Rect","tl":[0,0],"br":[5,5],"ln":0}',
    ])
    libPath = _writeLayoutCell(tmp_path, "library", "child", [
        ('{"type":"Inst","lib":"library","cell":"grandchild","view":"layout",'
         '"loc":[0,0],"ic":1,"nam":"I0","bbox":[0,0,5,5]}'),
    ])
    scene = _sceneWithLibrary(libPath)
    instance = layoutItems(scene).create({
        "type": "Inst", "lib": "library", "cell": "child", "view": "layout",
        "loc": [0, 0], "ic": 1, "nam": "I1", "bbox": [0, 0, 5, 5],
    })
    scene.addItem(instance)
    return scene, instance


def _flatInstanceScene(tmp_path):
    """child(rect) -> top-level instance; deferred."""
    libPath = _writeLayoutCell(tmp_path, "library", "child", [
        '{"type":"Rect","tl":[0,0],"br":[10,20],"ln":0}',
    ])
    scene = _sceneWithLibrary(libPath)
    instance = layoutItems(scene).create({
        "type": "Inst", "lib": "library", "cell": "child", "view": "layout",
        "loc": [0, 0], "ic": 1, "nam": "I1", "bbox": [0, 0, 10, 20],
    })
    scene.addItem(instance)
    return scene, instance


def test_hier_depth_counts_instance_ancestors(qapp, tmp_path):
    scene, instance = _nestedInstanceScene(tmp_path)

    assert instance.hierDepth() == 1
    nested = instance.shapes[0]
    assert isinstance(nested, lshp.layoutInstance)
    assert nested.hierDepth() == 2


def test_display_level_collapses_deferred_top_instance(qapp, tmp_path):
    scene, instance = _flatInstanceScene(tmp_path)
    assert instance._deferredLoader is not None

    scene.displayLevel = 0
    _paintItem(instance)

    assert instance._childrenHidden
    # Collapsed paint must not realise deferred children.
    assert instance._deferredLoader is not None
    assert not instance.childItems()


def test_display_level_collapses_only_at_threshold_depth(qapp, tmp_path):
    scene, instance = _nestedInstanceScene(tmp_path)

    scene.displayLevel = 1
    _paintItem(instance)

    # Depth 1 <= 1: full-detail paint realises the deferred children.
    assert instance._deferredLoader is None
    nested = instance.shapes[0]
    assert isinstance(nested, lshp.layoutInstance)

    _paintItem(nested)
    # Depth 2 > 1: the nested instance collapses and stays deferred.
    assert nested._childrenHidden
    assert nested._deferredLoader is not None
    assert not nested.childItems()


def test_display_level_max_restores_children(qapp, tmp_path):
    scene, instance = _flatInstanceScene(tmp_path)

    scene.displayLevel = 0
    _paintItem(instance)
    assert instance._childrenHidden
    assert instance._deferredLoader is not None

    scene.displayLevel = 20
    _paintItem(instance)

    assert instance._deferredLoader is None
    assert not instance._childrenHidden
    children = instance.childItems()
    assert len(children) == 1
    assert children[0].isVisible() == children[0].layer.visible


def test_user_collapsed_overrides_show_all_level(qapp, tmp_path):
    scene, instance = _flatInstanceScene(tmp_path)
    assert scene.displayLevel == 20

    instance.userCollapsed = True
    _paintItem(instance)

    assert instance._childrenHidden
    assert instance._deferredLoader is not None

    scene.expandAllInstances()
    assert instance.userCollapsed is False

    _paintItem(instance)
    assert instance._deferredLoader is None
    assert not instance._childrenHidden


def test_collapse_expand_selected_instances(qapp, tmp_path):
    scene, instance = _flatInstanceScene(tmp_path)
    instance.setSelected(True)

    scene.collapseSelectedInstances()
    assert instance.userCollapsed is True

    scene.expandSelectedInstances()
    assert instance.userCollapsed is False
