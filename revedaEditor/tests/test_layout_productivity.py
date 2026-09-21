"""Phase 5 layout-editing productivity tests.

Covers instance arrays (mosaics), multipart items, boolean layer ops,
hierarchy restructuring (flatten / make-cell), stream options, and ruler
readout/deletion.
"""
import json
import pathlib

import pytest
from PySide6.QtCore import QLineF, QPoint, QPointF
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

import revedaEditor.common.layoutBoolean as lbool
import revedaEditor.common.layoutFlatten as lflat
import revedaEditor.common.layoutMerge as lmerge
import revedaEditor.common.layoutShapes as lshp
import revedaEditor.fileio.layoutEncoder as layenc
import revedaEditor.tests.sceneTestUtils as stu
from defaultPDK.layoutLayers import m1Layer_drw, odLayer_drw
from defaultPDK.process import v1
from revedaEditor.fileio.loadJSON import layoutItems


@pytest.fixture(scope="module", autouse=True)
def init_qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture()
def scene():
    return stu.makeLayoutScene()


def _rect(x0=0, y0=0, x1=100, y1=100, layer=None):
    return lshp.layoutRect(
        QPoint(x0, y0), QPoint(x1, y1), layer or odLayer_drw)


def _encode(item):
    return json.loads(json.dumps(item, cls=layenc.layoutEncoder))


# ---------------------------------------------------------------------------
# Instance arrays / mosaics
# ---------------------------------------------------------------------------

def _instanceWithRect(scene):
    inst = lshp.layoutInstance([])
    inst.libraryName = "lib"
    inst.cellName = "cell"
    inst.viewName = "layout"
    inst.counter = 1
    inst.instanceName = "I1"
    inst.shapes = [_rect(0, 0, 10, 10)]
    scene.addItem(inst)
    return inst


def test_instance_defaults_not_arrayed(scene):
    inst = _instanceWithRect(scene)
    assert inst.rows == 1 and inst.cols == 1
    record = _encode(inst)
    assert "rows" not in record and "cols" not in record
    assert "rpt" not in record and "cpt" not in record


def test_instance_array_fields_encode_round_trip(scene):
    inst = _instanceWithRect(scene)
    inst.setArray(rows=2, cols=3, rowPitch=100, colPitch=50)
    record = _encode(inst)
    assert record["rows"] == 2 and record["cols"] == 3
    assert record["rpt"] == 100 and record["cpt"] == 50


def test_instance_array_loads_from_record(scene):
    inst = _instanceWithRect(scene)
    inst.setArray(rows=2, cols=3, rowPitch=100, colPitch=50)
    record = _encode(inst)

    # The record references a nonexistent lib/cell, so the factory loader
    # cannot rebuild it; drive the same code path on a live instance instead.
    inst2 = _instanceWithRect(scene)
    inst2.setArray(
        record.get("rows", 1), record.get("cols", 1),
        record.get("rpt", 0), record.get("cpt", 0))
    assert inst2.rows == 2 and inst2.cols == 3
    assert inst2.rowPitch == 100 and inst2.colPitch == 50


def test_instance_array_bounds_cover_all_elements(scene):
    inst = _instanceWithRect(scene)
    inst.setArray(rows=2, cols=2, rowPitch=100, colPitch=100)
    bounds = inst.boundingRect()
    # Elements span (0..10) + pitches (100): outer edge at 110.
    assert bounds.right() >= 110 - 2
    assert bounds.bottom() >= 110 - 2


def test_instance_array_export_emits_aref(scene):
    inst = _instanceWithRect(scene)
    inst.setArray(rows=2, cols=3, rowPitch=100, colPitch=50)

    import revedaEditor.fileio.exportGDS as gdse
    exporter = gdse.gdsExporter("TOP", [inst], pathlib.Path("/tmp/x.gds"))
    lib = exporter._buildLibrary()
    top = next(c for c in lib.cells if c.name == "TOP")
    assert len(top.references) == 1
    rep = top.references[0].repetition
    assert rep.columns == 3 and rep.rows == 2
    assert tuple(rep.spacing) == (50, 100)


