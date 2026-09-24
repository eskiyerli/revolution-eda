import io
import logging
import zipfile
from pathlib import Path

import pytest

from revedaEditor.backend.fileUtils import atomicWriteText, safeExtractZip
from revedaEditor.backend import pdkLoader
from revedaEditor.backend.pdkLoader import pdkConfig
from revedaEditor.backend.projectManager import ProjectManager


def test_safe_extract_zip_rejects_parent_member(tmp_path: Path):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as zipFile:
        zipFile.writestr("../outside.txt", "unsafe")
    archive.seek(0)

    with zipfile.ZipFile(archive) as zipFile:
        with pytest.raises(ValueError, match="Unsafe archive member path"):
            safeExtractZip(zipFile, tmp_path / "install")

    assert not (tmp_path / "outside.txt").exists()


def test_safe_extract_zip_allows_members_inside_destination(tmp_path: Path):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as zipFile:
        zipFile.writestr("library/data.txt", "safe")
    archive.seek(0)

    destination = tmp_path / "install"
    with zipfile.ZipFile(archive) as zipFile:
        safeExtractZip(zipFile, destination)

    assert (destination / "library/data.txt").read_text() == "safe"


def test_atomic_write_preserves_original_on_failure(tmp_path: Path):
    target = tmp_path / "view.json"
    target.write_text("original")

    def fail(output):
        output.write("partial")
        raise RuntimeError("serialization failed")

    with pytest.raises(RuntimeError, match="serialization failed"):
        atomicWriteText(target, fail)

    assert target.read_text() == "original"
    assert list(tmp_path.glob(".view.json.*.tmp")) == []


def test_pdk_config_invalid_json_falls_back_without_secondary_error(tmp_path: Path):
    (tmp_path / "config.json").write_text("{ invalid")
    config = pdkConfig(tmp_path)
    assert config.pdkConfig == {}


def test_pdk_import_reports_transitive_dependency(monkeypatch, caplog):
    missing = ModuleNotFoundError("No module named 'dependency'", name="dependency")

    def fail_import(_name):
        raise missing

    monkeypatch.setattr(pdkLoader.importlib, "import_module", fail_import)
    monkeypatch.setattr(pdkLoader, "_get_pdk_path", lambda: Path("/tmp/test_pdk"))
    pdkLoader._module_cache.clear()

    with caplog.at_level(logging.ERROR):
        assert pdkLoader.importPDKModule("callbacks") is None

    assert "missing dependency dependency" in caplog.text


def test_library_includes_resolve_relative_to_containing_file(tmp_path: Path):
    included = tmp_path / "nested" / "library.json"
    included.parent.mkdir()
    included.write_text('{"libdefs": {"cells": "cells"}}')

    root = tmp_path / "library.json"
    root.write_text('{"include": ["nested/library.json"]}')

    result = ProjectManager(None)._read_lib_def_file(root)
    assert result == {"cells": included.parent / "cells"}