#    “Commons Clause” License Condition v1.0
#
#    The Software is provided to you by the Licensor under the License, as defined
#    below, subject to the following condition.
#
#    Without limiting other conditions in the License, the grant of rights under the
#    License will not include, and the License does not grant to you, the right to
#    Sell the Software.
#
#   Add-ons and extensions developed for this software may be distributed
#   under their own separate licenses.
#
#    Software: Revolution EDA
#    License: Mozilla Public License 2.0
#    Licensor: Revolution Semiconductor (Registered in the Netherlands)

import base64
import hashlib
import json
import platform
import uuid
from datetime import date
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

# ---------------------------------------------------------------------------
# PUBLIC KEY (safe to ship with the application)
# Run scripts/generate_keypair.py once on the server, then paste the public
# key here. The matching private key must NEVER leave the server.
# ---------------------------------------------------------------------------
PUBLIC_KEY_PEM = b"""-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAYSnG7/SFnxzvnRW+/EOapUjGrR0cxP9BpvcV7834zh0=
-----END PUBLIC KEY-----"""


def _load_public_key():
    return serialization.load_pem_public_key(PUBLIC_KEY_PEM)


def get_machine_fingerprint() -> str:
    """Return a short node-locked fingerprint for the current machine."""
    raw = f"{uuid.getnode()}:{platform.node()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _license_dir() -> Path:
    d = Path.home() / ".reveda" / "licenses"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _license_file(plugin_name: str) -> Path:
    return _license_dir() / f"{plugin_name}.lic"


# ===========================================================================
# REMOVE BEFORE SHIPPING — the functions below are server-side helpers kept
# here only for local testing.  They require the PRIVATE key and must NOT be
# included in the distributed application.
# ===========================================================================

# def _sign_payload_ed25519(payload: dict, private_key) -> str:
#     """Sign a license payload with Ed25519 (server-side only)."""
#     payload_str = json.dumps(payload, separators=(",", ":"), sort_keys=True)
#     signature = private_key.sign(payload_str.encode())
#     return base64.urlsafe_b64encode(signature).decode().rstrip("=")


# def generate_license_key(
#     plugin_name: str, machine_fp: str, expiry_iso: str, lic_type: str = "subscription",
#     *, _private_key_pem: bytes | None = None,
# ) -> str:
#     """Generate a node-locked license key string (server-side only).

#     **Do not ship this function in the client application.**
#     """
#     if _private_key_pem is None:
#         raise RuntimeError("Private key required — this function is server-side only.")
#     private_key = serialization.load_pem_private_key(_private_key_pem, password=None)
#     payload = {
#         "p": plugin_name,
#         "m": machine_fp,
#         "e": expiry_iso,
#         "t": lic_type,
#     }
#     payload_str = json.dumps(payload, separators=(",", ":"), sort_keys=True)
#     payload_b64 = base64.urlsafe_b64encode(payload_str.encode()).decode().rstrip("=")
#     sig = _sign_payload_ed25519(payload, private_key)
#     return f"{payload_b64}.{sig}"

# ===========================================================================
# END OF SERVER-SIDE FUNCTIONS
# ===========================================================================


def validate_license_key(plugin_name: str, key: str) -> dict | None:
    """Validate a license key for the current machine and plugin using Ed25519."""
    try:
        parts = key.split(".")
        if len(parts) != 2:
            return None
        payload_b64, sig_b64 = parts

        # Restore padding for base64 decoding
        def _pad(b64: str) -> str:
            pad = 4 - len(b64) % 4
            return b64 + ("=" * pad) if pad != 4 else b64

        payload_bytes = base64.urlsafe_b64decode(_pad(payload_b64))
        signature = base64.urlsafe_b64decode(_pad(sig_b64))
        payload = json.loads(payload_bytes)

        public_key = _load_public_key()
        payload_str = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        try:
            public_key.verify(signature, payload_str.encode())
        except InvalidSignature:
            return None

        if payload.get("p") != plugin_name:
            return None

        if payload.get("m") != get_machine_fingerprint():
            return None

        lic_type = payload.get("t", "subscription")
        if lic_type == "subscription":
            expiry = payload.get("e")
            if expiry and date.fromisoformat(expiry) < date.today():
                return None

        return payload
    except Exception:
        return None


def has_valid_license(plugin_name: str) -> bool:
    """Return True if a locally-stored license is present and valid."""
    lic_file = _license_file(plugin_name)
    if not lic_file.exists():
        return False
    key = lic_file.read_text().strip()
    return validate_license_key(plugin_name, key) is not None


def store_license(plugin_name: str, key: str) -> bool:
    """Validate and persist a license key to disk."""
    if validate_license_key(plugin_name, key):
        _license_file(plugin_name).write_text(key)
        return True
    return False


class LicenseDialog(QDialog):
    """Dialog shown when a plugin license is missing or expired."""

    def __init__(self, plugin_name: str, payment_url: str | None = None, parent=None):
        super().__init__(parent)
        self.plugin_name = plugin_name
        self.payment_url = payment_url
        self.setWindowTitle(f"License Required — {plugin_name}")
        self.resize(420, 220)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                f"The plugin <b>{plugin_name}</b> requires an active license to run on this machine."
            )
        )
        layout.addWidget(QLabel("You can buy a new license or enter an existing key below."))

        if self.payment_url:
            buy_btn = QPushButton("Buy License")
            buy_btn.clicked.connect(self._open_payment)
            layout.addWidget(buy_btn)

        layout.addWidget(QLabel("License Key:"))
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Paste your license key here...")
        layout.addWidget(self.key_input)

        btn_layout = QHBoxLayout()
        self.activate_btn = QPushButton("Activate")
        self.activate_btn.clicked.connect(self._activate)
        btn_layout.addWidget(self.activate_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

    def _open_payment(self):
        QDesktopServices.openUrl(QUrl(self.payment_url))
        QMessageBox.information(
            self,
            "Payment Page Opened",
            "A payment page has been opened in your browser. "
            "After completing the purchase, your license key will be sent to you by email.",
        )

    def _activate(self):
        key = self.key_input.text().strip()
        if not key:
            self.status_label.setText("Please enter a license key.")
            return

        if store_license(self.plugin_name, key):
            self.status_label.setText("License activated successfully!")
            self.accept()
        else:
            self.status_label.setText(
                "Invalid license key. It may be expired, for a different plugin, or tied to another machine."
            )


def check_and_prompt_license(
    plugin_name: str, payment_url: str | None = None, parent=None
) -> bool:
    """Return True if the plugin is licensed, or prompt the user to activate.

    If the user successfully activates a valid key, the result is cached on disk.
    """
    if has_valid_license(plugin_name):
        return True

    dialog = LicenseDialog(plugin_name, payment_url, parent)
    return dialog.exec() == QDialog.DialogCode.Accepted