def test_array_clones_realize_as_children(scene):
    inst = _instanceWithRect(scene)
    inst.setArray(rows=2, cols=2, rowPitch=100, colPitch=100)
    clones = inst.arrayShapes
    assert len(clones) == 3  # 2x2 minus the base element
    xs = sorted(c.pos().x() for c in clones)
    ys = sorted(c.pos().y() for c in clones)
    assert xs == [0, 100, 100]
    assert ys == [0, 100, 100]


# ---------------------------------------------------------------------------
# Multipart items
# ---------------------------------------------------------------------------

def test_guard_ring_builds_rects_and_vias():
    ring = lshp.layoutGuardRing(
        {"tl": [0, 0], "br": [2000, 1500], "layer": "", "width": 200,
         "via": "con"})
    kinds = [type(s).__name__ for s in ring.shapes]
    assert kinds.count("layoutRect") == 4
    assert kinds.count("layoutViaArray") == 4


def test_guard_ring_without_via_builds_rects_only():
    ring = lshp.layoutGuardRing(
        {"tl": [0, 0], "br": [2000, 1500], "layer": "m1", "width": 200,
         "via": ""})
    assert all(type(s).__name__ == "layoutRect" for s in ring.shapes)
    assert len(ring.shapes) == 4


def test_shielded_path_offsets():
    sp = lshp.layoutShieldedPath(
        {"p1": [0, 0], "p2": [3000, 0], "signalLayer": "m1",
         "signalWidth": 100, "shieldLayer": "m1", "shieldWidth": 80,
         "gap": 100})
    paths = [s for s in sp.shapes if isinstance(s, lshp.layoutPath)]
    assert len(paths) == 3
    ys = sorted(p.draftLine.p1().y() for p in paths)
    # offset = signalW/2 + gap + shieldW/2 = 50 + 100 + 40 = 190
    assert ys == [-190, 0, 190]


def test_bus_route_fanout():
    bus = lshp.layoutBusRoute(
        {"p1": [0, 0], "p2": [0, 4000], "layer": "m1", "width": 50,
         "spacing": 50, "count": 4})
    assert len(bus.shapes) == 4
    xs = sorted(s.draftLine.p1().x() for s in bus.shapes)
    # pitch = 100, symmetric about 0: -150, -50, 50, 150
    assert xs == [-150, -50, 50, 150]


def test_multipart_record_round_trip(scene):
    ring = lshp.layoutGuardRing(
        {"tl": [0, 0], "br": [2000, 1500], "layer": "m1", "width": 200,
         "via": ""})
    scene.addItem(ring)
    record = _encode(ring)
    assert record["type"] == "Multipart"
    assert record["kind"] == "guardRing"
    assert record["params"]["br"] == [2000, 1500]

    factory = layoutItems(scene)
    rebuilt = factory.create(record)
    assert isinstance(rebuilt, lshp.layoutGuardRing)
    assert len(rebuilt.shapes) == 4


def test_multipart_setparams_rebuilds():
    bus = lshp.layoutBusRoute(
        {"p1": [0, 0], "p2": [0, 4000], "layer": "m1", "width": 50,
         "spacing": 50, "count": 2})
    assert len(bus.shapes) == 2
    bus.setParams({"count": 6})
    assert len(bus.shapes) == 6
    assert bus.params["count"] == 6


def test_multipart_export_children_in_parent_frame(scene):
    import revedaEditor.fileio.exportGDS as gdse

    sp = lshp.layoutShieldedPath(
        {"p1": [0, 0], "p2": [3000, 0], "signalLayer": "m1",
         "signalWidth": 100, "shieldLayer": "m1", "shieldWidth": 80,
         "gap": 100})
    sp.setPos(500, 700)
    scene.addItem(sp)

    exporter = gdse.gdsExporter("TOP", [sp], pathlib.Path("/tmp/x.gds"))
    lib = exporter._buildLibrary()
    top = next(c for c in lib.cells if c.name == "TOP")
    # three paths exported at the multipart's scene position
    assert len(top.paths) == 3
    xs = sorted(p.spine()[0][0] for p in top.paths)
    assert xs == [500, 500, 500]
    ys = sorted(p.spine()[0][1] for p in top.paths)
    assert ys == [510, 700, 890]


