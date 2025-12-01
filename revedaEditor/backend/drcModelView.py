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

from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex, Signal
from PySide6.QtWidgets import QTableView
from typing import List, Dict, Any


class DRCTableModel(QAbstractTableModel):
    def __init__(self, data: List[Dict[str, Any]]):
        super().__init__()
        self._data = data
        self._headers = ['Category', 'Cell', 'Visited', 'Multiplicity', 'Polygons', 'Points']

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
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
            return row.get('cell', '')
        elif col == 2:
            return str(row.get('visited', ''))
        elif col == 3:
            return str(row.get('multiplicity', ''))
        elif col == 4:
            polygons = row.get('polygons', [])
            return f"{len(polygons)} polygon(s)" if polygons else "0 polygon(s)"
        elif col == 5:
            return str(row.get('points', ''))

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]
        return None

    def getPolygons(self, row):
        return self._data[row]['polygons']


class DRCTableView(QTableView):
    polygonSelected = Signal(list)  # Signal to emit selected polygons

    def __init__(self, data):
        super().__init__()
        self.model = DRCTableModel(data)
        self.setModel(self.model)
        self.selectionModel().currentRowChanged.connect(self.onRowChanged)

    def onRowChanged(self, current, previous):
        if current.isValid():
            polygons = self.model.getPolygons(current.row())
            self.polygonSelected.emit(polygons)
