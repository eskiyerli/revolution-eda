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

"""Icon decoration infrastructure for library browser items.

Each ``libraryItem``/``cellItem``/``viewItem`` gets a base icon plus optional
overlay badges painted in the bottom-right corner. The built-in decorator
shows a lock badge when the cellview's ``.lock`` file exists.

Plugins (e.g. version-control integrations) can contribute their own badges
with :func:`registerItemDecorator`. A decorator is a callable taking the
``QStandardItem`` and returning one of:

- ``None`` — no contribution,
- ``QIcon`` — painted as an overlay badge,
- ``(QIcon, str)`` — badge plus tooltip text appended to the item's tooltip.

Call ``refreshDecorations(model)`` to re-evaluate every item after external
state changes (e.g. a VCS status refresh).
"""

from __future__ import annotations

import datetime
import logging
from typing import Callable, Optional, Tuple, Union

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QGuiApplication, QIcon, QPainter, QStandardItem

import revedaEditor.backend.cellviewState as cvstate

logger = logging.getLogger("reveda")

_ITEM_ROLE = Qt.ItemDataRole.UserRole + 1
_PATH_ROLE = Qt.ItemDataRole.UserRole + 2

_BASE_ICONS = {
    "library": ":/icons/books-stack.png",
    "cell": ":/icons/node-design.png",
}

_VIEW_TYPE_ICONS = {
    "schematic": ":/icons/blue-document-node.png",
    "symbol": ":/icons/node-design.png",
    "layout": ":/icons/layer-shape.png",
    "pcell": ":/icons/blue-document-attribute-s.png",
    "config": ":/icons/document-task.png",
    "veriloga": ":/icons/script-text.png",
    "spice": ":/icons/script-text.png",
    "spectre": ":/icons/script-text.png",
    "vacask": ":/icons/script-text.png",
    "spef": ":/icons/script-text.png",
    "revbench": ":/icons/application-wave.png",
    "dcspec": ":/icons/table.png",
}
_DEFAULT_VIEW_ICON = ":/icons/document.png"

_ICON_SIZE = 16
_OVERLAY_SIZE = 10

DecoratorResult = Union[QIcon, Tuple[QIcon, str], None]
ItemDecorator = Callable[[QStandardItem], DecoratorResult]

_decorators: list[ItemDecorator] = []


def registerItemDecorator(fn: ItemDecorator) -> None:
    """Register a decorator invoked for every library-browser item."""
    if fn not in _decorators:
        _decorators.append(fn)


def unregisterItemDecorator(fn: ItemDecorator) -> None:
    """Remove a decorator previously added with :func:`registerItemDecorator`."""
    if fn in _decorators:
        _decorators.remove(fn)


def itemDecorators() -> tuple[ItemDecorator, ...]:
    return tuple(_decorators)


def _baseIconFor(item: QStandardItem) -> QIcon:
    kind = item.data(_ITEM_ROLE)
    if kind == "view":
        viewType = getattr(item, "viewType", None)
        return QIcon(_VIEW_TYPE_ICONS.get(viewType, _DEFAULT_VIEW_ICON))
    return QIcon(_BASE_ICONS.get(kind, _DEFAULT_VIEW_ICON))


def lockOwnerText(record: dict | None) -> str:
    """Human-readable 'user@host (pid N) since ...' for a lock record."""
    if not record:
        return "unknown owner"
    owner = (f"{record.get('user', '?')}@{record.get('host', '?')} "
             f"(pid {record.get('pid', '?')})")
    timestamp = record.get("time")
    if isinstance(timestamp, (int, float)):
        try:
            since = datetime.datetime.fromtimestamp(timestamp).strftime(
                "%Y-%m-%d %H:%M:%S")
            return f"{owner} since {since}"
        except (OSError, OverflowError, ValueError):
            pass
    return owner


def lockStatusText(status: str, record: dict | None) -> str:
    """Summary line used by tooltips and the File Information dialogue."""
    if status == "locked":
        return f"Locked by {lockOwnerText(record)}"
    if status == "mine":
        return f"Locked by this session ({lockOwnerText(record)})"
    if status == "stale":
        return f"Stale lock ({lockOwnerText(record)})"
    return "Not locked"


def _lockDecorator(item: QStandardItem) -> DecoratorResult:
    """Built-in decorator: lock badge for cellviews with a .lock file."""
    viewPath = item.data(_PATH_ROLE)
    if viewPath is None:
        return None
    status, record = cvstate.inspectLock(viewPath)
    if status == "none":
        return None
    return QIcon(":/icons/lock.png"), lockStatusText(status, record)


def composeIcon(base: QIcon, overlays: list[QIcon],
                size: int = _ICON_SIZE) -> QIcon:
    """Paint overlay badges stacked leftwards in the base icon's corner."""
    if not overlays:
        return base
    pixmap = base.pixmap(size, size)
    painter = QPainter(pixmap)
    x = size - _OVERLAY_SIZE
    y = size - _OVERLAY_SIZE
    for overlay in overlays:
        painter.drawPixmap(QRect(x, y, _OVERLAY_SIZE, _OVERLAY_SIZE),
                           overlay.pixmap(_OVERLAY_SIZE, _OVERLAY_SIZE))
        x -= _OVERLAY_SIZE
    painter.end()
    return QIcon(pixmap)


def decorate(item: QStandardItem) -> None:
    """Set the item's icon and tooltip from its base icon plus badges."""
    base = _baseIconFor(item)
    results: list[DecoratorResult] = []
    if item.data(_ITEM_ROLE) == "view":
        results.append(_lockDecorator(item))
    for fn in _decorators:
        try:
            results.append(fn(item))
        except Exception:
            logger.exception(f"Item decorator {fn!r} failed")
    overlays: list[QIcon] = []
    tips: list[str] = []
    for res in results:
        if res is None:
            continue
        if isinstance(res, tuple):
            icon, tip = res
            overlays.append(icon)
            if tip:
                tips.append(tip)
        elif isinstance(res, QIcon):
            overlays.append(res)
    if overlays and QGuiApplication.instance() is not None:
        item.setIcon(composeIcon(base, overlays))
    else:
        item.setIcon(base)
    if tips:
        item.setToolTip("; ".join(tips))
    else:
        item.setToolTip("")


def refreshDecorations(modelOrItem) -> None:
    """Re-evaluate decorations for an item subtree or a whole model."""
    if isinstance(modelOrItem, QStandardItem):
        _decorateSubtree(modelOrItem)
        return
    root = modelOrItem.invisibleRootItem()
    _decorateSubtree(root)


def _decorateSubtree(item: QStandardItem) -> None:
    for row in range(item.rowCount()):
        child = item.child(row)
        decorate(child)
        if child.hasChildren():
            _decorateSubtree(child)
