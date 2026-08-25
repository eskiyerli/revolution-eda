#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
#
# Copyright (c) 2024-2026 Revolution Semiconductor (Registered in the Netherlands)
#
# Standalone machine-fingerprint utility for Revolution EDA licensing.
#
# Share THIS SINGLE FILE with customers. They do NOT need Revolution EDA,
# PySide6, cryptography, or any third-party package installed - only a
# standard Python 3 interpreter (3.8+).
#
# The value printed here is IDENTICAL to the fingerprint the licensed
# application computes internally, so it can be pasted straight into a
# license request.
#
# Usage:
#     python machine_fingerprint.py
#
# The fingerprint algorithm MUST stay in sync with
# revedaLicense.licenseManager.get_machine_fingerprint().

import hashlib
import platform
import uuid
from pathlib import Path


def _stableMachineId() -> str | None:
    """Return a persistent, OS-provided machine identifier if available.

    Uses a stable per-install ID that does not change across reboots, network
    changes, or virtual adapters:
      - Windows: registry MachineGuid (HKLM\\SOFTWARE\\Microsoft\\Cryptography)
      - Linux:   /etc/machine-id (or /var/lib/dbus/machine-id)
      - macOS:   IOPlatformUUID from ioreg

    Returns None if the platform ID cannot be read, so the caller can fall back.
    """
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


def getMachineFingerprint() -> str:
    """Return the short node-locked fingerprint for the current machine.

    Mirrors revedaLicense.licenseManager.get_machine_fingerprint():
    prefers a persistent OS-provided machine ID, falling back to the legacy
    MAC/hostname derivation only when no stable ID is available. The result
    is SHA-256 truncated to 16 hex chars.
    """
    machineId = _stableMachineId()
    if machineId:
        raw = f"reveda:{machineId}"
    else:
        raw = f"{uuid.getnode()}:{platform.node()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def main() -> None:
    fingerprint = getMachineFingerprint()
    print("=" * 60)
    print("Revolution EDA - Machine Fingerprint")
    print("=" * 60)
    print(f"Hostname:            {platform.node()}")
    print(f"Operating system:    {platform.system()} {platform.release()}")
    print()
    print(f"Machine fingerprint: {fingerprint}")
    print("=" * 60)
    print("Copy the 16-character fingerprint above and send it to")
    print("support@reveda.eu together with the plugin name you want")
    print("to license.")
    print("=" * 60)


if __name__ == "__main__":
    main()
