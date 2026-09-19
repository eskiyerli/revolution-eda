import pytest
from PySide6.QtCore import QPoint, QPointF, QLineF, QRectF
from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import QApplication, QGraphicsScene

import revedaEditor.backend.undoStack as us
import revedaEditor.common.layoutMerge as lmerge
from revedaEditor.common import layoutShapes as lshp
from defaultPDK.layoutLayers import odLayer_drw, poLayer_drw


@pytest.fixture(scope="module", autouse=True)
def init_qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def _scene_with(*items):
    scene = QGraphicsScene()
    for item in items:
        scene.addItem(item)
    return scene


def _path(p1, p2, layer=odLayer_drw, width=10.0, se=0, ee=0, mode=0):
    return lshp.layoutPath(
        QLineF(QPointF(*p1), QPointF(*p2)), layer, width, se, ee, mode
    )


def _rect(start, end, layer=odLayer_drw):
    return lshp.layoutRect(QPoint(*start), QPoint(*end), layer)


def _polygon(points, layer=odLayer_drw):
    return lshp.layoutPolygon([QPointF(*p) for p in points], layer)


# ---------- paths ----------


def test_collinear_paths_touching_end_to_end():
    p1 = _path((0, 0), (100, 0))
    p2 = _path((100, 0), (200, 0))
    scene = _scene_with(p1, p2)
    produced, consumed = lmerge.mergeLayoutItems([p1, p2])
    assert len(produced) == 1
    assert set(consumed) == {p1, p2}
    ends = {tuple(p.toTuple()) for p in produced[0].sceneEndPoints}
    assert ends == {(0.0, 0.0), (200.0, 0.0)}
    assert produced[0].width == 10.0
    assert produced[0].layer is odLayer_drw


def test_collinear_paths_overlapping():
    p1 = _path((0, 0), (150, 0))
    p2 = _path((100, 0), (200, 0))
    scene = _scene_with(p1, p2)
    produced, consumed = lmerge.mergeLayoutItems([p1, p2])
    assert len(produced) == 1
    ends = {tuple(p.toTuple()) for p in produced[0].sceneEndPoints}
    assert ends == {(0.0, 0.0), (200.0, 0.0)}


def test_transitive_path_chain():
    p1 = _path((0, 0), (100, 0))
    p2 = _path((100, 0), (200, 0))
    p3 = _path((200, 0), (300, 0))
    scene = _scene_with(p1, p2, p3)
    produced, consumed = lmerge.mergeLayoutItems([p1, p2, p3])
    assert len(produced) == 1
    assert len(consumed) == 3
    ends = {tuple(p.toTuple()) for p in produced[0].sceneEndPoints}
    assert ends == {(0.0, 0.0), (300.0, 0.0)}


def test_paths_extends_preserved_in_drawn_span():
    # p1 has 5-unit start extend, p2 has 10-unit end extend: drawn span
    # is [-5, 210] while the merged centreline is [0, 200].
    p1 = _path((0, 0), (100, 0), se=5)
    p2 = _path((100, 0), (200, 0), ee=10)
    scene = _scene_with(p1, p2)
    produced, _ = lmerge.mergeLayoutItems([p1, p2])
    merged = produced[0]
    ends = sorted(tuple(p.toTuple()) for p in merged.sceneEndPoints)
    assert ends == [(0.0, 0.0), (200.0, 0.0)]
    # Extends must reproduce the union drawn span on whichever end it lands.
    assert sorted((merged.startExtend, merged.endExtend)) == [5, 10]


def test_paths_different_widths_no_merge():
    p1 = _path((0, 0), (100, 0), width=10.0)
    p2 = _path((100, 0), (200, 0), width=20.0)
    scene = _scene_with(p1, p2)
    produced, consumed = lmerge.mergeLayoutItems([p1, p2])
    assert produced == []
    assert consumed == []


def test_paths_different_layers_no_merge():
    p1 = _path((0, 0), (100, 0), layer=odLayer_drw)
    p2 = _path((100, 0), (200, 0), layer=poLayer_drw)
    scene = _scene_with(p1, p2)
    produced, consumed = lmerge.mergeLayoutItems([p1, p2])
    assert produced == []
    assert consumed == []


def test_paths_non_collinear_no_merge():
    # mode=2 (any angle): the draft line is not snapped to manhattan.
    p1 = _path((0, 0), (100, 0), mode=2)
    p2 = _path((100, 0), (200, 50), mode=2)
    scene = _scene_with(p1, p2)
    produced, consumed = lmerge.mergeLayoutItems([p1, p2])
    assert produced == []
    assert consumed == []


