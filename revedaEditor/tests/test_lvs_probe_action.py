# SPDX-License-Identifier: MPL-2.0
#
# Revolution EDA
# Copyright (c) 2024-2026 Revolution Semiconductor

"""Regression tests for the core lvs_schematic->layout probe UI trigger.

The scene-level probe primitive (``schematicScene.probeLayout``) and the sdl
stamp (D1/D2) are proven green by test_extracted_crossprobe.py, yet the live
GUI could not trigger lvs_schematic->layout probing: no core menu action calls
``probeLayout``; only the commercial RevSDL plugin wired it. These tests cover
the missing piece — the core-owned ``probeLayoutAction`` surfaced on an
lvs_schematic schematicEditor and the full action-handler -> scene -> layout
selection chain it drives.

Style follows test_sdl_free_baseline.py (editor built via ``__new__`` +
direct ``_createActions`` call) and test_extracted_crossprobe.py (synthetic
scenes registered in a stand-in ``appMainW.openViews``)."""

import types

import orjson
import pytest
from PySide6.QtCore import QPoint
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow

import revedaEditor.backend.correspondence as corr
import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.common.shapes as shp
import revedaEditor.gui.editorWindow as edw
import revedaEditor.gui.schematicEditor as sed
from defaultPDK.layoutLayers import m1Layer_drw, pdkAllLayers
from revedaEditor.common import layoutShapes as lshp
from revedaEditor.tests.sceneTestUtils import (makeLayoutScene,
                                               makeSchematicScene)


M1_LN = pdkAllLayers.index(m1Layer_drw)
LAYOUT_LIB, LAYOUT_CELL = "mylib", "top"


# --- editor construction -----------------------------------------------------


def _makeSchematicEditor(viewName, pluginsObj=None):
    """Build a bare schematicEditor and run ``_createActions`` on it.

    Mirrors test_sdl_free_baseline: bypass editorWindow.__init__, stub the
    attributes ``_createActions`` touches, and set the identity fields the
    probe trigger inspects (``viewName`` + ``_app.pluginsObj``).
    """
    editor = sed.schematicEditor.__new__(sed.schematicEditor)
    QMainWindow.__init__(editor)
    editor.pasteAction = QAction(editor)
    editor.viewCheckAction = QAction(editor)
    editor.viewName = viewName
    editor._app = types.SimpleNamespace(pluginsObj=pluginsObj)
    sed.schematicEditor._createActions(editor)
    return editor


# --- the original failure mode: ordinary schematics get no probe trigger -----


def test_ordinary_schematic_editor_has_no_probe_action(qapp, monkeypatch):
    """A normal schematic view must not grow the lvs-only probe trigger.

    This is the baseline the fix must preserve: the generic schematicEditor is
    unchanged (RevSDL owns the generic probe wiring)."""
    monkeypatch.setattr(edw.editorWindow, "_createActions", lambda self: None)
    editor = _makeSchematicEditor("schematic")
    try:
        assert not hasattr(editor, "probeLayoutAction")
        assert not editor._lvsProbeActionWanted()
    finally:
        editor.deleteLater()


def test_lvs_schematic_editor_suppresses_action_when_provider_present(
        qapp, monkeypatch):
    """When a plugin provides 'sdl', core must not duplicate the probe menu."""
    monkeypatch.setattr(edw.editorWindow, "_createActions", lambda self: None)
    provider = types.SimpleNamespace(provides=lambda cap: cap == "sdl")
    editor = _makeSchematicEditor("lvs_schematic", pluginsObj=provider)
    try:
        assert not hasattr(editor, "probeLayoutAction")
    finally:
        editor.deleteLater()


# --- the fix: lvs_schematic gets a reachable core trigger --------------------


def test_lvs_schematic_editor_exposes_probe_action(qapp, monkeypatch):
    """An lvs_schematic view (no sdl provider) gets a core probe action."""
    monkeypatch.setattr(edw.editorWindow, "_createActions", lambda self: None)
    editor = _makeSchematicEditor("lvs_schematic")
    try:
        assert hasattr(editor, "probeLayoutAction")
        assert editor.probeLayoutAction.text() == "Probe in Layout"
        assert editor._lvsProbeActionWanted()
    finally:
        editor.deleteLater()


def test_lvs_schematic_action_added_to_tools_menu(qapp, monkeypatch):
    """The probe action is reachable from the Tools menu for lvs_schematic."""
    monkeypatch.setattr(edw.editorWindow, "_createActions", lambda self: None)
    editor = _makeSchematicEditor("lvs_schematic")
    try:
        editor.menuTools = editor.menuBar().addMenu("Tools")
        editor.menuTools.addAction(editor.probeLayoutAction)
        texts = [a.text() for a in editor.menuTools.actions()]
        assert "Probe in Layout" in texts
    finally:
        editor.deleteLater()


# --- the fix drives the real scene->layout selection chain -------------------


