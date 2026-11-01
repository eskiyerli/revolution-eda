# SPDX-License-Identifier: MPL-2.0
#
# Revolution EDA
# Copyright (c) 2026 Revolution Semiconductor

"""Tests for LVS lvs_schematic <-> layout cross-probing (milestone D1+D2).

D1 stamps the ``sdl`` correspondence field onto generated lvs_schematic
symbols (extractedSchematic.klayoutSchematicGenerator); D1-persistence
round-trips that stamp through the schematic symbol encoder/loader; D2 wires
bidirectional editor-to-editor probing between the lvs_schematic and its
layout, reusing the Phase-6 probe primitives. Style follows
test_correspondence.py (synthetic parsers/scenes, no pytest-qt)."""

import types

import orjson
import pytest
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication

import revedaEditor.backend.correspondence as corr
import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.backend.libBackEnd as libb
import revedaEditor.common.shapes as shp
import revedaEditor.fileio.extractedSchematic as extsch
import revedaEditor.fileio.loadJSON as lj
import revedaEditor.fileio.schematicEncoder as schenc
from defaultPDK.layoutLayers import m1Layer_drw, pdkAllLayers
from revedaEditor.common import layoutShapes as lshp
from revedaEditor.tests.sceneTestUtils import (makeLayoutScene,
                                               makeSchematicScene)


@pytest.fixture(scope="module", autouse=True)
def init_qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


M1_LN = pdkAllLayers.index(m1Layer_drw)
LAYOUT_LIB, LAYOUT_CELL = "mylib", "top"
LAYOUT_KEY = (LAYOUT_LIB, LAYOUT_CELL, "layout")


# --- synthetic LVS parser ----------------------------------------------------


class _FakeParser:
    """Minimal parser exposing only what buildPositionMapping consumes."""

    def __init__(self, layoutDevices, crossref=None):
        self._layoutDevices = layoutDevices
        self._crossref = crossref

    def get_layout_devices(self, cellName):
        return self._layoutDevices

    def get_crossref(self, cellName):
        return self._crossref


def _makeGenerator(layoutDevices, crossref=None, layoutInstanceNames=None):
    """Build a generator over a fake parser + fake (optionally open) layout.

    ``layoutInstanceNames`` seeds the fake layout scene's instanceNames so the
    name map can prefer the real placement name (open-layout path).
    """
    scene = None
    if layoutInstanceNames is not None:
        insts = []
        for name in layoutInstanceNames:
            inst = lshp.layoutInstance([])
            inst.instanceName = name
            insts.append(inst)
        scene = types.SimpleNamespace(items=lambda: list(insts))
    layoutEditor = types.SimpleNamespace(
        libName=LAYOUT_LIB, cellName=LAYOUT_CELL,
        centralW=types.SimpleNamespace(scene=scene))
    gen = extsch.klayoutSchematicGenerator(
        parser=_FakeParser(layoutDevices, crossref),
        layoutEditor=layoutEditor,
        revedaMain=types.SimpleNamespace(),
        findSymbolViewNameTuple=lambda *a, **k: None,
        logger=extsch.logger,
    )
    gen.buildPositionMapping()
    return gen


# --- D1: sdl stamp on generated symbols --------------------------------------


def test_stamp_sdl_resolves_layout_instance_name():
    gen = _makeGenerator(
        [{"id": 1, "name": "M1", "position": {"x": 0, "y": 0}},
         {"id": 2, "name": "M2", "position": {"x": 1, "y": 0}}])
    symbol = types.SimpleNamespace()
    gen._stampSdlSource(symbol, {"id": 1, "name": "M1"})
    assert corr.sdlSourceKey(symbol._sdlSource) == LAYOUT_KEY
    assert corr.sdlInstName(symbol._sdlSource) == "M1"
    assert corr.sdlLabels(symbol._sdlSource)["lvsDeviceName"][0] == "M1"


def test_stamp_sdl_prefers_open_layout_instance_name():
    # Open layout: the real placement name is preferred over the LVS device
    # name (here they coincide, confirming the open-layout path is taken).
    gen = _makeGenerator(
        [{"id": 7, "name": "M1", "position": {"x": 0, "y": 0}}],
        layoutInstanceNames=["M1"])
    symbol = types.SimpleNamespace()
    gen._stampSdlSource(symbol, {"id": 7, "name": "M1"})
    assert corr.sdlInstName(symbol._sdlSource) == "M1"


