import json
import math
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import gdstk
import pytest
from PySide6.QtWidgets import QApplication

import revedaEditor.backend.libBackEnd as libb
from revedaEditor.fileio.importGDS import gdsImporter


@pytest.fixture(scope="module", autouse=True)
def init_qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def _make_parent(tmp_path: Path):
    model = Mock()
    model.libraryDict = {}
    designView = SimpleNamespace(
        libraryModel=model,
        reworkDesignLibrariesView=Mock(),
    )
    browser = SimpleNamespace(designView=designView)
    return SimpleNamespace(libraryBrowser=browser, logger=Mock())


def _make_import_lib(tmp_path: Path) -> libb.libraryItem:
    lib_path = tmp_path / "importLib"
    lib_path.mkdir(parents=True)
    return libb.libraryItem(lib_path)


def test_import_snaps_polygons_to_pdk_grid(tmp_path: Path):
    """Off-grid GDS coordinates must snap to the PDK snap grid."""
    parent = _make_parent(tmp_path)
    import_lib = _make_import_lib(tmp_path)

    lib = gdstk.Library(unit=1e-6, precision=1e-9)
    cell = lib.new_cell("snap_test")
    # defaultPDK dbu=1000, snapGrid=0.05 um -> scene grid = 50.
    # 1.003 um should snap to 1.000 um (scene value 1000).
    cell.add(gdstk.rectangle((1.003, 2.0), (3.0, 4.0), layer=1, datatype=0))
    gds_path = tmp_path / "snap.gds"
    lib.write_gds(str(gds_path))

    importer = gdsImporter(parent, gds_path, import_lib)
    importer.importGDS()

    layout_file = import_lib.libraryPath / "snap_test" / "layout.json"
    data = json.loads(layout_file.read_text())
    polygon = next(item for item in data if item.get("type") == "Polygon")
    tl, _, br, _ = polygon["ps"]

    assert tl[0] == 1000
    assert tl[1] == 2000
    assert br[0] == 3000
    assert br[1] == 4000


def test_import_scales_by_gds_unit_not_assumes_one_um(tmp_path: Path):
    """A GDS with 1 nm user unit must scale differently than one with 1 um."""
    parent = _make_parent(tmp_path)
    import_lib = _make_import_lib(tmp_path)

    lib = gdstk.Library(unit=1e-9, precision=1e-9)
    cell = lib.new_cell("unit_test")
    # With a 1 nm user unit, a 1000 nm square is represented as (0,0)-(1000,1000).
    cell.add(gdstk.rectangle((0, 0), (1000, 1000), layer=1, datatype=0))
    gds_path = tmp_path / "unit.gds"
    lib.write_gds(str(gds_path))

    importer = gdsImporter(parent, gds_path, import_lib)
    importer.importGDS()

    layout_file = import_lib.libraryPath / "unit_test" / "layout.json"
    data = json.loads(layout_file.read_text())
    polygon = next(item for item in data if item.get("type") == "Polygon")

    # Should be 1 um square in scene units (dbu=1000 -> 1000 units).
    tl, _, br, _ = polygon["ps"]
    assert br == [1000, 1000]


def test_import_reuses_referenced_cells(tmp_path: Path):
    """Referenced cells should be imported once, not once per reference."""
    parent = _make_parent(tmp_path)
    import_lib = _make_import_lib(tmp_path)

    lib = gdstk.Library(unit=1e-6, precision=1e-9)
    child = lib.new_cell("child")
    child.add(gdstk.rectangle((0, 0), (1, 1), layer=1, datatype=0))
    parent_cell = lib.new_cell("parent")
    parent_cell.add(gdstk.Reference(child, origin=(0, 0)))
    parent_cell.add(gdstk.Reference(child, origin=(2, 0)))
    gds_path = tmp_path / "ref.gds"
    lib.write_gds(str(gds_path))

    importer = gdsImporter(parent, gds_path, import_lib)
    importer.importGDS()

    layout_file = import_lib.libraryPath / "parent" / "layout.json"
    data = json.loads(layout_file.read_text())
    insts = [item for item in data if item.get("type") == "Inst"]
    assert len(insts) == 2
    assert insts[0]["nam"] == "I1"
    assert insts[1]["nam"] == "I2"


