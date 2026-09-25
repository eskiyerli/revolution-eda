# `revedaEditor\backend\libraryModelView.py`

**Module:** `revedaEditor.backend.libraryModelView`

## Purpose

Module in `revedaEditor\backend`.

## Classes

- `BaseDesignLibrariesView(QWidget)`
  - `removeLibrary()`
  - `renameLib()`
  - `openView()`
  - `createNewCellView()`
  - `reworkDesignLibrariesView()`
  - `openCellView()`
  - `verilogaEditFinished()`
  - `spiceEditFinished()`
  - `spectreEditFinished()`
  - `vacaskEditFinished()`
  - internals: `_handle_text_view()`, `_handle_spice_view()`, `_handle_veriloga_view()`, `_handle_spectre_view()`, `_handle_vacask_view()`, `_handle_spef_view()`, `_handle_pcell_view()`
- `designLibrariesColumnView(BaseDesignLibrariesView)`
  - `onLibsListSelection()`
  - `recursive_clone()`
  - `onCellsListSelection()`
  - `createViewsListModel()`
  - `onViewsListSelection()`
  - `reworkDesignLibrariesView()`
  - `libsListContextMenuEvent()`
  - `cellsListContextMenuEvent()`
  - `viewsListContextMenuEvent()`
  - `createCell()`
  - `copyCell()`
  - `renameCell()`
  - `deleteCell()`
  - `copyView()`
  - `createCellView()`
  - `handleNewCellView()`
  - `renameView()`
  - `deleteView()`
  - `showClonedItemFileInfo()`
  - `showItemFileInfo()`
- `designLibrariesTreeView(BaseDesignLibrariesView)` — Deprecated for the moment. 4/3/2026.
  - `createCell()`
  - `copyCell()`
  - `renameCell()`
  - `deleteCell()`
  - `createCellView()`
  - `handleNewCellView()`
  - `copyView()`
  - `renameView()`
  - `deleteView()`
  - `reworkDesignLibrariesView()`
  - `showFileInfo()`
  - `contextMenuEvent()`
- `designLibrariesModel(QStandardItemModel)`
  - `initModel()`
  - `populateLibrary()`
  - `addLibraryToModel()`
  - `removeLibraryFromModel()`
  - `addCellToModel()`
  - `addViewToModel()`
  - `listLibraries()`
  - `listLibraryCells()`
  - `listCellViews()`
- `symbolViewsModel(designLibrariesModel)` — Initializes the object with the given `libraryDict` and `symbolViews`.
  - `populateLibrary()`
- `layoutViewsModel(designLibrariesModel)`
  - `populateLibrary()`
- `schematicViewsModel(designLibrariesModel)` — Model for selecting schematic views in Schematic-Driven Layout (SDL).
  - `populateLibrary()`
- `libraryCheckListView(QListView)`
  - `getCheckedLibraries()`

## Functions

- `updateJSONFieldInLibrary()` — Update a specific JSON field in all view files within a single library.
- `updateJSONFieldInCell()` — Update a specific JSON field in all view files within a single cell.

## Depends on

- [[revedaEditor\backend\dataDefinitions|revedaEditor.backend.dataDefinitions]]
- [[revedaEditor\backend\libBackEnd|revedaEditor.backend.libBackEnd]]
- [[revedaEditor\backend\libraryMethods|revedaEditor.backend.libraryMethods]]
- [[revedaEditor\fileio\schemaValidation|revedaEditor.fileio.schemaValidation]]
- [[revedaEditor\gui\configEditor|revedaEditor.gui.configEditor]]
- [[revedaEditor\gui\fileDialogues|revedaEditor.gui.fileDialogues]]
- [[revedaEditor\gui\layoutDialogues|revedaEditor.gui.layoutDialogues]]
- [[revedaEditor\gui\textEditor|revedaEditor.gui.textEditor]]

## Used by

- [[revedaEditor\fileio\importXschemSym|revedaEditor.fileio.importXschemSym]]
- [[revedaEditor\gui\editorWindow|revedaEditor.gui.editorWindow]]
- [[revedaEditor\gui\layoutEditor|revedaEditor.gui.layoutEditor]]
- [[revedaEditor\gui\libraryBrowser|revedaEditor.gui.libraryBrowser]]
- [[revedaEditor\gui\schematicEditor|revedaEditor.gui.schematicEditor]]
- [[revedaEditor\gui\symbolEditor|revedaEditor.gui.symbolEditor]]
- [[revedaEditor\scenes\layoutScene|revedaEditor.scenes.layoutScene]]
- [[revedaEditor\tests\test_netexpr|revedaEditor.tests.test_netexpr]]
- [[revedaEditor\tests\test_netlisting|revedaEditor.tests.test_netlisting]]
