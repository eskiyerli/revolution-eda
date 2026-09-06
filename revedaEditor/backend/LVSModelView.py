# SPDX-License-Identifier: MPL-2.0
#
# Copyright (c) 2024-2026 Revolution Semiconductor (Registered in the Netherlands)
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this file, You can obtain one at
# https://mozilla.org/MPL/2.0/.
#
# Add-ons and extensions developed for this software may be distributed
# under their own separate licenses.

from typing import List, Dict, Any, Optional

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

    def getNet(self, row):
        if 0 <= row < len(self._data):
            return self._data[row]
        return None

    def markVisited(self, row):
        if 0 <= row < len(self._data):
            self._data[row]['visited'] = True
            index = self.index(row, 3)  # Column 3 is 'Visited'
            self.dataChanged.emit(index, index)

    def updateData(self, nets: List[Dict[str, Any]]):
        self.beginResetModel()
        self._data = nets
        self.endResetModel()


class LVSNetsTableView(QTableView):
    netSelected = Signal(list)  # Signal to emit selected net's shapes
    netDataSelected = Signal(dict)  # Signal to emit selected net row data

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
            net_data = self.lvsNetsModel.getNet(row)
            if net_data:
                self.netDataSelected.emit(net_data)


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

    def updateData(self, devices: List[Dict[str, Any]]):
        self.beginResetModel()
        self._data = devices
        self.endResetModel()


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

    def updateData(self, cells: List[Dict[str, Any]]):
        self.beginResetModel()
        self._data = cells
        self.endResetModel()


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
        self._headers = ['Layout Cell', 'Schematic Cell', 'Equivalent', 'Net Mism.',
                        'Pin Mism.', 'Device Mism.', 'Total Items', 'Visited']

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
                return str(row.get('total_mappings', 0))
            elif col == 7:
                return str(row.get('visited', False))
        elif role == Qt.CheckStateRole and col == 7:
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
            index = self.index(row, 7)  # Column 7 is 'Visited'
            self.dataChanged.emit(index, index)

    def updateData(self, crossrefs: List[Dict[str, Any]]):
        self.beginResetModel()
        self._data = crossrefs
        self.endResetModel()


class LVSCrossrefsTableView(QTableView):
    # Signal emits (crossref_dict, mismatch_type) where mismatch_type is 'nets', 'pins', 'devices', or 'all'
    crossrefSelected = Signal(dict, str)

    # Column indices for mismatch columns
    NET_MISMATCH_COL = 3
    PIN_MISMATCH_COL = 4
    DEVICE_MISMATCH_COL = 5

    def __init__(self, crossrefs):
        super().__init__()
        self.lvsCrossrefsModel = LVSCrossrefsTableModel(crossrefs)
        self.setModel(self.lvsCrossrefsModel)
        self.clicked.connect(self.onCellClicked)
        self.header = self.horizontalHeader()
        for i in range(8):
            self.header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        self.header.setMaximumSectionSize(200)
        self.header.setStretchLastSection(False)

    def onCellClicked(self, index):
        """Handle cell click - emits crossref with mismatch type based on column."""
        if not index.isValid():
            return

        row = index.row()
        col = index.column()
        self.lvsCrossrefsModel.markVisited(row)
        crossref = self.lvsCrossrefsModel.getCrossref(row)
        if not crossref:
            return

        # Determine which type of mismatch was clicked based on column
        if col == self.NET_MISMATCH_COL:
            mismatch_type = 'nets'
        elif col == self.PIN_MISMATCH_COL:
            mismatch_type = 'pins'
        elif col == self.DEVICE_MISMATCH_COL:
            mismatch_type = 'devices'
        else:
            mismatch_type = 'all'

        self.crossrefSelected.emit(crossref, mismatch_type)


