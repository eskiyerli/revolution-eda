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
# nuitka-project: --deployment
# nuitka-project: --enable-plugin=pyside6
# nuitka-project: --include-data-dir=docs=docs
# nuitka-project: --include-package=revedaEditor
# nuitka-project: --include-package=markdown
# nuitka-project: --include-package=polars
# nuitka-project: --include-module=pydoc
# nuitka-project: --include-package=xml
# nuitka-project: --include-package=pyqtgraph
# nuitka-project: --include-module=PySide6.QtWebEngineWidgets
# nuitka-project: --include-module=PySide6.QtOpenGL
# nuitka-project: --nofollow-import-to=unittest
# nuitka-project: --nofollow-import-to=pytest
# nuitka-project: --nofollow-import-to=revedasim
# nuitka-project: --nofollow-import-to=revedaPlot
# nuitka-project: --nofollow-import-to=plugins
# nuitka-project: --nofollow-import-to=defaultPDK
# nuitka-project: --include-package-data=defaultPDK
# nuitka-project: --include-data-files=.env=.env
# nuitka-project-if: {OS} == "Windows":
#    nuitka-project: --output-dir=C:\Users\eskiye50\dist
# nuitka-project-if: {OS} == "Linux":
#    nuitka-project: --output-dir=/home/eskiyerli/dist
# nuitka-project: --product-name="Revolution EDA"
# nuitka-project: --product-version="0.8.7"
# nuitka-project: --company-name="Revolution EDA"
# nuitka-project: --file-description="Electronic Design Automation Software for Professional Custom IC Design Engineers"
# nuitka-project: --copyright="Revolution Semiconductor (C) 2025"

import logging
import os
import platform
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from PySide6.QtWidgets import QApplication
from dotenv import load_dotenv

import revedaEditor.gui.pythonConsole as pcon
import revedaEditor.gui.revedaMain as rvm
from revedaEditor.backend.pdkLoader import pdkConfig
from revedaEditor.backend.pluginsLoader import pluginsLoader


class revedaApp(QApplication):
    """Revolution EDA application with plugin support and path management."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.basePath = Path(__file__).resolve().parent
        load_dotenv()
        self._setupLogger()
        # self.appMainW = rvm.MainWindow()

        self._setupPaths()
        self.appMainW = rvm.MainWindow()

    def _setupLogger(self):
        """Initialize application logger."""
        self.logger = logging.getLogger("reveda")
        logFilePath = self.basePath / "reveda.log"
        handler = logging.FileHandler(logFilePath)
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        self.logger.addHandler(handler)

    def _setupPaths(self):
        pdkPath = os.environ.get("REVEDA_PDK_PATH")
        if pdkPath:
            path_obj = Path(pdkPath)
            self.revedaPdkPathObj = (
                path_obj if path_obj.is_absolute() else self.basePath / pdkPath).resolve()
            if self.revedaPdkPathObj.exists():
                sys.path.append(str(self.revedaPdkPathObj))
            else:
                self.revedaPdkPathObj = self.basePath / "defaultPDK"
                if self.revedaPdkPathObj.exists():
                    sys.path.append(str(self.revedaPdkPathObj))
                else:
                    self.logger.error('Default PDK path cannot be found.')
        else:
            self.revedaPdkPathObj = self.basePath / "defaultPDK"
            if self.revedaPdkPathObj.exists():
                sys.path.append(str(self.revedaPdkPathObj))
        if self.revedaPdkPathObj.exists():
            self.pdkConfigObj = pdkConfig(self.revedaPdkPathObj)
        else:
            self.pdkConfigObj = None

        pluginPath = os.environ.get("REVEDA_PLUGIN_PATH")
        if pluginPath:
            path_obj = Path(pluginPath)
            self.revedaPluginPathObj = (
                path_obj if path_obj.is_absolute() else self.basePath / pluginPath).resolve()
            if self.revedaPluginPathObj.exists():
                sys.path.append(str(self.revedaPluginPathObj))
                self.pluginsObj = pluginsLoader(self.revedaPluginPathObj)
        else:
            self.pluginsObj = None

    def updatePDKPath(self, newPath: Path):
        """Update PDK path and persist to .env file"""
        self.revedaPdkPathObj = newPath.resolve()

        # Update environment variable
        os.environ["REVEDA_PDK_PATH"] = str(self.revedaPdkPathObj)

        # Update sys.path
        if str(self.revedaPdkPathObj) not in sys.path:
            sys.path.append(str(self.revedaPdkPathObj))

        # Persist to .env file
        self.update_env_file("REVEDA_PDK_PATH", str(self.revedaPdkPathObj))

        self.logger.info(f"PDK path updated to: {self.revedaPdkPathObj}")

    def updatePluginsPath(self, newPath: str):
        """Update plugin path and persist to .env file"""
        if newPath:
            self.revedaPluginPathObj = Path(newPath).resolve()
            # Update environment variable
            os.environ["REVEDA_PLUGIN_PATH"] = str(self.revedaPluginPathObj)
            self.pluginsObj = pluginsLoader(self.revedaPluginPathObj)
            # Update sys.path
            if str(self.revedaPluginPathObj) not in sys.path:
                sys.path.append(str(self.revedaPluginPathObj))

            # Persist to .env file
            self.update_env_file("REVEDA_PLUGIN_PATH", str(self.revedaPluginPathObj))
            self.logger.info(f"Plugin path updated to: {self.revedaPluginPathObj}")

    def updateVaModulesPath(self, newPath: str):
        """Update plugin path and persist to .env file"""
        if newPath:
            # Update environment variable
            os.environ["REVEDA_VA_MODULE_PATH"] = str(Path(newPath).resolve())

            # Persist to .env file
            self.update_env_file("REVEDA_VA_MODULE_PATH",
                                 os.environ["REVEDA_VA_MODULE_PATH"])
            self.logger.info(
                f"Central Verilog-A module repository path: {os.environ["REVEDA_VA_MODULE_PATH"]}")

    def update_env_file(self, key, value):
        """Update or add environment variable in .env file"""
        env_file = self.basePath / ".env"
        lines = []

        # Read existing .env file if it exists
        if env_file.exists():
            with env_file.open('r') as f:
                lines = f.readlines()

        # Update or add the key-value pair
        key_found = False
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{key}="):
                lines[i] = f"{key}={value}\n"
                key_found = True
                break

        if not key_found:
            lines.append(f"{key}={value}\n")

        # Write back to .env file
        with env_file.open('w') as f:
            f.writelines(lines)


def main():
    app = revedaApp(sys.argv)
    style_map = {"Windows": "Fusion", "Linux": "Fusion", "Darwin": "macOS"}
    style = style_map.get(platform.system())
    if style:
        app.setStyle(style)
        print(f"Applied {style} style")
    mainW = app.appMainW
    mainW.setWindowTitle("Revolution EDA")
    app.mainW = mainW
    console = mainW.centralW.console
    redirect = pcon.Redirect(console.errorwrite)
    with redirect_stdout(console), redirect_stderr(redirect):
        mainW.show()
        return app.exec()


if __name__ == "__main__":
    main()
