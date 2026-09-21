"""Helpers for building an offscreen schematicScene in tests without
pytest-qt: a QObject container with a stubbed editor window."""

import logging
import pathlib
import types

from PySide6.QtCore import QObject, QPoint
from PySide6.QtGui import QFont

from revedaEditor.scenes.schematicScene import schematicScene


class _Container(QObject):
    pass


def makeSchematicScene() -> schematicScene:
    logger = logging.getLogger("test_scene")
    appMainW = types.SimpleNamespace(
        logger=logger,
        symbolChanged=types.SimpleNamespace(connect=lambda *a: None))
    editorWindow = types.SimpleNamespace(
        majorGrid=50, snapGrid=10, snapTuple=(10, 10),
        snapConnectDistance=10,
        file=pathlib.Path("/tmp/testcell/schematic.json"),
        libraryDict={}, appMainW=appMainW,
        messageLine=types.SimpleNamespace(setText=lambda *a: None),
        statusLine=types.SimpleNamespace(showMessage=lambda *a: None))
    container = _Container()
    container.editorWindow = editorWindow
    schematicScene._initializeFont = (
        lambda self: setattr(self, "fixedFont", QFont()))
    scene = schematicScene(container)
    scene.mouseMoveLoc = QPoint(0, 0)
    return scene


def makeLayoutScene():
    """Build an offscreen layoutScene with a stubbed editor window."""
    import revedaEditor.backend.dataDefinitions as ddef
    from defaultPDK import layoutLayers as laylyr
    from defaultPDK import process as fabproc
    from revedaEditor.scenes.layoutScene import layoutScene

    # defaultPDK does not define processPaths; layoutScene.__init__ needs one.
    if not hasattr(fabproc, "processPaths"):
        fabproc.processPaths = [ddef.layoutPathDefTuple(
            "m1", laylyr.m1Layer_drw, "", 0.2, 10.0, 0.0, 0.0, 0.1, 10.0)]

    logger = logging.getLogger("test_scene")
    appMainW = types.SimpleNamespace(
        logger=logger,
        symbolChanged=types.SimpleNamespace(connect=lambda *a: None))
    editorWindow = types.SimpleNamespace(
        majorGrid=50, snapGrid=10, snapTuple=(10, 10),
        snapConnectDistance=10,
        file=pathlib.Path("/tmp/testcell/layout.json"),
        libraryDict={}, appMainW=appMainW,
        messageLine=types.SimpleNamespace(setText=lambda *a: None),
        statusLine=types.SimpleNamespace(showMessage=lambda *a: None))
    container = _Container()
    container.editorWindow = editorWindow
    scene = layoutScene(container)
    scene.mouseMoveLoc = QPoint(0, 0)
    return scene
