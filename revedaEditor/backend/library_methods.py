#    “Commons Clause” License Condition v1.0
#   #
#    The Software is provided to you by the Licensor under the License, as defined
#    below, subject to the following condition.
#   #
#    Without limiting other conditions in the License, the grant of rights under the
#    License will not include, and the License does not grant to you, the right to
#    Sell the Software.
#   #
#    For purposes of the foregoing, “Sell” means practicing any or all of the rights
#    granted to you under the License to provide to third parties, for a fee or other
#    consideration (including without limitation fees for hosting) a product or service whose value
#    derives, entirely or substantially, from the functionality of the Software. Any
#    license notice or attribution required by the License must also include this
#    Commons Clause License Condition notice.
#   #
#    Software: Revolution EDA
#    License: Mozilla Public License 2.0
#    Licensor: Revolution Semiconductor (Registered in the Netherlands)

from typing import Union

from PySide6.QtCore import (
    Qt,
)
from PySide6.QtGui import QStandardItemModel

import revedaEditor.backend.lib_back_end as scb


def getLibItem(
        libraryModel: QStandardItemModel, libName: str
) -> Union[scb.LibraryItem, None]:
    return next((item for item in libraryModel.findItems(libName)
                 if item.data(Qt.ItemDataRole.UserRole + 1) == "library"), None)


def getCellItem(
        libItem: Union[scb.LibraryItem, None], cellNameInp: str
) -> Union[scb.CellItem, None]:
    if libItem is None:
        return None
    return next((libItem.child(i) for i in range(libItem.rowCount())
                 if libItem.child(i) and libItem.child(i).cellName == cellNameInp), None)


def getViewItem(CellItem: Union[scb.CellItem, None], viewNameInp: str) -> Union[
    scb.ViewItem, None]:
    if CellItem is None:
        return None
    return next((CellItem.child(i) for i in range(CellItem.rowCount())
                 if CellItem.child(i) and CellItem.child(i).text() == viewNameInp), None)


def findViewItem(libraryModel, libName: str, cellName: str, viewName: str) -> Union[
    scb.ViewItem, None]:
    libItem = getLibItem(libraryModel, libName)
    if libItem:
        CellItem = getCellItem(libItem, cellName)
        if CellItem:
            return getViewItem(CellItem, viewName)
    return None
