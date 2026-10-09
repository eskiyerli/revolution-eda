"""Startup lifecycle regressions: library browser logger ordering and
worker-signal emission during Qt shutdown."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from revedaEditor.backend.startThread import startThread
from revedaEditor.gui.libraryBrowser import libraryBrowser


def test_library_browser_logger_exists_before_plugin_menu_hook(qapp, tmp_path,
                                                               monkeypatch):
    monkeypatch.setattr(
        qapp, "pluginsObj",
        SimpleNamespace(
            applyPluginMenus=Mock(side_effect=RuntimeError("broken menu"))),
        raising=False)
    appMainW = SimpleNamespace(
        libraryDict={},
        logger=Mock(),
        libraryPathObj=tmp_path / "library.json",
        openViews={},
    )
    browser = libraryBrowser(appMainW)
    appMainW.logger.exception.assert_called_with("applyPluginMenus failed")
    browser.deleteLater()


@pytest.mark.parametrize("fn", [lambda: "ok",
                                Mock(side_effect=ValueError("boom"))])
def test_start_thread_survives_deleted_signal_source(fn):
    runner = startThread(fn)
    deletedSignal = Mock()
    deletedSignal.emit.side_effect = RuntimeError(
        "Signal source has been deleted")
    runner.signals = SimpleNamespace(result=deletedSignal, error=deletedSignal,
                                     finished=deletedSignal)
    runner.run()
