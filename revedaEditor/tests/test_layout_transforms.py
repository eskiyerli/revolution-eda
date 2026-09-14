import math
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QLineF, QPoint, QPointF, QRectF
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QGraphicsScene

from defaultPDK.layoutLayers import odLayer_drw
from defaultPDK.pcells import nmos
from defaultPDK.process import v1
from revedaEditor.common import layoutShapes as lshp
from revedaEditor.fileio.exportGDS import gdsExporter
from revedaEditor.fileio.layoutEncoder import layoutEncoder
from revedaEditor.fileio.loadJSON import layoutItems
from revedaEditor.scenes.layoutScene import layoutScene


@pytest.fixture(scope="module", autouse=True)
def init_qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def loader():
    scene = SimpleNamespace(
        libraryDict={},
        rulerFont=None,
        rulerTickLength=5,
        snapTuple=(10, 10),
        rulerWidth=1,
        rulerTickGap=10,
    )
    return layoutItems(scene)


def test_rect_round_trip_preserves_rotation_and_flip(loader):
    rect = lshp.layoutRect(QPointF(10, 20), QPointF(50, 40), odLayer_drw)
    rect.setTransformOriginPoint(QPointF(30, 30))
    rect.flipTuple = (-1, 1)
    rect.angle = 90

    saved = layoutEncoder().default(rect)
    restored = loader.createRectShape(saved)

    assert restored.angle == 90
    assert restored.flipTuple == (-1, 1)
    assert restored.mapToScene(restored.rect.topLeft()) == rect.mapToScene(rect.rect.topLeft())


def test_loader_accepts_legacy_layout_record_without_transform_fields(loader):
    restored = loader.createRectShape({
        "type": "Rect", "tl": [10, 20], "br": [50, 40], "ln": 0,
    })

    assert restored.angle == 0
    assert restored.flipTuple == (1, 1)


@pytest.mark.parametrize(
    ("flip_tuple", "expected_degrees", "expected_reflection"),
    [
        ((1, 1), 30, False),
        ((-1, -1), 210, False),
        ((1, -1), 30, True),
        ((-1, 1), 210, True),
    ],
)
def test_gdstk_transform_matches_editor_flip_matrix(
        flip_tuple, expected_degrees, expected_reflection):
    angle, reflection = gdsExporter._gdstk_transform(30, flip_tuple)

    assert math.degrees(angle) == pytest.approx(expected_degrees)
    assert reflection is expected_reflection


def test_gds_export_skips_layout_rulers():
    ruler = lshp.layoutRuler(QLineF(0, 0, 100, 0), 1, 10, 5, QFont())
    library = gdsExporter("ruler_test", [ruler], Path("/tmp/ruler_test.gds"))._buildLibrary()

    cell = library["ruler_test"]
    assert not cell.polygons
    assert not cell.paths
    assert not cell.references


def test_delete_all_rulers_cancels_in_progress_ruler():
    inProgress = lshp.layoutRuler(QLineF(0, 0, 0, 0), 1, 10, 5, QFont())
    completed = lshp.layoutRuler(QLineF(0, 0, 100, 0), 1, 10, 5, QFont())

    class RulerScene:
        def __init__(self):
            self._newRuler = inProgress
            self.deletedItems = []

        @staticmethod
        def items():
            return [inProgress, completed]

        def deleteListUndoStack(self, items):
            self.deletedItems = items

    scene = RulerScene()
    layoutScene.deleteAllRulers(scene)

    assert scene._newRuler is None
    assert set(scene.deletedItems) == {inProgress, completed}


def test_gds_export_reuses_identical_pcell_geometry():
    first = nmos()
    second = nmos()
    first(4.0, 0.13, 1)
    second(4.0, 0.13, 1)
    first.libraryName = second.libraryName = "defaultPDK"
    second.setPos(1000, 0)

    library = gdsExporter("pcell_test", [first, second], Path("/tmp/pcell_test.gds"))._buildLibrary()

    assert len(library.cells) == 2
    assert len(library["pcell_test"].references) == 2


def test_gds_export_keeps_via_enclosures_local_to_instance_cell():
    via = lshp.layoutVia(QPoint(0, 0), v1, 200, 200)
    via_array = lshp.layoutViaArray(QPoint(0, 0), via, 100, 100, 2, 1)
    instance = lshp.layoutInstance([via_array])
    instance.libraryName = "test"
    instance.cellName = "via"
    instance.viewName = "layout"
    instance.setPos(4000, 5000)

    library = gdsExporter("via_parent", [instance], Path("/tmp/via_parent.gds"))._buildLibrary()

    enclosure_points = [
        point for polygon in library["test_via_layout"].polygons for point in polygon.points
    ]
    assert max(abs(coordinate) for point in enclosure_points for coordinate in point) < 1000