def test_paths_parallel_offset_no_merge():
    p1 = _path((0, 0), (100, 0))
    p2 = _path((0, 5), (100, 5))
    scene = _scene_with(p1, p2)
    produced, consumed = lmerge.mergeLayoutItems([p1, p2])
    assert produced == []
    assert consumed == []


def test_paths_disjoint_no_merge():
    p1 = _path((0, 0), (100, 0))
    p2 = _path((150, 0), (200, 0))
    scene = _scene_with(p1, p2)
    produced, consumed = lmerge.mergeLayoutItems([p1, p2])
    assert produced == []
    assert consumed == []


def test_vertical_paths_merge():
    p1 = _path((0, 0), (0, 100))
    p2 = _path((0, 100), (0, 200))
    scene = _scene_with(p1, p2)
    produced, consumed = lmerge.mergeLayoutItems([p1, p2])
    assert len(produced) == 1
    ends = {tuple(p.toTuple()) for p in produced[0].sceneEndPoints}
    assert ends == {(0.0, 0.0), (0.0, 200.0)}


def test_path_name_preserved():
    p1 = _path((0, 0), (100, 0))
    p2 = _path((100, 0), (200, 0))
    p1.name = "mynet"
    scene = _scene_with(p1, p2)
    produced, _ = lmerge.mergeLayoutItems([p2, p1])
    assert produced[0].name == "mynet"


# ---------- rects / polygons ----------


def test_rects_sharing_edge_merge_to_rect():
    r1 = _rect((0, 0), (10, 10))
    r2 = _rect((10, 0), (20, 10))
    scene = _scene_with(r1, r2)
    produced, consumed = lmerge.mergeLayoutItems([r1, r2])
    assert len(produced) == 1
    assert isinstance(produced[0], lshp.layoutRect)
    assert set(consumed) == {r1, r2}
    bounds = produced[0].rect
    assert bounds == QRectF(0, 0, 20, 10)


def test_overlapping_rects_merge_to_rect():
    r1 = _rect((0, 0), (15, 10))
    r2 = _rect((10, 0), (25, 10))
    scene = _scene_with(r1, r2)
    produced, _ = lmerge.mergeLayoutItems([r1, r2])
    assert len(produced) == 1
    assert isinstance(produced[0], lshp.layoutRect)


def test_lshaped_union_produces_polygon():
    r1 = _rect((0, 0), (10, 10))
    r2 = _rect((10, 0), (20, 5))
    scene = _scene_with(r1, r2)
    produced, _ = lmerge.mergeLayoutItems([r1, r2])
    assert len(produced) == 1
    assert isinstance(produced[0], lshp.layoutPolygon)


def test_corner_touching_rects_consumed():
    # Corner contact counts as touching: both are consumed even though the
    # union result is two disjoint components.
    r1 = _rect((0, 0), (10, 10))
    r2 = _rect((10, 10), (20, 20))
    scene = _scene_with(r1, r2)
    produced, consumed = lmerge.mergeLayoutItems([r1, r2])
    assert set(consumed) == {r1, r2}
    total_area = sum(
        abs(_scene_area(item)) for item in produced
    )
    assert total_area == pytest.approx(200.0)


def test_rect_polygon_overlap_merges():
    r1 = _rect((0, 0), (10, 10))
    # Triangle sharing r1's right edge: union is a non-rectangular pentagon.
    poly = _polygon([(10, 0), (20, 5), (10, 10)])
    scene = _scene_with(r1, poly)
    produced, consumed = lmerge.mergeLayoutItems([r1, poly])
    assert len(produced) == 1
    assert isinstance(produced[0], lshp.layoutPolygon)
    assert set(consumed) == {r1, poly}


def test_disjoint_shapes_no_merge():
    r1 = _rect((0, 0), (10, 10))
    r2 = _rect((20, 0), (30, 10))
    scene = _scene_with(r1, r2)
    produced, consumed = lmerge.mergeLayoutItems([r1, r2])
    assert produced == []
    assert consumed == []


def test_shapes_different_layers_no_merge():
    r1 = _rect((0, 0), (10, 10), layer=odLayer_drw)
    r2 = _rect((10, 0), (20, 10), layer=poLayer_drw)
    scene = _scene_with(r1, r2)
    produced, consumed = lmerge.mergeLayoutItems([r1, r2])
    assert produced == []
    assert consumed == []


