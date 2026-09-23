# `revedaEditor/backend/licenseManager.py`

**Module:** `revedaEditor.backend.licenseManager`

## Purpose

Open-source licensing shim: re-exports the proprietary `revedaLicense` module when present, otherwise stubs so the unlicensed build still runs.

## Module docstring

Compatibility shim - real implementation is in revedaLicense (compiled, closed-source).

This file is open-source but contains no logic.  The revedaLicense package is
distributed alongside commercial plugins as a compiled .pyd/.so and is NOT part
of the base Revolution EDA installation.  If revedaLicense is absent, the app
runs normally but plugin license gates will deny access until it is installed.
