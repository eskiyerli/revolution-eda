# `revedaEditor\scenes\schematicScene.py`

**Module:** `revedaEditor.scenes.schematicScene`

## Purpose

Module in `revedaEditor\scenes`.

## Classes

- `findHit` — One find/replace result.
- `schematicScene(editorScene)`
  - `defineSnapRect()`
  - `drawMode()`
  - `mousePressEvent()`
  - `mouseMoveEvent()`
  - `mouseReleaseEvent()`
  - `ungroupSelectedItems()`
  - `instanceLabelRows()`
  - `popWireVertex()`
  - `cycleWireDrawMode()`
  - `toggleWireAutoRoute()`
  - `flipRouteOrientation()`
  - `updateStretchNet()`
  - `mergeSplitNets()`
  - `cleanUpNets()`
  - `mergeNets()`
  - `splitInputNet()`
  - `findSnapPoint()`
  - `findSnapTarget()`
  - `findConnectPoints()`
  - `orderPoints()`
  - `findFurthestPoints()`
  - `generatePinNetMap()`
  - `findSceneSymbolSet()`
  - `findSceneNetsSet()`
  - `findRectSymbolPin()`
  - `findRectSchemPins()`
  - `findSceneSchemPinsSet()`
  - `addStretchWires()`
  - `addPin()`
  - `addNote()`
  - `drawInstance()`
  - `instSymbol()`
  - `saveSchematic()`
  - `findEditorTypeString()`
  - `loadDesign()`
  - `createSchematicItems()`
  - `viewObjProperties()`
  - `setInstanceProperties()`
  - `setNetProperties()`
  - `setTextProperties()`
  - `setSchematicPinProperties()`
  - `hilightNets()`
  - `probeNets()`
  - `removeProbeMode()`
  - `clearProbe()`
  - `reapplyProbesAfterReload()`
  - `addProbe()`
  - `removeProbe()`
  - `applyProbe()`
  - `goDownHier()`
  - `descendInPlace()`
  - `setEipEditable()`
  - `saveInPlaceEdits()`
  - `ascendInPlace()`
  - `ignoreSymbol()`
  - `renumberInstances()`
  - `genSymbolPinNetMap()`
  - `markConnectivityDirty()`
  - `addItem()`
  - `removeItem()`
  - `rebuildConnectivity()`
  - `connectivity()`
  - `collectNetExprNames()`
  - `nameSceneNets()`
  - `toggleResolvedNames()`
  - `findItems()`
  - `replaceHitName()`
  - `netEndpointsForItem()`
  - `selectProbeTargets()`
  - `probeTargets()`
  - `probeLayout()`
  - `checkErrors()`
  - `deleteErrors()`
  - `isValidNetName()`
  - `createBusRanges()`
  - `parseBusNotation()`
  - internals: `_initializeFont()`, `_ensureSnapPointRect()`, `_handleMouseRelease()`, `_cursorRawLoc()`, `_releaseRawLoc()`, `_handleAddInstance()`, `_applyPendingInstanceParams()`, `_resolveInstanceLabels()`, `_handleDrawPin()`, `_handleDrawWire()`, `_handleDrawNet()`, `_createNet()` … (+58)

## Depends on

- [[revedaEditor\backend\dataDefinitions|revedaEditor.backend.dataDefinitions]]
- [[revedaEditor\backend\editFunctions|revedaEditor.backend.editFunctions]]
- [[revedaEditor\backend\libraryMethods|revedaEditor.backend.libraryMethods]]
- [[revedaEditor\backend\pdkLoader|revedaEditor.backend.pdkLoader]]
- [[revedaEditor\backend\undoStack|revedaEditor.backend.undoStack]]
- [[revedaEditor\checks\schematic|revedaEditor.checks.schematic]]
- [[revedaEditor\common\fileCache|revedaEditor.common.fileCache]]
- [[revedaEditor\common\labels|revedaEditor.common.labels]]
- [[revedaEditor\common\net|revedaEditor.common.net]]
- [[revedaEditor\common\params|revedaEditor.common.params]]
- [[revedaEditor\common\shapes|revedaEditor.common.shapes]]
- [[revedaEditor\connectivity\__init__|revedaEditor.connectivity.__init__]]
- [[revedaEditor\fileio\loadJSON|revedaEditor.fileio.loadJSON]]
- [[revedaEditor\fileio\schematicEncoder|revedaEditor.fileio.schematicEncoder]]
- [[revedaEditor\fileio\schemaValidation|revedaEditor.fileio.schemaValidation]]
- [[revedaEditor\gui\alignItems|revedaEditor.gui.alignItems]]
- [[revedaEditor\gui\fileDialogues|revedaEditor.gui.fileDialogues]]
- [[revedaEditor\gui\propertyDialogues|revedaEditor.gui.propertyDialogues]]
- [[revedaEditor\scenes\editorScene|revedaEditor.scenes.editorScene]]

## Used by

- [[revedaEditor\gui\editorViews|revedaEditor.gui.editorViews]]
- [[revedaEditor\gui\schematicEditor|revedaEditor.gui.schematicEditor]]
- [[revedaEditor\netlisting\spectreNetlist|revedaEditor.netlisting.spectreNetlist]]
- [[revedaEditor\netlisting\vacaskNetlist|revedaEditor.netlisting.vacaskNetlist]]
- [[revedaEditor\netlisting\xyceNetlist|revedaEditor.netlisting.xyceNetlist]]
- [[revedaEditor\tests\sceneTestUtils|revedaEditor.tests.sceneTestUtils]]
