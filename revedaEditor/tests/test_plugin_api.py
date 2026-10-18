"""Plugin contract tests: version/capability negotiation and update checks.

The pure helpers in ``backend/pluginApi.py`` need no Qt. Loader tests use
the session ``qapp`` fixture plus a monkeypatched ``logger`` attribute —
``pluginsLoader`` logs through ``QApplication.instance().logger``.
"""

import json
import logging
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QMainWindow

from revedaEditor.backend import licenseManager, pluginApi
from revedaEditor.backend.libraryModelView import BaseDesignLibrariesView
from revedaEditor.backend.pluginsLoader import (
    pluginsLoader,
    unimportPluginPath,
)
from revedaEditor.gui.editorFactory import EditorFactory

APP_VERSION = "1.0.0"


def test_standard_view_never_dispatches_to_plugin(monkeypatch):
    class editor:
        centralW = SimpleNamespace(
            scene=SimpleNamespace(fitItemsInView=lambda: None)
        )

        def loadSchematic(self):
            pass

        def show(self):
            pass

    plugin = SimpleNamespace(
        openCellView=lambda _: pytest.fail("standard view reached plugin")
    )
    browser = BaseDesignLibrariesView.__new__(BaseDesignLibrariesView)
    browser.appMainW = SimpleNamespace(openViews={})
    browser.libraryDict = {}
    browser._app = SimpleNamespace(pluginsObj=plugin)
    viewName = object()
    view = SimpleNamespace(
        viewItem=SimpleNamespace(viewType="schematic"),
        convertToViewNameTuple=lambda: viewName,
    )
    monkeypatch.setattr(EditorFactory, "getSupportedViewTypes", lambda: [])
    monkeypatch.setattr(EditorFactory, "createEditor", lambda *args: editor())

    assert browser.openCellView(view) is viewName


@pytest.mark.parametrize("operation", ["openCellView", "createCellView"])
def test_view_dispatch_isolates_plugin_metadata_failure(app_logger, tmp_path, operation):
    class unlicensedPlugin:
        def __getattr__(self, name):
            raise RuntimeError("designCopilot requires a valid license")

    loader = pluginsLoader(tmp_path)
    calls = []
    owner = SimpleNamespace(viewTypes=["revbench"])
    setattr(owner, operation, calls.append)
    loader.plugins = {"designCopilot": unlicensedPlugin(), "revedasim": owner}
    view = SimpleNamespace(viewItem=SimpleNamespace(viewType="revbench"))

    assert getattr(loader, operation)(view) is True
    assert calls == [view]


@pytest.mark.parametrize("operation", ["openCellView", "createCellView"])
def test_view_dispatch_preserves_owner_license_gate(
    app_logger, tmp_path, monkeypatch, operation
):
    loader = pluginsLoader(tmp_path)
    calls = []
    owner = SimpleNamespace(viewTypes=["dcspec"])
    setattr(owner, operation, calls.append)
    loader.plugins = {"designCopilot": owner}
    loader.pluginMenuConfig = {"designCopilot": {"license_required": True}}
    prompts = []
    monkeypatch.setattr(
        licenseManager, "check_and_prompt_license",
        lambda name, url, parent: prompts.append(name) or False,
    )
    view = SimpleNamespace(viewItem=SimpleNamespace(viewType="dcspec"))

    assert getattr(loader, operation)(view) is False
    assert calls == []
    assert prompts == ["designCopilot"]


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
        {"min_app_version": "1.0.1"}, APP_VERSION)
    assert issues and "app >= 1.0.1" in issues[0]


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


