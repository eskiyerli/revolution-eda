# `revedaEditor/scenes/layoutScene.py`

**Module:** `revedaEditor.scenes.layoutScene`

## Purpose

`layoutScene` — layout editing state: `saveLayoutCell`/`loadDesign`, connectivity + net highlighting, SDL incremental sync, flylines, boolean/flatten/merge/multipart operations, and persistent item grouping (`groupSelectedItems`/`ungroupSelectedItems` via `layoutGroup` + `undoGroupShapes`).

## Classes

- `layoutScene(editorScene)`
  - `drawMode()`
  - `toLayoutCoord()`
  - `toLayoutDistance()`
  - `toSceneCoord()`
  - `mousePressEvent()`
  - `mouseMoveEvent()`
  - `mouseReleaseEvent()`
  - `addLayoutViaArray()`
  - `snapToClosestEdge()`
  - `drawLayoutRuler()`
  - `drawLayoutMultipart()`
  - `finishCutLine()`
  - `mergeSelectedItems()`
  - `groupSelectedItems()`
  - `ungroupSelectedItems()`
  - `booleanSelectedItems()`
  - `flattenSelection()`
  - `makeCellFromSelection()`
  - `startCutLine()`
  - `drawLayoutPolygon()`
  - `addLayoutInstance()`
  - `addLayoutLabel()`
  - `drawLayoutPin()`
  - `drawLayoutRect()`
  - `drawLayoutPath()`
  - `cyclePathMode()`
  - `addNewInstance()`
  - `instLayout()`
  - `findScenelayoutCellSet()`
  - `pinLabelItems()`
  - `objectCategory()`
  - `objectVisible()`
  - `objectSelectable()`
  - `setObjectClassVisible()`
  - `setObjectClassSelectable()`
  - `addUndoStack()`
  - `addListUndoStack()`
  - `loadSchematicInstances()`
  - `updateFromSchematic()`
  - `saveLayoutCell()`
  - `exportCellGDS()`
  - `exportCellOAS()`
  - `loadDesign()`
  - `createLayoutItems()`
  - `deleteSelectedItems()`
  - `viewObjProperties()`
  - `layoutPolygonProperties()`
  - `layoutMultipartProperties()`
  - `layoutRectProperties()`
  - `layoutViaProperties()`
  - `layoutPathProperties()`
  - `layoutLabelProperties()`
  - `layoutPinProperties()`
  - `layoutInstanceProperties()`
  - `changePcellParameterFields()`
  - `extractPcellInstanceParameters()`
  - `clearLayout()`
  - `moveBySelectedItems()`
  - `copySelectedItems()`
  - `deleteAllRulers()`
  - `deleteSelectedRulers()`
  - `markConnectivityDirty()`
  - `addItem()`
  - `removeItem()`
  - `rebuildConnectivity()`
  - `connectivity()`
  - `highlightNetAtPoint()`
  - `clearNetHighlights()`
  - `clearFlylines()`
  - `rebuildFlylines()`
  - `probeSchematic()`
  - `selectProbeTargets()`
  - `highlightNetGroupsForEndpoints()`
  - `goDownHier()`
  - `findClosestFontSize()`
  - `setRulerFont()`
  - `updateItem()`
  - `renumberInstances()`
  - internals: `_updateLabelPlacementMarker()`, `_removeLabelPlacementMarker()`, `_handleMouseRelease()`, `_splitPolygonalShape()`, `_splitRect()`, `_splitPolygon()`, `_splitPath()`, `_handleAlignItemLine()`, `_createLayoutPath()`, `_filterBySelectModes()`, `_itemPassesFilter()`, `_applyItemObjectState()` … (+22)

## Depends on

- [[revedaEditor/backend/correspondence|revedaEditor.backend.correspondence]]
- [[revedaEditor/backend/dataDefinitions|revedaEditor.backend.dataDefinitions]]
- [[revedaEditor/backend/libraryMethods|revedaEditor.backend.libraryMethods]]
- [[revedaEditor/backend/libraryModelView|revedaEditor.backend.libraryModelView]]
- [[revedaEditor/backend/pdkLoader|revedaEditor.backend.pdkLoader]]
- [[revedaEditor/backend/undoStack|revedaEditor.backend.undoStack]]
- [[revedaEditor/common/layoutBoolean|revedaEditor.common.layoutBoolean]]
- [[revedaEditor/common/layoutFlatten|revedaEditor.common.layoutFlatten]]
- [[revedaEditor/common/layoutMerge|revedaEditor.common.layoutMerge]]
- [[revedaEditor/common/layoutShapes|revedaEditor.common.layoutShapes]]
- [[revedaEditor/connectivity/__init__|revedaEditor.connectivity.__init__]]
- [[revedaEditor/fileio/exportGDS|revedaEditor.fileio.exportGDS]]
- [[revedaEditor/fileio/layoutEncoder|revedaEditor.fileio.layoutEncoder]]
- [[revedaEditor/fileio/loadJSON|revedaEditor.fileio.loadJSON]]
- [[revedaEditor/fileio/schemaValidation|revedaEditor.fileio.schemaValidation]]
- [[revedaEditor/gui/alignItems|revedaEditor.gui.alignItems]]
- [[revedaEditor/gui/editFunctions|revedaEditor.gui.editFunctions]]
- [[revedaEditor/gui/fileDialogues|revedaEditor.gui.fileDialogues]]
- [[revedaEditor/gui/layoutDialogues|revedaEditor.gui.layoutDialogues]]
- [[revedaEditor/gui/propertyDialogues|revedaEditor.gui.propertyDialogues]]
- [[revedaEditor/scenes/editorScene|revedaEditor.scenes.editorScene]]

## Used by

- [[revedaEditor/gui/editorViews|revedaEditor.gui.editorViews]]
- [[revedaEditor/gui/layoutEditor|revedaEditor.gui.layoutEditor]]
- [[revedaEditor/tests/test_layout_transforms|revedaEditor.tests.test_layout_transforms]]
