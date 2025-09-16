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
# nuitka-project-if: {OS} == "Darwin":
#    nuitka-project: --standalone
#    nuitka-project: --macos-create-app-bundle
# The PySide6 plugin covers qt-plugins
# nuitka-project: --standalone
# nuitka-project: --enable-plugin=pyside6
# nuitka-project: --nofollow-import-to=defaultPDK, gf180_pdk,
# nuitka-project: --include-data-dir=compiled_plugins=plugins
# nuitka-project: --output-dir=dist
# nuitka-project: --product-version="0.7.9"
# nuitka-project: --linux-icon=./logo-color.png
# nuitka-project: --windows-icon-from-ico=./logo-color.png
# nuitka-project: --company-name="Revolution EDA"
# nuitka-project: --file-description="Electronic Design Automation Software for Professional Custom IC Design Engineers"

# import time
import importlib
import os
import pkgutil
import platform
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Optional
import logging
from dotenv import load_dotenv
from PySide6.QtWidgets import QApplication

import revedaEditor.gui.pythonConsole as pcon
import revedaEditor.gui.revedaMain as rvm


class revedaApp(QApplication):
    """Revolution EDA application with plugin support and path management."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        load_dotenv()
        self.base_path = Path(__file__).resolve().parent
        self._setup_logger()
        self._setup_paths()
        self._setup_plugins()

    def _setup_logger(self):
        """Initialize application logger."""
        self.logger = logging.getLogger("reveda")
        if not self.logger.handlers:
            handler = logging.FileHandler("reveda.log")
            handler.setLevel(logging.INFO)
            handler.setFormatter(logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
            self.logger.addHandler(handler)

    def _setup_paths(self):
        """Setup application paths from environment variables."""
        pdk_path = os.environ.get("REVEDA_PDK_PATH")
        if pdk_path:
            path_obj = Path(pdk_path)
            self.revedaPdkPathObj = (path_obj if path_obj.is_absolute() else self.base_path / pdk_path).resolve()
            if self.revedaPdkPathObj.exists():
                sys.path.append(str(self.revedaPdkPathObj))
            else:
                self.revedaPdkPathObj = self.base_path / "defaultPDK"
                sys.path.append(str(self.revedaPdkPathObj))
        else:
            self.revedaPdkPathObj = self.base_path / "defaultPDK"
            sys.path.append(str(self.revedaPdkPathObj))

        plugin_path = os.environ.get("REVEDA_PLUGIN_PATH")
        if plugin_path:
            path_obj = Path(plugin_path)
            self.revedaPluginPathObj = (path_obj if path_obj.is_absolute() else self.base_path / plugin_path).resolve()
            if self.revedaPluginPathObj.exists():
                sys.path.append(str(self.revedaPluginPathObj))
            else:
                self.revedaPluginPathObj = self.base_path / "plugins"
                sys.path.append(str(self.revedaPluginPathObj))

        else:
            self.revedaPluginPathObj = self.base_path / "plugins"
            sys.path.append(str(self.revedaPluginPathObj))

    def _setup_plugins(self):
        """Discover and load plugins."""
        self.plugins = {}
        for _, name, _ in pkgutil.iter_modules([str(self.revedaPluginPathObj)]):
            self.logger.info(f"Found plugin: {name}")
            
            try:
                module = importlib.import_module(name)
                self.plugins[f"plugins.{name}"] = module
            except ImportError as e:
                self.logger.error(f"Failed to load plugin {name}: {e}")
                
        self.logger.info(f"Loaded plugins: {list(self.plugins.keys())}")


def initialize_app(argv) -> tuple[revedaApp, Optional[str]]:
    """Initialize application and determine style."""
    app = revedaApp(argv)
    style_map = {"Windows": "Fusion", "Linux": "Fusion", "Darwin": "macOS"}
    return app, style_map.get(platform.system())



def main():
    app, style = initialize_app(sys.argv)
    if style:
        app.setStyle(style)
        print(f"Applied {style} style")
    mainW = rvm.MainWindow()
    mainW.setWindowTitle("Revolution EDA")
    app.mainW = mainW
    console = mainW.centralW.console
    redirect = pcon.Redirect(console.errorwrite)
    with redirect_stdout(console), redirect_stderr(redirect):
        mainW.show()
        return app.exec()

if __name__ == "__main__":
    main()
