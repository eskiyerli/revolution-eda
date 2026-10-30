"""Phase 7 — platform hardening: autosave/crash recovery, cellview lock
files, configurable bindkeys, and session save/restore in reveda.conf."""

import json
import logging
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QRect, QRectF
from PySide6.QtGui import QAction, QStandardItemModel
from PySide6.QtWidgets import QApplication

import revedaEditor.backend.bindkeys as bkeys
import revedaEditor.backend.cellviewState as cvstate
import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.backend.libBackEnd as libb
from revedaEditor.gui.editorWindow import editorWindow
from revedaEditor.gui.revedaMain import MainWindow


@pytest.fixture(scope="module", autouse=True)
def init_qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


# ---------------------------------------------------------------------------
# cellviewState: path contracts + lock lifecycle
# ---------------------------------------------------------------------------

def test_cellview_sidecar_paths(tmp_path: Path):
    viewFile = tmp_path / "cell" / "schematic.json"
    assert cvstate.autosavePathFor(viewFile) == tmp_path / "cell" / "schematic.json.autosave"
    assert cvstate.lockPathFor(viewFile) == tmp_path / "cell" / "schematic.json.lock"


def test_lock_write_read_roundtrip(tmp_path: Path):
    lockPath = tmp_path / "layout.json.lock"
    record = cvstate.writeLockFile(lockPath)
    assert record["pid"] == os.getpid()
    assert "user" in record and "host" in record and "time" in record
    assert cvstate.readLockFile(lockPath) == record


def test_acquire_lock_held_then_contended(tmp_path: Path):
    lockPath = tmp_path / "schematic.json.lock"
    status, record = cvstate.acquireLock(lockPath)
    assert status == "held"
    assert record["pid"] == os.getpid()

    # A live foreign process holding the lock must contend.
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        foreign = {"pid": proc.pid, "user": "other", "host": socket.gethostname(),
                   "time": time.time()}
        lockPath.write_text(json.dumps(foreign))
        status, owner = cvstate.acquireLock(lockPath)
        assert status == "contended"
        assert owner["pid"] == proc.pid
    finally:
        proc.terminate()
        proc.wait()


def test_acquire_lock_takes_over_stale(tmp_path: Path):
    lockPath = tmp_path / "symbol.json.lock"
    # Guaranteed-dead pid: spawn a trivial process and reap it.
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    stale = {"pid": proc.pid, "user": "ghost", "host": socket.gethostname(),
             "time": time.time() - 1000}
    lockPath.write_text(json.dumps(stale))
    status, record = cvstate.acquireLock(lockPath)
    assert status == "held"
    assert record["pid"] == os.getpid()


def test_acquire_lock_malformed_is_stale(tmp_path: Path):
    lockPath = tmp_path / "schematic.json.lock"
    lockPath.write_text("{ not json !")
    status, _ = cvstate.acquireLock(lockPath)
    assert status == "held"
    assert cvstate.readLockFile(lockPath)["pid"] == os.getpid()


def test_acquire_lock_does_not_probe_or_replace_remote_owner(tmp_path: Path):
    lockPath = tmp_path / "layout.json.lock"
    foreign = {"pid": os.getpid(), "user": "other", "host": "remote-host",
               "time": time.time()}
    lockPath.write_text(json.dumps(foreign))
    status, owner = cvstate.acquireLock(lockPath)
    assert status == "contended"
    assert owner == foreign
    assert cvstate.readLockFile(lockPath) == foreign


def test_release_lock_only_ours(tmp_path: Path):
    lockPath = tmp_path / "layout.json.lock"
    foreign = {"pid": 424242, "user": "other", "host": "x", "time": 1.0}
    lockPath.write_text(json.dumps(foreign))
    cvstate.releaseLock(lockPath)
    assert lockPath.exists()  # not ours -> untouched

    foreign["pid"] = os.getpid()
    lockPath.write_text(json.dumps(foreign))
    cvstate.releaseLock(lockPath)
    assert lockPath.exists()

    cvstate.writeLockFile(lockPath)
    cvstate.releaseLock(lockPath)
    assert not lockPath.exists()


