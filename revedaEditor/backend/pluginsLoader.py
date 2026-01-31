#    “Commons Clause” License Condition v1.0
#   #
#    The Software is provided to you by the Licensor under the License, as defined
#    below, subject to the following condition.
#
#    Without limiting other conditions in the License, the grant of rights under the
#    License will not include, and the License does not grant to you, the right to
#    Sell the Software.
#
#    For purposes of the foregoing, “Sell” means practicing any or all of the rights
#    granted to you under the License to provide to third parties, for a fee or other
#    consideration (including without limitation fees for hosting) a product or service whose value
#    derives, entirely or substantially, from the functionality of the Software. Any
#    license notice or attribution required by the License must also include this
#    Commons Clause License Condition notice.
#
#   Add-ons and extensions developed for this software may be distributed
#   under their own separate licenses.
#
#    Software: Revolution EDA
#    License: Mozilla Public License 2.0
#    Licensor: Revolution Semiconductor (Registered in the Netherlands)
#

import importlib
import pkgutil
from pathlib import Path

from PySide6.QtGui import (QAction, QIcon)
from PySide6.QtWidgets import (QApplication, )


class pluginsLoader:
    def __init__(self, pluginsPath: Path):
        self.plugins = {}
        self.pluginsPathObj = pluginsPath
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
        return f'plugins({list(self.plugins.keys())})'

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
                            f"Failed to load plugin config for {item.name}: {e}")

        self._app.logger.info(
            f"Loaded plugin menu config: {list(self.pluginMenuConfig.keys())}")

    def applyPluginMenus(self, editorWindow):
        """Apply plugin menus to an editor window"""
        if not hasattr(self, 'pluginMenuConfig'):
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
                callback = getattr(module, menuItem["callback"], None)
                if not callback:
                    continue

                # Find target menu and add action
                if hasattr(editorWindow, menuItem['location']):
                    for action in editorWindow.menuBar().actions():
                        if action.text().replace('&', '') == menuItem["menu"]:
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
                            new_action.triggered.connect(lambda c=False, cb=callback: cb(
                                editorWindow))
                            action.menu().addAction(new_action)
                            break

    def createCellView(self, viewItem):

        for pluginName, pluginModule in self.plugins.items():
            if (hasattr(pluginModule, 'viewTypes') and
                    viewItem.viewType in getattr(pluginModule, 'viewTypes')):
                pluginModule.createCellView(viewItem)

    def openCellView(self, viewItem):
        for pluginName, pluginModule in self.plugins.items():
            if (hasattr(pluginModule, 'viewTypes') and
                    viewItem.viewType in getattr(pluginModule, 'viewTypes')):
                pluginModule.openCellView(viewItem)
