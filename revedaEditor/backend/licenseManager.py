# SPDX-License-Identifier: MPL-2.0
#
# Copyright (c) 2024-2026 Revolution Semiconductor (Registered in the Netherlands)
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this file, You can obtain one at
# https://mozilla.org/MPL/2.0/.
#
# Add-ons and extensions developed for this software may be distributed
# under their own separate licenses.

"""Compatibility shim - real implementation is in revedaLicense (compiled, closed-source).

The revedaLicense package is distributed alongside commercial plugins as a
compiled .pyd/.so and is NOT part of the base Revolution EDA installation.
First-party commercial plugins also receive promotional access until the fixed
``PROMOTIONAL_ACCESS_END_UTC`` deadline. Older compiled modules can therefore be
bridged here, while the same policy must remain compiled into the released
revedaLicense binaries.
"""

from datetime import date, datetime, timezone

PROMOTIONAL_ACCESS_END_UTC = datetime(
    2027, 4, 1, 0, 0, 0, tzinfo=timezone.utc
)
PROMOTIONAL_PLUGIN_IDS = frozenset({
    "aiTerminal",
    "revedaPlot",
    "revedasim",
    "sdl",
})
MINIMUM_LICENSE_API_VERSION = 2


def _coerce_utc(now=None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if isinstance(now, date) and not isinstance(now, datetime):
        return datetime.combine(
            now, datetime.min.time(), tzinfo=timezone.utc
        )
    if not isinstance(now, datetime):
        raise TypeError("now must be a datetime, date, or None")
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def has_promotional_access(plugin_name: str, now=None) -> bool:
    return (
        str(plugin_name) in PROMOTIONAL_PLUGIN_IDS
        and _coerce_utc(now) < PROMOTIONAL_ACCESS_END_UTC
    )


try:
    from revedaLicense import licenseManager as _license_impl
    from revedaLicense.licenseManager import (  # noqa: F401
        LicenseDialog,
        LicenseStatusDialog,
        activate_license_with_server,
        get_license_info,
        get_machine_fingerprint,
        request_checkout_url,
        store_license,
        validate_license_key,
    )
    from revedaLicense.licenseManager import (  # noqa: F401
        check_and_prompt_license as _prompt_for_license,
    )
    _has_valid_paid_license = getattr(
        _license_impl,
        "has_paid_license",
        getattr(_license_impl, "has_valid_license"),
    )
    _compiled_get_access_info = getattr(
        _license_impl, "get_access_info", None
    )
except ImportError:
    _license_impl = None
    _compiled_get_access_info = None
    # revedaLicense not installed (open-source-only setup).
    # Provide minimal stubs so the base app starts without errors.
    import hashlib
    import platform
    import uuid
    from pathlib import Path

    def _stableMachineId() -> str | None:
        system = platform.system()
        try:
            if system == "Windows":
                import winreg

                with winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\Microsoft\Cryptography",
                    0,
                    winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
                ) as regKey:
                    value, _ = winreg.QueryValueEx(regKey, "MachineGuid")
                    machineId = str(value).strip()
                    return machineId or None

            if system == "Linux":
                for idPath in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
                    path = Path(idPath)
                    if path.exists():
                        machineId = path.read_text().strip()
                        if machineId:
                            return machineId
                return None

            if system == "Darwin":
                import re
                import subprocess

                output = subprocess.check_output(
                    ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                    text=True,
                    timeout=5,
                )
                match = re.search(r'"IOPlatformUUID"\s*=\s*"([^"]+)"', output)
                if match:
                    return match.group(1).strip()
                return None
        except Exception:
            return None

        return None

    def get_machine_fingerprint() -> str:
        machineId = _stableMachineId()
        if machineId:
            raw = f"reveda:{machineId}"
        else:
            raw = f"{uuid.getnode()}:{platform.node()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _has_valid_paid_license(plugin_name: str) -> bool:
        return False

    def validate_license_key(plugin_name: str, key: str):
        return None

    def store_license(plugin_name: str, key: str) -> bool:
        return False

    def request_checkout_url(plugin_name: str) -> str | None:
        return None

    def activate_license_with_server(plugin_name: str, key: str) -> bool:
        return False

    def get_license_info(plugin_name: str) -> dict | None:
        return None

    def _prompt_for_license(
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

    class LicenseStatusDialog:  # noqa: N801
        """Stub — revedaLicense not installed."""


def has_valid_license(plugin_name: str) -> bool:
    """Effective access: paid entitlement or the fixed promotional period."""
    try:
        if _has_valid_paid_license(plugin_name):
            return True
    except Exception:
        pass
    return has_promotional_access(plugin_name)


def check_and_prompt_license(
    plugin_name: str, payment_url=None, parent=None
) -> bool:
    if has_valid_license(plugin_name):
        return True
    return _prompt_for_license(plugin_name, payment_url, parent)


def get_access_info(plugin_name: str, now=None) -> dict:
    """UI-facing entitlement source and promotional deadline."""
    if callable(_compiled_get_access_info):
        info = _compiled_get_access_info(plugin_name, now)
        if isinstance(info, dict):
            return info

    paid = False
    try:
        paid = bool(_has_valid_paid_license(plugin_name))
    except Exception:
        paid = False

    if paid:
        return {
            "allowed": True,
            "source": "license",
            "license_info": get_license_info(plugin_name),
            "promotion_ends_at": PROMOTIONAL_ACCESS_END_UTC.isoformat(),
            "days_remaining": None,
        }

    current = _coerce_utc(now)
    if has_promotional_access(plugin_name, current):
        return {
            "allowed": True,
            "source": "promotion",
            "license_info": None,
            "promotion_ends_at": PROMOTIONAL_ACCESS_END_UTC.isoformat(),
            "days_remaining": max(
                0, (PROMOTIONAL_ACCESS_END_UTC - current).days
            ),
        }
    return {
        "allowed": False,
        "source": "none",
        "license_info": None,
        "promotion_ends_at": PROMOTIONAL_ACCESS_END_UTC.isoformat(),
        "days_remaining": 0,
    }


__all__ = [
    "PROMOTIONAL_ACCESS_END_UTC",
    "PROMOTIONAL_PLUGIN_IDS",
    "MINIMUM_LICENSE_API_VERSION",
    "activate_license_with_server",
    "check_and_prompt_license",
    "get_access_info",
    "get_license_info",
    "get_machine_fingerprint",
    "has_promotional_access",
    "has_valid_license",
    "LicenseDialog",
    "LicenseStatusDialog",
    "request_checkout_url",
    "store_license",
    "validate_license_key",
]