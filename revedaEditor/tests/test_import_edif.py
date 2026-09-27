import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import revedaEditor.backend.libBackEnd as libb
import revedaEditor.backend.libraryModelView as lmview
import revedaEditor.common.params as prm
import revedaEditor.fileio.schemaValidation as sv
from revedaEditor.backend.edifBackEnd import EdifError, edifC
from revedaEditor.connectivity.diagnostics import checkRecords
from revedaEditor.fileio.importEDIF import edifImporter
from revedaEditor.fileio.loadJSON import makeSymbolPinLocator


@pytest.fixture(scope="module", autouse=True)
def init_qapp(qapp):
    yield qapp


def _make_parent(tmp_path: Path, libraryDict=None):
    libDict = dict(libraryDict or {})
    try:
        # Real model so lib resolution exercises the browser path.
        model = lmview.designLibrariesModel(libDict)
    except RuntimeError:  # Qt unusable — fall back to a dict-only mock
        model = Mock()
        model.libraryDict = libDict
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


def _write_edif(tmp_path: Path, body: str, name="design.edf") -> Path:
    edif_path = tmp_path / name
    edif_path.write_text(
        f"""(edif TOP_DESIGN
  (edifVersion 2 0 0)
  (edifLevel 0)
  (keywordMap (keywordLevel 0))
  (status (written (timeStamp 2026 1 1 0 0 0)))
  {body}
)"""
    )
    return edif_path


_MINIMAL_BODY = """
  (library WORK (edifLevel 0)
    (technology (numberDefinition))
    (cell INV (cellType GENERIC)
      (view schematic_1 (viewType SCHEMATIC)
        (interface
          (port A (direction INPUT))
          (port Y (direction OUTPUT)))
        (contents
          (net A (joined (portRef A)))))))
  (design TOP (cellRef INV (libraryRef WORK)))
"""


def test_parse_minimal_edif(tmp_path):
    """A minimal EDIF 2 0 0 file parses into the semantic model."""
    edif = edifC(_write_edif(tmp_path, _MINIMAL_BODY))
    assert edif.designName == "TOP"
    assert edif.topLibName == "WORK"
    assert edif.topCellName == "INV"
    cell = edif.libraries["WORK"].cells["INV"]
    view = cell.bestView()
    assert view.viewType == "SCHEMATIC"
    assert [p.name for p in view.ports] == ["A", "Y"]
    assert view.ports[0].direction == "Input"
    assert [n.name for n in view.nets] == ["A"]


def test_parse_rejects_wrong_version(tmp_path):
    """Only EDIF 2 0 0 is accepted."""
    path = tmp_path / "old.edf"
    path.write_text(
        "(edif D (edifVersion 3 0 0) (library L (cell C "
        "(view v (viewType SCHEMATIC) (interface)))))"
    )
    with pytest.raises(EdifError, match="EDIF version"):
        edifC(path)


def test_parse_rejects_non_edif(tmp_path):
    path = tmp_path / "notedif.txt"
    path.write_text("(foo bar) (baz)")
    with pytest.raises(EdifError):
        edifC(path)


def test_parse_rename_and_escapes(tmp_path):
    """(rename id "display") and & escapes produce display names."""
    body = """
      (library L (cell (rename inv_1 "INV 1")
        (view v (viewType SCHEMATIC)
          (interface (port (rename &vdd "VDD!") (direction INOUT)
                         (property PORTTYPE (string "supply")))))))
    """
    edif = edifC(_write_edif(tmp_path, body))
    port = edif.libraries["L"].cells["INV 1"].bestView().ports[0]
    assert port.name == "VDD!"
    assert port.pinType == "Power"


def test_parse_arrays_bundles_members(tmp_path):
    """Array ports/instances and member portRefs flatten to name<i>."""
    body = """
      (library L (cell top
        (view v (viewType SCHEMATIC)
          (interface (port (array bus 4) (direction INPUT)))
          (contents
            (instance (array I 3) (viewRef s (cellRef sub)))
            (net n1 (joined (portRef (member bus 2))))))))
      (library L2 (cell sub
        (view s (viewType SCHEMATIC) (interface))))
    """
    edif = edifC(_write_edif(tmp_path, body))
    view = edif.libraries["L"].cells["top"].bestView()
    assert [p.name for p in view.ports] == [
        "bus<0>", "bus<1>", "bus<2>", "bus<3>"]
    assert [i.name for i in view.instances] == ["I<0>", "I<1>", "I<2>"]
    assert view.nets[0].refs[0].port == "bus<2>"


