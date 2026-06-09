# SPDX-License-Identifier: MPL-2.0
#
# Copyright (c) 2024-2026 Revolution Semiconductor (Registered in the Netherlands)
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this file, You can obtain one at
# https://mozilla.org/MPL/2.0/.
#
# Add-ons and extensions developed for this software may be distributed
# under their own separate licenses.

# nuitka-project-if: {OS} == "Darwin":
#    nuitka-project: --standalone
#    nuitka-project: --macos-create-app-bundle
# nuitka-project: --standalone
# nuitka-project: --deployment
# nuitka-project: --windows-disable-console
# nuitka-project: --enable-plugin=pyside6
# nuitka-project: --enable-plugin=data-files
# nuitka-project: --include-data-dir=docs=docs
# nuitka-project: --include-data-file=revedaLogo.png=revedaLogo.png
# nuitka-project: --include-package=revedaEditor
# nuitka-project: --include-package=cryptography
# nuitka-project: --include-package=markdown
# nuitka-project: --include-package=polars
# nuitka-project: --include-module=pydoc
# nuitka-project: --include-package=cProfile
# nuitka-project: --include-package=profile
# nuitka-project: --include-package=xml
# nuitka-project: --include-package=certifi
# nuitka-project: --include-module=PySide6.QtWebEngineWidgets
# nuitka-project: --include-module=PySide6.QtOpenGL
# nuitka-project: --nofollow-import-to=unittest
# nuitka-project: --nofollow-import-to=pytest
# nuitka-project: --nofollow-import-to=revedasim
# nuitka-project: --nofollow-import-to=revedaPlot
# nuitka-project: --nofollow-import-to=plugins
# nuitka-project: --nofollow-import-to=revedaLicense
# nuitka-project: --include-package=defaultPDK
# nuitka-project: --include-package-data=defaultPDK
# nuitka-project: --include-windows-runtime-dlls=yes
# nuitka-project-if: {OS} == "Windows":
#    nuitka-project: --output-dir=C:\Users\eskiye50\dist
# nuitka-project-if: {OS} == "Linux":
#    nuitka-project: --output-dir=/home/eskiyerli/dist
# nuitka-project: --product-name="Revolution EDA"
# nuitka-project: --product-version="0.9.0"
# nuitka-project: --company-name="Revolution EDA"
# nuitka-project: --file-description="Electronic Design Automation Software for Professional Custom IC Design Engineers"
# nuitka-project: --windows-icon-from-ico=revedaCoreLogo.ico
# nuitka-project: --copyright="Revolution Semiconductor (C) 2026"

import argparse
import logging
import os
import platform
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from dotenv import load_dotenv

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen

import revedaEditor.gui.pythonConsole as pcon
import revedaEditor.gui.revedaMain as rvm
from revedaEditor.backend.pdkLoader import pdkConfig
from revedaEditor.backend.pluginsLoader import pluginsLoader


def _create_splash(project_name: str = "", base_path: Path | None = None) -> QSplashScreen:
    """Create a splash screen shown during project switching."""
    # Try to load the logo
    logo_pixmap = None
    if base_path is not None:
        logo_path = base_path / "revedaLogo.png"
        if logo_path.exists():
            logo_pixmap = QPixmap(str(logo_path))

    # Build the splash pixmap: white background, black text, logo on top
    width, height = 420, 200
    pixmap = QPixmap(width, height)
    pixmap.fill(QColor("#ffffff"))
    painter = QPainter(pixmap)

    # Draw logo centered at the top
    y_offset = 10
    if logo_pixmap and not logo_pixmap.isNull():
        # Scale logo to fit nicely (max 80px tall, keep aspect ratio)
        scaled_logo = logo_pixmap.scaledToHeight(80, Qt.SmoothTransformation)
        logo_x = (width - scaled_logo.width()) // 2
        painter.drawPixmap(logo_x, y_offset, scaled_logo)
        y_offset += scaled_logo.height() + 15
    else:
        y_offset = 60

    # Draw the loading message in black
    painter.setPen(QColor("#000000"))
    font = QFont("Segoe UI", 13)
    painter.setFont(font)
    text_rect = QRect(0, y_offset, width, height - y_offset)
    msg = f"Loading project: {project_name}..." if project_name else "Loading..."
    painter.drawText(text_rect, Qt.AlignHCenter | Qt.AlignTop, msg)
    painter.end()

    splash = QSplashScreen(pixmap)
    splash.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.SplashScreen)
    return splash


