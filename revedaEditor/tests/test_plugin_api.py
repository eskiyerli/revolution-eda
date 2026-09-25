"""Plugin contract tests: version/capability negotiation and update checks.

The pure helpers in ``backend/pluginApi.py`` need no Qt. Loader tests use
the session ``qapp`` fixture plus a monkeypatched ``logger`` attribute —
``pluginsLoader`` logs through ``QApplication.instance().logger``.
"""

import json
import logging
from pathlib import Path

import pytest
from PySide6.QtWidgets import QMainWindow

from revedaEditor.backend import licenseManager, pluginApi
from revedaEditor.backend.pluginsLoader import pluginsLoader

APP_VERSION = "0.9.0"


def _make_plugin(root: Path, name: str, config: dict | None) -> Path:
    """Write a minimal importable plugin package under ``root``."""
    plugin_dir = root / name
    plugin_dir.mkdir()
    (plugin_dir / "__init__.py").write_text("")
    if config is not None:
        (plugin_dir / "config.json").write_text(json.dumps(config))
    return plugin_dir


@pytest.fixture
def app_logger(qapp, monkeypatch):
    """Give the session QApplication the ``logger`` pluginsLoader expects."""
    monkeypatch.setattr(
        qapp, "logger", logging.getLogger("reveda"), raising=False
    )
    return qapp


# ----------------------------------------------------------------------
# parseVersion / versionNewer
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("0.9.0", (0, 9, 0)),
        ("1", (1,)),
        ("v2.1", (2, 1)),
        ("0.9.0b1", (0, 9, 0)),
        ("1.2.3+build", (1, 2, 3)),
        ("", ()),
        ("abc", ()),
        (None, ()),
        (12, ()),
    ],
)
def test_parse_version(text, expected):
    assert pluginApi.parseVersion(text) == expected


@pytest.mark.parametrize(
    "candidate,current,newer",
    [
        ("1.0.0", "0.9.0", True),
        ("0.10.0", "0.9.0", True),
        ("0.9.0", "0.9.0", False),
        ("0.9", "0.9.0", False),     # trailing zeros pad equal
        ("0.8.9", "0.9.0", False),
        ("1.0.1", "1.0", True),
    ],
)
def test_version_newer(candidate, current, newer):
    assert pluginApi.versionNewer(candidate, current) is newer


# ----------------------------------------------------------------------
# checkPluginConfig
# ----------------------------------------------------------------------


def test_empty_config_is_compatible():
    assert pluginApi.checkPluginConfig({}, APP_VERSION) == []


def test_supported_api_version_is_compatible():
    config = {"plugin_api": pluginApi.PLUGIN_API_VERSION}
    assert pluginApi.checkPluginConfig(config, APP_VERSION) == []


def test_newer_api_blocks_import():
    issues = pluginApi.checkPluginConfig({"plugin_api": 99}, APP_VERSION)
    assert issues and "plugin_api 99" in issues[0]


def test_non_integer_api_blocks_import():
    issues = pluginApi.checkPluginConfig({"plugin_api": "2"}, APP_VERSION)
    assert issues and "not an integer" in issues[0]


def test_min_app_version():
    assert pluginApi.checkPluginConfig(
        {"min_app_version": "0.8.0"}, APP_VERSION) == []
    issues = pluginApi.checkPluginConfig(
        {"min_app_version": "1.0.0"}, APP_VERSION)
    assert issues and "app >= 1.0.0" in issues[0]


def test_max_app_version():
    assert pluginApi.checkPluginConfig(
        {"max_app_version": "1.0.0"}, APP_VERSION) == []
    issues = pluginApi.checkPluginConfig(
        {"max_app_version": "0.8.0"}, APP_VERSION)
    assert issues and "app <= 0.8.0" in issues[0]


def test_unparseable_app_constraint_blocks():
    issues = pluginApi.checkPluginConfig(
        {"min_app_version": "soon"}, APP_VERSION)
    assert issues and "not a version" in issues[0]


