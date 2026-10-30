"""Netlister tests against the real xyceNetlist API.

Covers the pure helpers (parseArrayNotation, expandPinNames), view selection
(_findViewFromSwitchList / determineNetlistView) against real cellItem/viewItem
objects, golden netlist-line generation from a real schematicSymbol, and an
end-to-end collectSubcircuitContent run on a real schematicScene backed by a
real designLibrariesModel built from a temporary on-disk library.
"""

import types

import pytest
from PySide6.QtCore import QPoint

import revedaEditor.backend.libBackEnd as libb
import revedaEditor.backend.libraryMethods as libm
import revedaEditor.backend.libraryModelView as lmview
import revedaEditor.common.labels as lbl
import revedaEditor.common.net as snet
import revedaEditor.common.shapes as shp
from revedaEditor.netlisting.xyceNetlist import xyceNetlist
from revedaEditor.tests.sceneTestUtils import makeSchematicScene


# --- fixtures ---------------------------------------------------------------

@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _writeLibrary(libPath, cells):
    """Create an on-disk library: reveda.lib marker + cell dirs with view files.

    cells: {"cellName": ["symbol", "schematic", ...]} - one empty json per view.
    """
    libPath.mkdir(parents=True, exist_ok=True)
    libPath.joinpath("reveda.lib").write_text("")
    for cellName, views in cells.items():
        cellDir = libPath / cellName
        cellDir.mkdir(exist_ok=True)
        for view in views:
            cellDir.joinpath(f"{view}.json").write_text("[]")


@pytest.fixture
def libraryModel(qapp, tmp_path):
    """A real designLibrariesModel over a temp library with top + res cells."""
    libPath = tmp_path / "testLib"
    _writeLibrary(libPath, {"top": ["schematic"], "res": ["symbol", "schematic"]})
    return lmview.designLibrariesModel({"testLib": libPath})


def _fakeEditor(scene, model, cellName="top"):
    """Duck-typed schematicEditor stand-in exposing only what xyceNetlist reads."""
    return types.SimpleNamespace(
        centralW=types.SimpleNamespace(scene=scene),
        libraryDict={},
        libraryView=types.SimpleNamespace(libraryModel=model),
        libName="testLib", cellName=cellName, viewName="schematic",
        switchViewList=["schematic", "symbol"],
        stopViewList=["symbol"],
    )


@pytest.fixture
def netlister(qapp, libraryModel, tmp_path):
    scene = makeSchematicScene()
    return xyceNetlist(_fakeEditor(scene, libraryModel), tmp_path / "out.cir")


def _makeSymbol(qapp, instName="I0",
                symattrs=None, pins=(("plus", QPoint(0, 0)), ("minus", QPoint(60, 0))),
                labels=(("[@instName]", "I0"), ("[@r:r=%:1k]", None))):
    """Real schematicSymbol with real symbolPins and resolved symbolLabels."""
    shapes = [shp.symbolPin(pos, name, "Inout", "Signal") for name, pos in pins]
    labelItems = [lbl.symbolLabel(QPoint(0, 0), definition, "NLPLabel", 12,
                                  "Left", "R0", "Normal")
                  for definition, _ in labels]
    symbolItem = shp.schematicSymbol(shapes + labelItems, symattrs or {})
    symbolItem.instanceName = instName
    # labelDefs() resolves label names only after parenting; addShapes keyed
    # them under "" at construction time, so rebuild the dict properly.
    for labelItem, (definition, forcedValue) in zip(labelItems, labels):
        labelItem.labelDefs()
        if forcedValue is not None:
            labelItem.labelValue = forcedValue
        symbolItem.labels[labelItem.labelName] = labelItem
    return symbolItem


# --- pure helpers -----------------------------------------------------------

@pytest.mark.parametrize("name,expected", [
    ("scalar", ("scalar", (-1, -1))),
    ("bus<5>", ("bus", (5, 5))),
    ("net<0:3>", ("net", (0, 3))),
    ("net<7:0>", ("net", (7, 0))),
])
def test_parse_array_notation(name, expected):
    assert xyceNetlist.parseArrayNotation(name) == expected


@pytest.mark.parametrize("pinNames,expected", [
    (["a", "b"], "a b"),
    (["a<0:1>", "b"], "a<0> a<1> b"),
    (["a<3:0>"], "a<3> a<2> a<1> a<0>"),
])
def test_expand_pin_names(pinNames, expected):
    assert xyceNetlist.expandPinNames(pinNames) == expected


