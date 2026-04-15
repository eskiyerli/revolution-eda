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
#    Add-ons and extensions developed for this software may be distributed
#    under their own separate licenses.
#
#    Software: Revolution EDA
#    License: Mozilla Public License 2.0
#    Licensor: Revolution Semiconductor (Registered in the Netherlands)
#
import importlib
import logging
import os
import pathlib
import sys
from types import ModuleType

from PySide6.QtGui import (QAction, QIcon)
from PySide6.QtWidgets import QApplication
from dotenv import load_dotenv

load_dotenv()

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
    """Clear the PDK module cache. Call when switching PDKs at runtime."""
    _module_cache.clear()
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