@pytest.mark.parametrize("licenseConfig", [
    {"license_required": True}, {"license": "Commercial"},
])
def test_commercial_menu_defers_callback_lookup(
    app_logger, tmp_path, monkeypatch, licenseConfig
):
    licensed = {"value": False}
    lookups = []
    calls = []
    prompts = []

    class commercialPlugin:
        def __getattr__(self, name):
            lookups.append(name)
            if not licensed["value"]:
                raise RuntimeError("designCopilot requires a valid license")
            return lambda window: calls.append((name, window))

    def prompt(pluginName, paymentUrl, parent):
        prompts.append(pluginName)
        return licensed["value"]

    monkeypatch.setattr(licenseManager, "check_and_prompt_license", prompt)
    loader = pluginsLoader(tmp_path)
    loader.plugins = {"designCopilot": commercialPlugin()}
    loader.pluginMenuConfig = {"designCopilot": {
        **licenseConfig,
        "menu_items": [{
            "location": "menuBar", "menu": "Utilities",
            "action": "Design Copilot", "callback": "openDesignCopilot",
            "apply": ["QMainWindow"],
        }],
    }}
    window = QMainWindow()
    menu = window.menuBar().addMenu("Utilities")
    try:
        loader.applyPluginMenus(window)
        assert lookups == []
        assert prompts == []
        assert len(menu.actions()) == 1

        menu.actions()[0].trigger()
        assert prompts == ["designCopilot"]
        assert lookups == []
        assert calls == []

        licensed["value"] = True
        menu.actions()[0].trigger()
        assert prompts == ["designCopilot", "designCopilot"]
        assert lookups == ["openDesignCopilot"]
        assert calls == [("openDesignCopilot", window)]
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


# ----------------------------------------------------------------------
# Extension-module ABI tags
# ----------------------------------------------------------------------

_RUNNING_TAG = f"cpython-{sys.version_info.major}{sys.version_info.minor}"
_OTHER_TAG = f"cpython-{sys.version_info.major}{sys.version_info.minor + 3}"


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("sdl.cpython-314-x86_64-linux-gnu.so", (3, 14)),
        ("x.cpython-312-x86_64-linux-gnu.so", (3, 12)),
        ("mod.cp312-win_amd64.pyd", (3, 12)),
        ("mod.cpython-38-x86_64-linux-gnu.so", (3, 8)),
        ("mod.abi3.so", None),
        ("mod.so", None),
        ("mod.pyd", None),
        ("plain.py", None),
    ],
)
def test_extension_py_version(filename, expected):
    assert pluginApi.extensionPyVersion(filename) == expected


def test_mismatched_extensions_package_and_sibling(tmp_path):
    pkg = _make_plugin(tmp_path, "ztbin", None)
    (pkg / f"inner.{_OTHER_TAG}-x86_64-linux-gnu.so").write_bytes(b"\x7fELF")
    (tmp_path / f"ztbin.{_OTHER_TAG}-x86_64-linux-gnu.so").write_bytes(b"\x7fELF")
    (tmp_path / f"ztbin.{_RUNNING_TAG}-x86_64-linux-gnu.so").write_bytes(b"\x7fELF")
    bad = pluginApi.mismatchedExtensions(tmp_path, "ztbin", True)
    assert len(bad) == 2
    for path, tag in bad:
        assert _OTHER_TAG in path.name
        assert tag == (sys.version_info.major, sys.version_info.minor + 3)


def test_mismatched_extensions_module_plugin(tmp_path):
    (tmp_path / f"ztmod.{_OTHER_TAG}-x86_64-linux-gnu.so").write_bytes(b"\x7fELF")
    bad = pluginApi.mismatchedExtensions(tmp_path, "ztmod", False)
    assert len(bad) == 1


def test_mismatched_extensions_ignores_tagless(tmp_path):
    (tmp_path / "ztmod.so").write_bytes(b"\x7fELF")
    (tmp_path / "ztmod.abi3.so").write_bytes(b"\x7fELF")
    assert pluginApi.mismatchedExtensions(tmp_path, "ztmod", False) == []


def test_explain_import_error():
    err = ImportError(
        "/p/sdl.cpython-399-x86_64-linux-gnu.so: undefined symbol: _PyX")
    hint = pluginApi.explainImportError(err)
    assert hint and "3.99" in hint
    hint = pluginApi.explainImportError(
        ImportError("/p/m.abi3.so: undefined symbol: _PyFoo"))
    assert hint and "incompatible" in hint
    assert pluginApi.explainImportError(
        ImportError("No module named 'dep'")) is None
    assert pluginApi.explainImportError(RuntimeError("x")) is None


