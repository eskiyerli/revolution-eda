"""Application update-check tests (``backend/updateCheck.py``).

The fetch helper is exercised through a monkeypatched ``urlopen``; the
QObject checker is tested the same way ``pluginsLoader`` update checks are
— a fake thread pool records workers, and the settings file is redirected
to ``tmp_path``.
"""

import io
import json

import pytest
from PySide6.QtCore import QSettings

from revedaEditor.backend import updateCheck


class _FakePool:
    """QThreadPool stand-in that records started workers."""

    def __init__(self):
        self.started = []

    def start(self, worker):
        self.started.append(worker)


class _FakeResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def checker(qapp, tmp_path, monkeypatch):
    monkeypatch.delenv("REVEDA_DISABLE_UPDATE_CHECK", raising=False)
    monkeypatch.delenv("REVEDA_UPDATE_URL", raising=False)
    c = updateCheck.appUpdateChecker(
        releasesUrl="https://example.test/releases.json")
    c._settingsFile = tmp_path / "settings.ini"
    c._threadPool = _FakePool()
    c._appVersion = "1.0.0"
    return c


def _patch_urlopen(monkeypatch, payload):
    """Route fetchLatestRelease's urlopen at a canned response."""
    monkeypatch.setattr(
        updateCheck.urllib.request, "urlopen",
        lambda req, timeout=5: _FakeResponse(payload),
    )


def test_checker_rejects_nonstring_url(qapp):
    with pytest.raises(TypeError):
        updateCheck.appUpdateChecker(object())


def test_checker_parent_kwarg_uses_default_url(qapp):
    c = updateCheck.appUpdateChecker(parent=qapp)
    assert c.releasesUrl == updateCheck.DEFAULT_RELEASES_URL


def test_fetch_latest_release_github_shape(monkeypatch):
    _patch_urlopen(monkeypatch, json.dumps({
        "tag_name": "v1.2.0",
        "html_url": "https://github.com/x/y/releases/tag/v1.2.0",
        "name": "1.2.0",
    }).encode())
    release = updateCheck.fetchLatestRelease("https://example.test/r")
    assert release["version"] == "v1.2.0"
    assert release["url"].endswith("/releases/tag/v1.2.0")
    assert release["notes"] == "1.2.0"


def test_fetch_latest_release_custom_manifest(monkeypatch):
    _patch_urlopen(monkeypatch, json.dumps({
        "version": "1.3.0", "url": "https://example.test/dl",
    }).encode())
    release = updateCheck.fetchLatestRelease("https://example.test/r")
    assert release["version"] == "1.3.0"
    assert release["url"] == "https://example.test/dl"


def test_fetch_latest_release_garbage(monkeypatch):
    _patch_urlopen(monkeypatch, b"[1, 2, 3]")
    assert updateCheck.fetchLatestRelease("https://example.test/r") == {}


def test_check_throttle(checker, monkeypatch):
    assert checker.checkForUpdates() is True
    assert checker.checkForUpdates() is False        # same-day throttle
    assert checker.checkForUpdates(force=True) is True
    monkeypatch.setenv("REVEDA_DISABLE_UPDATE_CHECK", "1")
    assert checker.checkForUpdates(force=True) is False
    assert len(checker._threadPool.started) == 2


def test_release_newer_emits_update_found(checker):
    found, finished = [], []
    checker.updateFound.connect(found.append)
    checker.checkFinished.connect(finished.append)
    checker._onReleaseFetched({"version": "v1.1.0",
                               "url": "https://example.test/r/1.1.0",
                               "notes": ""})
    assert found and found[0]["version"] == "v1.1.0"
    assert finished == [found[0]]
    cached = json.loads(
        QSettings(str(checker._settingsFile), QSettings.IniFormat)
        .value("appUpdateCheck/latest"))
    assert cached["version"] == "v1.1.0"


@pytest.mark.parametrize("version", ["1.0.0", "v0.9.0", ""])
def test_release_not_newer_emits_no_update(checker, version):
    found, finished = [], []
    checker.updateFound.connect(found.append)
    checker.checkFinished.connect(finished.append)
    checker._onReleaseFetched({"version": version, "url": "", "notes": ""})
    assert found == []
    assert len(finished) == 1


def test_fetch_error_signals(checker):
    failed, finished = [], []
    checker.checkFailed.connect(failed.append)
    checker.checkFinished.connect(finished.append)
    checker._onFetchError((OSError, ("boom",), "boom"))
    assert failed == ["boom"]
    assert finished == [{}]
