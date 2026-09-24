"""Plugin discovery and installation UX tests."""

from pathlib import Path

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow

from revedaEditor.gui.pluginsRegistry import PluginRegistryWindow
from revedaEditor.gui.revedaMain import MainWindow, pluginDiscoveryBanner


class _RestartParent(QMainWindow):
    def __init__(self):
        super().__init__()
        self.restartCount = 0

    def restartApplication(self):
        self.restartCount += 1


def _registry(monkeypatch, parent, tmp_path):
    monkeypatch.setattr(PluginRegistryWindow, "fetch_registry", lambda self: None)
    return PluginRegistryWindow(parent, plugins_dir=tmp_path)


def test_discovery_banner_actions(qtbot):
    banner = pluginDiscoveryBanner()
    qtbot.addWidget(banner)
    events = []
    banner.browseRequested.connect(lambda: events.append("browse"))
    banner.dismissed.connect(lambda: events.append("dismiss"))

    banner.browseButton.click()
    banner.dismissButton.click()

    assert events == ["browse", "dismiss"]


def test_update_action_count(qapp):
    holder = QMainWindow()
    holder.pluginUpdatesAction = QAction("Updates", holder)

    MainWindow._updatePluginUpdatesAction(holder, {})
    assert holder.pluginUpdatesAction.text() == "Updates"
    MainWindow._updatePluginUpdatesAction(holder, {"one": (), "two": ()})
    assert holder.pluginUpdatesAction.text() == "Updates (2)"


def test_install_success_can_restart(qtbot, monkeypatch, tmp_path):
    parent = _RestartParent()
    registry = _registry(monkeypatch, parent, tmp_path)
    qtbot.addWidget(parent)
    qtbot.addWidget(registry)
    monkeypatch.setattr(registry, "_askRestartAfterInstall", lambda name: True)

    registry._showInstallSuccess({"name": "Example Plugin"})

    assert parent.restartCount == 1


def test_install_completion_preserves_entry(qtbot, monkeypatch, tmp_path):
    parent = _RestartParent()
    registry = _registry(monkeypatch, parent, tmp_path)
    qtbot.addWidget(parent)
    qtbot.addWidget(registry)
    tracked = []
    completed = []
    monkeypatch.setattr(
        registry, "_track_download",
        lambda entry, url: tracked.append((entry, url)),
    )
    monkeypatch.setattr(
        registry, "_showInstallSuccess", completed.append
    )
    entry = {"name": "Example Plugin", "version": "1.0.0"}
    target = tmp_path / "example"
    url = "https://plugins.example/example.py"

    registry._on_download_complete(b"value = 1\n", url, target, entry)

    assert (target / "example.py").read_bytes() == b"value = 1\n"
    assert tracked == [(entry, url)]
    assert completed == [entry]
