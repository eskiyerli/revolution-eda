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
import pkgutil
from pathlib import Path

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication,
)

from revedaEditor.backend import licenseManager
from revedaEditor.backend.dataDefinitions import viewItemTuple


class pluginsLoader:
    def __init__(self, pluginsPath: Path):
        self.plugins = {}
        self.pluginsPathObj: Path = pluginsPath
        self._app = QApplication.instance()
        self.pluginMenuConfig = {}

        for _, name, _ in pkgutil.iter_modules([str(self.pluginsPathObj)]):
            self._app.logger.info(f"Found plugin: {name}")
            try:
                module = importlib.import_module(name)
                self.plugins[f"{name}"] = module
            except ImportError as e:
                self._app.logger.error(f"Failed to load plugin {name}: {e}")
        self._app.logger.info(f"Loaded plugins: {list(self.plugins.keys())}")
        self._loadPluginMenus()

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

    def _loadPluginMenus(self):
        """Load plugin menu configurations from JSON file"""
        import json

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

    def createCellView(self, viewItemT: viewItemTuple):
        for pluginName, pluginModule in self.plugins.items():
            if hasattr(
                pluginModule, "viewTypes"
            ) and viewItemT.viewItem.viewType in getattr(pluginModule, "viewTypes"):
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
            if hasattr(
                pluginModule, "viewTypes"
            ) and viewItemT.viewItem.viewType in getattr(pluginModule, "viewTypes"):
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