def test_layout_load_restores_scene_index_after_bulk_insert():
    scene = QGraphicsScene()
    scene.libraryDict = {}
    scene.rulerFont = QFont()
    scene.rulerTickLength = 5
    scene.snapTuple = (10, 10)
    scene.rulerWidth = 1
    scene.rulerTickGap = 10
    scene.setItemIndexMethod(QGraphicsScene.ItemIndexMethod.BspTreeIndex)

    layoutScene.createLayoutItems(scene, [
        {"type": "Rect", "tl": [0, 0], "br": [100, 50], "ln": 0},
    ])

    assert scene.itemIndexMethod() == QGraphicsScene.ItemIndexMethod.BspTreeIndex
    assert len(scene.items()) == 1


def test_layout_loader_skips_unknown_records(loader):
    assert loader.create({"type": "FutureShape"}) is None


def test_layout_loader_stops_recursive_instance_reference(tmp_path):
    cell_dir = tmp_path / "library" / "self"
    cell_dir.mkdir(parents=True)
    (cell_dir / "layout.json").write_text(
        '[{"viewType":"layout"},{"snapGrid":[10,10]},'
        '{"type":"Inst","lib":"library","cell":"self","view":"layout",'
        '"loc":[0,0],"ic":1,"nam":"I1"}]'
    )
    scene = _makeLayoutScene({"library": str(tmp_path / "library")})

    instance = layoutItems(scene).create({
        "type": "Inst", "lib": "library", "cell": "self", "view": "layout",
        "loc": [0, 0], "ic": 1, "nam": "I1",
    })
    scene.addItem(instance)

    assert instance is not None
    # Realising the deferred children hits the recursion guard.
    assert not instance.shapes
    scene.logger.error.assert_called_once()


def _writeLayoutCell(tmp_path, lib, cell, records):
    cellDir = tmp_path / lib / cell
    cellDir.mkdir(parents=True)
    (cellDir / "layout.json").write_text(
        '[{"viewType":"layout"},{"snapGrid":[10,10]},' + ",".join(records) + "]"
    )
    return tmp_path / lib


def _makeLayoutScene(libraryDict):
    scene = QGraphicsScene()
    scene.libraryDict = libraryDict
    scene.rulerFont = QFont()
    scene.rulerTickLength = 5
    scene.snapTuple = (10, 10)
    scene.rulerWidth = 1
    scene.rulerTickGap = 10
    scene.logger = Mock()
    scene.itemsRefSet = set()
    return scene


def test_instance_with_bbox_defers_child_construction(tmp_path):
    libPath = _writeLayoutCell(tmp_path, "library", "child", [
        '{"type":"Rect","tl":[0,0],"br":[10,20],"ln":0}',
    ])
    scene = SimpleNamespace(
        libraryDict={"library": str(libPath)},
        rulerFont=QFont(), rulerTickLength=5, snapTuple=(10, 10),
        rulerWidth=1, rulerTickGap=10, logger=Mock(),
    )

    instance = layoutItems(scene).create({
        "type": "Inst", "lib": "library", "cell": "child", "view": "layout",
        "loc": [100, 200], "ic": 1, "nam": "I1", "bbox": [0, 0, 10, 20],
    })

    assert isinstance(instance, lshp.layoutInstance)
    assert not instance.childItems()
    assert instance.boundingRect() == QRectF(0, 0, 10, 20).adjusted(-2, -2, 2, 2)
    # Not in a QGraphicsScene yet: shapes cannot be realised, stays deferred.
    assert instance.shapes == []
    assert instance._deferredLoader is not None


def test_deferred_instance_realises_children_on_shapes_access(tmp_path):
    libPath = _writeLayoutCell(tmp_path, "library", "child", [
        '{"type":"Rect","tl":[0,0],"br":[10,20],"ln":0}',
    ])
    scene = _makeLayoutScene({"library": str(libPath)})

    instance = layoutItems(scene).create({
        "type": "Inst", "lib": "library", "cell": "child", "view": "layout",
        "loc": [100, 200], "ic": 1, "nam": "I1", "bbox": [0, 0, 10, 20],
    })
    scene.addItem(instance)
    assert not instance.childItems()

    shapes = instance.shapes

    assert len(shapes) == 1
    assert isinstance(shapes[0], lshp.layoutRect)
    assert shapes[0].parentItem() is instance
    assert instance._deferredLoader is None
    assert shapes[0] in scene.itemsRefSet


def test_instance_without_bbox_computes_bounds_from_dicts(tmp_path):
    libPath = _writeLayoutCell(tmp_path, "library", "child", [
        '{"type":"Rect","tl":[0,0],"br":[10,20],"ln":0}',
    ])
    scene = SimpleNamespace(
        libraryDict={"library": str(libPath)},
        rulerFont=QFont(), rulerTickLength=5, snapTuple=(10, 10),
        rulerWidth=1, rulerTickGap=10, logger=Mock(),
    )

    instance = layoutItems(scene).create({
        "type": "Inst", "lib": "library", "cell": "child", "view": "layout",
        "loc": [0, 0], "ic": 1, "nam": "I1",
    })

    # Legacy record: still deferred, with bounds estimated from the dicts.
    assert not instance.childItems()
    assert instance._deferredLoader is not None
    # Stored bounds must cover the realised childrenBoundingRect
    # (0,0)-(10,20) plus each child's own margin.
    bounds = instance.boundingRect()
    assert bounds.contains(QRectF(-4, -4, 18, 28))