def test_import_converts_simple_gds_path_to_layout_path(tmp_path: Path):
    """A simple two-point GDS path with square caps becomes an editable layoutPath."""
    parent = _make_parent(tmp_path)
    import_lib = _make_import_lib(tmp_path)

    lib = gdstk.Library(unit=1e-6, precision=1e-9)
    cell = lib.new_cell("path_test")
    path = gdstk.FlexPath(
        [(1.0, 2.0), (3.0, 2.0)],
        width=0.2,
        ends="extended",
        simple_path=True,
        layer=1,
        datatype=0,
    )
    cell.add(path)
    gds_path = tmp_path / "path.gds"
    lib.write_gds(str(gds_path))

    importer = gdsImporter(parent, gds_path, import_lib)
    importer.importGDS()

    layout_file = import_lib.libraryPath / "path_test" / "layout.json"
    data = json.loads(layout_file.read_text())
    items = [item for item in data if item.get("type") in {"Path", "Polygon"}]
    assert len(items) == 1
    assert items[0]["type"] == "Path"
    assert items[0]["dfl1"] == [1000, 2000]
    assert items[0]["dfl2"] == [3000, 2000]
    assert items[0]["w"] == pytest.approx(200)
    assert items[0]["se"] == 100
    assert items[0]["ee"] == 100


def test_import_keeps_complex_paths_as_polygons(tmp_path: Path):
    """Multi-segment or round-cap paths stay as polygons."""
    parent = _make_parent(tmp_path)
    import_lib = _make_import_lib(tmp_path)

    lib = gdstk.Library(unit=1e-6, precision=1e-9)
    cell = lib.new_cell("poly_path_test")
    path = gdstk.FlexPath(
        [(0, 0), (1, 0), (2, 1)],
        width=0.2,
        ends="extended",
        simple_path=True,
        layer=1,
        datatype=0,
    )
    cell.add(path)
    gds_path = tmp_path / "poly_path.gds"
    lib.write_gds(str(gds_path))

    importer = gdsImporter(parent, gds_path, import_lib)
    importer.importGDS()

    layout_file = import_lib.libraryPath / "poly_path_test" / "layout.json"
    data = json.loads(layout_file.read_text())
    polygons = [item for item in data if item.get("type") == "Polygon"]
    paths = [item for item in data if item.get("type") == "Path"]
    assert len(polygons) == 1
    assert len(paths) == 0


def test_import_round_cap_path_fallback_to_polygon(tmp_path: Path):
    """Round end caps cannot be represented by layoutPath and stay as polygons."""
    parent = _make_parent(tmp_path)
    import_lib = _make_import_lib(tmp_path)

    lib = gdstk.Library(unit=1e-6, precision=1e-9)
    cell = lib.new_cell("round_path_test")
    path = gdstk.FlexPath(
        [(0, 0), (1, 0)],
        width=0.2,
        ends="round",
        simple_path=True,
        layer=1,
        datatype=0,
    )
    cell.add(path)
    gds_path = tmp_path / "round_path.gds"
    lib.write_gds(str(gds_path))

    importer = gdsImporter(parent, gds_path, import_lib)
    importer.importGDS()

    layout_file = import_lib.libraryPath / "round_path_test" / "layout.json"
    data = json.loads(layout_file.read_text())
    polygons = [item for item in data if item.get("type") == "Polygon"]
    paths = [item for item in data if item.get("type") == "Path"]
    assert len(polygons) == 1
    assert len(paths) == 0


def test_import_preserves_reference_rotation_and_flip(tmp_path: Path):
    """Reference rotation and x_reflection should round-trip to ang/fl."""
    parent = _make_parent(tmp_path)
    import_lib = _make_import_lib(tmp_path)

    lib = gdstk.Library(unit=1e-6, precision=1e-9)
    child = lib.new_cell("child")
    child.add(gdstk.rectangle((0, 0), (1, 1), layer=1, datatype=0))
    parent_cell = lib.new_cell("parent")
    parent_cell.add(
        gdstk.Reference(
            child, origin=(1, 2), rotation=math.radians(90), x_reflection=True
        )
    )
    gds_path = tmp_path / "rot.gds"
    lib.write_gds(str(gds_path))

    importer = gdsImporter(parent, gds_path, import_lib)
    importer.importGDS()

    layout_file = import_lib.libraryPath / "parent" / "layout.json"
    data = json.loads(layout_file.read_text())
    inst = next(item for item in data if item.get("type") == "Inst")

    assert inst["loc"] == [1000, 2000]
    assert inst["ang"] == pytest.approx(90)
    assert inst["fl"] == [1, -1]