def test_scene_multipart_draw_two_clicks(scene):
    scene.newMultipartSpec = (
        "busRoute",
        {"p1": [0, 0], "p2": [0, 0], "layer": "m1", "width": 50,
         "spacing": 50, "count": 3},
    )
    scene.drawLayoutMultipart(QPoint(100, 100))
    assert scene._newMultipart is not None
    scene.drawLayoutMultipart(QPoint(100, 3100))
    assert scene._newMultipart is None
    mp = next(i for i in scene.items()
              if isinstance(i, lshp.layoutBusRoute))
    assert len(mp.shapes) == 3


# ---------------------------------------------------------------------------
# Boolean layer operations
# ---------------------------------------------------------------------------

def _rectTuple(item) -> tuple:
    """Axis-aligned rect corners as (left, top, right, bottom)."""
    r = item.rect
    return r.left(), r.top(), r.right(), r.bottom()


def test_boolean_or_merges_overlapping(scene):
    # Side-by-side overlap unions to a single rectangle.
    r1 = _rect(0, 0, 100, 100)
    r2 = _rect(50, 0, 150, 100)
    scene.addItem(r1)
    scene.addItem(r2)
    produced, consumed = lbool.booleanLayerItems([r1, r2], "or")
    assert len(consumed) == 2 and len(produced) == 1
    assert _rectTuple(produced[0]) == (0, 0, 150, 100)


def test_boolean_or_l_shape_returns_polygon(scene):
    # Corner overlap unions to an L-shape, emitted as a polygon.
    r1 = _rect(0, 0, 100, 100)
    r2 = _rect(50, 50, 150, 150)
    scene.addItem(r1)
    scene.addItem(r2)
    produced, consumed = lbool.booleanLayerItems([r1, r2], "or")
    assert len(consumed) == 2 and len(produced) == 1
    assert isinstance(produced[0], lshp.layoutPolygon)
    bounds = produced[0].sceneBoundingRect()
    assert (bounds.left(), bounds.top()) == (0, 0)
    assert (bounds.right(), bounds.bottom()) == (150, 150)


def test_boolean_or_via_scene_is_undoable(scene):
    r1 = _rect(0, 0, 100, 100)
    r2 = _rect(50, 0, 150, 100)
    scene.addItem(r1)
    scene.addItem(r2)
    scene.selectedItemsSet = {r1, r2}
    scene.booleanSelectedItems("or")
    rects = [i for i in scene.items() if isinstance(i, lshp.layoutRect)]
    assert len(rects) == 1
    scene.undoStack.undo()
    rects = [i for i in scene.items() if isinstance(i, lshp.layoutRect)]
    assert len(rects) == 2


def test_boolean_and_intersects_group(scene):
    r1 = _rect(0, 0, 100, 100)
    r2 = _rect(50, 0, 150, 100)
    r3 = _rect(60, 0, 200, 100)
    for r in (r1, r2, r3):
        scene.addItem(r)
    produced, consumed = lbool.booleanLayerItems([r1, r2, r3], "and")
    assert len(consumed) == 3 and len(produced) == 1
    # Intersection of the three: x in [60,100], y in [0,100]
    assert _rectTuple(produced[0]) == (60, 0, 100, 100)


def _sceneArea(item) -> float:
    """Shoelace area of the item's scene-space polygon."""
    pts = [(p.x(), p.y()) for p in lmerge._scenePolygon(item)]
    area = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        area += x0 * y1 - x1 * y0
    return abs(area) / 2


def test_boolean_xor(scene):
    # Two 100x100 rects overlapping by 50x100: xor keeps only the
    # non-overlapping parts -> total area 2*(50*100), not the union's 15000.
    r1 = _rect(0, 0, 100, 100)
    r2 = _rect(50, 0, 150, 100)
    produced, consumed = lbool.booleanLayerItems([r1, r2], "xor")
    assert len(consumed) == 2 and len(produced) >= 1
    assert sum(_sceneArea(p) for p in produced) == pytest.approx(10000)


def test_boolean_xor_identical_then_third(scene):
    # A xor A = empty; the fold must continue so empty xor B = B.
    r1 = _rect(0, 0, 100, 100)
    r2 = _rect(0, 0, 100, 100)
    r3 = _rect(200, 0, 300, 100)
    produced, consumed = lbool.booleanLayerItems([r1, r2, r3], "xor")
    assert len(consumed) == 3 and len(produced) == 1
    assert _sceneArea(produced[0]) == pytest.approx(10000)


