# SPDX-License-Identifier: MPL-2.0
#
# Copyright (c) 2024-2026 Revolution Semiconductor (Registered in the Netherlands)
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this file, You can obtain one at
# https://mozilla.org/MPL/2.0/.

"""
Project management for Revolution EDA.

Provides ProjectManager (orchestrates project loading, switching, and state persistence)
and RecentProjectsStore (QSettings-backed recent project tracking).
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import load_dotenv

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QMessageBox

if TYPE_CHECKING:
    from revedaEditor.gui.revedaMain import MainWindow


class RecentProjectsStore:
    """QSettings-backed persistence for recently opened project directories.

    Stores up to MAX_ENTRIES paths in an INI file under ~/.reveda/.
    Most recently opened project is always at index 0.
    """

    MAX_ENTRIES = 5
    SETTINGS_DIR = Path.home() / ".reveda"
    SETTINGS_FILE = SETTINGS_DIR / "reveda_settings.ini"

    def __init__(self):
        self.SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        self._settings = QSettings(str(self.SETTINGS_FILE), QSettings.IniFormat)
        self._projects: list[Path] = self._load()

    @property
    def projects(self) -> list[Path]:
        """Ordered list of recent project paths (most recent first)."""
        return list(self._projects)

    def add(self, project_dir: Path) -> None:
        """Add or promote a project to the top. Trims to MAX_ENTRIES."""
        resolved = project_dir.resolve()
        # Remove if already present (will be re-added at top)
        self._projects = [p for p in self._projects if p != resolved]
        self._projects.insert(0, resolved)
        # Enforce max entries
        self._projects = self._projects[: self.MAX_ENTRIES]
        self._save()

    def remove(self, project_dir: Path) -> None:
        """Remove an entry (e.g., when the directory no longer exists)."""
        resolved = project_dir.resolve()
        self._projects = [p for p in self._projects if p != resolved]
        self._save()

    def _load(self) -> list[Path]:
        """Load from QSettings."""
        raw = self._settings.value("recentProjects", [])
        if raw is None:
            return []
        if isinstance(raw, str):
            # QSettings may return a single string instead of a list
            return [Path(raw)] if raw else []
        return [Path(p) for p in raw if p]

    def _save(self) -> None:
        """Persist to QSettings."""
        self._settings.setValue(
            "recentProjects", [str(p) for p in self._projects]
        )
        self._settings.sync()


class ProjectManager:
    """Orchestrates project loading, switching, and state persistence.

    Mediates between the GUI (MainWindow) and filesystem (project configuration
    files). On project open, it saves the current state, validates the target
    directory, loads configuration files, and updates the recent projects list.
    """

    MAX_RECENT_PROJECTS = 5
    SETTINGS_KEY = "recentProjects"

    def __init__(self, main_window: "MainWindow"):
        self._main_window = main_window
        self._app = QApplication.instance()
        self._active_project: Path | None = None
        self._recent_store = RecentProjectsStore()
        self._logger = logging.getLogger("reveda")

    @property
    def active_project(self) -> Path | None:
        """The currently active project directory, or None if no project is open."""
        return self._active_project

    def open_project(self, project_dir: Path) -> bool:
        """Open a project directory. Returns True on success, False on failure.

        Orchestrates save-current → validate → load sequence.
        """
        # 1. Validate directory
        project_dir = project_dir.resolve()
        if not project_dir.is_dir() or not os.access(project_dir, os.R_OK):
            QMessageBox.critical(
                self._main_window,
                "Open Project",
                f"Cannot open project: directory '{project_dir}' does not exist "
                f"or is not readable.",
            )
            return False

        # 2. Save current project state if switching
        if self._active_project is not None:
            self.save_current_state()

        # 3. Load .env (copies template if missing)
        self._load_env(project_dir)

        # 4. Resolve paths
        pdk_path = self._resolve_pdk_path(project_dir)
        plugin_path = self._resolve_plugin_path(project_dir)

        # 5. Update app paths (adds to sys.path, reinits PDK/plugins)
        self._app.updatePDKPath(pdk_path)
        if plugin_path is not None:
            self._app.updatePluginsPath(str(plugin_path))

        # 6. Load library definitions
        self._main_window.libraryDict = self._load_library_json(project_dir)

        # 7. Load and apply reveda.conf state
        conf = self._load_reveda_conf(project_dir)
        self._apply_state(conf)

        # 8. Update active project
        self._active_project = project_dir

        # 9. Update recent projects store
        self._recent_store.add(project_dir)

        # 10. Update window title
        self._main_window.setWindowTitle(f"Revolution EDA - {project_dir.name}")

        self._logger.info(f"Opened project: {project_dir}")
        return True

    def switch_project(self, project_dir: Path) -> None:
        """Switch to a different project by restarting the application.

        Saves current state, validates the target directory, records it in recent
        projects, and triggers an application restart with --project pointing to the
        new directory.
        """
        project_dir = project_dir.resolve()
        if not project_dir.is_dir() or not os.access(project_dir, os.R_OK):
            QMessageBox.critical(
                self._main_window,
                "Open Project",
                f"Cannot open project: directory '{project_dir}' does not exist "
                f"or is not readable.",
            )
            return

        # Save current project state before switching
        self.save_current_state()

        # Record in recent projects so it shows up after restart
        self._recent_store.add(project_dir)

        # Signal the restart loop with the target project path
        os.environ["REVEDA_RESTART_PROJECT"] = str(project_dir)

        # Mark the window so closeEvent skips the confirmation dialog
        self._main_window._restartingForProjectSwitch = True

        # Exit with the restart code
        app = QApplication.instance()
        app.exit(app.RESTART_EXIT_CODE)

    def save_current_state(self) -> bool:
        """Save application state to reveda.conf in the active project directory.

        Returns True if save succeeded or no active project, False on I/O failure.
        """
        if self._active_project is None:
            return True

        items = {
            "runPath": str(self._main_window.runPath),
            "pdkPath": str(self._main_window.pdkPath),
            "outputPrefixPath": str(self._main_window.outputPrefixPath),
            "switchViewList": self._main_window.switchViewList,
            "stopViewList": self._main_window.stopViewList,
            "windowGeometry": [
                self._main_window.x(),
                self._main_window.y(),
                self._main_window.width(),
                self._main_window.height(),
            ],
            "threadPoolMaxCount": self._main_window.threadPool.maxThreadCount(),
        }

        conf_file = self._active_project / "reveda.conf"
        try:
            with conf_file.open(mode="w", encoding="utf-8") as f:
                json.dump(items, f, indent=4)
        except (IOError, OSError) as e:
            self._logger.error(f"Failed to save project state to {conf_file}: {e}")
            QMessageBox.warning(
                self._main_window,
                "Save Error",
                f"Failed to save project configuration:\n{e}",
            )
            return False

        return True

    def _load_env(self, project_dir: Path) -> None:
        """Load .env from project_dir, copying template if needed."""
        env_file = project_dir / ".env"
        if not env_file.exists():
            self._copy_env_template(project_dir)
        if env_file.exists():
            load_dotenv(env_file, override=True)

    def _load_library_json(self, project_dir: Path) -> dict:
        """Load library.json, return library dict. Returns {} on failure."""
        lib_file = project_dir / "library.json"
        return self._read_lib_def_file(lib_file)

    def _read_lib_def_file(self, lib_file: Path) -> dict:
        """Read a library definition file and return a dict mapping names to Paths.

        Handles both 'libdefs' and 'include' formats. Returns {} on failure.
        """
        if not lib_file.exists():
            return {}

        try:
            with lib_file.open(mode="r") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            self._logger.error(f"Malformed library.json at {lib_file}: {e}")
            return {}
        except IOError as e:
            self._logger.error(f"Failed to read library.json at {lib_file}: {e}")
            return {}

        library_dict = {}
        if data.get("libdefs") is not None:
            library_dict = {key: Path(value) for key, value in data["libdefs"].items()}
        elif data.get("include") is not None:
            for item in data["include"]:
                library_dict.update(self._read_lib_def_file(Path(item)))
        return library_dict

    def _load_reveda_conf(self, project_dir: Path) -> dict:
        """Load reveda.conf, return settings dict. Returns {} on failure."""
        conf_file = project_dir / "reveda.conf"
        if not conf_file.exists():
            return {}
        try:
            with conf_file.open(mode="r") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            self._logger.error(f"Malformed reveda.conf at {conf_file}: {e}")
            return {}
        except IOError as e:
            self._logger.error(f"Failed to read reveda.conf at {conf_file}: {e}")
            return {}

    def _resolve_pdk_path(self, project_dir: Path) -> Path:
        """Resolve REVEDA_PDK_PATH to absolute, fall back to defaultPDK."""
        default_pdk = self._app.basePath / "defaultPDK"
        pdk_path = os.environ.get("REVEDA_PDK_PATH")
        if not pdk_path:
            return default_pdk

        resolved = Path(pdk_path)
        if not resolved.is_absolute():
            resolved = (project_dir / pdk_path).resolve()

        if not resolved.exists():
            self._logger.warning(
                f"PDK path '{resolved}' not found, falling back to defaultPDK"
            )
            return default_pdk

        return resolved

    def _resolve_plugin_path(self, project_dir: Path) -> Path | None:
        """Resolve REVEDA_PLUGIN_PATH to absolute."""
        plugin_path = os.environ.get("REVEDA_PLUGIN_PATH")
        if not plugin_path:
            default_plugins = self._app.basePath / "plugins"
            return default_plugins if default_plugins.exists() else None

        resolved = Path(plugin_path)
        if not resolved.is_absolute():
            resolved = (project_dir / plugin_path).resolve()

        if not resolved.exists():
            return None

        return resolved

    def _copy_env_template(self, project_dir: Path) -> bool:
        """Copy .env.example from app install dir to project_dir/.env.

        Returns True on success, False on failure.
        """
        template = self._app.basePath / ".env.example"
        destination = project_dir / ".env"

        if not template.exists():
            self._logger.warning(
                f"Template file not found: {template}"
            )
            return False

        try:
            shutil.copy2(template, destination)
        except OSError as e:
            self._logger.warning(
                f"Failed to copy .env template to {destination}: {e}"
            )
            return False

        return True

    def _apply_state(self, conf: dict) -> None:
        """Apply loaded reveda.conf settings to MainWindow attributes."""
        if not conf:
            return

        # Update path fields
        for attr in ("runPath", "pdkPath", "outputPrefixPath"):
            setattr(
                self._main_window,
                attr,
                Path(conf.get(attr, getattr(self._main_window, attr))),
            )

        # Update list fields only if non-empty and first element is not ""
        for attr in ("switchViewList", "stopViewList"):
            value = conf.get(attr, [""])
            if value and value[0] != "":
                setattr(self._main_window, attr, value)

        # Restore window geometry
        if "windowGeometry" in conf:
            geom = conf["windowGeometry"]
            if isinstance(geom, list) and len(geom) == 4:
                self._main_window.setGeometry(*geom)

        # Restore thread pool settings
        if "threadPoolMaxCount" in conf:
            self._main_window.threadPool.setMaxThreadCount(
                conf["threadPoolMaxCount"]
            )
