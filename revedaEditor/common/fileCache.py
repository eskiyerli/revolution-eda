# SPDX-License-Identifier: MPL-2.0
#
# Copyright (c) 2024-2026 Revolution Semiconductor (Registered in the Netherlands)
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this file, You can obtain one at
# https://mozilla.org/MPL/2.0/.
#
# Add-ons and extensions developed for this software may be distributed
# under their own separate licenses.

"""File content caching with modification-time invalidation."""

import logging
import os
import pathlib
from typing import Any, Optional

import orjson

logger = logging.getLogger(__name__)


class FileCache:
    """Singleton file content cache with mtime-based invalidation."""

    _instance: Optional["FileCache"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._cache: dict[str, tuple[float, Any]] = {}
            cls._instance._max_size = 256
        return cls._instance

    def get_json(self, file_path: str | pathlib.Path) -> Optional[Any]:
        """Load and cache JSON file contents, invalidating on mtime change."""
        path_str = str(file_path)

        try:
            mtime = os.path.getmtime(path_str)
        except OSError:
            self._cache.pop(path_str, None)
            return None

        cached = self._cache.get(path_str)
        if cached is not None and cached[0] == mtime:
            return cached[1]

        try:
            with open(path_str, "rb") as f:
                content = orjson.loads(f.read())
        except (orjson.JSONDecodeError, OSError) as e:
            logger.debug(f"Failed to load {path_str}: {e}")
            self._cache.pop(path_str, None)
            return None

        if len(self._cache) >= self._max_size:
            to_remove = list(self._cache.keys())[:self._max_size // 4]
            for key in to_remove:
                del self._cache[key]

        self._cache[path_str] = (mtime, content)
        return content

    def invalidate(self, file_path: str | pathlib.Path) -> None:
        """Remove a specific file from the cache."""
        self._cache.pop(str(file_path), None)

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    @property
    def size(self) -> int:
        """Return number of cached entries."""
        return len(self._cache)