def test_requires_core():
    assert pluginApi.checkPluginConfig(
        {"requires_core": ["menuItems"]}, APP_VERSION) == []
    issues = pluginApi.checkPluginConfig(
        {"requires_core": ["sdlSync"]}, APP_VERSION)
    assert issues and "sdlSync" in issues[0]


def test_multiple_issues_reported():
    issues = pluginApi.checkPluginConfig(
        {"plugin_api": 99, "min_app_version": "9.9"}, APP_VERSION)
    assert len(issues) == 2


# ----------------------------------------------------------------------
# updatesAvailable
# ----------------------------------------------------------------------


def test_updates_available():
    installed = {"aiTerminal": "0.9.0", "manual": "1.0"}
    registry = [
        {"name": "aiTerminal", "version": "1.0.0"},
        {"name": "manual", "version": "1.0"},
        {"name": "uninstalled", "version": "9.9"},
    ]
    assert pluginApi.updatesAvailable(installed, registry) == {
        "aiTerminal": ("0.9.0", "1.0.0")
    }


def test_updates_available_handles_junk():
    assert pluginApi.updatesAvailable({}, None) == {}
    assert pluginApi.updatesAvailable({"a": "1"}, [None, "x", {}]) == {}


# ----------------------------------------------------------------------
# pluginsLoader negotiation
# ----------------------------------------------------------------------


def test_loader_gates_and_capabilities(qapp, app_logger, tmp_path,
                                       monkeypatch):
    monkeypatch.syspath_prepend(str(tmp_path))
    _make_plugin(tmp_path, "ztgood", {
        "plugin_api": 2,
        "plugin_name": "ztgood",
        "plugin_version": "1.0",
        "provides": ["sdl"],
    })
    _make_plugin(tmp_path, "zttonew", {"plugin_api": 999})
    _make_plugin(tmp_path, "ztminapp", {"min_app_version": "99.0"})
    _make_plugin(tmp_path, "ztbadcore", {"requires_core": ["sdlSync"]})
    (tmp_path / "ztbare.py").write_text("")  # module plugin: implicit api 1

    loader = pluginsLoader(tmp_path)

    assert "ztgood" in loader.plugins
    assert loader.provides("sdl")
    assert loader.capabilityProvider("sdl") == "ztgood"
    assert not loader.provides("other")
    assert loader.pluginVersion("ztgood") == "1.0"
    assert "ztbare" in loader.plugins
    for name in ("zttonew", "ztminapp", "ztbadcore"):
        assert name not in loader.plugins
        assert loader.incompatible[name], name


def test_incompatible_or_failed_sdl_plugin_is_not_provider(
        qapp, app_logger, tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(tmp_path))
    _make_plugin(tmp_path, "ztbadsdl", {
        "plugin_api": 999,
        "provides": ["sdl"],
    })
    failed = _make_plugin(tmp_path, "ztfailsdl", {
        "plugin_api": 2,
        "provides": ["sdl"],
    })
    (failed / "__init__.py").write_text("raise RuntimeError('boom')\n")

    loader = pluginsLoader(tmp_path)

    assert "ztbadsdl" in loader.incompatible
    assert "ztfailsdl" not in loader.plugins
    assert not loader.provides("sdl")
    assert loader.capabilityProvider("sdl") is None