def test_parse_transform_and_figure(tmp_path):
    """Instance transforms and net figure segments are extracted."""
    body = """
      (external P (technology (numberDefinition
        (scale 1 (e 1 -3) (unit DISTANCE))))
        (cell r (view s (viewType NETLIST) (interface))))
      (library L (cell top
        (view v (viewType SCHEMATIC)
          (interface)
          (contents
            (instance i1 (viewRef s (cellRef r (libraryRef P)))
              (transform (translation (pt 10 20)) (orientation MYR90)))
            (net n (joined (portRef p (instanceRef i1)))
              (figure (figureGroup
                (path (pointList (pt 0 0) (pt 5 0) (pt 5 5))))))))))
    """
    edif = edifC(_write_edif(tmp_path, body))
    view = edif.libraries["L"].cells["top"].bestView()
    inst = view.instances[0]
    assert inst.pos == (10.0, 20.0)
    assert inst.angle == pytest.approx(90.0)
    assert inst.flip == (-1, 1)
    assert view.nets[0].segments == [[(0.0, 0.0), (5.0, 0.0), (5.0, 5.0)]]


def test_parse_multi_page(tmp_path):
    """Page wrappers merge while keeping distinct page indices."""
    body = """
      (library L (cell top
        (view v (viewType SCHEMATIC)
          (interface)
          (contents
            (page "p1" (instance i1 (viewRef s (cellRef c))))
            (page "p2" (instance i2 (viewRef s (cellRef c))))))))
    """
    edif = edifC(_write_edif(tmp_path, body))
    view = edif.libraries["L"].cells["top"].bestView()
    assert len(view.instances) == 2
    assert len({i.page for i in view.instances}) == 2


def _run_import(tmp_path: Path, body: str, libraryDict=None):
    parent = _make_parent(tmp_path, libraryDict)
    import_lib = _make_import_lib(tmp_path)
    importer = edifImporter(
        parent, _write_edif(tmp_path, body), import_lib)
    importer.importEDIF()
    return importer, import_lib


def _read(lib_path: Path, cell: str, view: str):
    return json.loads(lib_path.joinpath(cell, f"{view}.json").read_text())


def test_import_writes_schema_valid_views(tmp_path):
    """Every imported cell gets schema-valid schematic and symbol views."""
    _, import_lib = _run_import(tmp_path, _MINIMAL_BODY)
    for viewName in ("schematic", "symbol"):
        data = _read(import_lib.libraryPath, "INV", viewName)
        valid, errors = sv.validate_design_file(
            data, viewName, strict=True)
        assert valid, errors


def test_import_emits_sheet_pins_and_named_nets(tmp_path):
    """Interface ports become scp pins; net names persist as SET (ns=3)."""
    _, import_lib = _run_import(tmp_path, _MINIMAL_BODY)
    data = _read(import_lib.libraryPath, "INV", "schematic")
    pins = [r for r in data if r.get("type") == "scp"]
    nets = [r for r in data if r.get("type") == "scn"]
    assert {p["pn"] for p in pins} >= {"A"}
    assert any(n["nam"] == "A" and n["ns"] == 3 for n in nets)


def test_import_viewless_cell_dialect(tmp_path):
    """Cells with interface/contents directly under (cell …) — no (view …)
    wrapper — import as schematics; ;; comments and keyword-first scale
    are tolerated. A joined interface port names the net."""
    body = """
      ;; external library with a view-less cell
      (external analogLib
        (technology (numberDefinition (scale distance 1 (E 1 -6))))
        (cell res (cellType GENERIC)
          (interface (port p (direction INOUT)) (port n (direction INOUT)))))
      (library MY_WORK_LIB
        (technology (numberDefinition (scale distance 1 (E 1 -6))))
        (cell schematic_top (cellType GENERIC)
          (interface (port IN (direction INPUT)))
          (contents
            (instance R1 (cellRef res (libraryRef analogLib))
              (property r (string "1K")))
            (net net_in
              (joined
                (portRef IN)             ; top-level input port
                (portRef p (instanceRef R1)))
              (figure wire (path (pointList (pt 0 100) (pt 200 100))))))))
      (design top_level
        (cellRef schematic_top (libraryRef MY_WORK_LIB)))
    """
    _, import_lib = _run_import(tmp_path, body)
    data = _read(import_lib.libraryPath, "schematic_top", "schematic")
    inst = next(r for r in data if r.get("type") == "sys")
    assert inst["nam"] == "R1"
    assert inst["cell"] == "res"          # stub generated for analogLib/res
    assert inst["ld"]["@r"] == ["1K", True]
    pins = [r for r in data if r.get("type") == "scp"]
    assert any(p["pn"] == "IN" for p in pins)
    # Interface pin asserts the net name — wires carry "IN", not "net_in".
    nets = [r for r in data if r.get("type") == "scn"]
    assert nets and all(n["nam"] == "IN" for n in nets)
    valid, errors = sv.validate_design_file(data, "schematic", strict=True)
    assert valid, errors
    _, diags = checkRecords(
        data, pinLocator=makeSymbolPinLocator(
            {import_lib.libraryName: import_lib.libraryPath}))
    assert not [d for d in diags if d.kind == "netNameConflict"]
    # Stub symbol got the interface ports p/n.
    sym = _read(import_lib.libraryPath, "res", "symbol")
    assert {r["nam"] for r in sym if r.get("type") == "pin"} == {"p", "n"}


