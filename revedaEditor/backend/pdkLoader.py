# SPDX-License-Identifier: MPL-2.0
#
# Copyright (c) 2024-2026 Revolution Semiconductor (Registered in the Netherlands)
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this file, You can obtain one at
# https://mozilla.org/MPL/2.0/.
#
# Add-ons and extensions developed for this software may be distributed
# under their own separate licenses.

import importlib
import logging
import os
import pathlib
import sys
from types import ModuleType

from PySide6.QtGui import (QAction, QIcon)
from PySide6.QtWidgets import QApplication

_module_cache: dict[tuple[str, str], ModuleType] = {}
logger = logging.getLogger(__name__)


def _get_pdk_path() -> pathlib.Path:
    """Get and cache PDK path"""
    base_path = pathlib.Path(__file__).resolve().parent.parent.parent
    pdkPath = os.environ.get("REVEDA_PDK_PATH")
    
    if pdkPath:
        pdkPathObj = pathlib.Path(pdkPath)
        if not pdkPathObj.is_absolute():
            pdkPathObj = base_path / pdkPath
    else:
        pdkPathObj = base_path / 'defaultPDK'
    
    pdkPathObj = pdkPathObj.resolve()

    if not pdkPathObj.exists():
        pdkPathObj = (base_path / 'defaultPDK').resolve()
        if not pdkPathObj.exists():
            raise FileNotFoundError(f"PDK path not found: {pdkPathObj}")

    pdkPathParentStr = str(pdkPathObj.parent)
    if pdkPathParentStr not in sys.path:
        sys.path.append(pdkPathParentStr)

    return pdkPathObj


def importPDKModule(moduleName: str) -> ModuleType | None:
    """Import a PDK submodule dynamically.
    
    Returns the module if found, None otherwise.
    Does not cache failed imports to allow recovery after PDK fixes.
    Cache key includes PDK path to handle PDK switching.
    """
    pdkPathObj = _get_pdk_path()
    cache_key = (str(pdkPathObj), moduleName)
    
    if cache_key in _module_cache:
        return _module_cache[cache_key]

    fullModuleName = f"{pdkPathObj.name}.{moduleName}"

    try:
        module = importlib.import_module(fullModuleName)
        _module_cache[cache_key] = module
        logger.debug(f"Loaded PDK module: {fullModuleName}")
        return module
    except ModuleNotFoundError:
        logger.warning(f"PDK module not found: {fullModuleName}")
        return None
    except Exception as e:
        logger.error(f"Failed to import PDK module {fullModuleName}: {e}")
        return None


def clearPDKModuleCache() -> None:
    """Clear the PDK module cache and remove stale PDK modules from sys.modules.

    Call when switching PDKs at runtime. This ensures that subsequent imports
    load the new PDK's modules fresh rather than returning stale cached objects.
    """
    # Determine the old PDK package name(s) from cached entries
    old_pdk_names = {pathlib.Path(path).name for path, _ in _module_cache.keys()}

    _module_cache.clear()

    # Also try to determine the current PDK name from environment before the switch
    # (the caller updates os.environ BEFORE calling this function)
    try:
        current_pdk = _get_pdk_path().name
    except (FileNotFoundError, Exception):
        current_pdk = None

    # Remove all modules belonging to old PDK packages from sys.modules
    # so that importlib.import_module() will do a fresh import
    keys_to_remove = []
    for mod_name in list(sys.modules.keys()):
        for pdk_name in old_pdk_names:
            if mod_name == pdk_name or mod_name.startswith(f"{pdk_name}."):
                keys_to_remove.append(mod_name)
                break

    for key in keys_to_remove:
        del sys.modules[key]

    # Invalidate import caches so Python's import machinery picks up new paths
    importlib.invalidate_caches()

    if keys_to_remove:
        logger.debug(
            f"PDK module cache cleared; removed {len(keys_to_remove)} entries "
            f"from sys.modules: {keys_to_remove}"
        )
    else:
        logger.debug("PDK module cache cleared")


class pdkConfig:
    def __init__(self, pdkPathObj):
        self_app = QApplication.instance()
        self.pdkPathObj = pdkPathObj
        self.pdkConfig = self._loadPDKConfig()

    def _loadPDKConfig(self):
        """Load PDK configuration from JSON file"""
        import json
        if not self.pdkPathObj.exists():
            return {}

        try:
            with open(self.pdkPathObj / "config.json") as f:
                config = json.load(f)
                return config
        except Exception as e:
            self._app.logger.warning(
                f"Failed to load plugin config for {item.name}: {e}")
            return {}

    def applyPDKMenus(self, editorWindow):
        if self.pdkConfig:
            editorClassName = editorWindow.__class__.__name__
            for menuItem in self.pdkConfig.get("menu_items", []):
                # Check applicability
                if "apply" in menuItem and editorClassName not in menuItem["apply"]:
                    continue
                # Get callback
                module = importPDKModule(menuItem["module"])
                if not module:
                    continue
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


def getPDKPath():
    """Get the resolved PDK path"""
    return _get_pdk_path()
