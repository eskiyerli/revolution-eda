"""Regression contract for the SDL functionality already released on master."""

import types
from unittest.mock import Mock

import orjson
import pytest
from PySide6.QtCore import QPoint
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QDialog, QMainWindow, QMessageBox

import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.backend.libBackEnd as libb
import revedaEditor.gui.editorWindow as edw
import revedaEditor.gui.layoutEditor as led
import revedaEditor.gui.schematicEditor as sed
from defaultPDK import pcells
from defaultPDK.layoutLayers import m1Layer_drw, pdkAllLayers
from revedaEditor.common import layoutShapes as lshp
from revedaEditor.tests.sceneTestUtils import makeLayoutScene


M1_LN = pdkAllLayers.index(m1Layer_drw)


def _sysRecord(name="M1", cell="sub", labels=None, **values):
    record = {
        "type": "sys",
        "lib": "mylib",
        "cell": cell,
        "view": "symbol",
        "nam": name,
        "ic": 7,
        "loc": [12, 34],
        "ang": 90,
        "fl": [-1, 1],
        "ld": labels or {},
    }
    record.update(values)
    return record


def _writeLibrary(tmp_path, records):
    libDir = tmp_path / "mylib"
    (libDir / "top").mkdir(parents=True)
    (libDir / "sub").mkdir()
    (libDir / "top" / "schematic.json").write_bytes(orjson.dumps([
        {"viewType": "schematic"},
        {"snapGrid": [10, 10]},
        *records,
    ]))
    (libDir / "sub" / "layout.json").write_bytes(orjson.dumps([
        {"viewType": "layout"},
        {"snapGrid": [10, 10]},
        {
            "type": "Pin",
            "tl": [0, 0],
            "br": [40, 40],
            "pn": "A",
            "pd": "Input",
            "pt": "Signal",
            "ln": M1_LN,
        },
    ]))
    return libDir


def _schematicTuple(libDir):
    return ddef.viewItemTuple(
        libb.libraryItem(libDir),
        libb.cellItem(libDir / "top"),
        libb.viewItem(libDir / "top" / "schematic.json"),
    )


def _sceneFor(libDir):
    scene = makeLayoutScene()
    scene.libraryDict = {"mylib": libDir}
    return scene


class _Combo:
    def __init__(self, value=""):
        self.value = value

    def setCurrentText(self, value):
        self.value = value

    def currentText(self):
        return self.value


class _Dialog:
    def __init__(self, result):
        self.result = result
        self.libNamesCB = _Combo("mylib")
        self.cellCB = _Combo("top")
        self.viewCB = _Combo("schematic")

    def exec(self):
        return self.result


def _fakeEditorForChooser(items=None):
    scene = types.SimpleNamespace(
        clear=Mock(),
        items=Mock(return_value=list(items or [])),
        itemsRefSet=set(["existing"]),
        undoStack=Mock(),
        loadSchematicInstances=Mock(),
        updateFromSchematic=Mock(),
    )
    editor = types.SimpleNamespace(
        libraryDict={"mylib": object()},
        libName="mylib",
        cellName="top",
        centralW=types.SimpleNamespace(scene=scene),
    )
    return editor, scene


def _patchChooser(monkeypatch, result):
    dialog = _Dialog(result)
    monkeypatch.setattr(led.lmview, "schematicViewsModel", lambda *_: object())
    monkeypatch.setattr(led.fd, "selectCellViewDialog", lambda *_: dialog)
    monkeypatch.setattr(led.libm, "getLibItem", lambda *_: "libItem")
    monkeypatch.setattr(led.libm, "getCellItem", lambda *_: "cellItem")
    monkeypatch.setattr(led.libm, "getViewItem", lambda *_: "viewItem")
    return dialog


def test_free_editor_exposes_only_master_sdl_action(qapp, monkeypatch):
    monkeypatch.setattr(edw.editorWindow, "_createActions", lambda self: None)
    editor = led.layoutEditor.__new__(led.layoutEditor)
    QMainWindow.__init__(editor)
    try:
        led.layoutEditor._createActions(editor)
        assert editor.sdlLoadAction.text() == "Load from Schematic..."
        assert editor.sdlLoadAction.toolTip() == "Create layout instances from schematic"
        assert not hasattr(editor, "flylinesAction")
        assert not hasattr(editor, "clearFlylinesAction")
        assert not hasattr(editor, "probeSchematicAction")
    finally:
        editor.deleteLater()


def test_free_schematic_editor_has_no_layout_probe_action(qapp, monkeypatch):
    monkeypatch.setattr(edw.editorWindow, "_createActions", lambda self: None)
    editor = sed.schematicEditor.__new__(sed.schematicEditor)
    QMainWindow.__init__(editor)
    editor.pasteAction = QAction(editor)
    editor.viewCheckAction = QAction(editor)
    try:
        sed.schematicEditor._createActions(editor)
        assert not hasattr(editor, "probeLayoutAction")
    finally:
        editor.deleteLater()


def test_free_load_chooser_replaces_scene_and_calls_master_loader(monkeypatch):
    editor, scene = _fakeEditorForChooser()
    _patchChooser(monkeypatch, QDialog.DialogCode.Accepted)

    led.layoutEditor.sdlLoadClick(editor)

    scene.clear.assert_called_once_with()
    scene.undoStack.clear.assert_called_once_with()
    assert scene.itemsRefSet == set()
    scene.loadSchematicInstances.assert_called_once()
    scene.updateFromSchematic.assert_not_called()


