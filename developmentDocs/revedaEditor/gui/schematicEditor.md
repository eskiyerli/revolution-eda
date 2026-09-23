# `revedaEditor/gui/schematicEditor.py`

**Module:** `revedaEditor.gui.schematicEditor`

## Purpose

`schematicEditor` window + `schematicContainer`: schematic menus/actions, load/save flows, config-view creation.

## Module docstring

Schematic editor module for Revolution EDA.

This module provides the schematicEditor class for editing circuit schematics,
creating symbols, and generating netlists. It supports hierarchical designs,
config views, and plugin integration.

## Classes

- `schematicEditor(edw.editorWindow)` — Schematic editor window for creating and editing circuit schematics.
  - `init_UI()`
  - `createNetClick()`
  - `createBusClick()`
  - `createInstClick()`
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
  - `clipboardCopyClick()`
  - `pasteClick()`
  - `findClick()`
  - internals: `__repr__()`, `_createActions()`, `_addActions()`, `_createTriggers()`, `_createToolBars()`, `_schematicContextMenu()`, `_createShortcuts()`, `_symbolParamDefs()`, `_getNetlistableViews()`, `_startNetlisting()`, `_parse_pin_names()`, `_categorize_pins()` … (+2)
- `schematicContainer(edw.editorContainer)`
  - `init_UI()`

## Depends on

- [[revedaEditor/backend/dataDefinitions|revedaEditor.backend.dataDefinitions]]
- [[revedaEditor/backend/libBackEnd|revedaEditor.backend.libBackEnd]]
- [[revedaEditor/backend/libraryMethods|revedaEditor.backend.libraryMethods]]
- [[revedaEditor/backend/libraryModelView|revedaEditor.backend.libraryModelView]]
- [[revedaEditor/checks/schematic|revedaEditor.checks.schematic]]
- [[revedaEditor/common/params|revedaEditor.common.params]]
- [[revedaEditor/common/shapes|revedaEditor.common.shapes]]
- [[revedaEditor/fileio/loadJSON|revedaEditor.fileio.loadJSON]]
- [[revedaEditor/fileio/symbolEncoder|revedaEditor.fileio.symbolEncoder]]
- [[revedaEditor/gui/editorFactory|revedaEditor.gui.editorFactory]]
- [[revedaEditor/gui/editorViews|revedaEditor.gui.editorViews]]
- [[revedaEditor/gui/editorWindow|revedaEditor.gui.editorWindow]]
- [[revedaEditor/gui/fileDialogues|revedaEditor.gui.fileDialogues]]
- [[revedaEditor/gui/findDialogue|revedaEditor.gui.findDialogue]]
- [[revedaEditor/gui/propertyDialogues|revedaEditor.gui.propertyDialogues]]
- [[revedaEditor/gui/toolsDialogues|revedaEditor.gui.toolsDialogues]]
- [[revedaEditor/netlisting/__init__|revedaEditor.netlisting.__init__]]
- [[revedaEditor/scenes/schematicScene|revedaEditor.scenes.schematicScene]]

## Used by

- [[revedaEditor/gui/configEditor|revedaEditor.gui.configEditor]]
