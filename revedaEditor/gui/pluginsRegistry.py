#    "Commons Clause" License Condition v1.0
#
#    Software: Revolution EDA
#    License: Mozilla Public License 2.0
#    Licensor: Revolution Semiconductor (Registered in the Netherlands)

import json
import os
import platform
import re
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
                               QMainWindow, QMessageBox, QPushButton, QProgressBar,
                               QTextEdit, QVBoxLayout, QWidget, QHeaderView)


class PluginRegistryWindow(QMainWindow):
    DEFAULT_REGISTRY = "https://raw.githubusercontent.com/eskiyerli/revolutionEDA_plugins/main/plugins.json"

    def __init__(self, parent=None, registry_url: str | None = None,
                 plugins_dir: Path | None = None):
        super().__init__(parent)
        self.setWindowTitle("Revolution EDA Plugin Registry")
        self.resize(800, 400)

        self.registry_url = registry_url or self.DEFAULT_REGISTRY
        self.pluginsDir = (Path(os.environ.get("REVEDA_PLUGIN_PATH")) if os.environ.get(
            "REVEDA_PLUGIN_PATH") else (plugins_dir or Path.cwd() / "plugins"))
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
        self.tableWidget.setHorizontalHeaderLabels(
            ["Installed", "Plugin", "Type", "Version", "License"])
        self.tableWidget.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
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
        self.uninstall_btn = QPushButton("Uninstall")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        right_l.addWidget(self.progress)
        right_l.addWidget(self.download_btn)
        right_l.addWidget(self.uninstall_btn)
        main_l.addWidget(right_w, 2)

        self.tableWidget.itemSelectionChanged.connect(self._onSelect)
        self.tableWidget.itemDoubleClicked.connect(self._on_item_activated)
        self.download_btn.clicked.connect(self._on_download)
        self.uninstall_btn.clicked.connect(self._on_uninstall)
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
            name = entry.get("name", "unknown")
            plugin_dir = self.pluginsDir / re.sub(r"[^A-Za-z0-9_.-]", "_", name)

            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            checkbox_item.setCheckState(
                Qt.CheckState.Checked if plugin_dir.exists() else Qt.CheckState.Unchecked)
            checkbox_item.setData(Qt.ItemDataRole.UserRole, entry)
            self.tableWidget.setItem(row, 0, checkbox_item)

            self.tableWidget.setItem(row, 1, QTableWidgetItem(name))
            self.tableWidget.setItem(row, 2,
                                     QTableWidgetItem(entry.get("type", "source").title()))
            self.tableWidget.setItem(row, 3,
                                     QTableWidgetItem(entry.get("version", "0.0.0")))
            self.tableWidget.setItem(row, 4,
                                     QTableWidgetItem(entry.get("license", "Unknown")))

    def _onSelect(self):
        self.desc.clear()
        current_row = self.tableWidget.currentRow()
        if current_row < 0:
            return
        item = self.tableWidget.item(current_row, 0)
        if not item:
            return
        entry = item.data(Qt.ItemDataRole.UserRole) or {}
        text = f"{entry.get('description', '')}\\n\\nType: {entry.get('type', 'source').title()}\\nVersion: {entry.get('version', 'N/A')}\\nLicense: {entry.get('license', 'Unknown')}\\nURL: {entry.get('url', '')}"
        self.desc.setPlainText(text)

    def _on_item_activated(self, item: QTableWidgetItem):
        entry = item.data(Qt.ItemDataRole.UserRole) or {}
        name = entry.get("name", "plugin")
        ret = QMessageBox.question(self, "Install Plugin", f"Install plugin '{name}'?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret == QMessageBox.StandardButton.Yes:
            self._install_entry(entry)

    def _on_download(self):
        current_row = self.tableWidget.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "No selection", "Please select a plugin first.")
            return
        item = self.tableWidget.item(current_row, 0)
        if item:
            entry = item.data(Qt.ItemDataRole.UserRole) or {}
            name = entry.get("name", "plugin")
            ret = QMessageBox.question(self, "Install Plugin", f"Install '{name}'?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ret == QMessageBox.StandardButton.Yes:
                self._install_entry(entry)

    def _install_entry(self, entry: dict):
        name = re.sub(r"[^A-Za-z0-9_.-]", "_", entry.get("name", "plugin"))
        url = self._get_binary_url(entry) if entry.get("type") == "binary" else entry.get(
            "url")

        if not url:
            QMessageBox.warning(self, "Error", "No URL for your platform.")
            return

        target_subdir = self.pluginsDir / name
        if target_subdir.exists():
            ok = QMessageBox.question(self, "Overwrite", f"{name} exists. Overwrite?",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ok != QMessageBox.StandardButton.Yes:
                return
            shutil.rmtree(target_subdir, ignore_errors=True)

        try:
            with urllib.request.urlopen(url) as resp:
                tmp_fd, tmp_path = tempfile.mkstemp()
                os.close(tmp_fd)
                with open(tmp_path, "wb") as out:
                    out.write(resp.read())

            self.pluginsDir.mkdir(parents=True, exist_ok=True)
            if url.lower().endswith(".zip"):
                with zipfile.ZipFile(tmp_path, "r") as zf:
                    zf.extractall(path=self.pluginsDir)
            else:
                target_subdir.mkdir(parents=True, exist_ok=True)
                (target_subdir / Path(url).name).write_bytes(Path(tmp_path).read_bytes())

            os.remove(tmp_path)
            self.fetch_registry()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _get_binary_url(self, entry: dict) -> str:
        binary_urls = entry.get("binary_urls", {})
        if not binary_urls:
            return entry.get("url")

        system = platform.system().lower()
        arch = platform.machine().lower()
        py_ver = f"py{sys.version_info.major}{sys.version_info.minor}"

        # Try most specific first
        for key in [f"{system}-{arch}-{py_ver}", f"{system}-{arch}", system]:
            if key in binary_urls:
                return binary_urls[key]

        return entry.get("url")

    def _on_uninstall(self):
        current_row = self.tableWidget.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "No selection", "Please select a plugin first.")
            return
        item = self.tableWidget.item(current_row, 0)
        if not item:
            return
        entry = item.data(Qt.ItemDataRole.UserRole) or {}
        name = entry.get("name", "plugin")
        plugin_dir = self.pluginsDir / re.sub(r"[^A-Za-z0-9_.-]", "_", name)

        if not plugin_dir.exists():
            QMessageBox.information(self, "Not Installed", f"'{name}' is not installed.")
            return

        ret = QMessageBox.question(self, "Uninstall", f"Uninstall '{name}'?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret == QMessageBox.StandardButton.Yes:
            try:
                shutil.rmtree(plugin_dir)
                self.fetch_registry()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