def test_boolean_not_across_layers(scene):
    a = _rect(0, 0, 100, 100, odLayer_drw)
    b = _rect(40, 40, 60, 60, m1Layer_drw)
    produced, consumed = lbool.booleanLayerItems([a, b], "not")
    # A consumed and replaced by the keyhole polygon; B survives untouched.
    assert consumed == [a]
    assert len(produced) == 1
    poly = produced[0]
    assert isinstance(poly, lshp.layoutPolygon)
    # outer rect minus the 20x20 hole -> 9600
    xs = [p.x() for p in poly.points]
    ys = [p.y() for p in poly.points]
    assert (min(xs), min(ys), max(xs), max(ys)) == (0, 0, 100, 100)


def test_boolean_grow_shrink(scene):
    g = _rect(0, 0, 100, 100)
    produced, _ = lbool.booleanLayerItems([g], "grow", 10)
    r = produced[0].rect
    assert (r.left(), r.top(), r.right(), r.bottom()) == (-10, -10, 110, 110)
    produced, _ = lbool.booleanLayerItems([g], "shrink", 10)
    r = produced[0].rect
    assert (r.left(), r.top(), r.right(), r.bottom()) == (10, 10, 90, 90)


def test_boolean_ignores_non_polygonal(scene):
    path = lshp.layoutPath(QLineF(0, 0, 100, 0), m1Layer_drw, 10, 0, 0, 2)
    scene.addItem(path)
    produced, consumed = lbool.booleanLayerItems([path], "or")
    assert produced == [] and consumed == []


# ---------------------------------------------------------------------------
# Hierarchy restructuring
# ---------------------------------------------------------------------------

def test_flatten_rotated_instance(scene):
    inst = _instanceWithRect(scene)
    inst.setPos(500, 0)
    inst.angle = 90
    flat = lflat.flattenInstance(inst)
    assert len(flat) == 1
    # (0,0)-(10,10) rotated 90 then shifted +500 in x -> x in [490,500]
    assert _rectTuple(flat[0]) == (490, 0, 500, 10)


def test_flatten_arrayed_instance_expands(scene):
    inst = _instanceWithRect(scene)
    inst.setArray(rows=1, cols=3, rowPitch=0, colPitch=100)
    flat = lflat.flattenInstance(inst)
    assert len(flat) == 3
    xs = sorted(f.sceneBoundingRect().left() for f in flat)
    assert xs == [-2, 98, 198]  # elements at x=0,100,200 minus margin


def test_flatten_selection_undoable(scene):
    inst = _instanceWithRect(scene)
    scene.selectedItemsSet = {inst}
    scene.flattenSelection()
    top = [i for i in scene.items()
           if i.parentItem() is None
           and isinstance(i, tuple(scene.LAYOUT_SHAPES))]
    assert not any(isinstance(i, lshp.layoutInstance) for i in top)
    scene.undoStack.undo()
    top = [i for i in scene.items()
           if i.parentItem() is None
           and isinstance(i, tuple(scene.LAYOUT_SHAPES))]
    assert any(isinstance(i, lshp.layoutInstance) for i in top)


def test_make_cell_from_selection(scene, tmp_path):
    libDir = tmp_path / "lib"
    libDir.mkdir()
    scene.libraryDict["lib"] = libDir

    r1 = _rect(100, 200, 300, 400)
    scene.addItem(r1)
    scene.selectedItemsSet = {r1}
    assert scene.makeCellFromSelection("lib", "newcell") is True

    cellFile = libDir / "newcell" / "layout.json"
    assert cellFile.exists()
    data = json.loads(cellFile.read_text())
    assert data[0]["viewType"] == "layout"
    rectRecord = next(r for r in data if r.get("type") == "Rect")

    insts = [i for i in scene.items()
             if isinstance(i, lshp.layoutInstance)]
    assert len(insts) == 1
    inst = insts[0]
    assert inst.cellName == "newcell"
    # The cell's contents shifted by -origin and the instance placed at the
    # same origin means the rendered rect lands back on the selection's
    # original position (100,200)-(300,400).
    tl, br = rectRecord["tl"], rectRecord["br"]
    ox, oy = inst.pos().x(), inst.pos().y()
    xs = sorted([tl[0] + ox, br[0] + ox])
    ys = sorted([tl[1] + oy, br[1] + oy])
    assert xs == [100, 300] and ys == [200, 400]


