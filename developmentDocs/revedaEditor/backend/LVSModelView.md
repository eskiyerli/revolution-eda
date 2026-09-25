# `revedaEditor\backend\LVSModelView.py`

**Module:** `revedaEditor.backend.LVSModelView`

## Purpose

Module in `revedaEditor\backend`.

## Classes

- `LVSNetsTableModel(QAbstractTableModel)`
  - `rowCount()`
  - `columnCount()`
  - `data()`
  - `headerData()`
  - `getShapes()`
  - `getNet()`
  - `markVisited()`
  - `updateData()`
- `LVSNetsTableView(QTableView)`
  - `onRowChanged()`
- `LVSDevicesTableModel(QAbstractTableModel)`
  - `rowCount()`
  - `columnCount()`
  - `data()`
  - `headerData()`
  - `getDevice()`
  - `markVisited()`
  - `updateData()`
- `LVSDevicesTableView(QTableView)`
  - `onRowChanged()`
- `LVSCellsTableModel(QAbstractTableModel)`
  - `rowCount()`
  - `columnCount()`
  - `data()`
  - `headerData()`
  - `getCell()`
  - `markVisited()`
  - `updateData()`
- `LVSCellsTableView(QTableView)`
  - `onCellClicked()`
- `LVSCrossrefsTableModel(QAbstractTableModel)`
  - `rowCount()`
  - `columnCount()`
  - `data()`
  - `headerData()`
  - `getCrossref()`
  - `markVisited()`
  - `updateData()`
- `LVSCrossrefsTableView(QTableView)`
  - `onCellClicked()`
- `LVSDeviceParamMismatchTableModel(QAbstractTableModel)`
  - `rowCount()`
  - `columnCount()`
  - `data()`
  - `headerData()`
  - `getRow()`
  - `updateData()`
- `LVSDeviceParamMismatchTableView(QTableView)`
  - `onCellClicked()`
- `LVSTerminalMismatchTableModel(QAbstractTableModel)`
  - `rowCount()`
  - `columnCount()`
  - `data()`
  - `headerData()`
  - `getRow()`
  - `updateData()`
- `LVSTerminalMismatchTableView(QTableView)`
  - `onCellClicked()`
- `LVSNetMismatchTableModel(QAbstractTableModel)`
  - `rowCount()`
  - `columnCount()`
  - `data()`
  - `headerData()`
  - `getRow()`
  - `updateData()`
- `LVSNetMismatchTableView(QTableView)`
  - `onCellClicked()`
- `LVSMissingItemTableModel(QAbstractTableModel)`
  - `rowCount()`
  - `columnCount()`
  - `data()`
  - `headerData()`
  - `getRow()`
  - `updateData()`
- `LVSMissingItemTableView(QTableView)`
  - `onCellClicked()`

## Used by

- [[revedaEditor\gui\lvsResults|revedaEditor.gui.lvsResults]]
- [[revedaEditor\tests\test_lvs_mismatch_view|revedaEditor.tests.test_lvs_mismatch_view]]