def test_stamp_sdl_merged_device_records_full_set():
    # One extracted device aggregates two layout fingers via source_device_ids.
    gen = _makeGenerator(
        [{"id": 10, "name": "M1a", "position": {"x": 0, "y": 0}},
         {"id": 11, "name": "M1b", "position": {"x": 1, "y": 0}}])
    symbol = types.SimpleNamespace()
    device = {"id": 10, "name": "M1", "source_device_ids": [11]}
    gen._stampSdlSource(symbol, device)
    # Primary stamped; the whole layout-device set recorded in labels.
    assert corr.sdlInstName(symbol._sdlSource) == "M1a"
    labels = corr.sdlLabels(symbol._sdlSource)
    assert labels["lvsLayoutInstances"][0] == "M1a,M1b"


def test_stamp_sdl_unresolvable_device_is_skipped():
    gen = _makeGenerator([])
    symbol = types.SimpleNamespace()
    # No layout device, no name -> nothing resolvable: skip without crashing.
    gen._stampSdlSource(symbol, {"id": 99})
    assert not hasattr(symbol, "_sdlSource")


def test_stamp_sdl_hierarchical_instance_uses_instance_name():
    # Hierarchical instances carry id=None; the sdl names the subcircuit
    # instance by its extracted name, not an aggregated leaf device.
    gen = _makeGenerator(
        [{"id": 1, "name": "leaf0", "position": {"x": 0, "y": 0}}])
    symbol = types.SimpleNamespace()
    hierDevice = {"id": None, "name": "X1", "type": "sub",
                  "source_device_ids": [1]}
    gen._stampSdlSource(symbol, hierDevice)
    assert corr.sdlInstName(symbol._sdlSource) == "X1"


def test_build_position_mapping_adds_xref_schematic_ids():
    crossref = {"mapping": {"devices": [
        {"layout_dev": 1, "schem_dev": 101},
    ]}}
    gen = _makeGenerator(
        [{"id": 1, "name": "M1", "position": {"x": 2, "y": 3}}],
        crossref=crossref)
    # Both the layout id and the paired schematic id resolve to the name.
    assert gen.schem_to_layout_name[1] == "M1"
    assert gen.schem_to_layout_name[101] == "M1"


# --- D1-persistence: sdl round-trips on schematic symbols --------------------


def _writeSymbolLibrary(tmp_path):
    """mylib/dev/symbol.json with a single pin, usable by the loader."""
    libDir = tmp_path / "mylib"
    (libDir / "dev").mkdir(parents=True)
    (libDir / "dev" / "symbol.json").write_bytes(orjson.dumps([
        {"viewType": "symbol"},
        {},
        {"type": "pin", "nam": "A", "loc": [0, 0], "st": [0, 0],
         "pd": "Input"},
    ]))
    return libDir


def _makeStampedSymbol(scene, instName="M1", sdlInst="M1"):
    pin = shp.symbolPin(QPoint(0, 0), "A", "Input", "Signal")
    symbol = shp.schematicSymbol([pin], {})
    symbol.libraryName = "mylib"
    symbol.cellName = "dev"
    symbol.viewName = "symbol"
    symbol.instanceName = instName
    symbol.counter = 0
    symbol._sdlSource = corr.makeSdlSource(
        LAYOUT_LIB, LAYOUT_CELL, "layout", sdlInst, {"lvsDeviceName":
                                                     [sdlInst, False]})
    scene.addItem(symbol)
    return symbol


def test_schematic_symbol_sdl_round_trip(tmp_path):
    scene = makeSchematicScene()
    symbol = _makeStampedSymbol(scene)
    record = schenc.schematicEncoder().default(symbol)
    assert record["type"] == "sys"
    assert record["sdl"]["inst"] == "M1"
    assert record["sdl"]["view"] == "layout"
    assert record["sdl"]["lib"] == LAYOUT_LIB

    # Decode through the loader (library absent -> draft path still restores).
    loader = lj.schematicItems(scene)
    loader.libraryDict = {}
    restored = loader._createSymbolShape(record)
    assert corr.sdlInstName(restored._sdlSource) == "M1"
    assert corr.sdlSourceKey(restored._sdlSource) == LAYOUT_KEY


def test_schematic_symbol_without_sdl_omits_field(tmp_path):
    scene = makeSchematicScene()
    pin = shp.symbolPin(QPoint(0, 0), "A", "Input", "Signal")
    symbol = shp.schematicSymbol([pin], {})
    symbol.libraryName, symbol.cellName, symbol.viewName = "mylib", "dev", "symbol"
    symbol.instanceName, symbol.counter = "M1", 0
    scene.addItem(symbol)
    record = schenc.schematicEncoder().default(symbol)
    # No stamp -> no sdl key (ordinary schematic records are unchanged).
    assert "sdl" not in record