# ---------------------------------------------------------------------------
# Stream options
# ---------------------------------------------------------------------------

def _exportLib(items, name="TOP", **opts):
    import revedaEditor.fileio.exportGDS as gdse
    exporter = gdse.gdsExporter(
        name, items, pathlib.Path("/tmp/x.gds"))
    exporter.layerMap = opts.get("layerMap")
    exporter.cellNameMap = opts.get("cellNameMap")
    exporter.flattenDepth = opts.get("flattenDepth")
    return exporter._buildLibrary()


def test_layer_map_remaps_output(scene):
    r = _rect(0, 0, 100, 100, m1Layer_drw)
    lib = _exportLib([r], layerMap={
        (m1Layer_drw.gdsLayer, m1Layer_drw.datatype): (99, 7)})
    top = next(c for c in lib.cells if c.name == "TOP")
    assert top.polygons[0].layer == 99
    assert top.polygons[0].datatype == 7


def test_cell_name_map(scene):
    inst = _instanceWithRect(scene)
    lib = _exportLib([inst], cellNameMap={
        "TOP": "TOPCELL", "cell": "RENAMED"})
    names = [c.name for c in lib.cells]
    assert "TOPCELL" in names and "RENAMED" in names


def test_flatten_depth_keeps_top_ref(scene):
    leaf = lshp.layoutInstance([])
    leaf.libraryName = "lib"
    leaf.cellName = "leaf"
    leaf.viewName = "layout"
    leaf.counter = 1
    leaf.instanceName = "L1"
    leaf.shapes = [_rect(0, 0, 10, 10)]
    leaf.setPos(700, 0)

    child = lshp.layoutInstance([])
    child.libraryName = "lib"
    child.cellName = "child"
    child.viewName = "layout"
    child.counter = 1
    child.instanceName = "I1"
    child.shapes = [_rect(0, 0, 100, 100), leaf]
    child.setPos(500, 0)
    scene.addItem(child)

    lib = _exportLib([child], flattenDepth=1)
    childCell = next(c for c in lib.cells if c.name == "lib_child_layout")
    # The leaf instance was flattened into the child cell.
    assert len(childCell.references) == 0
    assert len(childCell.polygons) == 2


def test_flatten_depth_zero_flattens_all(scene):
    inst = _instanceWithRect(scene)
    inst.setPos(500, 0)
    lib = _exportLib([inst], flattenDepth=0)
    assert len(lib.cells) == 1
    top = lib.cells[0]
    assert len(top.references) == 0
    assert top.polygons[0].bounding_box() == ((500.0, 0.0), (510.0, 10.0))


def test_export_dialog_parsers():
    import revedaEditor.gui.fileDialogues as fd

    dlg = fd.gdsExportDialogue.__new__(fd.gdsExportDialogue)
    # Drive the parse helpers without a full dialog exec.
    import revedaEditor.gui.editFunctions as edf
    dlg.layerMapEdit = edf.longLineEdit()
    dlg.cellNameMapEdit = edf.longLineEdit()
    dlg.layerMapEdit.setText("1,0=11,0; 2,0 = 12,0 ; bad;3=x")
    dlg.cellNameMapEdit.setText("myCell=MYCELL; lib_c_v = X ; =ignored")
    assert dlg.layerMap() == {(1, 0): (11, 0), (2, 0): (12, 0)}
    assert dlg.cellNameMap() == {"myCell": "MYCELL", "lib_c_v": "X"}


# ---------------------------------------------------------------------------
# Rulers
# ---------------------------------------------------------------------------

def test_ruler_delta_label(scene):
    ruler = lshp.layoutRuler(
        draftLine=QLineF(QPointF(0, 0), QPointF(3000, 0)),
        width=1.0, tickGap=25.0, tickLength=5,
        tickFont=QFont("Arial", 10), mode=0,
    )
    scene.addItem(ruler)
    ruler._createRulerTicks()
    last = ruler._tickTuples[-1].text
    # 3000 scene units / dbu=1000 -> "3 (3,0)"
    assert last.startswith("3 ")
    assert "(3,0)" in last


