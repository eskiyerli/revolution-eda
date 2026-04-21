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


class LVSDevicesTableModel(QAbstractTableModel):
    def __init__(self, devices: List[Dict[str, Any]]):
        super().__init__()
        self._data = devices
        self._headers = ['Device ID', 'Type', 'Name', 'Position', 'Visited']

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
                return str(row.get('id', ''))
            elif col == 1:
                return row.get('type', '')
            elif col == 2:
                return row.get('name', '')
            elif col == 3:
                pos = row.get('position')
                if pos:
                    if isinstance(pos, (list, tuple)) and len(pos) >= 2:
                        return f"({pos[0]}, {pos[1]})"
                    elif isinstance(pos, dict):
                        x = pos.get('x', '')
                        y = pos.get('y', '')
                        return f"({x}, {y})"
                return ""
            elif col == 4:
                return str(row.get('visited', False))
        elif role == Qt.CheckStateRole and col == 4:
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

    def getDevice(self, row):
        """Return the device dict at the given row."""
        if 0 <= row < len(self._data):
            return self._data[row]
        return None

    def markVisited(self, row):
        if 0 <= row < len(self._data):
            self._data[row]['visited'] = True
            index = self.index(row, 4)  # Column 4 is 'Visited'
            self.dataChanged.emit(index, index)


class LVSDevicesTableView(QTableView):
    deviceSelected = Signal(dict)  # Signal to emit selected device dict

    def __init__(self, devices):
        super().__init__()
        self.lvsDevicesModel = LVSDevicesTableModel(devices)
        self.setModel(self.lvsDevicesModel)
        self.selectionModel().currentRowChanged.connect(self.onRowChanged)
        self.header = self.horizontalHeader()
        self.header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.header.setMaximumSectionSize(200)
        self.header.setStretchLastSection(False)

    def onRowChanged(self, current, previous):
        if current.isValid():
            row = current.row()
            self.lvsDevicesModel.markVisited(row)
            device = self.lvsDevicesModel.getDevice(row)
            if device:
                self.deviceSelected.emit(device)


class LVSCellsTableModel(QAbstractTableModel):
    def __init__(self, cells: List[Dict[str, Any]]):
        super().__init__()
        self._data = cells
        self._headers = ['Cell Name', 'Bbox', 'Nets', 'Devices', 'Visited']

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
                return row.get('name', '')
            elif col == 1:
                bbox = row.get('bbox')
                if bbox:
                    if isinstance(bbox, list) and len(bbox) == 2:
                        x1, y1 = bbox[0]
                        x2, y2 = bbox[1]
                        return f"({x1}, {y1}) to ({x2}, {y2})"
                return "No bbox"
            elif col == 2:
                return str(row.get('net_count', 0))
            elif col == 3:
                return str(row.get('device_count', 0))
            elif col == 4:
                return str(row.get('visited', False))
        elif role == Qt.CheckStateRole and col == 4:
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

    def getCell(self, row):
        """Return the cell dict at the given row."""
        if 0 <= row < len(self._data):
            return self._data[row]
        return None

    def markVisited(self, row):
        if 0 <= row < len(self._data):
            self._data[row]['visited'] = True
            index = self.index(row, 4)  # Column 4 is 'Visited'
            self.dataChanged.emit(index, index)


class LVSCellsTableView(QTableView):
    cellSelected = Signal(dict)  # Signal to emit selected cell dict

    def __init__(self, cells):
        super().__init__()
        self.lvsCellsModel = LVSCellsTableModel(cells)
        self.setModel(self.lvsCellsModel)
        self.clicked.connect(self.onCellClicked)  # Use clicked instead of currentRowChanged
        self.header = self.horizontalHeader()
        self.header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.header.setMaximumSectionSize(200)
        self.header.setStretchLastSection(False)

    def onCellClicked(self, index):
        """Handle cell click (fires even on repeated clicks to same row)."""
        if index.isValid():
            row = index.row()
            self.lvsCellsModel.markVisited(row)
            cell = self.lvsCellsModel.getCell(row)
            if cell:
                self.cellSelected.emit(cell)


class LVSCrossrefsTableModel(QAbstractTableModel):
    def __init__(self, crossrefs: List[Dict[str, Any]]):
        super().__init__()
        self._data = crossrefs
        self._headers = ['Layout Cell', 'Schematic Cell', 'Equivalent', 'Net Mismatches',
                        'Pin Mismatches', 'Device Mismatches', 'Visited']

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
                return row.get('layout_cell', '')
            elif col == 1:
                return row.get('schem_cell', '')
            elif col == 2:
                equiv = row.get('equivalent', False)
                return "✓" if equiv else "✗"
            elif col == 3:
                return str(row.get('net_mismatches', 0))
            elif col == 4:
                return str(row.get('pin_mismatches', 0))
            elif col == 5:
                return str(row.get('device_mismatches', 0))
            elif col == 6:
                return str(row.get('visited', False))
        elif role == Qt.CheckStateRole and col == 6:
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

    def getCrossref(self, row):
        """Return the crossref dict at the given row."""
        if 0 <= row < len(self._data):
            return self._data[row]
        return None

    def markVisited(self, row):
        if 0 <= row < len(self._data):
            self._data[row]['visited'] = True
            index = self.index(row, 6)  # Column 6 is 'Visited'
            self.dataChanged.emit(index, index)


class LVSCrossrefsTableView(QTableView):
    crossrefSelected = Signal(dict)  # Signal to emit selected crossref dict

    def __init__(self, crossrefs):
        super().__init__()
        self.lvsCrossrefsModel = LVSCrossrefsTableModel(crossrefs)
        self.setModel(self.lvsCrossrefsModel)
        self.clicked.connect(self.onRowClicked)
        self.header = self.horizontalHeader()
        for i in range(7):
            self.header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        self.header.setMaximumSectionSize(200)
        self.header.setStretchLastSection(False)

    def onRowClicked(self, index):
        """Handle row click (fires even on repeated clicks)."""
        if index.isValid():
            row = index.row()
            self.lvsCrossrefsModel.markVisited(row)
            crossref = self.lvsCrossrefsModel.getCrossref(row)
            if crossref:
                self.crossrefSelected.emit(crossref)
