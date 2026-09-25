"""Contract tests for the versioned core SDL plugin adapter."""

import types

import orjson
import pytest
from PySide6.QtCore import QLineF
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication, QGraphicsLineItem, QMainWindow, QMenu,
)

from revedaEditor.backend import pluginApi
from revedaEditor.backend.pluginsLoader import pluginsLoader
import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.gui.editorWindow as edw
import revedaEditor.gui.layoutEditor as led
from revedaEditor.common import layoutShapes as lshp
from revedaEditor.tests.sceneTestUtils import makeLayoutScene


@pytest.fixture(scope="module", autouse=True)
def initQapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _record():
    return {
        "type": "sys",
        "lib": "mylib",
        "cell": "sub",
        "view": "symbol",
        "nam": "M1",
        "ic": 3,
        "loc": [2, 4],
        "ang": 0,
        "fl": [1, 1],
        "ld": {},
    }


def _source():
    return {
        "lib": "mylib",
        "cell": "top",
        "view": "schematic",
        "inst": "M1",
        "labels": {},
    }


def test_sdl_adapter_capability_is_negotiable():
    assert "sdlAdapterV1" in pluginApi.CORE_CAPABILITIES
    assert pluginApi.checkPluginConfig({
        "plugin_api": 2,
        "requires_core": ["sdlAdapterV1"],
    }, "1.0.0") == []


def test_adapter_creates_stamps_and_describes_instance(monkeypatch):
    scene = makeLayoutScene()
    instance = lshp.layoutInstance([])
    instance.libraryName = "mylib"
    instance.cellName = "sub"
    instance.viewName = "layout"
    monkeypatch.setattr(scene, "instLayout", lambda *_: instance)

    created = scene.createLayoutInstanceFromRecord(
        object(), _record(), _source())

    assert created is instance
    assert instance.scene() is scene
    assert instance.instanceName == "M1"
    assert instance._sdlSource == _source()
    assert scene.layoutInstanceDescriptors() == [{
        "item": instance,
        "name": "M1",
        "cell": "sub",
        "sdl": _source(),
    }]


def test_adapter_resolves_layout_before_pcell(tmp_path):
    libDir = tmp_path / "mylib"
    cellDir = libDir / "sub"
    cellDir.mkdir(parents=True)
    (cellDir / "layout.json").write_bytes(orjson.dumps([
        {"viewType": "layout"}, {"snapGrid": [10, 10]},
    ]))
    (cellDir / "pcell.json").write_bytes(orjson.dumps([
        {"cellView": "pcell"}, {"reference": "nmos"},
    ]))
    scene = makeLayoutScene()
    scene.libraryDict = {"mylib": libDir}

    resolved = scene.resolveLayoutView("mylib", "sub")

    assert isinstance(resolved, ddef.viewItemTuple)
    assert resolved.viewItem.viewName == "layout"


def test_adapter_refuses_every_mutation_when_read_only(monkeypatch):
    scene = makeLayoutScene()
    scene.readOnly = True
    instance = lshp.layoutInstance([])
    instance.libraryName = "mylib"
    instance.cellName = "sub"
    instance.viewName = "layout"
    instLayout = lambda *_: instance
    monkeypatch.setattr(scene, "instLayout", instLayout)

    assert scene.createLayoutInstanceFromRecord(
        object(), _record(), _source()) is None
    assert not scene.stampSdlSource(instance, _source())
    assert not scene.applySchematicParameters(instance, _record())
    assert not scene.removeLayoutItemsUndo([instance])
    assert instance.scene() is None


def test_overlay_api_does_not_invalidate_connectivity():
    scene = makeLayoutScene()
    invalidated = []
    scene.connectivityInvalidated.connect(lambda: invalidated.append(True))
    overlay = QGraphicsLineItem(QLineF(0, 0, 10, 10))

    scene.addOverlayItem(overlay)
    scene.removeOverlayItem(overlay)

    assert invalidated == []
    assert overlay.scene() is None


def test_connectivity_lifecycle_signals_are_emitted():
    scene = makeLayoutScene()
    invalidated, rebuilt = [], []
    scene.connectivityInvalidated.connect(lambda: invalidated.append(True))
    scene.connectivityRebuilt.connect(lambda: rebuilt.append(True))

    scene.markConnectivityDirty()
    scene.rebuildConnectivity()

    assert invalidated == [True]
    assert rebuilt == [True]


def test_plugin_actions_follow_read_only_safety_property(qapp):
    window = edw.editorWindow.__new__(edw.editorWindow)
    QMainWindow.__init__(window)
    safe = QAction("Safe", window)
    safe.setProperty("readOnlySafe", True)
    mutating = QAction("Mutating", window)
    mutating.setProperty("readOnlySafe", False)
    window._pluginActions = [safe, mutating]
    window._preLockActionEnabled = {}
    try:
        edw.editorWindow._setLockReadOnlyActions(window)
        assert safe.isEnabled()
        assert not mutating.isEnabled()
        edw.editorWindow._restoreLockActions(window)
        assert safe.isEnabled()
        assert mutating.isEnabled()
    finally:
        window.deleteLater()


