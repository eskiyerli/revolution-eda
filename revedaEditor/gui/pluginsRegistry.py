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

# revedaEditor/gui/plugin_registry.py
from unittest.mock import DEFAULT
import json
import os
import platform
import re
import shutil
import sys
import tarfile
import tempfile
import threading
import urllib.request
import zipfile
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
                               QMainWindow, QMessageBox, QPushButton, QProgressBar,
                               QTextEdit, QVBoxLayout, QWidget, QHeaderView)


class _DownloadWorker(QObject):
    progress = Signal(int)
    finished = Signal(str, dict)
    error = Signal(str)

    def __init__(self, url: str, target_dir: Path, name: str, entry: dict):
        super().__init__()
        self.url = url
        self.target_dir = target_dir
        self.name = name
        self.entry = entry

    def run(self):
        try:
            # Handle OS-specific binary downloads
            url = self._get_os_specific_url()
            with urllib.request.urlopen(url) as resp:
                if getattr(resp, "status", 200) != 200:
                    raise RuntimeError(f"HTTP {getattr(resp, 'status', '??')}")
                tmp_fd, tmp_path = tempfile.mkstemp()
                os.close(tmp_fd)
                downloaded = 0
                total = getattr(resp, "length", 0) or 0
                with open(tmp_path, "wb") as out:
                    chunk_size = 32 * 1024
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        out.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            pct = int(downloaded * 100 / total)
                            self.progress.emit(pct)

            self.target_dir.mkdir(parents=True, exist_ok=True)
            dest = self.target_dir / self.name
            lower = self.url.lower()
            try:
                if lower.endswith(".tar.gz") or lower.endswith(".tgz") or tarfile.is_tarfile(tmp_path):
                    with tarfile.open(tmp_path, "r:*") as tf:
                        self._safe_extract_tar(tf, self.target_dir)
                    result = f"Extracted archive to {self.target_dir}"
                elif lower.endswith(".zip") or zipfile.is_zipfile(tmp_path):
                    with zipfile.ZipFile(tmp_path, "r") as zf:
                        self._safe_extract_zip(zf, self.target_dir)
                    result = f"Extracted zip to {self.target_dir}"
                else:
                    # single file -> place inside plugin subdir
                    if not dest.exists():
                        dest.mkdir(parents=True, exist_ok=True)
                    file_name = Path(self.url).name or "plugin.py"
                    (dest / file_name).write_bytes(Path(tmp_path).read_bytes())
                    result = f"Saved plugin to {dest}"
            finally:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

            self.progress.emit(100)
            self.finished.emit(result, self.entry)
        except Exception as exc:
            self.error.emit(str(exc))

    def _safe_extract_tar(self, tar: tarfile.TarFile, target: Path):
        for member in tar.getmembers():
            member_path = target / member.name
            if not self._is_within_directory(target, member_path):
                raise RuntimeError("Attempted Path Traversal in tar file")
        tar.extractall(path=target)

    def _safe_extract_zip(self, zipf: zipfile.ZipFile, target: Path):
        for member in zipf.namelist():
            member_path = target / member
            if not self._is_within_directory(target, member_path):
                raise RuntimeError("Attempted Path Traversal in zip file")
        zipf.extractall(path=target)

    def _get_os_specific_url(self) -> str:
        """Get OS-specific URL for binary plugins with Python version support"""
        plugin_type = self.entry.get("type", "source")
        if plugin_type != "binary":
            return self.url

        binary_urls = self.entry.get("binary_urls", {})
        print('binary_urls:', binary_urls)
        if not binary_urls:
            return self.url
        
        system = platform.system().lower()
        arch = platform.machine().lower()
        py_ver = f"py{sys.version_info.major}{sys.version_info.minor}"
        
        # Try system-arch-pyversion first (most specific)
        key = f"{system}-{arch}-{py_ver}"
        print('key:', key)
        if key in binary_urls:
            return binary_urls[key]
        
        # Try name-system-arch combination
        key = f"{system}-{arch}"
        if key in binary_urls:
            return binary_urls[key]
        
        # Fall back to system only
        if system in binary_urls:
            return binary_urls[system]
        
        # Default fallback
        return self.url
    
    @staticmethod
    def _is_within_directory(directory: Path, target: Path) -> bool:
        try:
            directory = directory.resolve()
            target = target.resolve()
            return str(target).startswith(str(directory))
        except Exception:
            return False


