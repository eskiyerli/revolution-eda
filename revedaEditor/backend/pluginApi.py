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
import sys
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


# ----------------------------------------------------------------------
# Extension-module ABI tags
# ----------------------------------------------------------------------

# Filename tags: "x.cpython-314-x86_64-linux-gnu.so", "x.cp312-win_amd64.pyd".
# The digit run encodes major+minor ("314" -> 3.14, "38" -> 3.8).
_EXT_TAG_RE = re.compile(r"\.cp(?:ython)?-?(\d)(\d+)[-.]")
_EXT_SUFFIXES = {".so", ".pyd", ".dll"}


def extensionPyVersion(filename) -> tuple[int, int] | None:
    """``(major, minor)`` an extension filename's CPython tag encodes."""
    match = _EXT_TAG_RE.search(str(filename))
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def pluginExtensionFiles(pluginsDir, name: str, ispkg: bool) -> list[Path]:
    """Binary extension files belonging to plugin ``name``.

    Covers both layouts: modules inside ``pluginsDir/name/`` (compiled
    package) and siblings like ``pluginsDir/name.cpython-314-...so``
    (bare compiled module loaded by a shim ``__init__.py``).
    """
    root = Path(pluginsDir)
    found: list[Path] = []
    if ispkg:
        pkgDir = root / name
        if pkgDir.is_dir():
            found.extend(
                p for p in pkgDir.rglob("*")
                if p.is_file() and p.suffix in _EXT_SUFFIXES
            )
    found.extend(
        p for p in root.glob(f"{name}.*")
        if p.is_file() and p.suffix in _EXT_SUFFIXES
    )
    return found


def mismatchedExtensions(pluginsDir, name: str,
                         ispkg: bool) -> list[tuple[Path, tuple[int, int]]]:
    """Plugin extension files tagged for a different CPython minor."""
    here = tuple(sys.version_info[:2])
    bad = []
    for path in pluginExtensionFiles(pluginsDir, name, ispkg):
        tag = extensionPyVersion(path.name)
        if tag is not None and tag != here:
            bad.append((path, tag))
    return bad


def explainImportError(error: BaseException) -> str | None:
    """Plain-language hint for a plugin ``ImportError``, else ``None``.

    Identifies two common ABI failures: a filename tag for another CPython
    minor (``cpython-314`` under 3.12) and unresolved ``_Py*``/Python symbols
    or conflicting ``pythonXY.dll`` — both mean the binary was built for a
    different Python than the app runs.
    """
    if not isinstance(error, ImportError):
        return None
    message = str(error)
    running = f"{sys.version_info.major}.{sys.version_info.minor}"
    tag = extensionPyVersion(message)
    if tag and tag != tuple(sys.version_info[:2]):
        return (
            f"built for Python {tag[0]}.{tag[1]}, but this app runs "
            f"Python {running} — install a plugin build matching the app"
        )
    if (
        "undefined symbol" in message
        or "conflicts with this version of Python" in message
    ):
        return (
            "binary extension is incompatible with this app's Python "
            f"{running} — install a plugin build matching the app"
        )
    return None
