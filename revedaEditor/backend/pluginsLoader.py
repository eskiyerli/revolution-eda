# 
# Revolution EDA
# 
# Copyright (c) 2026 Revolution Semiconductor
#
# This Source Code Form is subject to the terms of the
# Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
##

import importlib
import json
import os
import pkgutil
import sys
import urllib.request
from datetime import date
from pathlib import Path

from PySide6.QtCore import QObject, QSettings, QThreadPool, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication,
)

import revedaEditor
import revedaEditor.backend.editFunctions as edf
from revedaEditor.backend import licenseManager, pluginApi
from revedaEditor.backend.dataDefinitions import viewItemTuple
from revedaEditor.backend.startThread import startThread


def _moduleWithinDir(module, directory: Path) -> bool:
    """True when ``module`` was imported from inside ``directory``."""
    modFile = getattr(module, "__file__", None)
    if modFile is not None and Path(modFile).is_relative_to(directory):
        return True
    modPaths = getattr(module, "__path__", None) or ()
    return any(Path(p).is_relative_to(directory) for p in modPaths)


def unimportPluginPath(pluginPathObj: Path) -> None:
    """Detach a plugin directory from the import machinery.

    Removes its ``sys.path`` entries (including per-package subdirectories
    a loader may have appended) and evicts modules imported from it, so a
    later scan cannot resolve stale or shadowed packages. Called when the
    plugin path changes at runtime; without this a shim package left on
    ``sys.path`` can execute an incompatible binary extension and crash
    the interpreter.
    """
    root = str(pluginPathObj)
    prefix = root + os.sep
    sys.path[:] = [
        entry for entry in sys.path
        if entry != root and not entry.startswith(prefix)
    ]
    for modName, module in list(sys.modules.items()):
        modFile = getattr(module, "__file__", "") or ""
        modPaths = getattr(module, "__path__", None) or ()
        if modFile.startswith(prefix) or any(
            str(path).startswith(prefix) for path in modPaths
        ):
            del sys.modules[modName]


