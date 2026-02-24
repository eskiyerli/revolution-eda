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
                            Signal, QPoint, QRect)
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QHeaderView, QTableView, QMenu)
from revedaEditor.backend.pdkLoader import importPDKModule

process = importPDKModule("process")



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
        if orientation == Qt.Orientation.Horizontal:
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
    zoomToRect = Signal(QRect) # Signal to emit polygon to be zoomed.
    def __init__(self, data, categories):
        super().__init__()
        self.drcOutputsModel = DRCTableModel(data, categories)
        self.setModel(self.drcOutputsModel)
        self.selectionModel().currentRowChanged.connect(self.onRowChanged)
        self.header = self.horizontalHeader()
        self.header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.header.setSectionResizeMode(1, QHeaderView.Stretch)
        self.header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.header.setMaximumSectionSize(200)
        self.header.setStretchLastSection(False)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._onContextMenuRequested)

    def onRowChanged(self, current, previous):
        if current.isValid():
            row = current.row()
            self.drcOutputsModel.markVisited(row)
            polygons = self.drcOutputsModel.getPolygons(row)
            self.polygonSelected.emit(polygons)

    def _onContextMenuRequested(self, pos: QPoint):
        index = self.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        menu = QMenu(self)
        # Example actions (customize as needed)
        copy_points = menu.addAction("Zoom To Error")
        copy_points.triggered.connect(lambda: self._zoomToError(row))
        # menu.addAction("Other action...")
        menu.exec(self.viewport().mapToGlobal(pos))

    def _zoomToError(self, row: int):
        polygonItems = self.drcOutputsModel.getPolygons(row)
        if polygonItems:
            polygonItem = self.drcOutputsModel.getPolygons(row)[0]
            padding = int(getattr(process, 'dbu', 1000)/2)
            self.zoomToRect.emit(polygonItem.polygon().toPolygon().boundingRect().adjusted(-padding, -padding, padding, padding))
            # self.zoomToPolygon.emit(self.drcOutputsModel.getPoints(row))