def test_plugin_loader_registers_action_safety(qapp):
    loader = pluginsLoader.__new__(pluginsLoader)
    loader.plugins = {"test": types.SimpleNamespace(run=lambda *_: None)}
    loader.pluginMenuConfig = {
        "test": {
            "menu_items": [
                {
                    "location": "menuBar",
                    "menu": "Tools",
                    "action": "Safe",
                    "callback": "run",
                    "read_only_safe": True,
                },
                {
                    "location": "menuBar",
                    "menu": "Tools",
                    "action": "Mutating",
                    "callback": "run",
                },
            ]
        }
    }
    window = QMainWindow()
    window._pluginActions = []
    window.menuBar().addMenu("Tools")
    try:
        loader.applyPluginMenus(window)
        assert len(window._pluginActions) == 2
        assert window._pluginActions[0].property("readOnlySafe") is True
        assert window._pluginActions[1].property("readOnlySafe") is False
    finally:
        window.deleteLater()


class _SdlPlugins:
    def __init__(self, installed: bool):
        self.installed = installed

    def provides(self, capability: str) -> bool:
        return self.installed and capability == "sdl"

    def applyPluginMenus(self, window):
        if not self.installed:
            return
        action = QAction("Update from Schematic...", window)
        action.setProperty("readOnlySafe", False)
        window._pluginActions.append(action)
        window.menuTools.addAction(action)


def _layoutEditorForPluginMenu(pluginsObj):
    editor = led.layoutEditor.__new__(led.layoutEditor)
    QMainWindow.__init__(editor)
    editor._app = types.SimpleNamespace(pluginsObj=pluginsObj)
    editor._pluginActions = []
    for name in (
        "selectDeviceAction", "selectWireAction", "removeSelectFilterAction",
        "objPropAction", "stretchAction", "cutAction", "mergeAction",
        "layerOpsAction", "groupItemsAction", "ungroupItemsAction",
        "createInstAction", "createRectAction", "createPathAction",
        "createPinAction", "createLabelAction", "createViaAction",
        "createPolygonAction", "multipartAction", "rulerAction",
        "delSelectedRulerAction", "delRulerAction", "renumberInstanceAction",
        "exportGDSAction", "exportOASAction", "highlightNetAction",
        "clearNetHighlightsAction", "goUpAction", "goDownAction",
        "flattenAction", "makeCellAction",
    ):
        setattr(editor, name, QAction(name, editor))
    editor.sdlLoadAction = QAction("Load from Schematic...", editor)
    editor.selectMenu = QMenu("Selection", editor)
    editor.propertyMenu = QMenu("Properties", editor)
    editor.menuEdit = editor.menuBar().addMenu("Edit")
    editor.menuCreate = editor.menuBar().addMenu("Create")
    editor.menuTools = editor.menuBar().addMenu("Tools")
    editor.menuUtilities = editor.menuBar().addMenu("Utilities")
    editor.cellAccessMenu = editor.menuUtilities.addMenu("Cell Access")
    editor.readOnlyCellAction = QAction("Read Only", editor)
    editor.retryLockAction = QAction("Retry Edit Access", editor)
    editor.cellAccessMenu.addAction(editor.readOnlyCellAction)
    editor.cellAccessMenu.addAction(editor.retryLockAction)
    return editor


def test_installed_sdl_capability_replaces_free_load_action(qapp, monkeypatch):
    monkeypatch.setattr(edw.editorWindow, "_addActions", lambda self: None)
    editor = _layoutEditorForPluginMenu(_SdlPlugins(True))
    try:
        led.layoutEditor._addActions(editor)
        texts = [action.text() for action in editor.menuTools.actions()]
        assert "Load from Schematic..." not in texts
        assert texts.count("Update from Schematic...") == 1
        # no leading separator before Highlight Net when SDL is suppressed
        first = editor.menuTools.actions()[0]
        assert not first.isSeparator()
    finally:
        editor.deleteLater()


def test_absent_sdl_capability_keeps_free_load_action(qapp, monkeypatch):
    monkeypatch.setattr(edw.editorWindow, "_addActions", lambda self: None)
    plugins = _SdlPlugins(False)
    editor = _layoutEditorForPluginMenu(plugins)
    try:
        led.layoutEditor._addActions(editor)
        texts = [action.text() for action in editor.menuTools.actions()]
        assert "Load from Schematic..." in texts
        assert "Update from Schematic..." not in texts
        separators = [
            i for i, a in enumerate(editor.menuTools.actions())
            if a.isSeparator()
        ]
        assert separators == [1]
    finally:
        editor.deleteLater()


def test_utilities_submenus_order_and_tools_layout(qapp, monkeypatch):
    monkeypatch.setattr(edw.editorWindow, "_addActions", lambda self: None)
    editor = _layoutEditorForPluginMenu(_SdlPlugins(False))
    try:
        led.layoutEditor._addActions(editor)
        utilityTitles = [
            a.text() for a in editor.menuUtilities.actions()
        ]
        assert utilityTitles == ["Instances", "Export", "Cell Access"]
        assert editor.instanceUtilitiesMenu.actions() == [
            editor.renumberInstanceAction
        ]
        assert editor.exportUtilitiesMenu.actions() == [
            editor.exportGDSAction, editor.exportOASAction
        ]
        toolsActions = [
            a for a in editor.menuTools.actions()
            if not a.isSeparator()
        ]
        assert toolsActions == [
            editor.sdlLoadAction, editor.highlightNetAction,
            editor.clearNetHighlightsAction,
        ]
    finally:
        editor.deleteLater()