class PluginRegistryWindow(QMainWindow):
    DEFAULT_REGISTRY = "https://raw.githubusercontent.com/eskiyerli/revolutionEDA_plugins/main/plugins.json"
    #DEFAULT_REGISTRY = "file://" + str(Path(__file__).parent.parent.parent / "plugins.json")

    def __init__(self, parent=None, registry_url: str | None = None, plugins_dir: Path | None = None):
        super().__init__(parent)
        self.setWindowTitle("Revolution EDA Plugin Registry")
        self.resize(800, 400)

        self.registry_url = registry_url or self.DEFAULT_REGISTRY
        self.registry_path = Path(self.registry_url.replace("file://", ""))
        self.pluginsDir = (Path(os.environ.get("REVEDA_PLUGIN_PATH")) if os.environ.get("REVEDA_PLUGIN_PATH")
                            else (plugins_dir or Path.cwd() / "plugins"))
        self.pluginsDir = self.pluginsDir.resolve()

        self._initUI()
        self._registry = []
        self.fetch_registry()

    def _initUI(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_l = QHBoxLayout(central)

        left_w = QWidget()
        left_l = QVBoxLayout(left_w)
        left_l.setContentsMargins(0, 0, 0, 0)
        self.tableWidget = QTableWidget()
        self.tableWidget.setColumnCount(5)
        self.tableWidget.setHorizontalHeaderLabels(["  Plugin  ", "Type", "Version", "Downloads", "License"])
        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tableWidget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tableWidget.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        left_l.addWidget(QLabel("Available plugins:"))
        left_l.addWidget(self.tableWidget)
        self.refresh_btn = QPushButton("Refresh")
        left_l.addWidget(self.refresh_btn)
        main_l.addWidget(left_w, 2)

        right_w = QWidget()
        right_l = QVBoxLayout(right_w)
        right_l.setContentsMargins(0, 0, 0, 0)
        right_l.addWidget(QLabel("Description:"))
        self.desc = QTextEdit()
        self.desc.setReadOnly(True)
        right_l.addWidget(self.desc, 1)
        self.download_btn = QPushButton("Download / Install")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        right_l.addWidget(self.progress)
        right_l.addWidget(self.download_btn)
        main_l.addWidget(right_w, 2)

        self.tableWidget.itemSelectionChanged.connect(self._onSelect)
        # activate item (double-click) to prompt and install only that plugin
        self.tableWidget.itemDoubleClicked.connect(self._on_item_activated)
        self.download_btn.clicked.connect(self._on_download)
        self.refresh_btn.clicked.connect(self.fetch_registry)

    def fetch_registry(self):
        self.tableWidget.setRowCount(0)
        self.desc.clear()
        self.progress.setValue(0)
        try:
            with urllib.request.urlopen(self.registry_url) as resp:
                raw = resp.read()
                index = json.loads(raw.decode("utf-8"))
                if isinstance(index, dict) and "plugins" in index:
                    index = index["plugins"]
                self._registry = index if isinstance(index, list) else []
        except Exception as exc:
            QMessageBox.warning(self, "Registry Error", f"Failed to fetch registry:\n{exc}")
            self._registry = []

        self.tableWidget.setRowCount(len(self._registry))
        for row, entry in enumerate(self._registry):
            name = entry.get("name", entry.get("id", entry.get("url", "unknown")))
            registry_version = entry.get("version", "0.0.0")
            downloads = entry.get("downloads", 0)
            
            # Check if installed and version
            plugin_dir = self.pluginsDir / re.sub(r"[^A-Za-z0-9_.-]", "_", name)
            if plugin_dir.exists():
                config_path = plugin_dir / "config.json"
                installed_version = "0.0.0"
                if config_path.exists():
                    try:
                        with open(config_path, "r") as f:
                            config = json.load(f)
                            installed_version = config.get("plugin_version", "0.0.0")
                    except Exception:
                        pass
                if installed_version < registry_version:
                    name += " (Update available)"
                else:
                    name += " (Installed)"
            
            # Plugin name
            item = QTableWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, entry)
            self.tableWidget.setItem(row, 0, item)
            
            # Type
            plugin_type = entry.get("type", "source")
            type_item = QTableWidgetItem(plugin_type.title())
            self.tableWidget.setItem(row, 1, type_item)
            
            # Version
            version_item = QTableWidgetItem(registry_version)
            self.tableWidget.setItem(row, 2, version_item)
            
            # Downloads
            downloads_item = QTableWidgetItem(str(downloads))
            self.tableWidget.setItem(row, 3, downloads_item)
            
            # License
            license = entry.get("license", "Unknown")
            license_item = QTableWidgetItem(license)
            self.tableWidget.setItem(row, 4, license_item)

    def _save_registry(self):
        try:
            data = {"plugins": self._registry}
            with open(self.registry_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "Save Error", f"Failed to save registry: {e}")

    def _onSelect(self):
        self.desc.clear()
        current_row = self.tableWidget.currentRow()
        if current_row < 0:
            return
        item = self.tableWidget.item(current_row, 0)
        if not item:
            return
        entry = item.data(Qt.ItemDataRole.UserRole) or {}
        text = entry.get("description", "") + "\n\n" + f"Type: {entry.get('type', 'source').title()}\n" + f"Version: {entry.get('version', 'N/A')}\n" + f"Downloads: {entry.get('downloads', 0)}\n" + f"License: {entry.get('license', 'Unknown')}\n" + f"URL: {entry.get('url','')}"
        
        # Show binary URLs if available
        if entry.get("type") == "binary" and entry.get("binary_urls"):
            text += "\n\nBinary URLs:"
            for platform_key, url in entry.get("binary_urls", {}).items():
                text += f"\n  {platform_key}: {url}"
        
        # Check installed version
        name = entry.get("name", entry.get("id", entry.get("url", "unknown")))
        plugin_dir = self.pluginsDir / re.sub(r"[^A-Za-z0-9_.-]", "_", name)
        if plugin_dir.exists():
            config_path = plugin_dir / "config.json"
            installed_version = "Unknown"
            if config_path.exists():
                try:
                    with open(config_path, "r") as f:
                        config = json.load(f)
                        installed_version = config.get("plugin_version", "Unknown")
                except Exception:
                    pass
            text += f"\nInstalled Version: {installed_version}"
        
        self.desc.setPlainText(text)

    def _on_item_activated(self, item: QTableWidgetItem):
        entry = item.data(Qt.ItemDataRole.UserRole) or {}
        name = entry.get("name") or Path(entry.get("url", "")).stem or "plugin"
        ret = QMessageBox.question(self, "Install Plugin", f"Install plugin \"{name}\"?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret != QMessageBox.StandardButton.Yes:
            return
        self._install_entry(entry)

    def _on_download(self):
        current_row = self.tableWidget.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "No selection", "Please select a plugin first.")
            return
        item = self.tableWidget.item(current_row, 0)
        if not item:
            return
        entry = item.data(Qt.ItemDataRole.UserRole) or {}
        ret = QMessageBox.question(self, "Install Plugin", f"Download and install plugin \"{entry.get('name','') or Path(entry.get('url','')).stem}\"?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret != QMessageBox.StandardButton.Yes:
            return
        self._install_entry(entry)

    def _install_entry(self, entry: dict):
        plugin_type = entry.get("type", "source")
        url = entry.get("url")
        
        # For binary plugins, check if OS-specific URL exists
        if plugin_type == "binary":
            binary_urls = entry.get("binary_urls", {})
            if binary_urls:
                system = platform.system().lower()
                arch = platform.machine().lower()
                key = f"{system}-{arch}"
                if key not in binary_urls and system not in binary_urls:
                    QMessageBox.warning(self, "Unsupported Platform", 
                                       f"Binary plugin not available for {system}-{arch}")
                    return
        
        if not url:
            QMessageBox.warning(self, "Invalid entry", "Selected plugin has no URL.")
            return

        # sanitize name to prevent path components
        raw_name = entry.get("name") or Path(url).stem or "plugin"
        name = re.sub(r"[^A-Za-z0-9_.-]", "_", raw_name)

        target_subdir = self.pluginsDir / name
        if target_subdir.exists():
            ok = QMessageBox.question(self, "Overwrite", f"{target_subdir} already exists. Overwrite?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ok != QMessageBox.StandardButton.Yes:
                return
            try:
                if target_subdir.is_dir():
                    shutil.rmtree(target_subdir)
                else:
                    target_subdir.unlink()
            except Exception as e:
                QMessageBox.warning(self, "Remove failed", f"Failed to remove existing path:\n{e}")
                return

        self.pluginsDir.mkdir(parents=True, exist_ok=True)
        self.download_btn.setEnabled(False)
        worker = _DownloadWorker(url, self.pluginsDir, name, entry)

        def on_progress(p):
            self.progress.setValue(p)

        def on_finished(msg, entry):
            self.download_btn.setEnabled(True)
            self.progress.setValue(100)
            QMessageBox.information(self, "Done", msg)
            # Increment download count
            entry["downloads"] = entry.get("downloads", 0) + 1
            self._save_registry()

        def on_error(e):
            self.download_btn.setEnabled(True)
            QMessageBox.critical(self, "Download error", e)

        worker.progress.connect(on_progress)
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)

        worker_thread = threading.Thread(target=worker.run, daemon=True)
        worker_thread.start()