def test_transitive_shape_chain():
    r1 = _rect((0, 0), (10, 10))
    r2 = _rect((10, 0), (20, 10))
    r3 = _rect((20, 0), (30, 10))
    scene = _scene_with(r1, r2, r3)
    produced, consumed = lmerge.mergeLayoutItems([r1, r2, r3])
    assert len(produced) == 1
    assert isinstance(produced[0], lshp.layoutRect)
    assert len(consumed) == 3


def test_merged_polygon_points_are_qpoint():
    # layoutPolygon stretch logic does QPoint - point arithmetic; QPointF
    # vertices crash it, so merged polygons must carry integer QPoint.
    r1 = _rect((0, 0), (10, 10))
    r2 = _rect((10, 0), (20, 5))
    scene = _scene_with(r1, r2)
    produced, _ = lmerge.mergeLayoutItems([r1, r2])
    poly = produced[0]
    assert isinstance(poly, lshp.layoutPolygon)
    assert all(type(p) is QPoint for p in poly.points)
    eventPos = QPoint(8, 4)
    idx = min(
        range(len(poly.points)),
        key=lambda i: (eventPos - poly.points[i]).manhattanLength(),
    )
    assert poly.points[idx] == QPoint(10, 5)


def test_union_with_hole_is_keyhole_polygon():
    # Four bars forming a ring: union has a hole -> single keyhole polygon.
    bars = [
        _polygon([(0, 0), (10, 0), (10, 3), (0, 3)]),
        _polygon([(0, 7), (10, 7), (10, 10), (0, 10)]),
        _polygon([(0, 3), (3, 3), (3, 7), (0, 7)]),
        _polygon([(7, 3), (10, 3), (10, 7), (7, 7)]),
    ]
    scene = _scene_with(*bars)
    produced, consumed = lmerge.mergeLayoutItems(bars)
    assert len(produced) == 1
    assert isinstance(produced[0], lshp.layoutPolygon)
    assert len(consumed) == 4
    # Keyhole representation: the channel path connecting the hole to the
    # outer boundary makes the point count exceed a simple ring.
    assert len(produced[0].points) > 8


def test_mixed_selection_merges_only_valid_group():
    r1 = _rect((0, 0), (10, 10))
    r2 = _rect((10, 0), (20, 10))
    other = _rect((50, 50), (60, 60))
    scene = _scene_with(r1, r2, other)
    produced, consumed = lmerge.mergeLayoutItems([r1, r2, other])
    assert len(produced) == 1
    assert set(consumed) == {r1, r2}
    assert other not in consumed


def test_paths_and_shapes_merge_independently():
    p1 = _path((0, 0), (100, 0))
    p2 = _path((100, 0), (200, 0))
    r1 = _rect((0, 50), (10, 60))
    r2 = _rect((10, 50), (20, 60))
    scene = _scene_with(p1, p2, r1, r2)
    produced, consumed = lmerge.mergeLayoutItems([p1, p2, r1, r2])
    assert len(produced) == 2
    assert len(consumed) == 4
    kinds = {type(item) for item in produced}
    assert lshp.layoutPath in kinds


def test_single_candidate_no_merge():
    r1 = _rect((0, 0), (10, 10))
    scene = _scene_with(r1)
    produced, consumed = lmerge.mergeLayoutItems([r1])
    assert produced == []
    assert consumed == []


# ---------- undo/redo ----------


def test_undo_redo_cycle():
    r1 = _rect((0, 0), (10, 10))
    r2 = _rect((10, 0), (20, 10))
    scene = _scene_with(r1, r2)
    scene.itemsRefSet = set(scene.items())
    stack = QUndoStack()
    produced, consumed = lmerge.mergeLayoutItems([r1, r2])
    stack.push(us.addDeleteShapesUndo(scene, produced, consumed))

    assert r1.scene() is None and r2.scene() is None
    assert produced[0] in scene.items()

    stack.undo()
    assert r1 in scene.items() and r2 in scene.items()
    assert produced[0].scene() is None

    stack.redo()
    assert produced[0] in scene.items()
    assert r1.scene() is None


# ---------- helpers ----------


def _scene_area(item):
    if isinstance(item, lshp.layoutRect):
        rect = item.rect
        return rect.width() * rect.height()
    # Area via the shoelace formula on the scene polygon.
    poly = lmerge._scenePolygon(item)
    area = 0.0
    n = len(poly)
    for i in range(n):
        p1, p2 = poly[i], poly[(i + 1) % n]
        area += p1.x() * p2.y() - p2.x() * p1.y()
    return abs(area) / 2
