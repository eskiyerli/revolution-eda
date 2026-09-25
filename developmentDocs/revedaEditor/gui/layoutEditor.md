# `revedaEditor\gui\layoutEditor.py`

**Module:** `revedaEditor.gui.layoutEditor`

## Purpose

Module in `revedaEditor\gui`.

## Classes

- `layoutEditor(edw.editorWindow)`
  - `init_UI()`
  - `highlightNetClick()`
  - `clearNetHighlightsClick()`
  - `cutClick()`
  - `mergeClick()`
  - `layerOpsClick()`
  - `flattenClick()`
  - `makeCellClick()`
  - `createRectClick()`
  - `createRulerClick()`
  - `delSelectedRulerClick()`
  - `delRulerClick()`
  - `createPathClick()`
  - `editActivePlacementOptions()`
  - `createPinClick()`
  - `createLabelClick()`
  - `createViaClick()`
  - `createMultipartClick()`
  - `createPolygonClick()`
  - `objPropClick()`
  - `goDownClick()`
  - `checkSaveCell()`
  - `saveCell()`
  - `loadLayout()`
  - `createInstClick()`
  - `exportGDSClick()`
  - `exportOASClick()`
  - `handlePolygonSelection()`
  - `clearDRCPolygons()`
  - `handleLVSRectSelection()`
  - `renumberInstanceClick()`
  - `sdlLoadClick()`
  - `dispConfigEdit()`
  - `closeEvent()`
  - `lvsRectangles()`
  - `drcPolygons()`
  - internals: `_createMenuBar()`, `_createActions()`, `_addActions()`, `_layoutContextMenu()`, `_createToolBars()`, `_createTriggers()`, `_createShortcuts()`, `_configureRulerOptions()`, `_configureLayoutInstanceOptions()`, `_configureLayoutPinPlacement()`, `_configureLayoutLabelPlacement()`, `_configureViaPlacement()` … (+4)
- `layoutContainer(edw.editorContainer)`
  - `init_UI()`
  - `findSelectedLayer()`
  - `selectLayer()`
  - `layerSelectableChange()`
  - `layerVisibleChange()`
  - `objectVisibleChange()`
  - `objectSelectableChange()`
- `LayerFilterProxyModel(QSortFilterProxyModel)` — Proxy model that matches the search string against layer name OR purpose,
  - `setUsedLayersOnly()`
  - `setUsedLayerRows()`
  - `filterAcceptsRow()`
- `lswWindow(QWidget)`
  - internals: `_updateFilteredLayers()`, `_allLayersVisible()`, `_noLayersVisible()`, `_allLayersSelectable()`, `_noLayersSelectable()`, `_toggleUsedLayers()`, `_getUsedLayerRows()`

## Depends on

- [[revedaEditor\backend\dataDefinitions|revedaEditor.backend.dataDefinitions]]
- [[revedaEditor\backend\libBackEnd|revedaEditor.backend.libBackEnd]]
- [[revedaEditor\backend\libraryMethods|revedaEditor.backend.libraryMethods]]
- [[revedaEditor\backend\libraryModelView|revedaEditor.backend.libraryModelView]]
- [[revedaEditor\backend\pdkLoader|revedaEditor.backend.pdkLoader]]
- [[revedaEditor\common\layoutShapes|revedaEditor.common.layoutShapes]]
- [[revedaEditor\gui\editorViews|revedaEditor.gui.editorViews]]
- [[revedaEditor\gui\editorWindow|revedaEditor.gui.editorWindow]]
- [[revedaEditor\gui\fileDialogues|revedaEditor.gui.fileDialogues]]
- [[revedaEditor\gui\layoutDialogues|revedaEditor.gui.layoutDialogues]]
- [[revedaEditor\gui\lsw|revedaEditor.gui.lsw]]
- [[revedaEditor\scenes\layoutScene|revedaEditor.scenes.layoutScene]]

## Used by

- [[revedaEditor\tests\test_sdl_adapter|revedaEditor.tests.test_sdl_adapter]]
- [[revedaEditor\tests\test_sdl_free_baseline|revedaEditor.tests.test_sdl_free_baseline]]
