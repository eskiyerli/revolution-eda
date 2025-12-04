#     "Commons Clause" License Condition v1.0
#    #
#     The Software is provided to you by the Licensor under the License, as defined
#     below, subject to the following condition.
#  #
#     Without limiting other conditions in the License, the grant of rights under the
#     License will not include, and the License does not grant to you, the right to
#     Sell the Software.
#  #
#     For purposes of the foregoing, "Sell" means practicing any or all of the rights
#     granted to you under the License to provide to third parties, for a fee or other
#     consideration (including without limitation fees for hosting) a product or service whose value
#     derives, entirely or substantially, from the functionality of the Software. Any
#     license notice or attribution required by the License must also include this
#     Commons Clause License Condition notice.
#  #
#    Add-ons and extensions developed for this software may be distributed
#    under their own separate licenses.
#  #
#     Software: Revolution EDA
#     License: Mozilla Public License 2.0
#     Licensor: Revolution Semiconductor (Registered in the Netherlands)

from PySide6.QtCore import (QAbstractTableModel, Qt, QModelIndex, QPersistentModelIndex, Signal)
from PySide6.QtWidgets import (QHeaderView, QTableView)
from PySide6.QtGui import QFont
from typing import List, Dict, Any


class DRCTableModel(QAbstractTableModel):
    def __init__(self, violations: List[Dict[str, Any]],
                 categories: Dict[str, str]):
        super().__init__()
        self._data = violations

        self._categories = categories
        self._headers = ['Category', 'Description', 'Cell', 'Visited',
                         'Multiplicity', 'Points']

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None

        row = self._data[index.row()]

        col = index.column()

        # Handle case where row might be a string instead of dict
        if isinstance(row, str):
            return row if col == 0 else ""

        if col == 0:
            return row.get('category', '')
        elif col == 1:
            return self._categories.get(row.get('category', ''))
        elif col == 2:
            return row.get('cell', '')
        elif col == 3:
            return str(row.get('visited', ''))
        elif col == 4:
            return str(row.get('multiplicity', ''))
        elif col == 5:
            return str(row.get('points', ''))

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                return self._headers[section]
            elif role == Qt.FontRole:
                font = QFont()
                font.setBold(True)
                return font
        return None

    def getPolygons(self, row):
        return self._data[row]['polygons']
    
    def markVisited(self, row):
        if 0 <= row < len(self._data):
            self._data[row]['visited'] = True
            index = self.index(row, 3)  # Column 3 is 'Visited'
            self.dataChanged.emit(index, index)


class DRCTableView(QTableView):
    polygonSelected = Signal(list)  # Signal to emit selected polygons

    def __init__(self, data, categories):
        super().__init__()
        self.model = DRCTableModel(data, categories)
        self.setModel(self.model)
        self.selectionModel().currentRowChanged.connect(self.onRowChanged)
        self.header = self.horizontalHeader()
        self.header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.header.setStretchLastSection(True)

    def onRowChanged(self, current, previous):
        if current.isValid():
            row = current.row()
            self.model.markVisited(row)
            polygons = self.model.getPolygons(row)
            self.polygonSelected.emit(polygons)
