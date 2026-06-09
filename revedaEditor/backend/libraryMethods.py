# SPDX-License-Identifier: MPL-2.0
#
# Copyright (c) 2024-2026 Revolution Semiconductor (Registered in the Netherlands)
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this file, You can obtain one at
# https://mozilla.org/MPL/2.0/.
#
# Add-ons and extensions developed for this software may be distributed
# under their own separate licenses.

from typing import Union

from PySide6.QtCore import (
    Qt,
)
from PySide6.QtGui import QStandardItemModel

import revedaEditor.backend.libBackEnd as scb


def getLibItem(
        libraryModel: QStandardItemModel, libName: str
) -> Union[scb.libraryItem, None]:
    return next((item for item in libraryModel.findItems(libName)
                 if item.data(Qt.ItemDataRole.UserRole + 1) == "library"), None)


def getCellItem(
        libItem: Union[scb.libraryItem, None], cellNameInp: str
) -> Union[scb.cellItem, None]:
    if libItem is None:
        return None
    return next((libItem.child(i) for i in range(libItem.rowCount())
                 if libItem.child(i) and libItem.child(i).cellName == cellNameInp), None)


def getViewItem(cellItem: Union[scb.cellItem, None], viewNameInp: str) -> Union[
    scb.viewItem, None]:
    if cellItem is None:
        return None
    return next((cellItem.child(i) for i in range(cellItem.rowCount())
                 if cellItem.child(i) and cellItem.child(i).text() == viewNameInp), None)


def findViewItem(libraryModel, libName: str, cellName: str, viewName: str) -> Union[
    scb.viewItem, None]:
    libItem = getLibItem(libraryModel, libName)
    if libItem:
        cellItem = getCellItem(libItem, cellName)
        if cellItem:
            return getViewItem(cellItem, viewName)
    return None
