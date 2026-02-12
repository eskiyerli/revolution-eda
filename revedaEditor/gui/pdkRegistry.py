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
import logging
from pathlib import Path
import revedaEditor.backend.editFunctions as edf

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QHeaderView,
    QApplication,
    QFileDialog,
)


class PDKRegistryWindow(QMainWindow):
    DEFAULT_REGISTRY = (
        "https://raw.githubusercontent.com/eskiyerli/revolutionEDA_pdks/main/pdks.json"
    )

    def __init__(self, parent=None, registry_url: str | None = None):
        super().__init__(parent)
        self.setWindowTitle("Revolution EDA PDK Registry")
        self.resize(900, 400)
        self.logger = logging.getLogger("reveda")

        self.registry_url = registry_url or self.DEFAULT_REGISTRY
        app = QApplication.instance()
        self.pdksDir = app.basePath.parent/'pdks'
        self.pdksDir = self.pdksDir.resolve()
        if not self.pdksDir.exists():
            self.pdksDir.mkdir(parents=True)

        self._initUI()
        self._registry = []
        self.fetch_registry()

    def _initUI(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_l = QVBoxLayout(central)
        
        # PDK directory path display
        pathLayout = QHBoxLayout()
        pathLayout.addWidget(
            edf.boldLabel("Local PDKs Directory"), 1)
        self.pdkPathEdit = edf.longLineEdit()
        self.pdkPathEdit.setText(str(self.pdksDir))
        pathLayout.addWidget(self.pdkPathEdit, 5)
        self.pdkPathButton = QPushButton("...")
        self.pdkPathButton.clicked.connect(self.onPDKPathButtonClicked)
        pathLayout.addWidget(self.pdkPathButton, 1)
        main_l.addLayout(pathLayout)
        
        # Main content area
        content_l = QHBoxLayout()

        left_w = QWidget()
        left_l = QVBoxLayout(left_w)
        left_l.setContentsMargins(0, 0, 0, 0)
        self.tableWidget = QTableWidget()
        self.tableWidget.setColumnCount(6)
        self.tableWidget.setHorizontalHeaderLabels(
            ["Installed", "Binary","PDK", "Process", "Version", "License"]
        )
        self.tableWidget.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.tableWidget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tableWidget.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        left_l.addWidget(QLabel("Available PDKs:"))
        left_l.addWidget(self.tableWidget)
        self.refresh_btn = QPushButton("Refresh")
        left_l.addWidget(self.refresh_btn)
        content_l.addWidget(left_w, 2)

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
        content_l.addWidget(right_w, 2)
        
        main_l.addLayout(content_l)

        self.tableWidget.itemSelectionChanged.connect(self._onSelect)
        self.tableWidget.itemDoubleClicked.connect(self._on_item_activated)
        self.tableWidget.itemChanged.connect(self._on_checkbox_changed)
        self.download_btn.clicked.connect(self._on_download)
        self.uninstall_btn.clicked.connect(self._on_uninstall)
        self.refresh_btn.clicked.connect(self.fetch_registry)


    def onPDKPathButtonClicked(self):
        self.pdkPathEdit.setText(
            QFileDialog.getExistingDirectory(self, caption="Select PDK Repo Path")
        )
        self.pdksDir = Path(self.pdkPathEdit.text())

    def fetch_registry(self):
        self.tableWidget.setRowCount(0)
        self.desc.clear()
        self.progress.setValue(0)
        try:
            with urllib.request.urlopen(self.registry_url) as resp:
                raw = resp.read()
                index = json.loads(raw.decode("utf-8"))
                if isinstance(index, dict) and "pdks" in index:
                    index = index["pdks"]
                self._registry = index if isinstance(index, list) else []
        except Exception as exc:
            QMessageBox.warning(
                self, "Registry Error", f"Failed to fetch registry:\n{exc}"
            )
            self._registry = []

        self.tableWidget.setRowCount(len(self._registry))
        for row, entry in enumerate(self._registry):
            name = entry.get("name", "unknown")
            pdk_dir = self.pdksDir / re.sub(r"[^A-Za-z0-9_.-]", "_", name)

            # Check if installed and get local version
            config_path = pdk_dir / 'config.json'
            isInstalled = config_path.exists()
            isBinary = entry.get("type") == "binary"
            local_version = None
            
            if isInstalled:
                try:
                    with open(config_path) as f:
                        config = json.load(f)
                        local_version = config.get("pdk_version", "0.0.0")
                except Exception:
                    local_version = "0.0.0"
            
            # Compare versions
            remote_version = entry.get("pdk_version", "0.0.0")
            is_upgradeable = isInstalled and local_version and self._compare_versions(local_version, remote_version) < 0
            installedItem = QTableWidgetItem()
            installedItem.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            installedItem.setCheckState(
                Qt.CheckState.Checked if isInstalled else Qt.CheckState.Unchecked
            )
            installedItem.setData(Qt.ItemDataRole.UserRole, entry)
            if is_upgradeable:
                installedItem.setText("⬆")
                installedItem.setToolTip(f"Update available: {local_version} → {remote_version}")

            binaryItem = QTableWidgetItem()
            binaryItem.setFlags(Qt.ItemFlag.ItemIsEnabled)
            binaryItem.setCheckState(
                Qt.CheckState.Checked if isBinary else Qt.CheckState.Unchecked
            )
            binaryItem.setData(Qt.ItemDataRole.UserRole, entry)
            self.tableWidget.setItem(row, 0, installedItem)
            self.tableWidget.setItem(row, 1, binaryItem)

            self.tableWidget.setItem(row, 2, QTableWidgetItem(name))
            self.tableWidget.setItem(
                row, 3, QTableWidgetItem(entry.get("process", "N/A"))
            )
            self.tableWidget.setItem(
                row, 4, QTableWidgetItem(entry.get("version", "0.0.0"))
            )
            self.tableWidget.setItem(
                row, 5, QTableWidgetItem(entry.get("license", "Unknown"))
            )

    def _compare_versions(self, v1: str, v2: str) -> int:
        """Compare two version strings. Returns -1 if v1 < v2, 0 if equal, 1 if v1 > v2"""
        try:
            parts1 = [int(x) for x in v1.split(".")]
            parts2 = [int(x) for x in v2.split(".")]
            for p1, p2 in zip(parts1, parts2):
                if p1 < p2:
                    return -1
                elif p1 > p2:
                    return 1
            
            if len(parts1) < len(parts2):
                return -1
            elif len(parts1) > len(parts2):
                return 1
            return 0
        except Exception:
            return 0

    def _on_checkbox_changed(self, item: QTableWidgetItem):
        if item.column() != 0:
            return
        entry = item.data(Qt.ItemDataRole.UserRole)
        if not entry:
            return
        
        name = re.sub(r"[^A-Za-z0-9_.-]", "_", entry.get("name", "pdk"))
        pdk_dir = self.pdksDir / name
        
        if item.checkState() == Qt.CheckState.Checked and not pdk_dir.exists():
            self._install_entry(entry)
        elif item.checkState() == Qt.CheckState.Unchecked and pdk_dir.exists():
            self._uninstall_pdk(name, pdk_dir)

    def _uninstall_pdk(self, name: str, pdk_dir: Path):
        try:
            # Remove main PDK directory
            shutil.rmtree(pdk_dir)
            
            # Remove any other files/directories containing PDK name
            for item in self.pdksDir.iterdir():
                if name.lower() in item.name.lower():
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
            
            self.logger.info(f"PDK '{name}' and related files uninstalled.")
            self.fetch_registry()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self.fetch_registry()

    def _onSelect(self):
        self.desc.clear()
        current_row = self.tableWidget.currentRow()
        if current_row < 0:
            return
        item = self.tableWidget.item(current_row, 0)
        if not item:
            return
        entry = item.data(Qt.ItemDataRole.UserRole) or {}
        urlText = f'source URL: {entry.get("url", "")}' if entry.get("type") == "source" else f'binary URL: {entry.get("binary_urls", "")}'
        
        # Get version info
        name = entry.get("name", "unknown")
        pdk_dir = self.pdksDir / re.sub(r"[^A-Za-z0-9_.-]", "_", name)
        config_path = pdk_dir / "config.json"
        version_info = f"Remote Version: {entry.get('version', 'N/A')}"
        
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config = json.load(f)
                    local_version = config.get("version", "Unknown")
                    version_info += f"\nInstalled Version: {local_version}"
                    if self._compare_versions(local_version, entry.get('version', '0.0.0')) < 0:
                        version_info += " (Update available)"
            except Exception:
                pass
        
        text = f"{entry.get('description', '')}\n\nProcess: {entry.get('process', 'N/A')}\n{version_info}\nLicense: {entry.get('license', 'Unknown')}\n{urlText}"
        self.desc.setPlainText(text)

    def _on_item_activated(self, item: QTableWidgetItem):
        entry = item.data(Qt.ItemDataRole.UserRole) or {}
        name = entry.get("name", "pdk")
        ret = QMessageBox.question(
            self,
            "Install PDK",
            f"Install PDK '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ret == QMessageBox.StandardButton.Yes:
            self._install_entry(entry)

    def _on_download(self):
        current_row = self.tableWidget.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "No selection", "Please select a PDK first.")
            return
        item = self.tableWidget.item(current_row, 0)
        if item:
            entry = item.data(Qt.ItemDataRole.UserRole) or {}
            name = entry.get("name", "pdk")
            ret = QMessageBox.question(
                self,
                "Install PDK",
                f"Install '{name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ret == QMessageBox.StandardButton.Yes:
                self._install_entry(entry)

    def _install_entry(self, entry: dict):
        name = re.sub(r"[^A-Za-z0-9_.-]", "_", entry.get("name", "pdk"))
        url = (
            self._get_binary_url(entry)
            if entry.get("type") == "binary"
            else entry.get("url")
        )

        if not url:
            QMessageBox.warning(self, "Error", "No URL for your platform.")
            return

        target_subdir = self.pdksDir / name
        if target_subdir.exists():
            ok = QMessageBox.question(
                self,
                "Overwrite",
                f"{name} exists. Overwrite?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ok != QMessageBox.StandardButton.Yes:
                return
            shutil.rmtree(target_subdir, ignore_errors=True)

        try:
            with urllib.request.urlopen(url) as resp:
                tmp_fd, tmp_path = tempfile.mkstemp()
                os.close(tmp_fd)
                with open(tmp_path, "wb") as out:
                    out.write(resp.read())

            self.pdksDir.mkdir(parents=True, exist_ok=True)
            if url.lower().endswith(".zip"):
                with zipfile.ZipFile(tmp_path, "r") as zf:
                    zf.extractall(path=self.pdksDir)
            else:
                target_subdir.mkdir(parents=True, exist_ok=True)
                (target_subdir / Path(url).name).write_bytes(
                    Path(tmp_path).read_bytes()
                )

            os.remove(tmp_path)
            self.fetch_registry()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _get_binary_url(self, entry: dict) -> str:
        binary_urls = entry.get("binary_urls", {})

        system = platform.system().lower()
        arch = platform.machine().lower()
        py_ver = f"py{sys.version_info.major}{sys.version_info.minor}"

        # Try most specific first
        for key in [f"{system}-{arch}-{py_ver}", f"{system}-{arch}", system]:
            if key in binary_urls:
                return binary_urls[key]
        return ""


    def _on_uninstall(self):
        current_row = self.tableWidget.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "No selection", "Please select a PDK first.")
            return
        item = self.tableWidget.item(current_row, 0)
        if not item:
            return
        entry = item.data(Qt.ItemDataRole.UserRole) or {}
        name = entry.get("name", "pdk")
        pdk_dir = self.pdksDir / re.sub(r"[^A-Za-z0-9_.-]", "_", name)

        if not pdk_dir.exists():
            QMessageBox.information(
                self, "Not Installed", f"'{name}' is not installed."
            )
            return

        ret = QMessageBox.question(
            self,
            "Uninstall",
            f"Uninstall '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ret == QMessageBox.StandardButton.Yes:
            self._uninstall_pdk(re.sub(r"[^A-Za-z0-9_.-]", "_", name), pdk_dir)