def test_import_instances_properties_and_stub_symbols(tmp_path):
    """External refs become stub symbols; properties land in ld/paramDefs."""
    body = """
      (external PRIMS
        (cell RES (view s (viewType NETLIST)
          (interface (port PLUS (direction INOUT))
                     (port MINUS (direction INOUT))))))
      (library WORK (cell top
        (view v (viewType SCHEMATIC)
          (interface)
          (contents
            (instance I1 (viewRef s (cellRef RES (libraryRef PRIMS)))
              (property VALUE (string "1k")))
            (net n1 (joined (portRef PLUS (instanceRef I1))))))))
    """
    _, import_lib = _run_import(tmp_path, body)
    schem = _read(import_lib.libraryPath, "top", "schematic")
    inst = next(r for r in schem if r.get("type") == "sys")
    assert inst["cell"] == "RES"
    assert inst["lib"] == "importLib"
    assert inst["ld"]["@VALUE"] == ["1k", True]
    # Stub symbol generated with declared interface and paramDefs.
    sym = _read(import_lib.libraryPath, "RES", "symbol")
    valid, errors = sv.validate_design_file(sym, "symbol", strict=True)
    assert valid, errors
    assert {r["nam"] for r in sym if r.get("type") == "pin"} == {
        "PLUS", "MINUS"}
    attrs = {r["nam"]: r["def"] for r in sym if r.get("type") == "attr"}
    defs = prm.paramDefsFromSymattrs(attrs)
    assert [d.name for d in defs] == ["VALUE"]


def test_import_honours_figure_geometry(tmp_path):
    """EDIF net figures become scn segments near the recorded geometry."""
    body = """
      (library L (cell top
        (view v (viewType SCHEMATIC)
          (interface (port A (direction INPUT)))
          (contents
            (net A (joined (portRef A))
              (figure (figureGroup
                (path (pointList (pt 0 0) (pt 10 0) (pt 10 10))))))))))
    """
    _, import_lib = _run_import(tmp_path, body)
    data = _read(import_lib.libraryPath, "top", "schematic")
    segs = [r for r in data if r.get("type") == "scn" and r["nam"] == "A"]
    assert len(segs) == 2  # 3-point path -> 2 segments
    assert segs[0]["ns"] == 3
    # The interface pin must sit on a segment (not floating).
    pin = next(r for r in data if r.get("type") == "scp")
    pinPt = tuple(pin["st"])
    assert any(
        pinPt in (tuple(s["st"]), tuple(s["end"])) for s in segs)


def test_import_fallback_placement_and_stub_nets(tmp_path):
    """Without geometry, instances auto-place and pins get named stubs."""
    body = """
      (external P (cell dev (view s (viewType NETLIST)
        (interface (port G (direction INPUT))))))
      (library L (cell top
        (view v (viewType SCHEMATIC)
          (interface)
          (contents
            (instance i1 (viewRef s (cellRef dev (libraryRef P))))
            (instance i2 (viewRef s (cellRef dev (libraryRef P))))
            (net net_a (joined (portRef G (instanceRef i1))
                               (portRef G (instanceRef i2))))))))
    """
    _, import_lib = _run_import(tmp_path, body)
    data = _read(import_lib.libraryPath, "top", "schematic")
    insts = [r for r in data if r.get("type") == "sys"]
    assert len({tuple(r["loc"]) for r in insts}) == 2  # distinct positions
    # Both G pins got stubs named net_a -> connect by name.
    result, diags = checkRecords(
        data, pinLocator=makeSymbolPinLocator(
            {import_lib.libraryName: import_lib.libraryPath}))
    floating = [d for d in diags if d.kind == "floatingPin"]
    assert not floating, [d.message for d in floating]
    netNames = {result.segName[sid][0]
                for sid in result.segName
                if result.segName[sid][0] == "net_a"}
    assert netNames == {"net_a"}


def _write_loaded_lib_symbol(lib_path: Path, cell_name: str) -> Path:
    """Create a loaded-library cell with a minimal symbol view."""
    cell_dir = lib_path / cell_name
    cell_dir.mkdir(parents=True)
    lib_path.joinpath("reveda.lib").touch()
    cell_dir.joinpath("symbol.json").write_text(json.dumps([
        sv.make_view_header("symbol"), {},
        {"type": "pin", "st": [0, 0], "nam": "PLUS", "pd": "Inout",
         "pt": "Signal", "loc": [0, 0], "ang": 0, "fl": [1, 1]},
        {"type": "attr", "nam": "pinOrder", "def": "PLUS"},
    ]))
    return cell_dir