def test_loader_skips_python_mismatched_plugin(qapp, app_logger, tmp_path,
                                             monkeypatch):
    monkeypatch.syspath_prepend(str(tmp_path))
    _make_plugin(tmp_path, "ztbin", {"plugin_version": "1.0"})
    (tmp_path / f"ztbin.{_OTHER_TAG}-x86_64-linux-gnu.so").write_bytes(
        b"\x7fELF")
    loader = pluginsLoader(tmp_path)
    assert "ztbin" not in loader.plugins
    issue = loader.incompatible["ztbin"][0]
    assert f"Python {sys.version_info.major}.{sys.version_info.minor + 3}" \
        in issue


# ----------------------------------------------------------------------
# Runtime plugin-path switching / sys.path hygiene
# ----------------------------------------------------------------------


def _clean_plugin_import_state(root: Path, *names: str) -> None:
    """Drop sys.path entries under ``root`` and cached plugin modules."""
    root_str = str(root)
    sys.path[:] = [
        entry for entry in sys.path if not str(entry).startswith(root_str)
    ]
    for name in names:
        sys.modules.pop(name, None)


def test_unimportPluginPath_detaches_directory(tmp_path):
    """Removes sys.path entries (incl. package subdirs) and cached modules."""
    pkg = tmp_path / "goneplug"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("MARKER = 'old'")
    saved_path = list(sys.path)
    sys.path.insert(0, str(tmp_path))
    sys.path.insert(0, str(pkg))  # per-package dir a loader would append
    try:
        import goneplug
        assert "goneplug" in sys.modules
        unimportPluginPath(tmp_path)
        assert str(tmp_path) not in sys.path
        assert str(pkg) not in sys.path
        assert "goneplug" not in sys.modules
    finally:
        sys.path[:] = saved_path
        sys.modules.pop("goneplug", None)


def test_loader_shadowed_package_resolves_own_directory(
    qapp, app_logger, tmp_path, monkeypatch
):
    """A same-named package earlier on sys.path must not shadow the plugin.

    Regression: switching the plugin path left the previous directory on
    sys.path, so a same-named shim there was imported instead — and a shim
    executing an incompatible binary extension crashes the interpreter.
    """
    stale = tmp_path / "stale"
    target = tmp_path / "target"
    (stale / "shadedplug").mkdir(parents=True)
    (target / "shadedplug").mkdir(parents=True)
    (stale / "shadedplug" / "__init__.py").write_text(
        "raise RuntimeError('stale plugin must not be imported')"
    )
    (target / "shadedplug" / "__init__.py").write_text("MARKER = 'target'")
    monkeypatch.syspath_prepend(str(stale))
    loader = pluginsLoader(target)
    try:
        assert loader.plugins["shadedplug"].MARKER == "target"
    finally:
        _clean_plugin_import_state(target, "shadedplug")


def test_loader_evicts_stale_cached_module(
    qapp, app_logger, tmp_path, monkeypatch
):
    """A cached module imported from another directory must not shadow."""
    foreign = tmp_path / "foreign"
    target = tmp_path / "target"
    (foreign / "evictplug").mkdir(parents=True)
    (target / "evictplug").mkdir(parents=True)
    (foreign / "evictplug" / "__init__.py").write_text("MARKER = 'foreign'")
    (target / "evictplug" / "__init__.py").write_text("MARKER = 'target'")
    monkeypatch.syspath_prepend(str(foreign))
    import evictplug
    assert evictplug.MARKER == "foreign"
    loader = pluginsLoader(target)
    try:
        assert loader.plugins["evictplug"].MARKER == "target"
    finally:
        _clean_plugin_import_state(target, "evictplug")


def test_loader_leaves_plugin_root_importable_once(qapp, app_logger, tmp_path):
    """After a scan the plugin root stays on sys.path once, not promoted."""
    _make_plugin(tmp_path, "rootrest", None)
    loader = pluginsLoader(tmp_path)
    try:
        assert "rootrest" in loader.plugins
        assert sys.path[0] != str(tmp_path)
        assert sys.path.count(str(tmp_path)) == 1
    finally:
        _clean_plugin_import_state(tmp_path, "rootrest")
