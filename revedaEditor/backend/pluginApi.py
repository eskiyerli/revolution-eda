#
# Revolution EDA
#
# Copyright (c) 2026 Revolution Semiconductor
#
# This Source Code Form is subject to the terms of the
# Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
"""Qt-free plugin contract: version/capability negotiation and update checks.

``pluginsLoader`` evaluates this contract *before* importing a plugin, so an
incompatible plugin's code never executes. All functions here are import-free
and GUI-free — they run on decoded ``config.json`` dicts and the fetched
``plugins.json`` registry entries, so tests need no Qt at all.

``config.json`` fields consumed by the negotiation (all optional):

    plugin_api       int — plugin-contract version the plugin was built
                     against. Absent means 1 (the original menu-callback
                     contract). Greater than :data:`PLUGIN_API_VERSION`
                     blocks the import.
    min_app_version  str — lowest reveda version the plugin supports.
    max_app_version  str — highest reveda version the plugin supports.
    provides         list[str] — capabilities this plugin owns (e.g.
                     ``"sdl"``); lets core editors suppress native actions
                     the plugin replaces.
    requires_core    list[str] — entries of :data:`CORE_CAPABILITIES` the
                     plugin cannot run without; unknown entries block the
                     import.
    plugin_version   str — installed version, compared against the registry
                     ``version`` for update notices.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# Contract version implemented by this core. API 1 is the original
# config.json menu wiring (``callback(editorWindow)``, ``viewTypes`` /
# ``openCellView`` / ``createCellView`` dispatch). API 2 adds the
# negotiation fields documented above.
PLUGIN_API_VERSION = 2

# Plugin catalog listing name/version/url per published plugin.
DEFAULT_REGISTRY_URL = "https://plugins.reveda.eu/plugins.json"

# Named core services a plugin may hard-require via ``requires_core``.
# Extend as core exposes new plugin-facing services (e.g. "sdlAdapterV1").
CORE_CAPABILITIES = frozenset({"menuItems", "viewTypes", "sdlAdapterV1"})

_VERSION_RE = re.compile(r"\d+(?:\.\d+)*")


def parseVersion(text) -> tuple[int, ...]:
    """``"0.9.0"`` -> ``(0, 9, 0)``; ``()`` when nothing parses.

    Tolerant of ``v`` prefixes and pre-release suffixes — the first
    dotted-numeric run wins, so ``"0.9.0b1"`` -> ``(0, 9, 0)``.
    """
    if not isinstance(text, str):
        return ()
    match = _VERSION_RE.search(text)
    if not match:
        return ()
    return tuple(int(part) for part in match.group(0).split("."))


def _compareVersions(a: tuple, b: tuple) -> int:
    """-1/0/1 comparing two parsed versions, shorter padded with zeros."""
    width = max(len(a), len(b))
    a = a + (0,) * (width - len(a))
    b = b + (0,) * (width - len(b))
    return (a > b) - (a < b)


def versionNewer(candidate: str, current: str) -> bool:
    """True when ``candidate`` parses to a version newer than ``current``."""
    return _compareVersions(parseVersion(candidate), parseVersion(current)) > 0


def readPluginConfig(pluginDir) -> dict:
    """Decoded ``<pluginDir>/config.json``; ``{}`` when absent or malformed."""
    try:
        return json.loads(
            (Path(pluginDir) / "config.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return {}


def pluginCapabilities(config: dict) -> set[str]:
    """Normalized ``provides`` entries from a plugin config."""
    caps = config.get("provides")
    if not isinstance(caps, (list, tuple)):
        return set()
    return {str(cap) for cap in caps}


def checkPluginConfig(
    config: dict,
    appVersion: str,
    coreCapabilities=CORE_CAPABILITIES,
    apiVersion: int = PLUGIN_API_VERSION,
) -> list[str]:
    """Negotiation issues for a plugin config; empty means compatible.

    Declared constraints the core cannot honor are reported — the caller
    skips importing the plugin. Absent fields are ignored, so existing
    plugins (implicit ``plugin_api`` 1) keep loading unchanged.
    """
    issues: list[str] = []

    api = config.get("plugin_api")
    if api is not None:
        if not isinstance(api, int) or isinstance(api, bool):
            issues.append(f"plugin_api {api!r} is not an integer")
        elif api > apiVersion:
            issues.append(
                f"requires plugin_api {api}, app supports {apiVersion}"
            )

    app = parseVersion(appVersion)
    for key in ("min_app_version", "max_app_version"):
        raw = config.get(key)
        if raw is None:
            continue
        required = parseVersion(str(raw))
        if not required:
            issues.append(f"{key} {raw!r} is not a version")
        elif not app:
            continue  # cannot verify — do not block on an unreadable app version
        elif key == "min_app_version" and _compareVersions(app, required) < 0:
            issues.append(f"requires app >= {raw} (running {appVersion})")
        elif key == "max_app_version" and _compareVersions(app, required) > 0:
            issues.append(f"requires app <= {raw} (running {appVersion})")

    for cap in config.get("requires_core") or []:
        if cap not in coreCapabilities:
            issues.append(f"requires unsupported core capability {cap!r}")

    return issues


def updatesAvailable(
    installed: dict[str, str], registryEntries
) -> dict[str, tuple[str, str]]:
    """``{name: (installed, latest)}`` for plugins the registry has newer.

    ``installed`` maps plugin name (folder or ``plugin_name``) to its
    installed ``plugin_version``; ``registryEntries`` is the decoded
    ``plugins`` list from the registry JSON.
    """
    result: dict[str, tuple[str, str]] = {}
    for entry in registryEntries or []:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        latest = str(entry.get("version", ""))
        current = installed.get(name)
        if name and current and latest and versionNewer(latest, current):
            result[name] = (current, latest)
    return result
