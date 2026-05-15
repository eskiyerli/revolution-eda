# 
# Revolution EDA
# 
# Copyright (c) 2026 Revolution Semiconductor
#
# This Source Code Form is subject to the terms of the
# Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
##


import importlib
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

from PySide6.QtCore import Qt, QUrl, QThread, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
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
)


class DownloadThread(QThread):
    progress = Signal(int)
    finished = Signal(bytes)
    error = Signal(str)
    
    def __init__(self, url: str):
        super().__init__()
        self.url = url
    
    def run(self):
        try:
            with urllib.request.urlopen(self.url) as resp:
                content_length = resp.headers.get('Content-Length')
                total_size = int(content_length) if content_length else 0
                downloaded = 0
                chunks = []
                
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    downloaded += len(chunk)
                    
                    if total_size > 0:
                        progress = int((downloaded / total_size) * 100)
                        self.progress.emit(min(progress, 100))
                    else:
                        # If no content length, show indeterminate progress
                        self.progress.emit(0)
                
                content = b''.join(chunks)
                self.finished.emit(content)
        except Exception as e:
            self.error.emit(str(e))


class PluginRegistryWindow(QMainWindow):
    DEFAULT_REGISTRY = "https://plugins.reveda.eu/plugins.json"

    def __init__(
        self,
        parent=None,
        registry_url: str | None = None,
        plugins_dir: Path | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Revolution EDA Plugin Registry")
        self.resize(800, 400)

        self.registry_url = registry_url or self.DEFAULT_REGISTRY
        plugin_path = os.environ.get("REVEDA_PLUGIN_PATH")
        self.pluginsDir = (
            Path(plugin_path)
            if plugin_path
            else (plugins_dir or Path.cwd() / "plugins")
        )
        self.pluginsDir = self.pluginsDir.resolve()

        self._current_payment_url = None
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
            ["Installed", "Plugin", "Type", "Version", "License"]
        )
        self.tableWidget.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
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
        self.buy_btn = QPushButton("Buy License")
        self.buy_btn.setVisible(False)
        self.uninstall_btn = QPushButton("Uninstall")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        right_l.addWidget(self.progress)
        right_l.addWidget(self.download_btn)
        right_l.addWidget(self.buy_btn)
        right_l.addWidget(self.uninstall_btn)
        main_l.addWidget(right_w, 2)

        self.tableWidget.itemSelectionChanged.connect(self._onSelect)
        self.tableWidget.itemDoubleClicked.connect(self._on_item_activated)
        self.download_btn.clicked.connect(self._on_download)
        self.buy_btn.clicked.connect(self._on_buy)
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
            QMessageBox.warning(
                self, "Registry Error", f"Failed to fetch registry:\n{exc}"
            )
            self._registry = []

        self.tableWidget.setRowCount(len(self._registry))
        for row, entry in enumerate(self._registry):
            name = entry.get("name", "unknown")
            plugin_dir = self.pluginsDir / re.sub(r"[^A-Za-z0-9_.-]", "_", name)

            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            checkbox_item.setCheckState(
                Qt.CheckState.Checked
                if plugin_dir.exists()
                else Qt.CheckState.Unchecked
            )
            checkbox_item.setData(Qt.ItemDataRole.UserRole, entry)
            self.tableWidget.setItem(row, 0, checkbox_item)

            self.tableWidget.setItem(row, 1, QTableWidgetItem(name))
            self.tableWidget.setItem(
                row, 2, QTableWidgetItem(entry.get("type", "source").title())
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
        url_text = ""
        if entry.get('type') == 'binary':
            url_text = f"Binary URLs: {entry.get('binary_urls', {})}"
        else:
            url_text = f"URL: {entry.get('url', '')}"
        payment_url = entry.get('payment_url', '')
        if payment_url:
            url_text += f"\nCheckout: {payment_url}"
        text = f"{entry.get('description', '')}\n\nType: {entry.get('type', 'source').title()}\nVersion: {entry.get('version', 'N/A')}\nLicense: {entry.get('license', 'Unknown')}\n{url_text}"
        self.desc.setPlainText(text)

        # Show Buy button only for paid plugins with a payment URL
        license_type = entry.get('license', '')
        is_paid = license_type in ('Commercial', 'Proprietary', 'Paid') or entry.get('license_required', False)
        self.buy_btn.setVisible(is_paid and bool(payment_url))
        self._current_payment_url = payment_url if is_paid else None

    def _on_item_activated(self, item: QTableWidgetItem):
        entry = item.data(Qt.ItemDataRole.UserRole) or {}
        name = entry.get("name", "plugin")
        ret = QMessageBox.question(
            self,
            "Install Plugin",
            f"Install plugin '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ret == QMessageBox.StandardButton.Yes:
            self._install_entry(entry)

    def _on_download(self):
        current_row = self.tableWidget.currentRow()
        if current_row < 0:
            QMessageBox.information(
                self, "No selection", "Please select a plugin first."
            )
            return
        item = self.tableWidget.item(current_row, 0)
        if item:
            entry = item.data(Qt.ItemDataRole.UserRole) or {}
            name = entry.get("name", "plugin")
            ret = QMessageBox.question(
                self,
                "Install Plugin",
                f"Install '{name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ret == QMessageBox.StandardButton.Yes:
                self._install_entry(entry)

    def _on_buy(self):
        if self._current_payment_url:
            QDesktopServices.openUrl(QUrl(self._current_payment_url))
            QMessageBox.information(
                self,
                "Payment Page Opened",
                "A payment page has been opened in your browser. "
                "After completing the purchase, your license key will be sent to you by email.",
            )

    def _install_entry(self, entry: dict):
        # Commercial plugins need the compiled revedaLicense module
        if self._plugin_requires_license(entry):
            if not self._ensure_revedaLicense():
                return

        name = re.sub(r"[^A-Za-z0-9_.-]", "_", entry.get("name", "plugin"))
        url = (
            self._get_binary_url(entry)
            if entry.get("type") == "binary"
            else entry.get("url")
        )

        if not url:
            QMessageBox.warning(self, "Error", "No URL for your platform.")
            return

        target_subdir = self.pluginsDir / name
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

        # Reset and show progress bar
        self.progress.setValue(0)
        self.progress.setVisible(True)
        self.download_btn.setEnabled(False)
        
        # Create download thread
        self.download_thread = DownloadThread(url)
        self.download_thread.progress.connect(self.progress.setValue)
        self.download_thread.finished.connect(lambda content: self._on_download_complete(content, url, target_subdir))
        self.download_thread.error.connect(self._on_download_error)
        self.download_thread.start()
    
    def _on_download_complete(self, content: bytes, url: str, target_subdir: Path):
        """Handle successful download completion."""
        try:
            tmp_fd, tmp_path = tempfile.mkstemp()
            os.close(tmp_fd)
            with open(tmp_path, "wb") as out:
                out.write(content)

            self.pluginsDir.mkdir(parents=True, exist_ok=True)
            if url.lower().endswith(".zip"):
                with zipfile.ZipFile(tmp_path, "r") as zf:
                    zf.extractall(path=self.pluginsDir)
            else:
                target_subdir.mkdir(parents=True, exist_ok=True)
                (target_subdir / Path(url).name).write_bytes(
                    Path(tmp_path).read_bytes()
                )

            os.remove(tmp_path)
            self.progress.setValue(100)
            self.fetch_registry()
            # Track successful download
            entry = self._get_current_entry()
            if entry:
                self._track_download(entry, url)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
        finally:
            self.download_btn.setEnabled(True)
            # Hide progress bar after a delay
            QApplication.instance().processEvents()
            
    def _on_download_error(self, error_msg: str):
        """Handle download error."""
        QMessageBox.critical(self, "Download Error", f"Failed to download: {error_msg}")
        self.download_btn.setEnabled(True)
        self.progress.setValue(0)
    
    def _get_current_entry(self) -> dict | None:
        """Get the currently selected registry entry."""
        current_row = self.tableWidget.currentRow()
        if current_row < 0:
            return None
        item = self.tableWidget.item(current_row, 0)
        if not item:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _track_download(self, entry: dict, url: str):
        """Emit analytics event for plugin download/install."""
        try:
            import urllib.request
            import json

            payload = json.dumps({
                "api_key": "phc_x4FKMrfv531eW4oLBuMExK6swzZ73yDHlLOIOmkVpUT",  # Replace with your PostHog project API key
                "event": "plugin_downloaded",
                "properties": {
                    "plugin_name": entry.get("name"),
                    "plugin_version": entry.get("version"),
                    "plugin_license": entry.get("license"),
                    "download_url": url,
                    "platform": f"{platform.system()}-{platform.machine()}",
                    "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
                    "distinct_id": f"reveda_{platform.node()}",
                }
            }).encode()

            req = urllib.request.Request(
                "https://eu.i.posthog.com/capture/",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5):
                pass
        except Exception:
            pass  # silently ignore analytics failures

    def _get_binary_url(self, entry: dict) -> str | None:
        binary_urls = entry.get("binary_urls", {})
        if not binary_urls:
            return entry.get("url")

        system = platform.system().lower()
        arch = platform.machine().lower()
        py_ver = f"py{sys.version_info.major}.{sys.version_info.minor}"

        # Try most specific first
        for key in [f"{system}-{arch}-{py_ver}", f"{system}-{arch}", system]:
            if key in binary_urls:
                return binary_urls[key]

        return entry.get("url")

    @staticmethod
    def _plugin_requires_license(entry: dict) -> bool:
        """Return True if the plugin entry requires a commercial license."""
        if entry.get("license_required", False):
            return True
        return entry.get("license", "") in ("Commercial", "Proprietary", "Paid")

    def _app_root(self) -> Path:
        """Return the Revolution EDA application root directory."""
        app = QApplication.instance()
        if app and hasattr(app, "basePath"):
            return app.basePath
        # Fallback: parent of revedaEditor package
        return Path(__file__).resolve().parents[2]

    def _revedaLicense_url(self) -> str | None:
        """Construct the download URL for the compiled revedaLicense extension."""
        system = platform.system().lower()
        major = sys.version_info.major
        minor = sys.version_info.minor
        base = "https://plugins.reveda.eu/revedaLicense"

        if system == "linux":
            arch = platform.machine().lower()
            return f"{base}/revedaLicense.cpython-{major}{minor}-{arch}-linux-gnu.so"
        elif system == "windows":
            return f"{base}/revedaLicense.cp{major}{minor}-win_amd64.pyd"
        elif system == "darwin":
            return f"{base}/revedaLicense.cpython-{major}{minor}-darwin.so"
        return None

    def _download_revedaLicense(self) -> bool:
        """Download and install the compiled revedaLicense extension.

        Returns True on success, False otherwise.
        """
        url = self._revedaLicense_url()
        if not url:
            QMessageBox.warning(
                self,
                "Unsupported Platform",
                "Automatic download of the license module is not available for your platform.\n"
                "Please install the revedaLicense module manually.",
            )
            return False

        # Reset and show progress bar
        self.progress.setValue(0)
        self.progress.setVisible(True)
        self.download_btn.setEnabled(False)
        
        # Create download thread
        self.license_download_thread = DownloadThread(url)
        self.license_download_thread.progress.connect(self.progress.setValue)
        self.license_download_thread.finished.connect(self._on_license_download_complete)
        self.license_download_thread.error.connect(self._on_license_download_error)
        self.license_download_thread.start()
        
        # Wait for completion (blocking since we need to return result)
        self.license_download_thread.wait()
        return hasattr(self, '_license_download_success') and self._license_download_success
    
    def _on_license_download_complete(self, content: bytes):
        """Handle successful license download completion."""
        url = self._revedaLicense_url()
        app_root = self._app_root()
        filename = Path(url).name
        target = app_root / filename

        try:
            target.write_bytes(content)
            # Ensure the extension is executable on Unix
            if platform.system() != "Windows":
                target.chmod(target.stat().st_mode | 0o755)
            # Invalidate import caches so the new module can be found
            importlib.invalidate_caches()
            self._license_download_success = True
        except Exception as e:
            QMessageBox.critical(
                self, "Install Error", f"Failed to write revedaLicense module:\n{e}"
            )
            self._license_download_success = False
        finally:
            self.download_btn.setEnabled(True)
    
    def _on_license_download_error(self, error_msg: str):
        """Handle license download error."""
        if "404" in error_msg:
            url = self._revedaLicense_url()
            QMessageBox.warning(
                self,
                "License Module Not Found",
                f"The license module was not found on the server for your platform.\n"
                f"URL: {url}\n\n"
                f"Please contact support or install the module manually.",
            )
        else:
            QMessageBox.critical(
                self, "Download Error", f"Failed to download revedaLicense: {error_msg}"
            )
        self._license_download_success = False
        self.download_btn.setEnabled(True)
        self.progress.setValue(0)

    def _ensure_revedaLicense(self) -> bool:
        """Ensure the compiled revedaLicense module is available.

        Returns True if already present or successfully downloaded.
        """
        try:
            import revedaLicense  # noqa: F401
            return True
        except ImportError:
            pass

        ret = QMessageBox.question(
            self,
            "License Module Required",
            "The revedaLicense module is required for commercial plugins but is not installed.\n\n"
            "Would you like to download and install it now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ret != QMessageBox.StandardButton.Yes:
            return False

        return self._download_revedaLicense()

    def _on_uninstall(self):
        current_row = self.tableWidget.currentRow()
        if current_row < 0:
            QMessageBox.information(
                self, "No selection", "Please select a plugin first."
            )
            return
        item = self.tableWidget.item(current_row, 0)
        if not item:
            return
        entry = item.data(Qt.ItemDataRole.UserRole) or {}
        name = entry.get("name", "plugin")
        plugin_dir = self.pluginsDir / re.sub(r"[^A-Za-z0-9_.-]", "_", name)

        if not plugin_dir.exists():
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
            try:
                shutil.rmtree(plugin_dir)
                self.fetch_registry()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
