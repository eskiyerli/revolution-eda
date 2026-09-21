#
# Revolution EDA
#
# Copyright (c) 2026 Revolution Semiconductor
#
# This Source Code Form is subject to the terms of the
# Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
##

"""Bindkey configuration: key sequence -> QAction name.

Shipped defaults live in ``revedaEditor/resources/bindkeys.json``; a
project-level ``bindkeys.json`` in the run directory overrides them. The file
format groups bindings per editor view type so the same key can mean a
different action in schematic vs layout::

    {
        "*":         {"Shift+U": "redoAction", ...},
        "schematic": {"W": "createNetAction", ...},
        "layout":    {"W": "createPathAction", ...},
        "symbol":    {"W": "createLineAction", ...}
    }

Action names are ``QAction`` attribute names on the editor window (for example
``undoAction``). Unknown names or unparsable key sequences are skipped with a
warning so a bad config never breaks editing.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from PySide6.QtGui import QAction, QKeySequence

logger = logging.getLogger("reveda")

DEFAULT_BINDKEYS_PATH = (
    Path(__file__).resolve().parent.parent / "resources" / "bindkeys.json"
)


def _readBindkeySection(raw: dict, source: Path) -> dict:
    """Validate one parsed JSON file; return {section: {keyseq: actionName}}."""
    sections: dict = {}
    if not isinstance(raw, dict):
        logger.warning(f"Bindkey file {source} is not a JSON object; ignored")
        return sections
    for section, mapping in raw.items():
        if not isinstance(mapping, dict):
            logger.warning(
                f"Bindkey section '{section}' in {source} is not an object; skipped"
            )
            continue
        cleaned = {}
        for keySeq, actionName in mapping.items():
            if not isinstance(keySeq, str) or not isinstance(actionName, str):
                logger.warning(
                    f"Invalid bindkey entry {keySeq!r}: {actionName!r} in {source}"
                )
                continue
            cleaned[keySeq] = actionName
        sections[section] = cleaned
    return sections


def loadBindkeyMap(
    defaultsPath: Path | None = None, userPath: Path | None = None
) -> dict:
    """Load shipped defaults merged with the project-level override.

    Returns ``{section: {keySeq: actionName}}``; user entries override the
    defaults within each section.
    """
    defaultsPath = Path(defaultsPath) if defaultsPath else DEFAULT_BINDKEYS_PATH
    merged: dict = {}
    for path in (defaultsPath, userPath):
        if path is None:
            continue
        path = Path(path)
        if not path.is_file():
            continue
        try:
            with path.open("r", encoding="utf-8") as f:
                sections = _readBindkeySection(json.load(f), path)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Cannot read bindkey file {path}: {e}")
            continue
        for section, mapping in sections.items():
            merged.setdefault(section, {}).update(mapping)
    return merged


def applyBindkeys(
    window, keyMap: dict, viewType: str = "*", log: logging.Logger | None = None
) -> int:
    """Apply configured shortcuts to a window's QAction attributes.

    Applies the ``"*"`` section first, then the ``viewType`` section on top.
    Returns the number of shortcuts applied. Unknown action names and invalid
    key sequences are logged and skipped.
    """
    log = log or logger
    applied = 0
    for section in ("*", viewType):
        for keySeq, actionName in keyMap.get(section, {}).items():
            action = getattr(window, actionName, None)
            if not isinstance(action, QAction):
                log.warning(
                    f"Bindkey '{keySeq}' -> '{actionName}' skipped: "
                    f"no such QAction on {type(window).__name__}"
                )
                continue
            sequence = QKeySequence(keySeq)
            if sequence.isEmpty():
                log.warning(
                    f"Bindkey '{keySeq}' -> '{actionName}' skipped: "
                    "unparsable key sequence"
                )
                continue
            action.setShortcut(sequence)
            applied += 1
    return applied