class LVSDeviceParamMismatchTableModel(QAbstractTableModel):
    def __init__(self, rows: List[Dict[str, Any]]):
        super().__init__()
        self._data = rows
        self._headers = [
            'Layout Dev', 'Schem Dev', 'Type', 'Parameter',
            'Layout Value', 'Schem Value', 'Delta / Diff', 'Status'
        ]

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return None

        row = self._data[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return str(row.get('layout_dev', ''))
            elif col == 1:
                return str(row.get('schem_dev', ''))
            elif col == 2:
                return str(row.get('device_type', ''))
            elif col == 3:
                return str(row.get('param_name', ''))
            elif col == 4:
                return str(row.get('layout_val_str', ''))
            elif col == 5:
                return str(row.get('schem_val_str', ''))
            elif col == 6:
                return str(row.get('delta_str', ''))
            elif col == 7:
                return str(row.get('status', ''))
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in (4, 5, 6):
                return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            elif col == 7:
                return int(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                return self._headers[section]
            elif role == Qt.ItemDataRole.FontRole:
                font = QFont()
                font.setBold(True)
                return font
        return None

    def getRow(self, row: int) -> Optional[Dict[str, Any]]:
        if 0 <= row < len(self._data):
            return self._data[row]
        return None

    def updateData(self, rows: List[Dict[str, Any]]):
        self.beginResetModel()
        self._data = rows
        self.endResetModel()


class LVSDeviceParamMismatchTableView(QTableView):
    itemSelected = Signal(dict)

    def __init__(self, rows: List[Dict[str, Any]] = None):
        super().__init__()
        self.paramModel = LVSDeviceParamMismatchTableModel(rows or [])
        self.setModel(self.paramModel)
        self.clicked.connect(self.onCellClicked)
        self.setAlternatingRowColors(True)
        self.header = self.horizontalHeader()
        for i in range(len(self.paramModel._headers)):
            self.header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        self.header.setStretchLastSection(False)

    def onCellClicked(self, index):
        if index.isValid():
            row_data = self.paramModel.getRow(index.row())
            if row_data:
                self.itemSelected.emit(row_data)


class LVSTerminalMismatchTableModel(QAbstractTableModel):
    def __init__(self, rows: List[Dict[str, Any]]):
        super().__init__()
        self._data = rows
        self._headers = [
            'Device / Instance', 'Terminal', 'Layout Net', 'Schematic Net', 'Status'
        ]

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return None

        row = self._data[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return str(row.get('device_name', ''))
            elif col == 1:
                return str(row.get('terminal', ''))
            elif col == 2:
                return str(row.get('layout_net', ''))
            elif col == 3:
                return str(row.get('schem_net', ''))
            elif col == 4:
                return str(row.get('status', ''))
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col == 4:
                return int(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                return self._headers[section]
            elif role == Qt.ItemDataRole.FontRole:
                font = QFont()
                font.setBold(True)
                return font
        return None

    def getRow(self, row: int) -> Optional[Dict[str, Any]]:
        if 0 <= row < len(self._data):
            return self._data[row]
        return None

    def updateData(self, rows: List[Dict[str, Any]]):
        self.beginResetModel()
        self._data = rows
        self.endResetModel()


class LVSTerminalMismatchTableView(QTableView):
    itemSelected = Signal(dict)

    def __init__(self, rows: List[Dict[str, Any]] = None):
        super().__init__()
        self.terminalModel = LVSTerminalMismatchTableModel(rows or [])
        self.setModel(self.terminalModel)
        self.clicked.connect(self.onCellClicked)
        self.setAlternatingRowColors(True)
        self.header = self.horizontalHeader()
        for i in range(len(self.terminalModel._headers)):
            self.header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        self.header.setStretchLastSection(False)

    def onCellClicked(self, index):
        if index.isValid():
            row_data = self.terminalModel.getRow(index.row())
            if row_data:
                self.itemSelected.emit(row_data)


class LVSNetMismatchTableModel(QAbstractTableModel):
    def __init__(self, rows: List[Dict[str, Any]]):
        super().__init__()
        self._data = rows
        self._headers = [
            'Type', 'Layout Net / Pin', 'Schematic Net / Pin', 'Status', 'Diagnostic Details'
        ]

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return None

        row = self._data[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return str(row.get('item_type', ''))
            elif col == 1:
                return str(row.get('layout_ref', ''))
            elif col == 2:
                return str(row.get('schem_ref', ''))
            elif col == 3:
                return str(row.get('status', ''))
            elif col == 4:
                return str(row.get('details', ''))
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col == 3:
                return int(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                return self._headers[section]
            elif role == Qt.ItemDataRole.FontRole:
                font = QFont()
                font.setBold(True)
                return font
        return None

    def getRow(self, row: int) -> Optional[Dict[str, Any]]:
        if 0 <= row < len(self._data):
            return self._data[row]
        return None

    def updateData(self, rows: List[Dict[str, Any]]):
        self.beginResetModel()
        self._data = rows
        self.endResetModel()


class LVSNetMismatchTableView(QTableView):
    itemSelected = Signal(dict)

    def __init__(self, rows: List[Dict[str, Any]] = None):
        super().__init__()
        self.netMismatchModel = LVSNetMismatchTableModel(rows or [])
        self.setModel(self.netMismatchModel)
        self.clicked.connect(self.onCellClicked)
        self.setAlternatingRowColors(True)
        self.header = self.horizontalHeader()
        for i in range(len(self.netMismatchModel._headers)):
            self.header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        self.header.setStretchLastSection(False)

    def onCellClicked(self, index):
        if index.isValid():
            row_data = self.netMismatchModel.getRow(index.row())
            if row_data:
                self.itemSelected.emit(row_data)


class LVSMissingItemTableModel(QAbstractTableModel):
    def __init__(self, rows: List[Dict[str, Any]]):
        super().__init__()
        self._data = rows
        self._headers = [
            'Category', 'Name / ID', 'Type', 'Parameters / Details', 'Terminals / Location', 'Status'
        ]

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return None

        row = self._data[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return str(row.get('category', ''))
            elif col == 1:
                return str(row.get('name', ''))
            elif col == 2:
                return str(row.get('type', ''))
            elif col == 3:
                return str(row.get('details', ''))
            elif col == 4:
                return str(row.get('terminals', ''))
            elif col == 5:
                return str(row.get('status', ''))
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in (0, 5):
                return int(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                return self._headers[section]
            elif role == Qt.ItemDataRole.FontRole:
                font = QFont()
                font.setBold(True)
                return font
        return None

    def getRow(self, row: int) -> Optional[Dict[str, Any]]:
        if 0 <= row < len(self._data):
            return self._data[row]
        return None

    def updateData(self, rows: List[Dict[str, Any]]):
        self.beginResetModel()
        self._data = rows
        self.endResetModel()


class LVSMissingItemTableView(QTableView):
    itemSelected = Signal(dict)

    def __init__(self, rows: List[Dict[str, Any]] = None):
        super().__init__()
        self.missingModel = LVSMissingItemTableModel(rows or [])
        self.setModel(self.missingModel)
        self.clicked.connect(self.onCellClicked)
        self.setAlternatingRowColors(True)
        self.header = self.horizontalHeader()
        for i in range(len(self.missingModel._headers)):
            self.header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        self.header.setStretchLastSection(False)

    def onCellClicked(self, index):
        if index.isValid():
            row_data = self.missingModel.getRow(index.row())
            if row_data:
                self.itemSelected.emit(row_data)