# --- D2: bidirectional editor-to-editor probing ------------------------------


def _makeLayoutLibrary(tmp_path):
    """mylib/sub/{layout,symbol}.json for updateFromSchematic-built layouts."""
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
    """A hand/GDS-style layout instance with no sdl stamp (the LVS case)."""
    inst = lshp.layoutInstance([])
    inst.libraryName = LAYOUT_LIB
    inst.cellName = "sub"
    inst.viewName = "layout"
    inst.instanceName = instName
    inst.counter = 0
    return inst


def _bindEditor(scene, viewName):
    """Attach lib/cell/view identity + a fake editor wrapper to a scene."""
    scene.editorWindow.libName = LAYOUT_LIB
    scene.editorWindow.cellName = LAYOUT_CELL
    scene.editorWindow.viewName = viewName
    editor = types.SimpleNamespace(
        centralW=types.SimpleNamespace(scene=scene),
        raise_=lambda: None, activateWindow=lambda: None)
    return editor


def test_probe_lvs_schematic_to_layout_selects_instance(tmp_path):
    """lvs_schematic selection -> layout selectProbeTargets picks the pair."""
    libDir = _makeLayoutLibrary(tmp_path)
    layoutScene = makeLayoutScene()
    layoutScene.libraryDict = {"mylib": libDir}
    inst = _plainLayoutInstance("M1")
    layoutScene.addItem(inst)
    # lvs_schematic symbol stamped at the layout instance M1.
    lvsScene = makeSchematicScene()
    symbol = _makeStampedSymbol(lvsScene, instName="M1", sdlInst="M1")

    openViews = {}
    layoutEditor = _bindEditor(layoutScene, "layout")
    lvsEditor = _bindEditor(lvsScene, "lvs_schematic")
    openViews[ddef.viewNameTuple(LAYOUT_LIB, LAYOUT_CELL, "layout")] = \
        layoutEditor
    openViews[ddef.viewNameTuple(LAYOUT_LIB, LAYOUT_CELL, "lvs_schematic")] = \
        lvsEditor
    appMainW = types.SimpleNamespace(openViews=openViews, logger=extsch.logger)
    lvsScene.editorWindow.appMainW = appMainW
    layoutScene.editorWindow.appMainW = appMainW

    symbol.setSelected(True)
    lvsScene.probeLayout()
    assert inst.isSelected()


def test_probe_layout_to_lvs_schematic_selects_symbol(tmp_path):
    """layout selection -> probeLvsSchematic picks the paired symbol."""
    libDir = _makeLayoutLibrary(tmp_path)
    layoutScene = makeLayoutScene()
    layoutScene.libraryDict = {"mylib": libDir}
    inst = _plainLayoutInstance("M1")
    layoutScene.addItem(inst)
    lvsScene = makeSchematicScene()
    symbol = _makeStampedSymbol(lvsScene, instName="M1", sdlInst="M1")

    openViews = {}
    layoutEditor = _bindEditor(layoutScene, "layout")
    lvsEditor = _bindEditor(lvsScene, "lvs_schematic")
    openViews[ddef.viewNameTuple(LAYOUT_LIB, LAYOUT_CELL, "lvs_schematic")] = \
        lvsEditor
    appMainW = types.SimpleNamespace(openViews=openViews, logger=extsch.logger)
    layoutScene.editorWindow.appMainW = appMainW

    inst.setSelected(True)
    layoutScene.probeLvsSchematic()
    # Layout instanceName "M1" resolves the lvs_schematic symbol via its
    # sdl.inst stamp (symmetric sdl-currency matching).
    assert symbol.isSelected()


def test_probe_lvs_schematic_counterpart_not_open(tmp_path):
    """Missing counterpart sets the message line instead of crashing."""
    layoutScene = makeLayoutScene()
    inst = _plainLayoutInstance("M1")
    layoutScene.addItem(inst)
    messages = []
    layoutScene.editorWindow.libName = LAYOUT_LIB
    layoutScene.editorWindow.cellName = LAYOUT_CELL
    layoutScene.editorWindow.messageLine = types.SimpleNamespace(
        setText=messages.append)
    layoutScene.messageLine = layoutScene.editorWindow.messageLine
    layoutScene.editorWindow.appMainW = types.SimpleNamespace(
        openViews={}, logger=extsch.logger)
    inst.setSelected(True)
    layoutScene.probeLvsSchematic()
    assert messages and "lvs_schematic" in messages[-1]