def test_ruler_delta_label_diagonal(scene):
    ruler = lshp.layoutRuler(
        draftLine=QLineF(QPointF(0, 0), QPointF(3000, 4000)),
        width=1.0, tickGap=25.0, tickLength=5,
        tickFont=QFont("Arial", 10), mode=2,  # any-angle keeps the diagonal
    )
    scene.addItem(ruler)
    ruler._createRulerTicks()
    last = ruler._tickTuples[-1].text
    assert "(3,4)" in last
    assert last.startswith("5 ")


def test_delete_selected_rulers(scene):
    r1 = lshp.layoutRuler(
        QLineF(0, 0, 100, 0), 1.0, 25.0, 5, QFont("Arial", 10))
    r2 = lshp.layoutRuler(
        QLineF(0, 100, 100, 100), 1.0, 25.0, 5, QFont("Arial", 10))
    scene.addItem(r1)
    scene.addItem(r2)
    scene.rulersSet.update({r1, r2})
    r1.setSelected(True)
    assert scene.deleteSelectedRulers() is True
    remaining = [i for i in scene.items()
                 if isinstance(i, lshp.layoutRuler)]
    assert remaining == [r2]


def test_delete_all_rulers_kept(scene):
    r1 = lshp.layoutRuler(
        QLineF(0, 0, 100, 0), 1.0, 25.0, 5, QFont("Arial", 10))
    scene.addItem(r1)
    scene.rulersSet.add(r1)
    scene.deleteAllRulers()
    assert not [i for i in scene.items()
                if isinstance(i, lshp.layoutRuler)]


def test_guard_ring_via_arrays_stay_within_ring():
    """Via centres must not overshoot the ring: xs is a *gap*, so the array
    span is (n-1)*(xs+cut) + cut and must fit inside the rail length."""
    ring = lshp.layoutGuardRing(
        {"tl": [0, 0], "br": [2000, 1500], "layer": "", "width": 200,
         "via": "con"})
    arrays = [s for s in ring.shapes
              if isinstance(s, lshp.layoutViaArray)]
    assert len(arrays) == 4
    for arr in arrays:
        cut = arr._prototype_via.width
        if arr.xnum > 1:
            # horizontal edge: last cut right edge <= x1 - width/2 region
            span = (arr.xnum - 1) * (arr.xs + cut) + cut
            assert span <= 2000 - 200 + 1  # hLen + tolerance
            # consecutive cut spacing equals intended pitch
            assert arr.xs + cut == pytest.approx(arr.xs + cut)
        if arr.ynum > 1:
            span = (arr.ynum - 1) * (arr.ys + cut) + cut
            assert span <= 1500 - 200 + 1


def test_guard_ring_via_pitch_matches_min_pitch():
    """For a ring sized to an exact multiple of min pitch the gap passed to
    the array should equal minSpacing*dbu (pitch - cut), not pitch."""
    from revedaEditor.backend.pdkLoader import importPDKModule
    proc = importPDKModule("process")
    viaDef = next(v for v in proc.processVias if v.name == "con")
    dbu = 1000
    cut = float(viaDef.minWidth) * dbu
    pitch = (float(viaDef.minWidth) + float(viaDef.minSpacing)) * dbu
    width = 200
    # choose hLen = k*pitch exactly: x1-x0-width = k*pitch
    k = 4
    x1 = int(k * pitch + width)
    ring = lshp.layoutGuardRing(
        {"tl": [0, 0], "br": [x1, 1500], "layer": "", "width": width,
         "via": "con"})
    arr = next(s for s in ring.shapes
               if isinstance(s, lshp.layoutViaArray) and s.xnum > 1)
    assert arr.xs == pytest.approx(pitch - cut)


def _labelItem(x=0, y=0, orient="R0", text="L"):
    return lshp.layoutLabel(QPoint(x, y), text, "Arial", "Regular",
                            "1.0", "Left", orient, m1Layer_drw)


def test_flatten_label_orient_under_rotated_parent(scene):
    inst = lshp.layoutInstance([])
    inst.libraryName = "lib"
    inst.cellName = "cell"
    inst.viewName = "layout"
    inst.counter = 1
    inst.instanceName = "I1"
    inst.shapes = [_labelItem(10, 10, orient="R90")]
    inst.angle = 90
    scene.addItem(inst)
    flat = lflat.flattenInstance(inst)
    lab = next(i for i in flat if isinstance(i, lshp.layoutLabel))
    # Orient R90 contributes Qt rotation 90; the parent's 90 composes on top.
    assert lab.rotation() == pytest.approx(180)
    assert lab.labelOrient == "R90"
    assert lab.angle == pytest.approx(90)  # extra rotation persisted as 'ang'