def test_instance_with_unboundable_record_loads_eagerly(tmp_path):
    libPath = _writeLayoutCell(tmp_path, "library", "child", [
        '{"type":"Rect","tl":[0,0],"br":[10,20],"ln":0}',
        '{"type":"Pcell","lib":"library","cell":"dev","view":"pcell",'
        '"loc":[0,0],"ic":1,"nam":"P1"}',
    ])
    scene = SimpleNamespace(
        libraryDict={"library": str(libPath)},
        rulerFont=QFont(), rulerTickLength=5, snapTuple=(10, 10),
        rulerWidth=1, rulerTickGap=10, logger=Mock(),
    )

    instance = layoutItems(scene).create({
        "type": "Inst", "lib": "library", "cell": "child", "view": "layout",
        "loc": [0, 0], "ic": 1, "nam": "I1",
    })

    # A Pcell record without a saved bbox cannot be bounded cheaply, so the
    # whole cell falls back to eager construction.
    assert instance._deferredLoader is None
    assert len(instance.childItems()) == 1


def test_nested_deferred_instance_stays_deferred(tmp_path):
    _writeLayoutCell(tmp_path, "library", "grandchild", [
        '{"type":"Rect","tl":[0,0],"br":[5,5],"ln":0}',
    ])
    libPath = _writeLayoutCell(tmp_path, "library", "child", [
        ('{"type":"Inst","lib":"library","cell":"grandchild","view":"layout",'
         '"loc":[0,0],"ic":1,"nam":"I0","bbox":[0,0,5,5]}'),
    ])
    scene = _makeLayoutScene({"library": str(libPath)})

    instance = layoutItems(scene).create({
        "type": "Inst", "lib": "library", "cell": "child", "view": "layout",
        "loc": [0, 0], "ic": 1, "nam": "I1", "bbox": [0, 0, 5, 5],
    })
    scene.addItem(instance)

    nested = instance.shapes[0]

    assert isinstance(nested, lshp.layoutInstance)
    assert not nested.childItems()
    assert nested._deferredLoader is not None
    assert len(nested.shapes) == 1


def test_deferred_recursive_instance_does_not_recurse(tmp_path):
    libPath = _writeLayoutCell(tmp_path, "library", "self", [
        ('{"type":"Inst","lib":"library","cell":"self","view":"layout",'
         '"loc":[0,0],"ic":1,"nam":"I0","bbox":[0,0,10,10]}'),
        '{"type":"Rect","tl":[0,0],"br":[10,10],"ln":0}',
    ])
    scene = _makeLayoutScene({"library": str(libPath)})

    instance = layoutItems(scene).create({
        "type": "Inst", "lib": "library", "cell": "self", "view": "layout",
        "loc": [0, 0], "ic": 1, "nam": "I1", "bbox": [0, 0, 10, 10],
    })
    scene.addItem(instance)

    shapes = instance.shapes

    assert len(shapes) == 1
    assert isinstance(shapes[0], lshp.layoutRect)
    scene.logger.error.assert_called_once()


def test_deferred_pcell_realises_on_shapes_access():
    instance = nmos()
    instance.deferParams({"width": 4.0, "length": 0.13, "nf": 1},
                       QRectF(0, 0, 10, 10))
    scene = _makeLayoutScene({})
    scene.addItem(instance)
    assert not instance.childItems()

    assert instance.shapes
    assert instance._deferredLoader is None


def test_encoder_writes_instance_bbox():
    rect = lshp.layoutRect(QPointF(10, 20), QPointF(50, 40), odLayer_drw)
    instance = lshp.layoutInstance([rect])
    instance.libraryName = "library"
    instance.cellName = "child"
    instance.viewName = "layout"
    instance.instanceName = "I1"
    instance.counter = 1

    bounds = instance.childrenBoundingRect()
    saved = layoutEncoder().default(instance)

    assert saved["bbox"] == pytest.approx(
        (bounds.x(), bounds.y(), bounds.width(), bounds.height())
    )


def test_encoder_writes_deferred_instance_bbox_without_realising(tmp_path):
    libPath = _writeLayoutCell(tmp_path, "library", "child", [
        '{"type":"Rect","tl":[0,0],"br":[10,20],"ln":0}',
    ])
    scene = SimpleNamespace(
        libraryDict={"library": str(libPath)},
        rulerFont=QFont(), rulerTickLength=5, snapTuple=(10, 10),
        rulerWidth=1, rulerTickGap=10, logger=Mock(),
    )
    instance = layoutItems(scene).create({
        "type": "Inst", "lib": "library", "cell": "child", "view": "layout",
        "loc": [0, 0], "ic": 1, "nam": "I1", "bbox": [0, 0, 10, 20],
    })

    saved = layoutEncoder().default(instance)

    assert saved["bbox"] == pytest.approx((0, 0, 10, 20))
    assert instance._deferredLoader is not None

