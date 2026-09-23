# `revedaEditor/backend/drcModelView.py`

**Module:** `revedaEditor.backend.drcModelView`

## Purpose

Qt table model/view pair used to browse KLayout DRC results.

## Classes

- `DRCTableModel(QAbstractTableModel)`
  - `rowCount()`
  - `columnCount()`
  - `data()`
  - `headerData()`
  - `getPolygons()`
  - `markVisited()`
- `DRCTableView(QTableView)`
  - `onRowChanged()`
  - internals: `_onContextMenuRequested()`, `_zoomToError()`

## Depends on

- [[revedaEditor/backend/pdkLoader|revedaEditor.backend.pdkLoader]]

## Used by

- [[revedaEditor/gui/layoutDialogues|revedaEditor.gui.layoutDialogues]]