# --- view selection ---------------------------------------------------------

def _viewItemsOf(cellItem):
    return [cellItem.child(row) for row in range(cellItem.rowCount())]


def test_switch_list_prefers_schematic(netlister, libraryModel):
    libItem = libm.getLibItem(libraryModel, "testLib")
    resCell = libm.getCellItem(libItem, "res")
    # res has both schematic and symbol views; schematic wins by switch order.
    assert netlister._findViewFromSwitchList(_viewItemsOf(resCell)) == "schematic"


def test_switch_list_stop_view_short_circuits(netlister, libraryModel):
    libItem = libm.getLibItem(libraryModel, "testLib")
    resCell = libm.getCellItem(libItem, "res")
    netlister.stopViewList = ["schematic", "symbol"]
    # schematic is a stop view: it is returned even though it appears first.
    assert netlister._findViewFromSwitchList(_viewItemsOf(resCell)) == "schematic"


def test_switch_list_falls_back_to_symbol(netlister, libraryModel):
    libItem = libm.getLibItem(libraryModel, "testLib")
    topCell = libm.getCellItem(libItem, "top")
    # top has only a schematic view; symbol is a stop view so it is the
    # reported terminal view when nothing matches earlier entries.
    netlister.stopViewList = ["symbol"]
    assert netlister._findViewFromSwitchList(_viewItemsOf(topCell)) == "schematic"


def test_determine_netlist_view_uses_config(netlister, libraryModel):
    libItem = libm.getLibItem(libraryModel, "testLib")
    resCell = libm.getCellItem(libItem, "res")
    symbol = types.SimpleNamespace(libraryName="testLib", cellName="res")
    netlister._useConfig = True
    netlister.configDict = {"res": ("testLib", "symbol")}
    assert netlister.determineNetlistView(symbol, resCell) == "symbol"


def test_determine_netlist_view_caches(netlister, libraryModel):
    libItem = libm.getLibItem(libraryModel, "testLib")
    resCell = libm.getCellItem(libItem, "res")
    symbol = types.SimpleNamespace(libraryName="testLib", cellName="res")
    assert netlister.determineNetlistView(symbol, resCell) == "schematic"
    assert ("testLib", "res") in netlister._viewNameCache


# --- golden netlist lines ----------------------------------------------------

def test_create_symbol_line_scalar(qapp, netlister):
    symbolItem = _makeSymbol(
        qapp, instName="I0",
        symattrs={"SpiceNetlistLine": "R@instName %pinOrder r=@r"})
    symbolItem.pinNetMap = {"plus": "in", "minus": "out"}
    assert netlister.createXyceSymbolLine(symbolItem) == [
        "RI0 in out r=1k"]


def test_create_symbol_line_array(qapp, netlister):
    symbolItem = _makeSymbol(
        qapp, instName="I0<0:1>",
        symattrs={"SpiceNetlistLine": "R@instName %pinOrder r=@r"})
    symbolItem.pinNetMap = {"plus": "in<0:1>", "minus": "out"}
    assert netlister.createXyceSymbolLine(symbolItem) == [
        "RI0<0> in<0> out r=1k",
        "RI0<1> in<1> out r=1k"]


def test_create_symbol_line_missing_inst_name(qapp, netlister):
    symbolItem = _makeSymbol(qapp, instName="I0", labels=(),
                             symattrs={"SpiceNetlistLine": "R@instName %pinOrder"})
    assert netlister.createXyceSymbolLine(symbolItem) == []


# --- end-to-end flat scene ----------------------------------------------------

def _addNet(scene, x1, y1, x2, y2):
    netItem = snet.schematicNet(QPoint(x1, y1), QPoint(x2, y2))
    scene.addItem(netItem)
    return netItem


def test_collect_subcircuit_content_flat(qapp, libraryModel, tmp_path):
    """A resistor wired between two named schematic pins netlists correctly."""
    scene = makeSchematicScene()
    symbolItem = _makeSymbol(
        qapp, instName="I0",
        symattrs={"SpiceNetlistLine": "R@instName %pinOrder r=@r",
                  "pinOrder": "plus,minus"})
    symbolItem.libraryName = "testLib"
    symbolItem.cellName = "res"
    scene.addItem(symbolItem)  # pins land at scene (0,0) and (60,0)

    _addNet(scene, -100, 0, 0, 0)
    _addNet(scene, 60, 0, 200, 0)
    scene.addItem(shp.schematicPin(QPoint(-100, 0), "in", "Input", "Signal"))
    scene.addItem(shp.schematicPin(QPoint(200, 0), "out", "Output", "Signal"))

    # Force res to its symbol view so no child schematicEditor is opened.
    netlister = xyceNetlist(_fakeEditor(scene, libraryModel),
                            tmp_path / "out.cir")
    netlister.switchViewList = ["symbol", "schematic"]

    content = []
    netlister.collectSubcircuitContent(netlister.schematic, content)
    assert content == ["RI0 in out r=1k"]


