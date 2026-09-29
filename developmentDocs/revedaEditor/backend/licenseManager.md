# `revedaEditor\backend\licenseManager.py`

**Module:** `revedaEditor.backend.licenseManager`

## Purpose

Compatibility shim - real implementation is in revedaLicense (compiled, closed-source).

It also exposes the fixed first-party plugin promotion running until
`2027-04-01T00:00:00Z`, plus `get_access_info()` for distinguishing paid
licenses from promotional access.
