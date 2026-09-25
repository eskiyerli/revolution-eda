# `revedaEditor\backend\pluginApi.py`

**Module:** `revedaEditor.backend.pluginApi`

## Purpose

Qt-free plugin contract: version/capability negotiation and update checks.

## Functions

- `parseVersion()` — `"0.9.0"` -> `(0, 9, 0)`; `()` when nothing parses.
- `_compareVersions()` — -1/0/1 comparing two parsed versions, shorter padded with zeros.
- `versionNewer()` — True when `candidate` parses to a version newer than `current`.
- `readPluginConfig()` — Decoded `<pluginDir>/config.json`; `{}` when absent or malformed.
- `pluginCapabilities()` — Normalized `provides` entries from a plugin config.
- `checkPluginConfig()` — Negotiation issues for a plugin config; empty means compatible.
- `updatesAvailable()` — `{name: (installed, latest)}` for plugins the registry has newer.
