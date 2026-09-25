# `revedaEditor\gui\schematicEditor.py`

**Module:** `revedaEditor.gui.schematicEditor`

## Purpose

Schematic editor module for Revolution EDA.

## Classes

- `schematicEditor(edw.editorWindow)` — Schematic editor window for creating and editing circuit schematics.
  - `init_UI()`
  - `createNetClick()`
  - `createBusClick()`
  - `createInstClick()`
  - `editActivePlacementOptions()`
  - `createPinClick()`
  - `createNoteClick()`
  - `createSymbolClick()`
  - `objPropClick()`
  - `renumberInstanceClick()`
  - `checkSaveCell()`
  - `saveCell()`
  - `loadSchematic()`
  - `createConfigView()`
  - `closeEvent()`
  - `createNetlistClick()`
  - `createNetlistObject()`
  - `goDownClick()`
  - `ignoreClick()`
  - `createNetNameClick()`
  - `hilightNetClick()`
  - `probeNetClick()`
  - `removeProbeNetClick()`
  - `showResolvedNamesClick()`
  - `removeAllProbesClick()`
  - `selectDeviceClick()`
  - `selectNetClick()`
  - `selectPinClick()`
  - `selectTextClick()`
  - `removeSelectFilterClick()`
  - `createSymbol()`
  - `generateSymbol()`
  - `checkRulesClick()`
  - `undoClick()`
  - `checkErrorsClick()`
  - `deleteErrorsClick()`
  - `findRelated()`
  - `findRelatedEditorsClick()`
  - `descendInPlaceClick()`
  - `ascendInPlaceClick()`
  - `saveInPlaceClick()`
  - `viewErrorsClick()`
  - `findClick()`
  - internals: `__repr__()`, `_createActions()`, `_addActions()`, `_createTriggers()`, `_createToolBars()`, `_schematicContextMenu()`, `_createShortcuts()`, `_configureSchematicInstanceParams()`, `_symbolParamDefs()`, `_configureSchematicPin()`, `_getNetlistableViews()`, `_startNetlisting()` … (+4)
- `schematicContainer(edw.editorContainer)`
  - `init_UI()`

## Depends on

- [[revedaEditor\backend\dataDefinitions|revedaEditor.backend.dataDefinitions]]
- [[revedaEditor\backend\libBackEnd|revedaEditor.backend.libBackEnd]]
- [[revedaEditor\backend\libraryMethods|revedaEditor.backend.libraryMethods]]
- [[revedaEditor\backend\libraryModelView|revedaEditor.backend.libraryModelView]]
- [[revedaEditor\checks\schematic|revedaEditor.checks.schematic]]
- [[revedaEditor\common\labels|revedaEditor.common.labels]]
- [[revedaEditor\common\params|revedaEditor.common.params]]
- [[revedaEditor\common\shapes|revedaEditor.common.shapes]]
- [[revedaEditor\fileio\loadJSON|revedaEditor.fileio.loadJSON]]
- [[revedaEditor\fileio\symbolEncoder|revedaEditor.fileio.symbolEncoder]]
- [[revedaEditor\gui\editorFactory|revedaEditor.gui.editorFactory]]
- [[revedaEditor\gui\editorViews|revedaEditor.gui.editorViews]]
- [[revedaEditor\gui\editorWindow|revedaEditor.gui.editorWindow]]
- [[revedaEditor\gui\fileDialogues|revedaEditor.gui.fileDialogues]]
- [[revedaEditor\gui\findDialogue|revedaEditor.gui.findDialogue]]
- [[revedaEditor\gui\propertyDialogues|revedaEditor.gui.propertyDialogues]]
- [[revedaEditor\gui\toolsDialogues|revedaEditor.gui.toolsDialogues]]
- [[revedaEditor\netlisting\__init__|revedaEditor.netlisting.__init__]]
- [[revedaEditor\scenes\schematicScene|revedaEditor.scenes.schematicScene]]

## Used by

- [[revedaEditor\gui\configEditor|revedaEditor.gui.configEditor]]
- [[revedaEditor\tests\test_sdl_free_baseline|revedaEditor.tests.test_sdl_free_baseline]]
