# `revedaEditor\gui\lsw.py`

**Module:** `revedaEditor.gui.lsw`

## Purpose

Module in `revedaEditor\gui`.

## Classes

- `layerDataModel(QStandardItemModel)`
  - `createData()`
  - `readFileContent()`
  - `createImage()`
- `TextureDelegate(QStyledItemDelegate)`
  - `paint()`
- `layerViewTable(QTableView)`
  - `setupUi()`
  - `connectSignals()`
  - `getLayerInfo()`
  - `onDataChanged()`
  - `onClicked()`
  - `onSelectionChanged()`
  - `updateAllLayers()`
  - `noLayersVisible()`
  - `allLayersVisible()`
  - `noLayersSelectable()`
  - `allLayersSelectable()`
- `objectsFilterModel(QStandardItemModel)` — Model backing the objects filter table: one row per object category
- `objectsFilterTable(QTableView)`
  - `setupUi()`
  - `onDataChanged()`

## Depends on

- [[revedaEditor\backend\pdkLoader|revedaEditor.backend.pdkLoader]]

## Used by

- [[revedaEditor\gui\layoutEditor|revedaEditor.gui.layoutEditor]]