def test_inspect_lock_states(tmp_path: Path):
    viewFile = tmp_path / "cell" / "schematic.json"
    lockPath = cvstate.lockPathFor(viewFile)
    assert cvstate.inspectLock(viewFile) == ("none", None)

    cvstate.writeLockFile(lockPath)
    status, record = cvstate.inspectLock(viewFile)
    assert status == "mine" and record["pid"] == os.getpid()

    foreign = {"pid": os.getpid(), "user": "other", "host": "remote-host",
               "time": time.time()}
    lockPath.write_text(json.dumps(foreign))
    status, record = cvstate.inspectLock(viewFile)
    assert status == "locked" and record == foreign

    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    stale = {"pid": proc.pid, "user": "ghost", "host": socket.gethostname(),
             "time": time.time()}
    lockPath.write_text(json.dumps(stale))
    status, _ = cvstate.inspectLock(viewFile)
    assert status == "stale"

    lockPath.write_text("{ not json !")
    assert cvstate.inspectLock(viewFile) == ("stale", None)


def test_force_release_lock(tmp_path: Path):
    lockPath = tmp_path / "layout.json.lock"
    foreign = {"pid": 424242, "user": "other", "host": "x", "time": 1.0}
    lockPath.write_text(json.dumps(foreign))
    assert cvstate.forceReleaseLock(lockPath)
    assert not lockPath.exists()
    assert cvstate.forceReleaseLock(lockPath)  # idempotent


def test_process_alive_checks():
    assert cvstate.processAlive(os.getpid())
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    assert not cvstate.processAlive(proc.pid)
    assert not cvstate.processAlive(-1)
    assert not cvstate.processAlive(0)


def test_is_autosave_newer(tmp_path: Path):
    viewFile = tmp_path / "schematic.json"
    autosaveFile = cvstate.autosavePathFor(viewFile)
    assert not cvstate.isAutosaveNewer(viewFile, autosaveFile)

    viewFile.write_text("[]")
    autosaveFile.write_text("[]")
    # Force deterministic mtimes: autosave strictly newer.
    os.utime(viewFile, (1000, 1000))
    os.utime(autosaveFile, (2000, 2000))
    assert cvstate.isAutosaveNewer(viewFile, autosaveFile)

    os.utime(autosaveFile, (500, 500))
    assert not cvstate.isAutosaveNewer(viewFile, autosaveFile)

    # Autosave survives a missing primary file (crash before first save).
    viewFile.unlink()
    os.utime(autosaveFile, (500, 500))
    assert cvstate.isAutosaveNewer(viewFile, autosaveFile)


# ---------------------------------------------------------------------------
# editorWindow: autosave slots, lock contention, restore prompt (unbound)
# ---------------------------------------------------------------------------

def _editor_stub(tmp_path: Path) -> SimpleNamespace:
    """Duck-typed editorWindow for driving its Phase-7 methods unbound."""
    file = tmp_path / "cell" / "schematic.json"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text("[]")
    scene = SimpleNamespace(readOnly=False, undoStack=None)
    stub = SimpleNamespace(
        file=file,
        _lockPath=cvstate.lockPathFor(file),
        _autosavePath=cvstate.autosavePathFor(file),
        _lockHeld=True,
        _lastAutosaveIndex=-1,
        _isPcellPreview=False,
        centralW=SimpleNamespace(scene=scene),
        libName="lib", cellName="cell", viewName="schematic",
        messageLine=SimpleNamespace(setText=Mock()),
        logger=logging.getLogger("test_p7"),
    )
    return stub


def test_autosave_writes_when_dirty(tmp_path: Path):
    stub = _editor_stub(tmp_path)
    saveCalls = []
    undoStack = SimpleNamespace(index=lambda: 3, isClean=lambda: False)
    stub.centralW.scene.undoStack = undoStack
    stub._saveCellviewTo = lambda p: (saveCalls.append(p) or True)
    editorWindow.autosaveCellview(stub)
    assert saveCalls == [stub._autosavePath]
    assert stub._lastAutosaveIndex == 3


def test_autosave_skips_clean_and_unchanged(tmp_path: Path):
    stub = _editor_stub(tmp_path)
    stub._saveCellviewTo = Mock(return_value=True)
    # Clean stack -> nothing to snapshot.
    stub.centralW.scene.undoStack = SimpleNamespace(
        index=lambda: 0, isClean=lambda: True)
    editorWindow.autosaveCellview(stub)
    stub._saveCellviewTo.assert_not_called()
    # Dirty but same index as last autosave -> skip.
    stub.centralW.scene.undoStack = SimpleNamespace(
        index=lambda: 7, isClean=lambda: False)
    stub._lastAutosaveIndex = 7
    editorWindow.autosaveCellview(stub)
    stub._saveCellviewTo.assert_not_called()


