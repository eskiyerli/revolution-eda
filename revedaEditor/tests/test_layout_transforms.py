import math
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QLineF, QPoint, QPointF
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
    scene = SimpleNamespace(
        libraryDict={"library": str(tmp_path / "library")},
        rulerFont=QFont(), rulerTickLength=5, snapTuple=(10, 10),
        rulerWidth=1, rulerTickGap=10, logger=Mock(),
    )

    instance = layoutItems(scene).create({
        "type": "Inst", "lib": "library", "cell": "self", "view": "layout",
        "loc": [0, 0], "ic": 1, "nam": "I1",
    })

    assert instance is not None
    assert not instance.shapes
    scene.logger.error.assert_called_once()