def test_import_resolves_loaded_library_symbols(tmp_path):
    """External refs resolve against loaded libraries by cell name."""
    other_lib = tmp_path / "loadedLib"
    _write_loaded_lib_symbol(other_lib, "RES")
    body = """
      (library L (cell top
        (view v (viewType SCHEMATIC)
          (interface)
          (contents
            (instance i1 (viewRef s (cellRef RES (libraryRef P))))))))
    """
    _, import_lib = _run_import(
        tmp_path, body, libraryDict={"loadedLib": other_lib})
    data = _read(import_lib.libraryPath, "top", "schematic")
    inst = next(r for r in data if r.get("type") == "sys")
    assert inst["lib"] == "loadedLib"
    assert inst["cell"] == "RES"
    assert inst["view"] == "symbol"
    assert not import_lib.libraryPath.joinpath("RES").exists()


def test_import_resolves_loaded_library_case_insensitive(tmp_path):
    """Loaded-library cell dirs resolve even when EDIF case differs."""
    other_lib = tmp_path / "loadedLib"
    _write_loaded_lib_symbol(other_lib, "res")
    body = """
      (library L (cell top
        (view v (viewType SCHEMATIC)
          (interface)
          (contents
            (instance i1 (viewRef s (cellRef RES (libraryRef P))))))))
    """
    _, import_lib = _run_import(
        tmp_path, body, libraryDict={"loadedLib": other_lib})
    data = _read(import_lib.libraryPath, "top", "schematic")
    inst = next(r for r in data if r.get("type") == "sys")
    # sys record uses the real on-disk cell name.
    assert (inst["lib"], inst["cell"], inst["view"]) == (
        "loadedLib", "res", "symbol")
    assert not import_lib.libraryPath.joinpath("RES").exists()


def test_import_multi_page_offsets(tmp_path):
    """Multi-page contents merge into one schematic with band offsets."""
    body = """
      (external P (cell dev (view s (viewType NETLIST) (interface))))
      (library L (cell top
        (view v (viewType SCHEMATIC)
          (interface)
          (contents
            (page "p1"
              (instance i1 (viewRef s (cellRef dev (libraryRef P)))
                (transform (translation (pt 0 0)))))
            (page "p2"
              (instance i2 (viewRef s (cellRef dev (libraryRef P)))
                (transform (translation (pt 0 0)))))))))
    """
    _, import_lib = _run_import(tmp_path, body)
    data = _read(import_lib.libraryPath, "top", "schematic")
    insts = [r for r in data if r.get("type") == "sys"]
    assert len(insts) == 2
    # Both at EDIF (0,0) but on different pages -> separated in scene.
    assert insts[0]["loc"] != insts[1]["loc"]


def test_import_twice_reuses_cells(tmp_path):
    """Re-importing refreshes existing cells rather than duplicating."""
    _, import_lib = _run_import(tmp_path, _MINIMAL_BODY)
    parent = _make_parent(tmp_path)
    importer = edifImporter(
        parent, _write_edif(tmp_path, _MINIMAL_BODY, "second.edf"),
        import_lib)
    importer.importEDIF()
    cell_dir = import_lib.libraryPath / "INV"
    assert cell_dir.is_dir()
    data = _read(import_lib.libraryPath, "INV", "schematic")
    valid, errors = sv.validate_design_file(data, "schematic", strict=True)
    assert valid, errors


def test_connectivity_check_on_imported_schematic(tmp_path):
    """checkRecords reports no errors on the imported top schematic."""
    body = """
      (external P (cell inv1 (view s (viewType NETLIST)
        (interface (port A (direction INPUT)) (port Y (direction OUTPUT))))))
      (library L (cell top
        (view v (viewType SCHEMATIC)
          (interface (port IN (direction INPUT))
                     (port OUT (direction OUTPUT)))
          (contents
            (instance i1 (viewRef s (cellRef inv1 (libraryRef P))))
            (net IN (joined (portRef IN) (portRef A (instanceRef i1))))
            (net OUT (joined (portRef OUT) (portRef Y (instanceRef i1))))))))
    """
    _, import_lib = _run_import(tmp_path, body)
    data = _read(import_lib.libraryPath, "top", "schematic")
    _, diags = checkRecords(
        data, pinLocator=makeSymbolPinLocator(
            {import_lib.libraryName: import_lib.libraryPath}))
    errors = [d for d in diags if d.severity == "error"]
    assert not errors, [d.message for d in errors]
    floating = [d for d in diags if d.kind == "floatingPin"]
    assert not floating, [d.message for d in floating]
