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

import revedaEditor.backend.libBackEnd as scb


def getLibItem(
    libraryModel: QStandardItemModel, libName: str
) -> Union[scb.libraryItem, None]:
    try:
        libItem = [
            item
            for item in libraryModel.findItems(libName)
            if item.data(Qt.UserRole + 1) == "library"
        ][0]
    except IndexError:
        return libraryModel.item(0, 0)
    return libItem


def getCellItem(
    libItem: scb.libraryItem, cellNameInp: str
) -> Union[scb.cellItem, None]:
    cellItems = [
        libItem.child(i)
        for i in range(libItem.rowCount())
        if libItem.child(i).cellName == cellNameInp
    ]
    if cellItems:
        return cellItems[0]
    return None


# def getViewItem(cellItem: scb.cellItem, viewNameInp: str) -> Union[scb.viewItem, None]:
#     if cellItem is not None:
#         viewItems = [
#             cellItem.child(i)
#             for i in range(cellItem.rowCount())
#             if cellItem.child(i).text() == viewNameInp
#         ]
#     if viewItems:
#         return viewItems[0]
#     return None
def getViewItem(cellItem: scb.cellItem, viewNameInp: str) -> Union[scb.viewItem, None]:
    if cellItem is None:
        return None
    for i in range(cellItem.rowCount()):
        child = cellItem.child(i)
        if child.text() == viewNameInp:
            return child
    return None


def findViewItem(libraryModel, libName: str, cellName: str, viewName: str):
    libItem = getLibItem(libraryModel, libName)
    if libItem:
        cellItem = getCellItem(libItem, cellName)
    if cellItem:
        return getViewItem(cellItem, viewName)