def test_autosave_skips_readonly_and_preview(tmp_path: Path):
    stub = _editor_stub(tmp_path)
    stub._saveCellviewTo = Mock(return_value=True)
    stub.centralW.scene.undoStack = SimpleNamespace(
        index=lambda: 2, isClean=lambda: False)
    stub.centralW.scene.readOnly = True
    editorWindow.autosaveCellview(stub)
    stub._saveCellviewTo.assert_not_called()

    stub.centralW.scene.readOnly = False
    stub._lockHeld = False  # contended lock: never autosave someone else's file
    editorWindow.autosaveCellview(stub)
    stub._saveCellviewTo.assert_not_called()


def test_save_cellview_to_dispatches_scene_method(tmp_path: Path):
    stub = _editor_stub(tmp_path)
    stub.centralW.scene.saveSchematic = Mock(return_value=True)
    assert editorWindow._saveCellviewTo(stub, stub._autosavePath)
    stub.centralW.scene.saveSchematic.assert_called_once_with(
        stub._autosavePath, markClean=False)


def test_save_cellview_to_reports_false_save_result(tmp_path: Path):
    stub = _editor_stub(tmp_path)
    stub.centralW.scene.saveSchematic = Mock(return_value=False)
    assert not editorWindow._saveCellviewTo(stub, stub._autosavePath)


def test_resolve_load_path_prompts_and_restores(tmp_path: Path, monkeypatch):
    stub = _editor_stub(tmp_path)
    stub._autosavePath.write_text('[{"viewType": "schematic"}]')
    os.utime(stub.file, (1000, 1000))
    os.utime(stub._autosavePath, (2000, 2000))

    from revedaEditor.gui import editorWindow as edwModule
    monkeypatch.setattr(edwModule.QMessageBox, "question",
                        lambda *a, **k: edwModule.QMessageBox.Yes)
    assert editorWindow._resolveLoadPath(stub) == stub._autosavePath


def test_resolve_load_path_decline_removes_autosave(tmp_path: Path, monkeypatch):
    stub = _editor_stub(tmp_path)
    stub._autosavePath.write_text('[{"viewType": "schematic"}]')
    os.utime(stub.file, (1000, 1000))
    os.utime(stub._autosavePath, (2000, 2000))

    from revedaEditor.gui import editorWindow as edwModule
    monkeypatch.setattr(edwModule.QMessageBox, "question",
                        lambda *a, **k: edwModule.QMessageBox.No)
    assert editorWindow._resolveLoadPath(stub) == stub.file
    assert not stub._autosavePath.exists()


def test_resolve_load_path_no_prompt_without_lock(tmp_path: Path, monkeypatch):
    """A read-only (contended) editor never gets the restore prompt."""
    stub = _editor_stub(tmp_path)
    stub._lockHeld = False
    stub._autosavePath.write_text('[{"viewType": "schematic"}]')
    os.utime(stub._autosavePath, (9999, 9999))
    from revedaEditor.gui import editorWindow as edwModule
    questionMock = Mock(return_value=edwModule.QMessageBox.Yes)
    monkeypatch.setattr(edwModule.QMessageBox, "question", questionMock)
    assert editorWindow._resolveLoadPath(stub) == stub.file
    questionMock.assert_not_called()


def test_lock_contention_forces_readonly(tmp_path: Path):
    stub = _editor_stub(tmp_path)
    stub.readOnlyCellAction = Mock()
    stub.saveCellAction = Mock()
    stub.checkCellAction = Mock()
    stub.deleteAction = QAction("Delete")
    stub.undoAction = QAction("Undo")
    stub.fitAction = QAction("Fit")
    foreign = {"pid": 4242, "user": "alice", "host": "ws1", "time": 1.0}
    editorWindow._applyLockContention(stub, foreign)
    assert stub.centralW.scene.readOnly is True
    stub.readOnlyCellAction.setChecked.assert_called_once_with(True)
    stub.readOnlyCellAction.setEnabled.assert_called_once_with(False)
    stub.saveCellAction.setEnabled.assert_called_once_with(False)
    stub.checkCellAction.setEnabled.assert_called_once_with(False)
    assert not stub.deleteAction.isEnabled()
    assert not stub.undoAction.isEnabled()
    assert stub.fitAction.isEnabled()


def test_clear_autosave(tmp_path: Path):
    stub = _editor_stub(tmp_path)
    stub._autosavePath.write_text('[{"viewType": "schematic"}]')
    stub._lastAutosaveIndex = 5
    editorWindow._clearAutosave(stub)
    assert not stub._autosavePath.exists()
    assert stub._lastAutosaveIndex == -1
    editorWindow._clearAutosave(stub)  # idempotent