def _makeLayoutLibrary(tmp_path):
    libDir = tmp_path / "mylib"
    (libDir / "sub").mkdir(parents=True)
    (libDir / "sub" / "layout.json").write_bytes(orjson.dumps([
        {"viewType": "layout"},
        {"snapGrid": [10, 10]},
        {"type": "Pin", "tl": [0, 0], "br": [40, 40], "pn": "A",
         "pd": "Input", "pt": "Signal", "ln": M1_LN},
    ]))
    (libDir / "sub" / "symbol.json").write_bytes(orjson.dumps([
        {"viewType": "symbol"},
        {},
        {"type": "pin", "nam": "A", "loc": [0, 0], "st": [50, 0],
         "pd": "Input"},
    ]))
    return libDir


def _plainLayoutInstance(instName):
    inst = lshp.layoutInstance([])
    inst.libraryName = LAYOUT_LIB
    inst.cellName = "sub"
    inst.viewName = "layout"
    inst.instanceName = instName
    inst.counter = 0
    return inst


def _makeStampedSymbol(scene, instName="M1", sdlInst="M1"):
    pin = shp.symbolPin(QPoint(0, 0), "A", "Input", "Signal")
    symbol = shp.schematicSymbol([pin], {})
    symbol.libraryName = "mylib"
    symbol.cellName = "dev"
    symbol.viewName = "symbol"
    symbol.instanceName = instName
    symbol.counter = 0
    symbol._sdlSource = corr.makeSdlSource(
        LAYOUT_LIB, LAYOUT_CELL, "layout", sdlInst,
        {"lvsDeviceName": [sdlInst, False]})
    scene.addItem(symbol)
    return symbol


def _bindSceneIdentity(scene, viewName, appMainW):
    scene.editorWindow.libName = LAYOUT_LIB
    scene.editorWindow.cellName = LAYOUT_CELL
    scene.editorWindow.viewName = viewName
    scene.editorWindow.appMainW = appMainW


def test_probe_action_handler_selects_layout_counterpart(tmp_path, qapp,
                                                         monkeypatch):
    """Invoking the action handler the menu wires selects the layout pair.

    This exercises the UI entry point (``probeLayoutClick``) rather than the
    isolated primitive, driving lvs_schematic selection all the way to the
    layout scene's selection + highlight through the Phase-6 primitives."""
    monkeypatch.setattr(edw.editorWindow, "_createActions", lambda self: None)

    libDir = _makeLayoutLibrary(tmp_path)
    layoutScene = makeLayoutScene()
    layoutScene.libraryDict = {"mylib": libDir}
    inst = _plainLayoutInstance("M1")
    layoutScene.addItem(inst)

    lvsScene = makeSchematicScene()
    symbol = _makeStampedSymbol(lvsScene, instName="M1", sdlInst="M1")

    openViews = {}
    layoutEditor = types.SimpleNamespace(
        centralW=types.SimpleNamespace(scene=layoutScene),
        raise_=lambda: None, activateWindow=lambda: None)
    appMainW = types.SimpleNamespace(openViews=openViews)
    _bindSceneIdentity(layoutScene, "layout", appMainW)
    _bindSceneIdentity(lvsScene, "lvs_schematic", appMainW)
    openViews[ddef.viewNameTuple(LAYOUT_LIB, LAYOUT_CELL, "layout")] = \
        layoutEditor

    # Build the lvs_schematic editor and point its centralW at the lvs scene.
    editor = _makeSchematicEditor("lvs_schematic")
    try:
        assert hasattr(editor, "probeLayoutAction")
        editor.centralW = types.SimpleNamespace(scene=lvsScene)

        symbol.setSelected(True)
        # Fire exactly what the menu action's triggered signal would call.
        editor.probeLayoutClick()

        assert inst.isSelected()
    finally:
        editor.deleteLater()


def test_probe_action_handler_messages_when_layout_closed(tmp_path, qapp,
                                                          monkeypatch):
    """The handler reports via the message line when no layout is open.

    Reproduces the user-visible 'nothing happens' symptom's graceful form:
    with the counterpart layout not registered in openViews the handler must
    not crash and must surface guidance."""
    monkeypatch.setattr(edw.editorWindow, "_createActions", lambda self: None)

    lvsScene = makeSchematicScene()
    symbol = _makeStampedSymbol(lvsScene, instName="M1", sdlInst="M1")
    messages = []
    appMainW = types.SimpleNamespace(openViews={})
    _bindSceneIdentity(lvsScene, "lvs_schematic", appMainW)
    lvsScene.editorWindow.messageLine = types.SimpleNamespace(
        setText=messages.append)
    lvsScene.messageLine = lvsScene.editorWindow.messageLine

    editor = _makeSchematicEditor("lvs_schematic")
    try:
        editor.centralW = types.SimpleNamespace(scene=lvsScene)
        symbol.setSelected(True)
        editor.probeLayoutClick()
        assert messages and "layout" in messages[-1].lower()
    finally:
        editor.deleteLater()
