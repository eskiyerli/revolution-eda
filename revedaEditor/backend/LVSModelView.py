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

from typing import List, Dict, Any

from PySide6.QtCore import (QAbstractTableModel, Qt, QModelIndex, QPersistentModelIndex,
                            Signal)
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QHeaderView, QTableView)


class LVSNetsTableModel(QAbstractTableModel):
    def __init__(self, nets: List[Dict[str, Any]]):
        super().__init__()
        self._data = nets
        self._headers = ['Net ID', 'Name', 'Shapes Count', 'Visited']

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        row = self._data[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:
                return row.get('net_id', '')
            elif col == 1:
                return row.get('name', '')
            elif col == 2:
                return str(len(row.get('shapes', [])))
            elif col == 3:
                return str(row.get('visited', False))
        elif role == Qt.CheckStateRole and col == 3:
            return Qt.Checked if row.get('visited', False) else Qt.Unchecked

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.DisplayRole:
                return self._headers[section]
            elif role == Qt.FontRole:
                font = QFont()
                font.setBold(True)
                return font
        return None

    def getShapes(self, row):
        return self._data[row].get('shapes', [])

    def markVisited(self, row):
        if 0 <= row < len(self._data):
            self._data[row]['visited'] = True
            index = self.index(row, 3)  # Column 3 is 'Visited'
            self.dataChanged.emit(index, index)


class LVSNetsTableView(QTableView):
    netSelected = Signal(list)  # Signal to emit selected net's shapes

    def __init__(self, nets):
        super().__init__()
        self.lvsNetsModel = LVSNetsTableModel(nets)
        self.setModel(self.lvsNetsModel)
        self.selectionModel().currentRowChanged.connect(self.onRowChanged)
        self.header = self.horizontalHeader()
        self.header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.header.setMaximumSectionSize(200)
        self.header.setStretchLastSection(False)

    def onRowChanged(self, current, previous):
        if current.isValid():
            row = current.row()
            self.lvsNetsModel.markVisited(row)
            shapes = self.lvsNetsModel.getShapes(row)
            self.netSelected.emit(shapes)