def test_devdocs_sources_exclude_private_ignored_modules():
    from scripts import generate_devdocs

    sources = {
        path.relative_to(generate_devdocs.REPO).as_posix()
        for path in generate_devdocs.collectSources()
    }
    assert not any(path.startswith("revedaLicense/") for path in sources)
    assert "scripts/generate_license.py" not in sources
    assert "scripts/obfuscate_key.py" not in sources


# ---------------------------------------------------------------------------
# bindkeys
# ---------------------------------------------------------------------------

def test_bindkey_defaults_shipped_loadable():
    keyMap = bkeys.loadBindkeyMap()
    assert "undoAction" in keyMap["*"].values()
    # Same key, different action per view type.
    assert keyMap["schematic"]["W"] == "createNetAction"
    assert keyMap["layout"]["W"] == "createPathAction"
    assert keyMap["symbol"]["W"] == "createLineAction"


def test_bindkey_user_override_merges(tmp_path: Path):
    defaults = tmp_path / "defaults.json"
    defaults.write_text(json.dumps({
        "*": {"U": "undoAction", "F": "fitAction"},
        "layout": {"K": "rulerAction"},
    }))
    user = tmp_path / "bindkeys.json"
    user.write_text(json.dumps({
        "*": {"F": "findAction"},  # overrides default fit
        "layout": {"K": "createViaAction"},
        "symbol": {"L": "createLabelAction"},
    }))
    keyMap = bkeys.loadBindkeyMap(defaultsPath=defaults, userPath=user)
    assert keyMap["*"]["U"] == "undoAction"
    assert keyMap["*"]["F"] == "findAction"
    assert keyMap["layout"]["K"] == "createViaAction"
    assert keyMap["symbol"]["L"] == "createLabelAction"


def test_bindkey_malformed_files_skipped(tmp_path: Path, caplog):
    bad = tmp_path / "bad.json"
    bad.write_text("{ not json")
    good = tmp_path / "good.json"
    good.write_text(json.dumps({"*": {"U": "undoAction"},
                                "bogus": "not-a-dict",
                                "empty": {42: "x"}}))
    keyMap = bkeys.loadBindkeyMap(defaultsPath=bad, userPath=good)
    assert keyMap["*"]["U"] == "undoAction"
    assert "bogus" not in keyMap


def test_apply_bindkeys_sets_shortcuts(qapp):
    undo = QAction("undo")
    fit = QAction("fit")
    window = SimpleNamespace(undoAction=undo, fitAction=fit)
    keyMap = {"*": {"U": "undoAction"},
              "schematic": {"F": "fitAction", "Z": "noSuchAction",
                            "": "fitAction"}}
    applied = bkeys.applyBindkeys(window, keyMap, "schematic")
    assert applied == 2  # U on undo + F on fit; unknown/empty skipped
    assert undo.shortcut().toString() == "U"
    assert fit.shortcut().toString() == "F"


def test_apply_bindkeys_viewtype_scoping(qapp):
    createNet = QAction("net")
    window = SimpleNamespace(createNetAction=createNet)
    keyMap = {"schematic": {"W": "createNetAction"},
              "layout": {"W": "otherAction"}}
    applied = bkeys.applyBindkeys(window, keyMap, "schematic")
    assert applied == 1
    assert createNet.shortcut().toString() == "W"


# ---------------------------------------------------------------------------
# session save/restore
# ---------------------------------------------------------------------------

def _library_model(tmp_path: Path):
    """Real QStandardItemModel with lib/cell/view items for restore tests."""
    libPath = tmp_path / "lib1"
    cellDir = libPath / "cell1"
    cellDir.mkdir(parents=True)
    viewFile = cellDir / "schematic.json"
    viewFile.write_text("[]")
    model = QStandardItemModel()
    libItem = libb.libraryItem(libPath)
    cellItem = libb.cellItem(cellDir)
    viewItem = libb.viewItem(viewFile)
    cellItem.appendRow(viewItem)
    libItem.appendRow(cellItem)
    model.appendRow(libItem)
    return model, libItem, cellItem, viewItem


def _fake_mainwindow(model, openViews=None):
    opened = []
    designView = SimpleNamespace(
        openCellView=lambda vT: opened.append(vT))
    return (SimpleNamespace(
        libraryModel=model,
        libraryBrowser=SimpleNamespace(designView=designView),
        openViews={} if openViews is None else openViews,
        logger=logging.getLogger("test_p7")), opened)