def test_free_load_chooser_confirms_before_wiping_scene(monkeypatch):
    """Non-empty scene: user must approve the destructive replace."""
    editor, scene = _fakeEditorForChooser(items=[object()])
    _patchChooser(monkeypatch, QDialog.DialogCode.Accepted)
    question = Mock(return_value=QMessageBox.StandardButton.Cancel)
    monkeypatch.setattr(QMessageBox, "question", question)

    led.layoutEditor.sdlLoadClick(editor)

    question.assert_called_once()
    scene.clear.assert_not_called()
    scene.undoStack.clear.assert_not_called()
    scene.loadSchematicInstances.assert_not_called()

    question = Mock(return_value=QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "question", question)

    led.layoutEditor.sdlLoadClick(editor)

    question.assert_called_once()
    scene.clear.assert_called_once_with()
    scene.undoStack.clear.assert_called_once_with()
    scene.loadSchematicInstances.assert_called_once()


def test_free_load_chooser_cancel_does_not_mutate(monkeypatch):
    editor, scene = _fakeEditorForChooser()
    _patchChooser(monkeypatch, QDialog.DialogCode.Rejected)

    led.layoutEditor.sdlLoadClick(editor)

    scene.clear.assert_not_called()
    scene.loadSchematicInstances.assert_not_called()
    scene.updateFromSchematic.assert_not_called()
    assert scene.itemsRefSet == {"existing"}


def test_free_loader_warns_and_cancel_preserves_existing_instances(
        tmp_path, monkeypatch):
    libDir = _writeLibrary(tmp_path, [_sysRecord()])
    scene = _sceneFor(libDir)
    existing = lshp.layoutInstance([])
    existing.libraryName = "mylib"
    existing.cellName = "sub"
    existing.viewName = "layout"
    existing.instanceName = "OLD"
    scene.addItem(existing)
    question = Mock(return_value=QMessageBox.StandardButton.Cancel)
    monkeypatch.setattr(QMessageBox, "question", question)

    scene.loadSchematicInstances(_schematicTuple(libDir))

    question.assert_called_once()
    assert existing.scene() is scene
    assert not any(
        isinstance(item, lshp.layoutInstance) and item.instanceName == "M1"
        for item in scene.items()
    )


def test_free_loader_creates_layout_instances_with_master_transform(tmp_path):
    libDir = _writeLibrary(tmp_path, [_sysRecord()])
    scene = _sceneFor(libDir)

    scene.loadSchematicInstances(_schematicTuple(libDir))

    instance = next(
        item for item in scene.items()
        if isinstance(item, lshp.layoutInstance)
    )
    assert instance.instanceName == "M1"
    assert instance.counter == 7
    assert instance.angle == 90
    assert instance.flipTuple == (-1, 1)
    assert instance.pos() == QPoint(120, 340)
    assert getattr(instance, "_sdlSource", None) is None


def test_free_loader_applies_existing_pcell_parameter_map(
        tmp_path, monkeypatch):
    labels = {
        "w": ["6", True],
        "l": ["0.4", True],
        "nf": ["2", True],
    }
    libDir = _writeLibrary(tmp_path, [_sysRecord(labels=labels)])
    scene = _sceneFor(libDir)
    instance = pcells.nmos()
    monkeypatch.setattr(scene, "_resolveLayoutView", lambda *_: object())
    monkeypatch.setattr(scene, "instLayout", lambda *_: instance)
    monkeypatch.setattr(
        scene,
        "_getPcellParameterMap",
        lambda *_: {"width": "w", "length": "l", "nf": "nf"},
    )

    scene.loadSchematicInstances(_schematicTuple(libDir))

    assert instance.width == 6.0
    assert instance.length == 0.4
    assert instance.nf == 2
    assert instance.instanceName == "M1"
    assert instance.pos() == QPoint(120, 340)


def test_free_loader_skips_missing_required_pcell_parameter(
        tmp_path, monkeypatch, caplog):
    labels = {"w": ["6", True], "l": ["0.4", True]}
    libDir = _writeLibrary(tmp_path, [_sysRecord(labels=labels)])
    scene = _sceneFor(libDir)
    instance = pcells.nmos()
    monkeypatch.setattr(scene, "_resolveLayoutView", lambda *_: object())
    monkeypatch.setattr(scene, "instLayout", lambda *_: instance)
    monkeypatch.setattr(
        scene,
        "_getPcellParameterMap",
        lambda *_: {"width": "w", "length": "l", "nf": "nf"},
    )

    scene.loadSchematicInstances(_schematicTuple(libDir))

    assert instance.scene() is None
    assert "Missing PCell parameters for" in caplog.text
    assert "nf" in caplog.text


def test_free_loader_skips_missing_layout_view(tmp_path, caplog):
    libDir = _writeLibrary(tmp_path, [_sysRecord(cell="missing")])
    scene = _sceneFor(libDir)

    scene.loadSchematicInstances(_schematicTuple(libDir))

    assert not [
        item for item in scene.items()
        if isinstance(item, lshp.layoutInstance)
    ]
    assert "No layout/pcell view for mylib/missing" in caplog.text