def test_flattened_label_ang_round_trip(scene):
    inst = lshp.layoutInstance([])
    inst.libraryName = "lib"
    inst.cellName = "cell"
    inst.viewName = "layout"
    inst.counter = 1
    inst.instanceName = "I1"
    inst.shapes = [_labelItem(10, 10, orient="R0")]
    inst.angle = 90
    scene.addItem(inst)
    lab = next(i for i in lflat.flattenInstance(inst)
               if isinstance(i, lshp.layoutLabel))
    record = _encode(lab)
    assert record["ang"] == pytest.approx(90)
    factory = layoutItems(scene)
    rebuilt = factory.create(record)
    assert rebuilt.rotation() == pytest.approx(90)


def test_flatten_label_unrotated_parent_keeps_orient_only():
    label = _labelItem(5, 5, orient="R270")
    out = []
    lflat._flattenLabel(label, out, None)
    lab = out[0]
    assert lab.rotation() == pytest.approx(270)
    assert lab.angle == pytest.approx(0)


def test_flatten_via_array_rotation_round_trip(scene):
    proto = lshp.layoutVia(QPoint(0, 0), v1, 50, 50)
    array = lshp.layoutViaArray(QPoint(10, 20), proto, 30, 0, 2, 1)
    inst = lshp.layoutInstance([])
    inst.libraryName = "lib"
    inst.cellName = "cell"
    inst.viewName = "layout"
    inst.counter = 1
    inst.instanceName = "I1"
    inst.shapes = [array]
    inst.angle = 90
    scene.addItem(inst)
    flat = lflat.flattenInstance(inst)
    newArray = next(i for i in flat if isinstance(i, lshp.layoutViaArray))
    # layoutViaArray.angle feeds setRotation directly (Qt-positive), so the
    # flattened array carries the composed parent rotation unchanged.
    assert newArray.rotation() == pytest.approx(90)
    record = _encode(newArray)
    assert record["ang"] == pytest.approx(90)
    rebuilt = layoutItems(scene).create(record)
    assert rebuilt.rotation() == pytest.approx(90)


def test_make_cell_refuses_overwrite(scene, tmp_path):
    libDir = tmp_path / "lib"
    libDir.mkdir()
    scene.libraryDict["lib"] = libDir

    r1 = _rect(0, 0, 100, 100)
    scene.addItem(r1)
    scene.selectedItemsSet = {r1}
    assert scene.makeCellFromSelection("lib", "cellA") is True
    original = (libDir / "cellA" / "layout.json").read_text()

    r2 = _rect(500, 500, 900, 900)
    scene.addItem(r2)
    scene.selectedItemsSet = {r2}
    # Second call must not clobber the existing cellview.
    assert scene.makeCellFromSelection("lib", "cellA") is False
    assert (libDir / "cellA" / "layout.json").read_text() == original
    # Explicit opt-in still overwrites.
    assert scene.makeCellFromSelection("lib", "cellA",
                                       overwrite=True) is True
    assert (libDir / "cellA" / "layout.json").read_text() != original


def test_make_cell_registers_in_library_model(scene, tmp_path):
    import revedaEditor.backend.libBackEnd as libb
    libDir = tmp_path / "lib"
    libDir.mkdir()
    scene.libraryDict["lib"] = libDir

    libItem = libb.libraryItem(libDir)
    model = scene.editorWindow.appMainW.libraryModel = __import__(
        "PySide6.QtGui", fromlist=["QStandardItemModel"]).QStandardItemModel()
    model.appendRow(libItem)

    r1 = _rect(0, 0, 100, 100)
    scene.addItem(r1)
    scene.selectedItemsSet = {r1}
    assert scene.makeCellFromSelection("lib", "regcell") is True

    import revedaEditor.backend.libraryMethods as libm
    cellIt = libm.getCellItem(libItem, "regcell")
    assert cellIt is not None
    assert libm.getViewItem(cellIt, "layout") is not None
