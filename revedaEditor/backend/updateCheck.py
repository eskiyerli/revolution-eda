# SPDX-License-Identifier: MPL-2.0
#
# Copyright (c) 2026 Revolution Semiconductor (Registered in the Netherlands)
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this file, You can obtain one at
# https://mozilla.org/MPL/2.0/.
#
"""Application update check against the GitHub releases API.

``fetchLatestRelease`` is Qt-free and blocking — it runs on a worker thread
via :class:`startThread`. ``appUpdateChecker`` mirrors the plugin registry
check in ``pluginsLoader``: throttled to once per calendar day through
QSettings, disabled with ``REVEDA_DISABLE_UPDATE_CHECK``, and overridable
with ``REVEDA_UPDATE_URL`` for non-GitHub manifests returning the same
shape (``tag_name``/``html_url`` or ``version``/``url``).
"""

import json
import logging
import os
import urllib.request
from datetime import date

from PySide6.QtCore import QObject, QThreadPool, Signal

import revedaEditor
import revedaEditor.backend.editFunctions as edf
from revedaEditor.backend import pluginApi
from revedaEditor.backend.startThread import startThread

GITHUB_REPO = "eskiyerli/revolution-eda"
DEFAULT_RELEASES_URL = (
    f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
)
RELEASES_PAGE_URL = f"https://github.com/{GITHUB_REPO}/releases"


def fetchLatestRelease(url: str = DEFAULT_RELEASES_URL,
                       timeout: int = 5) -> dict:
    """Blocking latest-release fetch; returns a normalized manifest dict.

    ``{"version", "url", "notes"}``; ``version``/``url`` are empty strings
    when the response lacks them. Raises on network/HTTP errors so the
    worker's ``error`` signal fires.
    """
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "revolution-eda-update-check",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if not isinstance(data, dict):
        return {}
    # Accept both the GitHub shape and a minimal custom manifest.
    version = data.get("tag_name") or data.get("version") or ""
    urlOut = data.get("html_url") or data.get("url") or RELEASES_PAGE_URL
    notes = data.get("name") or data.get("notes") or ""
    return {
        "version": str(version),
        "url": str(urlOut),
        "notes": str(notes),
    }


class appUpdateChecker(QObject):
    """Background app update check; emits on the GUI thread via signals."""

    updateFound = Signal(dict)    # normalized manifest newer than this app
    checkFinished = Signal(dict)  # fetched manifest ({} when nothing parsed)
    checkFailed = Signal(str)     # fetch/parse error description

    _SETTINGS_FILE = edf.APP_SETTINGS_FILE
    _KEY_LAST = "appUpdateCheck/lastCheck"
    _KEY_LATEST = "appUpdateCheck/latest"

    def __init__(self, releasesUrl: str | None = None, parent=None):
        if releasesUrl is not None and not isinstance(releasesUrl, str):
            raise TypeError(
                f"releasesUrl must be a URL string, got {releasesUrl!r}; "
                "use parent= for the QObject parent"
            )
        super().__init__(parent)
        self.releasesUrl = (
            releasesUrl
            or os.environ.get("REVEDA_UPDATE_URL")
            or DEFAULT_RELEASES_URL
        )
        self._appVersion = getattr(revedaEditor, "__version__", "0.0.0")
        self.latestRelease: dict = {}
        self._worker = None
        self._threadPool = QThreadPool.globalInstance()
        self._settingsFile = self._SETTINGS_FILE

    def checkForUpdates(self, force: bool = False) -> bool:
        """Start a background fetch; returns True when started.

        Throttled to once per calendar day via QSettings unless ``force``;
        disabled entirely with ``REVEDA_DISABLE_UPDATE_CHECK``.
        """
        if os.environ.get("REVEDA_DISABLE_UPDATE_CHECK"):
            return False
        self._settingsFile.parent.mkdir(parents=True, exist_ok=True)
        from PySide6.QtCore import QSettings
        settings = QSettings(
            str(self._settingsFile), QSettings.IniFormat
        )
        today = date.today().isoformat()
        if not force and settings.value(self._KEY_LAST, "") == today:
            return False
        settings.setValue(self._KEY_LAST, today)
        worker = startThread(fetchLatestRelease, self.releasesUrl)
        worker.signals.result.connect(self._onReleaseFetched)
        worker.signals.error.connect(self._onFetchError)
        self._worker = worker  # keep alive until the pool finishes it
        self._threadPool.start(worker)
        return True

    def _onReleaseFetched(self, release: dict) -> None:
        """Normalize/cache the manifest; emit ``updateFound`` when newer."""
        self.latestRelease = release or {}
        from PySide6.QtCore import QSettings
        settings = QSettings(
            str(self._settingsFile), QSettings.IniFormat
        )
        settings.setValue(self._KEY_LATEST, json.dumps(self.latestRelease))
        settings.sync()
        version = self.latestRelease.get("version", "")
        if version and pluginApi.versionNewer(version, self._appVersion):
            logging.getLogger("reveda").info(
                f"Application update available: "
                f"{self._appVersion} -> {version} "
                f"({self.latestRelease.get('url', '')})"
            )
            self.updateFound.emit(self.latestRelease)
        self.checkFinished.emit(self.latestRelease)

    def _onFetchError(self, error) -> None:
        msg = str(error[-1]) if isinstance(error, tuple) else str(error)
        logging.getLogger("reveda").warning(
            f"Application update check failed: {msg}"
        )
        self.checkFailed.emit(msg)
        self.checkFinished.emit({})