def test_collect_subcircuit_content_ignored_symbol(qapp, libraryModel, tmp_path):
    scene = makeSchematicScene()
    symbolItem = _makeSymbol(
        qapp, instName="I0",
        symattrs={"SpiceNetlistLine": "R@instName %pinOrder r=@r",
                  "NetlistIgnore": "1"})
    symbolItem.libraryName = "testLib"
    symbolItem.cellName = "res"
    scene.addItem(symbolItem)

    netlister = xyceNetlist(_fakeEditor(scene, libraryModel),
                            tmp_path / "out.cir")
    content = []
    netlister.collectSubcircuitContent(netlister.schematic, content)
    assert content == ["*I0 is excluded via NetlistIgnore attribute\n"]


# --- vacaskNetlist include dedup ---------------------------------------------

def test_vacask_include_dedup_symlinked_cellpath(qapp, tmp_path):
    """A cell's .vacask file is included once even under aliased roots.

    Selecting the vacask view emits an include via textViewFilePath
    (resolved path), while the symbol's VacaskIncludeFile attribute emits
    one via cellItem.cellPath (unresolved). On systems where /home is a
    symlink to /var/home the two spellings differed and the file was
    included twice.
    """
    from revedaEditor.netlisting.vacaskNetlist import vacaskNetlist

    realLib = tmp_path / "real" / "testLib"
    cellDir = realLib / "xtal"
    cellDir.mkdir(parents=True)
    realLib.joinpath("reveda.lib").write_text("")
    cellDir.joinpath("symbol.json").write_text("[]")
    cellDir.joinpath("vacask.json").write_text(
        '[{"cellView": "vacask"}, {"filePath": "xtal.vacask"}]')
    cellDir.joinpath("xtal.vacask").write_text(
        "subckt xtal (1 2)\nends xtal\n")

    linkRoot = tmp_path / "link"
    try:
        linkRoot.symlink_to(tmp_path / "real", target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"Directory symlinks are unavailable: {error}")
    model = lmview.designLibrariesModel({"testLib": linkRoot / "testLib"})

    netlister = vacaskNetlist(
        _fakeEditor(makeSchematicScene(), model), tmp_path / "out.cir")

    symbolItem = _makeSymbol(
        qapp, instName="I0",
        symattrs={"VacaskNetlistLine": "@instName (%pinOrder) xtal",
                  "VacaskIncludeFile": "xtal.vacask"})
    symbolItem.libraryName = "testLib"
    symbolItem.cellName = "xtal"
    symbolItem.pinNetMap = {"plus": "a", "minus": "b"}

    cellItem = netlister._getCellItem("testLib", "xtal")
    netlister.createTextViewLine(symbolItem, cellItem, "vacask")
    netlister._collectModelLoadInfo(symbolItem)

    expected = (cellDir / "xtal.vacask").resolve().as_posix()
    assert netlister.includeLines == {f'include "{expected}"'}


def test_extracted_schematic_sheet_pins_keep_device_endpoints(qapp):
    from revedaEditor.fileio.extractedSchematic import klayoutSchematicGenerator

    scene = makeSchematicScene()
    generator = object.__new__(klayoutSchematicGenerator)
    generator._getScene = lambda: scene
    netEndpoints = {}
    endpoint = QPoint(100, 0)

    def createPinNet(pinItem, symbolItem, device, endpoints):
        endpoints.setdefault("VDD", []).append(endpoint)
        return snet.schematicNet(QPoint(0, 0), endpoint)

    generator.createPinNet = createPinNet
    symbolItem = types.SimpleNamespace(pins={"plus": object()})
    generator.addDeviceNets(symbolItem, {}, netEndpoints)

    assert netEndpoints == {"VDD": [endpoint]}
    generator.addExtractedPins({"pins": ["VDD"]}, netEndpoints)
    pins = [item for item in scene.items() if isinstance(item, shp.schematicPin)]
    assert len(pins) == 1
    assert pins[0].pinName == "VDD"
    assert pins[0].scenePos() == endpoint


if __name__ == "__main__":
    pytest.main()