class revedaApp(QApplication):
    """Revolution EDA application with plugin support and path management."""

    # Exit code used to signal that the app should restart with a new project
    RESTART_EXIT_CODE = 99

    def __init__(self, *args, projectDir: Path | None = None, showSplash: bool = False,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.basePath = Path(__file__).resolve().parent
        self._projectDir = (projectDir if projectDir else Path.cwd()).resolve()
        self._splash = None

        # Show splash screen during initialization
        if showSplash:
            project_name = self._projectDir.name
            self._splash = _create_splash(project_name, self.basePath)
        else:
            self._splash = _create_splash("", self.basePath)
        self._splash.show()
        self.processEvents()

        # Load project-specific environment variables from .env if it exists
        project_env = self._projectDir / ".env"
        if project_env.exists():
            load_dotenv(project_env, override=True)
        else:
            # Fall back to base app .env
            self._ensureEnvFile()
            load_dotenv(self.basePath / ".env", override=True)

        self._setupLogger()
        self._setupPaths()  # Keep for initial defaults before project loads
        self.appMainW = rvm.MainWindow()
        # Load project from specified directory (handles .env, PDK, plugins, library, config)
        self.appMainW.projectManager.open_project(self._projectDir)
        # Refresh recent projects menu after initial project load
        self.appMainW._updateRecentProjectsMenu()

    def _ensureEnvFile(self):
        """Copy .env.example to .env on first run if .env doesn't exist."""
        env_file = self.basePath / ".env"
        if not env_file.exists():
            example_file = self.basePath / ".env.example"
            if example_file.exists():
                import shutil
                shutil.copy2(example_file, env_file)

    def _setupLogger(self):
        """Initialize application logger."""
        self.logger = logging.getLogger("reveda")
        logFilePath = Path.cwd() / "reveda.log"
        handler = logging.FileHandler(logFilePath)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        self.logger.addHandler(handler)

    def _setupPaths(self):
        pdkPath = os.environ.get("REVEDA_PDK_PATH")
        if pdkPath:
            path_obj = Path(pdkPath)
            self.revedaPdkPathObj = (
                path_obj if path_obj.is_absolute() else self._projectDir / pdkPath
            ).resolve()
            if self.revedaPdkPathObj.exists():
                sys.path.append(str(self.revedaPdkPathObj))
            else:
                self.revedaPdkPathObj = self.basePath / "defaultPDK"
                if self.revedaPdkPathObj.exists():
                    sys.path.append(str(self.revedaPdkPathObj))
                else:
                    self.logger.error("Default PDK path cannot be found.")
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
                path_obj if path_obj.is_absolute() else self._projectDir / pluginPath
            ).resolve()
        else:
            self.revedaPluginPathObj = (self.basePath / "plugins").resolve()

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
            self.update_env_file(
                "REVEDA_VA_MODULE_PATH", os.environ["REVEDA_VA_MODULE_PATH"]
            )
            self.logger.info(
                f"Central Verilog-A module repository path: {os.environ['REVEDA_VA_MODULE_PATH']}"
            )

    def update_env_file(self, key, value):
        """Update or add environment variable in .env file"""
        env_file = self._projectDir / ".env"
        lines = []

        # Read existing .env file if it exists
        if env_file.exists():
            with env_file.open("r") as f:
                lines = f.readlines()

        # Update or add the key-value pair
        keyFound = False
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{key}="):
                lines[i] = f"{key}={value}\n"
                keyFound = True
                break

        if not keyFound:
            lines.append(f"{key}={value}\n")

        # Write back to .env file
        with env_file.open("w") as f:
            f.writelines(lines)


def main():
    parser = argparse.ArgumentParser(description="Revolution EDA")
    parser.add_argument(
        "--project",
        type=str,
        default=None,
        help="Path to project directory to open on launch",
    )
    parser.add_argument(
        "--switching",
        action="store_true",
        help="Internal flag: show splash screen during project switch",
    )
    args, qt_args = parser.parse_known_args()

    # Determine project directory
    project_dir = Path(args.project).resolve() if args.project else None

    app = revedaApp([sys.argv[0]] + qt_args, projectDir=project_dir,
                    showSplash=args.switching)
    style_map = {"Windows": "Fusion", "Linux": "Fusion", "Darwin": "macOS"}
    style = style_map.get(platform.system())
    if style:
        app.setStyle(style)

    # Window title is now set by ProjectManager.open_project()
    console = app.appMainW.centralW.console
    with redirect_stdout(console), redirect_stderr(pcon.Redirect(console.errorwrite)):
        app.appMainW.show()
        # Dismiss splash once main window is visible
        if app._splash is not None:
            app._splash.finish(app.appMainW)
        exit_code = app.exec()

    # If exit code signals a restart, re-launch with the new project path
    if exit_code == revedaApp.RESTART_EXIT_CODE:
        new_project = os.environ.get("REVEDA_RESTART_PROJECT", "")
        # Determine how to restart the application.
        # For Nuitka standalone builds: sys.executable IS the compiled binary (e.g. reveda.exe)
        # For source runs: sys.executable is the Python interpreter
        executable = Path(sys.executable).absolute()
        is_python_interpreter = executable.stem.lower().startswith("python")
        if is_python_interpreter:
            # Running from source: need to pass the script path
            cmd = [str(executable), str(Path(__file__).resolve())]
        else:
            # Running as compiled binary (Nuitka): executable is the app itself
            cmd = [str(executable)]
        if new_project:
            cmd.extend(["--project", new_project])
        cmd.append("--switching")
        # Log the restart command for debugging
        logging.getLogger("reveda").info(f"Restarting with command: {cmd}")
        subprocess.Popen(cmd)
        os._exit(0)  # Hard exit to ensure process terminates immediately

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