class pluginsLoader(QObject):
    updatesChanged = Signal(dict)
    _UPDATE_SETTINGS_FILE = edf.APP_SETTINGS_FILE
    _UPDATE_SETTINGS_KEY = "pluginUpdateCheck/lastCheck"
    _UPDATE_CACHE_KEY = "pluginUpdateCheck/registry"

    def __init__(self, pluginsPath: Path):
        super().__init__()
        self.plugins = {}
        self.pluginsPathObj: Path = pluginsPath
        self._app = QApplication.instance()
        self.pluginMenuConfig = {}
        # Version/capability negotiation results (see backend/pluginApi.py).
        self.incompatible: dict = {}      # plugin name -> [issue, ...]
        self.capabilities: dict = {}      # capability -> owning plugin name
        self.pluginInfo: dict = {}        # plugin dir name -> metadata
        self.availableUpdates: dict = {}  # name -> (installed, latest)
        self.registryUrl = pluginApi.DEFAULT_REGISTRY_URL
        self._updateWorker = None
        self._threadPool = QThreadPool.globalInstance()
        self._updateSettingsFile = self._UPDATE_SETTINGS_FILE
        self._appVersion = getattr(revedaEditor, "__version__", "0.0.0")

        self._importPlugins()
        self._app.logger.info(f"Loaded plugins: {list(self.plugins.keys())}")
        self._loadPluginMenus()
        self._loadCachedUpdates()

    def _importPlugins(self):
        """Scan ``pluginsPathObj`` and import compatible plugins.

        The plugin root is promoted to the front of ``sys.path`` for the
        duration of the scan so that same-named packages left over from a
        previous plugin location cannot shadow — or hijack — the imports
        (a stale shim can execute an incompatible binary extension and
        crash the interpreter). Its original position is restored after.
        """
        plugins_root = str(self.pluginsPathObj)
        prev_pos = (
            sys.path.index(plugins_root) if plugins_root in sys.path else None
        )
        if prev_pos is not None:
            sys.path.pop(prev_pos)
        sys.path.insert(0, plugins_root)
        try:
            for _, name, ispkg in pkgutil.iter_modules([plugins_root]):
                self._app.logger.info(f"Found plugin: {name}")
                # Negotiate before importing: an incompatible plugin's code is
                # never executed. Single-file plugins carry no config.json and
                # load under the implicit plugin_api 1 contract.
                config = (
                    pluginApi.readPluginConfig(self.pluginsPathObj / name)
                    if ispkg
                    else {}
                )
                issues = pluginApi.checkPluginConfig(config, self._appVersion)
                if issues:
                    self.incompatible[name] = issues
                    self._app.logger.warning(
                        f"Skipping incompatible plugin {name}: {'; '.join(issues)}"
                    )
                    continue
                # Binaries tagged for another CPython minor can never import —
                # flag the version mismatch instead of a raw ImportError.
                mismatch = pluginApi.mismatchedExtensions(
                    self.pluginsPathObj, name, ispkg
                )
                if mismatch:
                    extPath, tag = mismatch[0]
                    issues = [
                        f"{extPath.name} was built for Python "
                        f"{tag[0]}.{tag[1]}, but this app runs Python "
                        f"{sys.version_info.major}.{sys.version_info.minor}; "
                        "install a plugin build matching the app"
                    ]
                    self.incompatible[name] = issues
                    self._app.logger.warning(
                        f"Skipping incompatible plugin {name}: {'; '.join(issues)}"
                    )
                    continue
                try:
                    if ispkg:
                        plugin_dir = str(self.pluginsPathObj / name)
                        if plugin_dir not in sys.path:
                            sys.path.append(plugin_dir)
                    cached = sys.modules.get(name)
                    if cached is not None and not _moduleWithinDir(
                        cached, self.pluginsPathObj
                    ):
                        # A stale same-named module imported from another
                        # directory would shadow this plugin — evict it so the
                        # import resolves inside pluginsPathObj.
                        del sys.modules[name]
                    module = importlib.import_module(name)
                    self.plugins[f"{name}"] = module
                    self._registerPluginMetadata(name, config)
                except Exception as e:  # Optional plugins must not block startup.
                    hint = pluginApi.explainImportError(e)
                    if hint:
                        self._app.logger.error(
                            f"Failed to load plugin {name}: {hint} [{e}]"
                        )
                    else:
                        self._app.logger.exception(
                            f"Failed to load plugin {name}: {e}"
                        )
        finally:
            while plugins_root in sys.path:
                sys.path.remove(plugins_root)
            if prev_pos is None:
                sys.path.append(plugins_root)
            else:
                sys.path.insert(min(prev_pos, len(sys.path)), plugins_root)

    def _registerPluginMetadata(self, name: str, config: dict) -> None:
        """Record a successfully imported plugin's version/capabilities."""
        caps = pluginApi.pluginCapabilities(config)
        for cap in caps:
            owner = self.capabilities.get(cap)
            if owner is not None and owner != name:
                self._app.logger.warning(
                    f"Plugin capability '{cap}' claimed by both "
                    f"{owner} and {name}; {owner} wins"
                )
            else:
                self.capabilities[cap] = name
        self.pluginInfo[name] = {
            "version": str(config.get("plugin_version", "")),
            "configName": str(config.get("plugin_name", "")),
            "provides": sorted(caps),
        }

    def provides(self, capability: str) -> bool:
        """True when a compatible plugin provides ``capability``.

        The provider may still require activation; menu callbacks use the
        normal license prompt before executing commercial functionality.
        """
        return capability in self.capabilities

    def capabilityProvider(self, capability: str) -> str | None:
        """Name of the plugin owning ``capability``, or None."""
        return self.capabilities.get(capability)

    def pluginVersion(self, name: str) -> str | None:
        """Installed ``plugin_version`` of a loaded plugin, or None."""
        info = self.pluginInfo.get(name)
        return info["version"] or None if info else None

    # ------------------------------------------------------------------
    # Background update check (registry fetch; results go to the log and
    # self.availableUpdates — no UI). The registry window highlights
    # outdated installs when the user opens it.
    # ------------------------------------------------------------------

    def checkForUpdates(self, force: bool = False) -> bool:
        """Start a background registry fetch; returns True when started.

        Throttled to once per calendar day via QSettings unless ``force``;
        disabled entirely with ``REVEDA_DISABLE_UPDATE_CHECK``. With no
        installed plugins there is nothing to compare, so it skips.
        """
        if os.environ.get("REVEDA_DISABLE_UPDATE_CHECK"):
            return False
        if not self.pluginInfo:
            return False
        self._updateSettingsFile.parent.mkdir(parents=True, exist_ok=True)
        settings = QSettings(
            str(self._updateSettingsFile), QSettings.IniFormat
        )
        today = date.today().isoformat()
        if not force and settings.value(self._UPDATE_SETTINGS_KEY, "") == today:
            return False
        settings.setValue(self._UPDATE_SETTINGS_KEY, today)
        worker = startThread(self._fetchRegistry, self.registryUrl)
        worker.signals.result.connect(self._onRegistryFetched)
        worker.signals.error.connect(self._onRegistryError)
        self._updateWorker = worker  # keep alive until the pool finishes it
        self._threadPool.start(worker)
        return True

    @staticmethod
    def _fetchRegistry(url: str) -> list:
        """Blocking registry fetch — runs on a worker thread."""
        with urllib.request.urlopen(url, timeout=5) as resp:
            index = json.loads(resp.read().decode("utf-8"))
        if isinstance(index, dict):
            index = index.get("plugins", [])
        return index if isinstance(index, list) else []

    def _installedVersions(self) -> dict[str, str]:
        installed = {}
        for dirName, info in self.pluginInfo.items():
            version = info.get("version")
            if not version:
                continue
            installed[dirName] = version
            configName = info.get("configName")
            if configName:
                installed.setdefault(configName, version)
        return installed

    def _loadCachedUpdates(self) -> None:
        settings = QSettings(
            str(self._updateSettingsFile), QSettings.IniFormat
        )
        try:
            entries = json.loads(settings.value(self._UPDATE_CACHE_KEY, "[]"))
        except (TypeError, json.JSONDecodeError):
            entries = []
        self.availableUpdates = pluginApi.updatesAvailable(
            self._installedVersions(), entries
        )

    def _onRegistryFetched(self, entries: list) -> None:
        """Compare installed plugin versions against registry entries."""
        self.availableUpdates = pluginApi.updatesAvailable(
            self._installedVersions(), entries
        )
        settings = QSettings(
            str(self._updateSettingsFile), QSettings.IniFormat
        )
        settings.setValue(self._UPDATE_CACHE_KEY, json.dumps(entries))
        settings.sync()
        for name, (current, latest) in sorted(self.availableUpdates.items()):
            self._app.logger.warning(
                f"Plugin update available: {name} {current} -> {latest} "
                "(Plugins -> Updates)"
            )
        self.updatesChanged.emit(dict(self.availableUpdates))

    def _onRegistryError(self, error) -> None:
        self._app.logger.warning(f"Plugin update check failed: {error}")

    def __repr__(self):
        return f"plugins({list(self.plugins.keys())})"

    @staticmethod
    def _plugin_requires_license(plugin_name: str, plugin_config: dict) -> bool:
        if plugin_config.get("license_required", False):
            return True
        license_type = plugin_config.get("license", "")
        return license_type in ("Commercial", "Proprietary", "Paid")

    def _wrap_callback_with_license(
        self, callback, plugin_name: str, payment_url: str | None
    ):
        def licensed_callback(editorWindow):
            if licenseManager.check_and_prompt_license(
                plugin_name, payment_url, editorWindow
            ):
                callback(editorWindow)
        return licensed_callback

    def _deferredPluginCallback(self, module, callbackName):
        def deferredCallback(editorWindow):
            try:
                callback = getattr(module, callbackName, None)
            except RuntimeError as e:
                # Compiled plugins may still enforce licensing inside
                # __getattr__ even after the license gate ran.
                self._app.logger.warning(
                    f"Plugin menu callback {callbackName} unavailable: {e}"
                )
                return
            if callback is None:
                self._app.logger.warning(
                    f"Plugin menu callback not found: {callbackName}"
                )
                return
            callback(editorWindow)
        return deferredCallback

    def _loadPluginMenus(self):
        """Load plugin menu configurations from JSON file"""
        self.pluginMenuConfig = {}
        if not self.pluginsPathObj.exists():
            return

        for item in self.pluginsPathObj.iterdir():
            if item.is_dir():
                configPath = item / "config.json"
                if configPath.exists():
                    try:
                        with open(configPath) as f:
                            config = json.load(f)
                        self.pluginMenuConfig[item.name] = config
                    except Exception as e:
                        self._app.logger.warning(
                            f"Failed to load plugin config for {item.name}: {e}"
                        )

        self._app.logger.info(
            f"Loaded plugin menu config: {list(self.pluginMenuConfig.keys())}"
        )

    def applyPluginMenus(self, editorWindow):
        """Apply plugin menus to an editor window"""
        if not hasattr(self, "pluginMenuConfig"):
            return
        editorClassName = editorWindow.__class__.__name__

        for plugin_name, plugin_config in self.pluginMenuConfig.items():
            # Get plugin module
            module = self.plugins.get(plugin_name)
            if not module:
                continue

            for menuItem in plugin_config.get("menu_items", []):
                # Check applicability
                if "apply" in menuItem and editorClassName not in menuItem["apply"]:
                    continue
                # Get callback
                try:
                    if self._plugin_requires_license(plugin_name, plugin_config):
                        callback = self._deferredPluginCallback(
                            module, menuItem["callback"]
                        )
                    else:
                        callback = getattr(module, menuItem["callback"], None)
                except RuntimeError as e:
                    # Compiled plugins may enforce licensing inside __getattr__.
                    # Provide a stub that opens the activation dialog and retries.
                    msg = str(e).lower()
                    if "license" not in msg and "revedaLicense" not in msg:
                        raise
                    payment_url = plugin_config.get("payment_url")

                    def _stub_callback(
                        editorWindow,
                        pn=plugin_name,
                        pu=payment_url,
                        mod=module,
                        cb_name=menuItem["callback"],
                    ):
                        if licenseManager.check_and_prompt_license(
                            pn, pu, editorWindow
                        ):
                            real_cb = getattr(mod, cb_name)
                            real_cb(editorWindow)

                    callback = _stub_callback
                if callback is None:
                    continue

                # Wrap with license gate if required
                if self._plugin_requires_license(plugin_name, plugin_config):
                    payment_url = plugin_config.get("payment_url")
                    callback = self._wrap_callback_with_license(
                        callback, plugin_name, payment_url
                    )

                # Find target menu and add action
                if hasattr(editorWindow, menuItem["location"]):
                    for action in editorWindow.menuBar().actions():
                        if action.text().replace("&", "") == menuItem["menu"]:
                            new_action = QAction(menuItem["action"], editorWindow)
                            if "text" in menuItem:
                                new_action.setText(menuItem["text"])
                            if "icon" in menuItem:
                                new_action.setIcon(QIcon(menuItem["icon"]))
                            if "shortcut" in menuItem:
                                new_action.setShortcut(menuItem["shortcut"])
                            if "checked" in menuItem:
                                new_action.setCheckable(True)
                                new_action.setChecked(menuItem["checked"])
                            new_action.setProperty(
                                "readOnlySafe",
                                bool(menuItem.get("read_only_safe", False)),
                            )
                            pluginActions = getattr(
                                editorWindow, "_pluginActions", None)
                            if pluginActions is None:
                                pluginActions = editorWindow._pluginActions = []
                            pluginActions.append(new_action)
                            new_action.triggered.connect(
                                lambda c=False, cb=callback: cb(editorWindow)
                            )
                            action.menu().addAction(new_action)
                            break

    def _check_license_or_prompt(self, plugin_name: str, plugin_config: dict) -> bool:
        if not self._plugin_requires_license(plugin_name, plugin_config):
            return True
        payment_url = plugin_config.get("payment_url")
        parent = QApplication.activeWindow()
        return licenseManager.check_and_prompt_license(
            plugin_name, payment_url, parent
        )

    def _pluginViewTypes(self, pluginName, pluginModule):
        try:
            return getattr(pluginModule, "viewTypes", ())
        except Exception as error:
            self._app.logger.warning(
                f"Skipping view dispatch for plugin {pluginName}: {error}"
            )
            return ()

    def createCellView(self, viewItemT: viewItemTuple):
        for pluginName, pluginModule in self.plugins.items():
            if viewItemT.viewItem.viewType in self._pluginViewTypes(
                pluginName, pluginModule
            ):
                plugin_config = self.pluginMenuConfig.get(pluginName, {})
                if not self._check_license_or_prompt(pluginName, plugin_config):
                    return False
                try:
                    pluginModule.createCellView(viewItemT)
                except RuntimeError as e:
                    msg = str(e).lower()
                    if "license" not in msg and "revedaLicense" not in msg:
                        raise
                    if self._check_license_or_prompt(pluginName, plugin_config):
                        pluginModule.createCellView(viewItemT)
                    else:
                        return False
                return True
        else:
            self._app.logger.warning(
                f"No plugin found to open view type: {viewItemT.viewItem.viewType}"
            )
            return False

    def openCellView(self, viewItemT: viewItemTuple):
        for pluginName, pluginModule in self.plugins.items():
            if viewItemT.viewItem.viewType in self._pluginViewTypes(
                pluginName, pluginModule
            ):
                plugin_config = self.pluginMenuConfig.get(pluginName, {})
                if not self._check_license_or_prompt(pluginName, plugin_config):
                    return False
                try:
                    pluginModule.openCellView(viewItemT)
                except RuntimeError as e:
                    msg = str(e).lower()
                    if "license" not in msg and "revedaLicense" not in msg:
                        raise
                    if self._check_license_or_prompt(pluginName, plugin_config):
                        pluginModule.openCellView(viewItemT)
                    else:
                        return False
                return True
        else:
            self._app.logger.warning(
                f"No plugin found to open view type: {viewItemT.viewItem.viewType}"
            )
            return False