def test_capability_provider_injects_license_gated_menu_item(
        qapp, app_logger, tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(tmp_path))
    plugin_dir = _make_plugin(tmp_path, "ztsdl", {
        "plugin_api": 2,
        "plugin_name": "ztsdl",
        "plugin_version": "1.0",
        "license_required": True,
        "provides": ["sdl"],
        "payment_url": "https://plugins.example/checkout",
        "menu_items": [{
            "location": "menuBar",
            "menu": "Tools",
            "action": "UpdateFromSchematic",
            "text": "Update from Schematic...",
            "callback": "run",
            "apply": ["QMainWindow"],
        }],
    })
    (plugin_dir / "__init__.py").write_text(
        "def run(editorWindow):\n    editorWindow.calls.append('run')\n")
    licensed = {"value": False}
    prompts = []

    def prompt(plugin_name, payment_url, parent):
        prompts.append((plugin_name, payment_url, parent))
        return licensed["value"]

    monkeypatch.setattr(
        licenseManager, "check_and_prompt_license", prompt)

    loader = pluginsLoader(tmp_path)
    window = QMainWindow()
    window.calls = []
    window.menuBar().addMenu("Tools")
    try:
        assert loader.provides("sdl")
        assert loader.capabilityProvider("sdl") == "ztsdl"
        loader.applyPluginMenus(window)
        actions = window.menuBar().actions()[0].menu().actions()
        assert [action.text() for action in actions] == [
            "Update from Schematic..."]

        actions[0].trigger()
        assert prompts == [(
            "ztsdl", "https://plugins.example/checkout", window)]
        assert window.calls == []

        licensed["value"] = True
        actions[0].trigger()
        assert len(prompts) == 2
        assert window.calls == ["run"]
    finally:
        window.deleteLater()


def test_loader_pluginless_config_still_imports(qapp, app_logger, tmp_path,
                                                monkeypatch):
    """A package without config.json loads under the api-1 contract."""
    monkeypatch.syspath_prepend(str(tmp_path))
    _make_plugin(tmp_path, "ztnoconf", None)
    loader = pluginsLoader(tmp_path)
    assert "ztnoconf" in loader.plugins
    assert loader.incompatible == {}


class _FakePool:
    """QThreadPool stand-in that records started workers."""

    def __init__(self):
        self.started = []

    def start(self, worker):
        self.started.append(worker)


def test_update_check_throttle(qapp, app_logger, tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.delenv("REVEDA_DISABLE_UPDATE_CHECK", raising=False)
    _make_plugin(tmp_path, "ztold", {"plugin_version": "1.0.0"})
    loader = pluginsLoader(tmp_path)
    loader._updateSettingsFile = tmp_path / "settings.ini"
    loader._threadPool = _FakePool()

    assert loader.checkForUpdates() is True
    assert loader.checkForUpdates() is False        # same-day throttle
    assert loader.checkForUpdates(force=True) is True
    monkeypatch.setenv("REVEDA_DISABLE_UPDATE_CHECK", "1")
    assert loader.checkForUpdates(force=True) is False
    assert len(loader._threadPool.started) == 2


def test_update_check_skipped_without_plugins(qapp, app_logger, tmp_path,
                                              monkeypatch):
    monkeypatch.delenv("REVEDA_DISABLE_UPDATE_CHECK", raising=False)
    loader = pluginsLoader(tmp_path)                # empty dir
    loader._updateSettingsFile = tmp_path / "settings.ini"
    loader._threadPool = _FakePool()
    assert loader.checkForUpdates() is False
    assert loader._threadPool.started == []


def test_registry_result_logs_updates(qapp, app_logger, tmp_path,
                                      monkeypatch, caplog):
    monkeypatch.syspath_prepend(str(tmp_path))
    _make_plugin(tmp_path, "ztold", {"plugin_version": "1.0.0"})
    loader = pluginsLoader(tmp_path)
    loader._updateSettingsFile = tmp_path / "settings.ini"
    emitted = []
    loader.updatesChanged.connect(emitted.append)
    with caplog.at_level(logging.WARNING, "reveda"):
        loader._onRegistryFetched([
            {"name": "ztold", "version": "1.1.0"},
            {"name": "ztother", "version": "2.0"},
        ])
    assert loader.availableUpdates == {"ztold": ("1.0.0", "1.1.0")}
    assert emitted == [{"ztold": ("1.0.0", "1.1.0")}]
    assert "Plugin update available: ztold 1.0.0 -> 1.1.0" in caplog.text
