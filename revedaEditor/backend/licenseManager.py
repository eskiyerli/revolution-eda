#    "Commons Clause" License Condition v1.0
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

"""Compatibility shim - real implementation is in revedaLicense (compiled, closed-source).

This file is open-source but contains no logic.  The revedaLicense package is
distributed alongside commercial plugins as a compiled .pyd/.so and is NOT part
of the base Revolution EDA installation.  If revedaLicense is absent, the app
runs normally but plugin license gates will deny access until it is installed.
"""

try:
    from revedaLicense.licenseManager import (  # noqa: F401
        LicenseDialog,
        check_and_prompt_license,
        get_machine_fingerprint,
        has_valid_license,
        store_license,
        validate_license_key,
    )
except ImportError:
    # revedaLicense not installed (open-source-only setup).
    # Provide minimal stubs so the base app starts without errors.
    import hashlib
    import platform
    import uuid

    def get_machine_fingerprint() -> str:
        raw = f"{uuid.getnode()}:{platform.node()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def has_valid_license(plugin_name: str) -> bool:
        return False

    def validate_license_key(plugin_name: str, key: str):
        return None

    def store_license(plugin_name: str, key: str) -> bool:
        return False

    def check_and_prompt_license(
        plugin_name: str, payment_url=None, parent=None
    ) -> bool:
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.warning(
            parent,
            "License Module Not Installed",
            "The 'revedaLicense' module is not installed.\n\n"
            "It is distributed alongside commercial plugins.\n"
            "Please reinstall the plugin package to activate your license.",
        )
        return False

    class LicenseDialog:  # noqa: N801
        """Stub — revedaLicense not installed."""

__all__ = [
    "validate_license_key",
    "has_valid_license",
    "store_license",
    "check_and_prompt_license",
    "get_machine_fingerprint",
    "LicenseDialog",
]