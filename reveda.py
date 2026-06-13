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
# nuitka-project: --windows-console-mode=disable
# nuitka-project: --enable-plugin=pyside6
# nuitka-project: --noinclude-qt-translations
# nuitka-project: --enable-plugin=data-files
# nuitka-project: --include-data-dir=docs=docs
# nuitka-project: --include-data-dir=revedaEditor/fileio/schemas=revedaEditor/fileio/schemas
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

# Add ~/.reveda/ to sys.path early so that the compiled revedaLicense module
# (installed there by the plugin registry) is discoverable before any module
# triggers `from revedaLicense.licenseManager import ...`.
_central_dir = str(Path.home() / ".reveda")
if _central_dir not in sys.path:
    sys.path.append(_central_dir)

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
    # Name of the central user-level directory for shared resources
    CENTRAL_DIR_NAME = ".reveda"

    def __init__(self, *args, projectDir: Path | None = None, showSplash: bool = False,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.basePath = Path(__file__).resolve().parent
        # For installed deployments, default to a writable user directory rather
        # than CWD (which may be System32, an AppImage mount point, etc.).
        if projectDir:
            self._projectDir = projectDir.resolve()
        else:
            self._projectDir = self._resolveDefaultProjectDir()

        # If the project directory doesn't exist, ask the user before creating it.
        if not self._projectDir.exists():
            self._projectDir = self._confirmOrPickProjectDir(self._projectDir)

        self._splash = None

        # Show splash screen during initialization
        if showSplash:
            project_name = self._projectDir.name
            self._splash = _create_splash(project_name, self.basePath)
        else:
            self._splash = _create_splash("", self.basePath)
        self._splash.show()
        self.processEvents()

        # Load environment variables with a clear priority chain:
        # 1. Project-specific .env (in the project directory)
        # 2. User-level .env (in ~/.reveda/)
        # 3. Bundled .env.example (in the install/base directory)
        project_env = self._projectDir / ".env"
        central_env = Path.home() / self.CENTRAL_DIR_NAME / ".env"
        if project_env.exists():
            load_dotenv(project_env, override=True)
        elif central_env.exists():
            load_dotenv(central_env, override=True)
        else:
            # Fall back to base app .env or .env.example
            self._ensureEnvFile()
            base_env = self.basePath / ".env"
            if base_env.exists():
                load_dotenv(base_env, override=True)
            else:
                example_env = self.basePath / ".env.example"
                if example_env.exists():
                    load_dotenv(example_env, override=True)

        self._setupLogger()
        self._setupPaths()  # Keep for initial defaults before project loads
        self.appMainW = rvm.MainWindow()
        # Load project from specified directory (handles .env, PDK, plugins, library, config)
        self.appMainW.projectManager.open_project(self._projectDir)
        # Refresh recent projects menu after initial project load
        self.appMainW._updateRecentProjectsMenu()

    def _resolveDefaultProjectDir(self) -> Path:
        """Determine a sensible default project directory.

        Priority:
        1. If CWD is writable, use it. This covers both development (running
           from the source tree) and 'cd my_project && reveda' workflows.
        2. Otherwise (read-only AppImage mount, system dirs) fall back to
           ~/reveda_projects/ as a stable writable default.
        """
        cwd = Path.cwd().resolve()

        # Check if CWD is writable
        try:
            test = cwd / ".reveda_write_test"
            test.touch()
            test.unlink()
            return cwd
        except OSError:
            return self._userProjectsDir()

    def _userProjectsDir(self) -> Path:
        """Return the default user projects directory path (without creating it).

        Creation is deferred to _confirmOrPickProjectDir so the user is asked first.
        """
        return Path.home() / "reveda_projects"

    def _confirmOrPickProjectDir(self, proposed: Path) -> Path:
        """Ask the user whether to create a non-existent project directory.

        Shows a dialog with three choices:
        - Create the proposed directory
        - Browse for an existing directory
        - Cancel (exits the application)

        Returns the confirmed/selected project directory (guaranteed to exist).
        """
        from PySide6.QtWidgets import QMessageBox, QFileDialog

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle("Project Directory")
        msg.setText(
            f"The project directory does not exist:\n\n{proposed}\n\n"
            f"Would you like to create it?"
        )
        create_btn = msg.addButton("Create", QMessageBox.AcceptRole)
        browse_btn = msg.addButton("Browse...", QMessageBox.ActionRole)
        cancel_btn = msg.addButton(QMessageBox.Cancel)
        msg.setDefaultButton(create_btn)
        msg.exec()

        clicked = msg.clickedButton()
        if clicked == create_btn:
            proposed.mkdir(parents=True, exist_ok=True)
            return proposed
        elif clicked == browse_btn:
            chosen = QFileDialog.getExistingDirectory(
                None, "Select Project Directory", str(Path.home())
            )
            if chosen:
                return Path(chosen).resolve()
            else:
                # User cancelled the browse dialog — exit gracefully
                sys.exit(0)
        else:
            # Cancel — exit gracefully
            sys.exit(0)

    def _ensureEnvFile(self):
        """Copy .env.example to .env on first run if .env doesn't exist."""
        env_file = self.basePath / ".env"
        if not env_file.exists():
            example_file = self.basePath / ".env.example"
            if example_file.exists():
                import shutil
                try:
                    shutil.copy2(example_file, env_file)
                except OSError as e:
                    # In read-only package layouts (like AppImage mount point), copying will fail.
                    # We log the warning and fallback gracefully to loading .env.example.
                    logger = logging.getLogger("reveda")
                    logger.warning(
                        f"Could not copy .env.example to .env at {env_file} (read-only filesystem?): {e}"
                    )

    def _getCentralDirectory(self) -> Path:
        """Return the platform-appropriate central directory path.

        Returns the path to the user-level central directory (~/.reveda/)
        used as the default shared location for the license module and plugins.
        """
        return Path.home() / self.CENTRAL_DIR_NAME

    def _ensureCentralDirectory(self) -> Path:
        """Create central directory and subdirectories if they don't exist.

        Creates the ~/.reveda/ directory structure including plugins/ subdirectory.
        The compiled license module (revedaLicense.pyd/.so) is installed directly
        in ~/.reveda/, not in a subdirectory.

        Returns:
            Path to the central directory.

        Raises:
            OSError: If directory creation fails (logged before raising).
        """
        logger = logging.getLogger("reveda")
        central_dir = self._getCentralDirectory()
        try:
            central_dir.mkdir(parents=True, exist_ok=True)
            (central_dir / "plugins").mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(
                f"Failed to create central directory structure at "
                f"{central_dir}: {e}"
            )
            raise
        return central_dir

    def _setupLicensePath(self, central_dir: Path) -> None:
        """Insert the appropriate path for revedaLicense into sys.path.

        ~/.reveda/ is always added to sys.path so that the revedaLicense module
        can be found there on every startup (including after it's downloaded
        at runtime via the plugin registry).

        If a source-relative revedaLicense/ directory exists (development mode),
        basePath is inserted with higher priority so the local copy wins.
        """
        logger = logging.getLogger("reveda")

        # Always add central directory to sys.path so revedaLicense
        # is discoverable there — even if downloaded later at runtime.
        # Append (not insert at 0) to avoid shadowing virtualenv packages
        # like cryptography whose Rust bindings won't resolve from ~/.reveda/.
        path_str = str(central_dir)
        if path_str not in sys.path:
            sys.path.append(path_str)

        # In development mode, source-relative takes higher priority
        source_relative = self.basePath / "revedaLicense"
        if source_relative.is_dir():
            base_str = str(self.basePath)
            if base_str not in sys.path:
                sys.path.insert(0, base_str)
            logger.debug(
                f"License path resolved from source-relative: {source_relative}"
            )
        else:
            logger.debug(
                f"License will be resolved from central directory: "
                f"{central_dir / 'revedaLicense'}"
            )

    def reloadLicenseModule(self) -> None:
        """Reload the revedaLicense module after installation.

        This should be called after the plugin registry installs the compiled
        revedaLicense module to ensure it's properly loaded and available.
        """
        import importlib
        
        logger = logging.getLogger("reveda")
        central_dir = self._getCentralDirectory()
        
        # Re-setup the license path
        self._setupLicensePath(central_dir)
        
        # Invalidate import caches
        importlib.invalidate_caches()
        
        # Reload the license manager module if it was already imported
        if "revedaEditor.backend.licenseManager" in sys.modules:
            importlib.reload(sys.modules["revedaEditor.backend.licenseManager"])
        
        logger.info("License module reloaded after installation")

    def _setupPluginPath(self, central_dir: Path) -> None:
        """Resolve and configure the plugin loading path.

        Priority:
        1. REVEDA_PLUGIN_PATH from .env or environment (non-empty)
        2. ~/.reveda/plugins/ (central directory default)

        If the resolved path exists, it is appended to sys.path and a
        pluginsLoader instance is created. Otherwise pluginsObj is set to None
        and a warning is logged.
        """
        logger = logging.getLogger("reveda")
        plugin_env = os.environ.get("REVEDA_PLUGIN_PATH")

        if plugin_env:
            # Environment variable is set and non-empty
            path_obj = Path(plugin_env).expanduser()
            self.revedaPluginPathObj = (
                path_obj if path_obj.is_absolute() else self._projectDir / plugin_env
            ).resolve()
        else:
            # Not set or empty string — fall back to central directory plugins
            self.revedaPluginPathObj = (central_dir / "plugins").resolve()

        if self.revedaPluginPathObj.exists():
            path_str = str(self.revedaPluginPathObj)
            if path_str not in sys.path:
                sys.path.append(path_str)
            self.pluginsObj = pluginsLoader(self.revedaPluginPathObj)
            logger.debug(f"Plugin path resolved: {self.revedaPluginPathObj}")
        else:
            self.pluginsObj = None
            logger.warning(
                f"Plugin path does not exist: {self.revedaPluginPathObj}. "
                f"Plugin loading skipped."
            )

    def _setupLogger(self):
        """Initialize application logger.

        Writes to the project directory if writable, otherwise to the central
        user directory (~/.reveda/). Never attempts to write to CWD directly,
        as it may be System32, an AppImage mount, or another read-only location.
        """
        self.logger = logging.getLogger("reveda")

        # Try project directory first, then central directory
        candidates = [
            self._projectDir / "reveda.log",
            Path.home() / self.CENTRAL_DIR_NAME / "reveda.log",
        ]

        for logFilePath in candidates:
            try:
                logFilePath.parent.mkdir(parents=True, exist_ok=True)
                handler = logging.FileHandler(logFilePath)
                handler.setLevel(logging.DEBUG)
                handler.setFormatter(
                    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
                )
                self.logger.addHandler(handler)
                return
            except OSError:
                continue

        # Fallback stream handler so the app never crashes due to logging permission errors
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logging.DEBUG)
        self.logger.addHandler(handler)

    def _setupPaths(self):
        """Orchestrates path resolution for PDK, license, and plugins."""
        # Ensure central directory exists and get its path
        central_dir = self._ensureCentralDirectory()

        # PDK path resolution:
        # - Absolute paths are used as-is.
        # - Relative paths are tried against project dir first, then basePath
        #   (the install directory where defaultPDK is bundled).
        pdkPath = os.environ.get("REVEDA_PDK_PATH")
        if pdkPath:
            path_obj = Path(pdkPath).expanduser()
            if path_obj.is_absolute():
                self.revedaPdkPathObj = path_obj.resolve()
            else:
                # Try relative to project directory first
                candidate = (self._projectDir / pdkPath).resolve()
                if candidate.exists():
                    self.revedaPdkPathObj = candidate
                else:
                    # Fall back to relative to basePath (install dir)
                    candidate = (self.basePath / pdkPath).resolve()
                    if candidate.exists():
                        self.revedaPdkPathObj = candidate
                    else:
                        self.revedaPdkPathObj = candidate  # will trigger error below
            if self.revedaPdkPathObj.exists():
                if str(self.revedaPdkPathObj) not in sys.path:
                    sys.path.append(str(self.revedaPdkPathObj))
            else:
                # Ultimate fallback: basePath/defaultPDK
                fallback = self.basePath / "defaultPDK"
                if fallback.exists():
                    self.revedaPdkPathObj = fallback
                    if str(fallback) not in sys.path:
                        sys.path.append(str(fallback))
                else:
                    self.logger.error(
                        f"PDK path not found: {self.revedaPdkPathObj}. "
                        f"Default PDK also not found at {fallback}."
                    )
        else:
            self.revedaPdkPathObj = self.basePath / "defaultPDK"
            if self.revedaPdkPathObj.exists():
                if str(self.revedaPdkPathObj) not in sys.path:
                    sys.path.append(str(self.revedaPdkPathObj))
            else:
                self.logger.error("Default PDK path cannot be found.")

        if self.revedaPdkPathObj.exists():
            self.pdkConfigObj = pdkConfig(self.revedaPdkPathObj)
        else:
            self.pdkConfigObj = None

        # License path resolution — delegate to helper
        self._setupLicensePath(central_dir)

        # Plugin path resolution — delegate to helper
        self._setupPluginPath(central_dir)

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
        
        # If writing to the base installation path (which is read-only in AppImage,
        # or shouldn't be polluted), fall back to writing to the user central .env.
        if (self._projectDir == self.basePath) or (env_file.parent == self.basePath):
            central_dir = Path.home() / self.CENTRAL_DIR_NAME
            try:
                central_dir.mkdir(parents=True, exist_ok=True)
                env_file = central_dir / ".env"
            except OSError:
                pass

        lines = []

        try:
            # Read existing .env file if it exists
            if env_file.exists():
                with env_file.open("r", encoding="utf-8") as f:
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
            with env_file.open("w", encoding="utf-8") as f:
                f.writelines(lines)
        except OSError as e:
            self.logger.warning(
                f"Could not persist setting '{key}={value}' to environment file at {env_file}: {e}"
            )


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
    project_dir = Path(args.project).expanduser().resolve() if args.project else None

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
        # Support AppImage, compiled standalone binaries, and source runs.
        appimage_path = os.environ.get("APPIMAGE")
        
        # Check if the application is compiled (Nuitka standalone defines sys.frozen or registers __compiled__)
        is_compiled = hasattr(sys, "frozen") or "__compiled__" in sys.modules
        
        executable = Path(sys.executable).absolute()
        
        # Nuitka standalone builds set sys.executable to a phantom path (e.g. .../reveda/python)
        # which does not actually exist. In standalone builds, sys.argv[0] contains the path of the
        # actual executable binary (such as reveda.bin).
        if is_compiled or not executable.exists() or not executable.is_absolute():
            # Try resolving from sys.argv[0] (which is the executed binary path in standalone mode)
            executable = Path(sys.argv[0]).absolute()
            
            # If sys.argv[0] is still not found/valid, try resolving sys.executable via PATH as fallback
            if not executable.exists():
                import shutil
                resolved = shutil.which(sys.executable)
                if resolved:
                    executable = Path(resolved).absolute()

        is_python_interpreter = executable.stem.lower().startswith("python")

        if appimage_path:
            # Running as AppImage: re-launch the .AppImage file itself (mount point is ephemeral)
            cmd = [appimage_path]
        elif is_python_interpreter:
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
