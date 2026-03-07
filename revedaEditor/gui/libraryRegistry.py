#    "Commons Clause" License Condition v1.0
#
#    Software: Revolution EDA
#    License: Mozilla Public License 2.0
#    Licensor: Revolution Semiconductor (Registered in the Netherlands)

import json
import os
import re
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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
)


class LibraryRegistryWindow(QMainWindow):
    DEFAULT_REGISTRY = "https://raw.githubusercontent.com/eskiyerli/revolutionEDA_libraries/main/libraries.json"

    def __init__(
        self,
        parent=None,
        registry_url: str | None = None,
        libraries_dir: Path | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Revolution EDA Library Registry")
        self.resize(800, 450)

        self.registry_url = registry_url or self.DEFAULT_REGISTRY
        self.librariesDir = libraries_dir or Path.cwd()
        self.librariesDir = self.librariesDir.resolve()

        self.appMainW = QApplication.instance().appMainW

        self._initUI()
        self._registry = []
        self.fetch_registry()

    def _initUI(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_l = QVBoxLayout(central)

        # Installation prefix section
        prefix_w = QWidget()
        prefix_l = QHBoxLayout(prefix_w)
        prefix_l.setContentsMargins(0, 0, 0, 0)
        prefix_l.addWidget(QLabel("Installation Prefix:"))
        self.prefix_edit = QLineEdit(str(self.librariesDir))
        prefix_l.addWidget(self.prefix_edit, 1)
        self.browse_btn = QPushButton("Browse...")
        prefix_l.addWidget(self.browse_btn)
        main_l.addWidget(prefix_w)

        # Main content area
        content_w = QWidget()
        content_l = QHBoxLayout(content_w)
        content_l.setContentsMargins(0, 0, 0, 0)

        # Left panel - table
        left_w = QWidget()
        left_l = QVBoxLayout(left_w)
        left_l.setContentsMargins(0, 0, 0, 0)
        self.tableWidget = QTableWidget()
        self.tableWidget.setColumnCount(5)
        self.tableWidget.setHorizontalHeaderLabels(
            ["Installed", "Library", "Type", "Version", "License"]
        )
        self.tableWidget.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.tableWidget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tableWidget.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        left_l.addWidget(QLabel("Available libraries:"))
        left_l.addWidget(self.tableWidget)
        self.refresh_btn = QPushButton("Refresh")
        left_l.addWidget(self.refresh_btn)
        content_l.addWidget(left_w, 2)

        # Right panel - details
        right_w = QWidget()
        right_l = QVBoxLayout(right_w)
        right_l.setContentsMargins(0, 0, 0, 0)
        right_l.addWidget(QLabel("Description:"))
        self.desc = QTextEdit()
        self.desc.setReadOnly(True)
        right_l.addWidget(self.desc, 1)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        right_l.addWidget(self.progress)
        self.download_btn = QPushButton("Download / Install")
        self.uninstall_btn = QPushButton("Uninstall")
        right_l.addWidget(self.download_btn)
        right_l.addWidget(self.uninstall_btn)
        content_l.addWidget(right_w, 2)

        main_l.addWidget(content_w)

        # Connect signals
        self.tableWidget.itemSelectionChanged.connect(self._onSelect)
        self.tableWidget.itemDoubleClicked.connect(self._on_item_activated)
        self.download_btn.clicked.connect(self._on_download)
        self.uninstall_btn.clicked.connect(self._on_uninstall)
        self.refresh_btn.clicked.connect(self.fetch_registry)
        self.browse_btn.clicked.connect(self._on_browse)
        self.prefix_edit.textChanged.connect(self._on_prefix_changed)

    def _on_browse(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Select Installation Directory", str(self.librariesDir)
        )
        if directory:
            self.prefix_edit.setText(directory)

    def _on_prefix_changed(self, text: str):
        self.librariesDir = Path(text).resolve()
        self.fetch_registry()

    def fetch_registry(self):
        self.tableWidget.setRowCount(0)
        self.desc.clear()
        self.progress.setValue(0)
        try:
            with urllib.request.urlopen(self.registry_url) as resp:
                raw = resp.read()
                index = json.loads(raw.decode("utf-8"))
                if isinstance(index, dict) and "libraries" in index:
                    index = index["libraries"]
                self._registry = index if isinstance(index, list) else []
        except Exception as exc:
            QMessageBox.warning(
                self, "Registry Error", f"Failed to fetch registry:\n{exc}"
            )
            self._registry = []

        self.tableWidget.setRowCount(len(self._registry))
        for row, entry in enumerate(self._registry):
            name = entry.get("name", "unknown")
            library_dir = self.librariesDir / re.sub(r"[^A-Za-z0-9_.-]", "_", name)

            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            checkbox_item.setCheckState(
                Qt.CheckState.Checked
                if library_dir.exists()
                else Qt.CheckState.Unchecked
            )
            checkbox_item.setData(Qt.ItemDataRole.UserRole, entry)
            self.tableWidget.setItem(row, 0, checkbox_item)

            self.tableWidget.setItem(row, 1, QTableWidgetItem(name))
            self.tableWidget.setItem(
                row, 2, QTableWidgetItem(entry.get("type", "design").title())
            )
            self.tableWidget.setItem(
                row, 3, QTableWidgetItem(entry.get("version", "0.0.0"))
            )
            self.tableWidget.setItem(
                row, 4, QTableWidgetItem(entry.get("license", "Unknown"))
            )

    def _onSelect(self):
        self.desc.clear()
        current_row = self.tableWidget.currentRow()
        if current_row < 0:
            return
        item = self.tableWidget.item(current_row, 0)
        if not item:
            return
        entry = item.data(Qt.ItemDataRole.UserRole) or {}
        text = f"{entry.get('description', '')}\n\nType: {entry.get('type', 'design').title()}\nVersion: {entry.get('version', 'N/A')}\nLicense: {entry.get('license', 'Unknown')}\nURL: {entry.get('url', '')}"
        self.desc.setPlainText(text)

    def _on_item_activated(self, item: QTableWidgetItem):
        entry = item.data(Qt.ItemDataRole.UserRole) or {}
        name = entry.get("name", "library")
        ret = QMessageBox.question(
            self,
            "Install Library",
            f"Install library '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ret == QMessageBox.StandardButton.Yes:
            self._install_entry(entry)

    def _on_download(self):
        current_row = self.tableWidget.currentRow()
        if current_row < 0:
            QMessageBox.information(
                self, "No selection", "Please select a library first."
            )
            return
        item = self.tableWidget.item(current_row, 0)
        if item:
            entry = item.data(Qt.ItemDataRole.UserRole) or {}
            name = entry.get("name", "library")
            ret = QMessageBox.question(
                self,
                "Install Library",
                f"Install '{name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ret == QMessageBox.StandardButton.Yes:
                self._install_entry(entry)

    def _on_uninstall(self):
        current_row = self.tableWidget.currentRow()
        if current_row < 0:
            QMessageBox.information(
                self, "No selection", "Please select a library first."
            )
            return
        item = self.tableWidget.item(current_row, 0)
        if not item:
            return
        entry = item.data(Qt.ItemDataRole.UserRole) or {}
        name = re.sub(r"[^A-Za-z0-9_.-]", "_", entry.get("name", "library"))
        library_dir = self.librariesDir / name

        if not library_dir.exists():
            QMessageBox.information(self, "Not Installed", f"'{name}' is not installed.")
            return

        ret = QMessageBox.question(
            self,
            "Uninstall Library",
            f"Uninstall '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ret == QMessageBox.StandardButton.Yes:
            try:
                shutil.rmtree(library_dir, ignore_errors=True)
                QMessageBox.information(self, "Success", f"'{name}' uninstalled.")
                self.fetch_registry()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to uninstall:\n{e}")

    def _install_entry(self, entry: dict):
        name = re.sub(r"[^A-Za-z0-9_.-]", "_", entry.get("name", "library"))
        url = entry.get("url")

        if not url:
            QMessageBox.warning(self, "Error", "No URL available.")
            return

        target_subdir = self.librariesDir / name
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
            self.progress.setValue(10)
            with urllib.request.urlopen(url) as resp:
                tmp_fd, tmp_path = tempfile.mkstemp()
                os.close(tmp_fd)
                with open(tmp_path, "wb") as out:
                    out.write(resp.read())

            self.progress.setValue(50)
            self.librariesDir.mkdir(parents=True, exist_ok=True)
            if url.lower().endswith(".zip"):
                with zipfile.ZipFile(tmp_path, "r") as zf:
                    zf.extractall(path=self.librariesDir)
            else:
                target_subdir.mkdir(parents=True, exist_ok=True)
                (target_subdir / Path(url).name).write_bytes(
                    Path(tmp_path).read_bytes()
                )

            os.remove(tmp_path)
            self.progress.setValue(100)
            QMessageBox.information(self, "Success", f"'{name}' installed successfully.")
            self.fetch_registry()
            self.appMainW.libraryDict[name]=target_subdir
            self.appMainW.libraryBrowser.writeLibDefFile(self.appMainW.libraryDict,
                                                         self.appMainW.libraryBrowser.libFilePath)
            self.appMainW.libraryBrowser.designView.reworkDesignLibrariesView(
                self.appMainW.libraryDict)
        except Exception as e:
            self.progress.setValue(0)
            QMessageBox.critical(self, "Error", f"Installation failed:\n{e}")