def test_session_snapshot_entries():
    view = SimpleNamespace(
        viewRect=QRectF(10, 20, 300, 200),
        mapToScene=lambda r: QRectF(0, 0, 1, 1),
        rect=lambda: QRect(0, 0, 800, 600))
    window = SimpleNamespace(
        centralW=SimpleNamespace(view=view),
        geometry=lambda: QRect(5, 6, 1600, 800))
    viewNameT = ddef.viewNameTuple("lib1", "cell1", "schematic")
    # A window without centralW.view (e.g. a text editor) must be skipped.
    openViews = {viewNameT: window,
                 ddef.viewNameTuple("lib1", "cell1", "spice"): object()}
    entries = MainWindow._sessionSnapshot(
        SimpleNamespace(openViews=openViews))
    assert entries == [{
        "library": "lib1", "cell": "cell1", "view": "schematic",
        "geometry": [5, 6, 1600, 800],
        "viewRect": [10.0, 20.0, 300.0, 200.0]}]


def test_session_restore_opens_views(tmp_path: Path):
    model, _libItem, _cellItem, viewItem = _library_model(tmp_path)
    mainW, opened = _fake_mainwindow(model)

    editor = SimpleNamespace(
        setGeometry=Mock(),
        centralW=SimpleNamespace(view=SimpleNamespace(
            fitInView=Mock(), determineViewRect=Mock())))

    def fakeOpen(viewItemT):
        opened.append(viewItemT)
        mainW.openViews[viewItemT.convertToViewNameTuple()] = editor

    mainW.libraryBrowser.designView.openCellView = fakeOpen
    entries = [{
        "library": "lib1", "cell": "cell1", "view": "schematic",
        "geometry": [1, 2, 800, 600],
        "viewRect": [0, 0, 100, 50]}]
    MainWindow._restoreSessionViews(mainW, entries)

    assert len(opened) == 1
    assert opened[0].viewItem is viewItem
    editor.setGeometry.assert_called_once_with(1, 2, 800, 600)
    editor.centralW.view.fitInView.assert_called_once()
    editor.centralW.view.determineViewRect.assert_called_once()


def test_session_restore_skips_missing(tmp_path: Path):
    model, _libItem, _cellItem, _viewItem = _library_model(tmp_path)
    mainW, opened = _fake_mainwindow(model)
    entries = [
        {"library": "goneLib", "cell": "cell1", "view": "schematic"},
        {"library": "lib1", "cell": "goneCell", "view": "schematic"},
        {"library": "lib1", "cell": "cell1", "view": "goneView"},
    ]
    MainWindow._restoreSessionViews(mainW, entries)
    assert opened == []
    assert mainW.openViews == {}


def test_session_restore_no_duplicates(tmp_path: Path):
    model, _libItem, _cellItem, _viewItem = _library_model(tmp_path)
    viewNameT = ddef.viewNameTuple("lib1", "cell1", "schematic")
    mainW, opened = _fake_mainwindow(
        model, openViews={viewNameT: object()})
    entries = [{"library": "lib1", "cell": "cell1", "view": "schematic"}]
    MainWindow._restoreSessionViews(mainW, entries)
    assert opened == []  # already open -> not reopened


def test_project_manager_persists_session(tmp_path: Path):
    """reveda.conf round-trip: snapshot entries land in saved config."""
    from revedaEditor.backend.projectManager import ProjectManager

    snapshotEntry = {
        "library": "lib1", "cell": "cell1", "view": "schematic",
        "geometry": [0, 0, 100, 100], "viewRect": [0, 0, 10, 10]}
    mainW = SimpleNamespace(
        runPath=tmp_path, pdkPath=tmp_path, outputPrefixPath=tmp_path,
        switchViewList=["schematic"], stopViewList=["layout"],
        x=lambda: 0, y=lambda: 0, width=lambda: 100, height=lambda: 100,
        threadPool=SimpleNamespace(maxThreadCount=lambda: 4),
        _sessionSnapshot=lambda: [snapshotEntry],
        autosaveEnabled=True, autosaveIntervalSec=120)
    pm = ProjectManager.__new__(ProjectManager)
    pm._main_window = mainW
    pm._active_project = tmp_path
    pm._logger = logging.getLogger("test_p7")
    assert pm.save_current_state()
    conf = json.loads((tmp_path / "reveda.conf").read_text())
    assert conf["openCellviews"] == [snapshotEntry]
    assert conf["autosaveIntervalSec"] == 120
