# `revedaEditor/gui/fileDialogues.py`

**Module:** `revedaEditor.gui.fileDialogues`

## Purpose

Cell/view/library dialogs: create/delete/rename/copy/select-cellview dialogs and the library dialogs.

## Classes

- `createCellDialog(QDialog)`
  - `init_UI()`
  - `selectLibrary()`
- `deleteCellDialog(createCellDialog)`
- `newCellViewDialog(createCellDialog)`
  - `setCurrentViewName()`
- `selectCellViewDialog(createCellDialog)`
  - `cellNameChanged()`
- `renameCellDialog(QDialog)`
  - `init_UI()`
- `copyCellDialog(QDialog)`
  - `init_UI()`
  - `selectLibrary()`
- `copyViewDialog(createCellDialog)`
- `closeLibDialog(QDialog)`
- `renameLibDialog(QDialog)`
- `renameViewDialog(QDialog)`
- `deleteSymbolDialog(QDialog)`
- `netlistExportDialogue(QDialog)`
  - `onDirButtonClicked()`
- `layoutExportDialogue(QDialog)`
  - `onDirButtonClicked()`
  - `layerMap()`
  - `cellNameMap()`
  - `flattenDepth()`
- `gdsExportDialogue(layoutExportDialogue)`
- `oasExportDialogue(layoutExportDialogue)`
- `gdsImportDialogue(QDialog)`
  - `onFileButtonClicked()`
- `goDownHierDialogue(QDialog)`
  - `onButtonClicked()`
- `importCellDialogue(QDialog)`
  - `changeCells()`
  - `onFileButtonClicked()`
  - internals: `_setup_ui()`
- `importVerilogaCellDialogue(importCellDialogue)`
  - `vaFileEdit()`
  - `vaViewName()`
  - `vaFileName()`
  - `vaFileName()`
- `importSpiceCellDialogue(importCellDialogue)`
  - `spiceFileEdit()`
  - `spiceViewName()`
  - `spiceFileName()`
  - `spiceFileName()`
- `importSpectreCellDialogue(importCellDialogue)`
  - `spectreFileEdit()`
  - `spectreViewName()`
- `importVacaskCellDialogue(importCellDialogue)`
  - `vacaskFileEdit()`
  - `vacaskViewName()`
- `createConfigViewDialogue(QDialog)`
- `appProperties(QDialog)`
  - `onRootPathButtonClicked()`
  - `onSimOutPathButtonClicked()`
  - `onSimInpPathButtonClicked()`
  - `onPluginsPathButtonClicked()`
- `libraryPathsModel(QStandardItemModel)`
- `libraryPathsTableView(QTableView)`
  - `contextMenuEvent()`
  - `removeLibraryPath()`
  - `addLibraryPath()`
- `libraryPathEditorDialog(QDialog)`
- `klayoutLaypImportDialogue(QDialog)`
  - `onFileButtonClicked()`
  - `onDirButtonClicked()`
- `klayoutLaytImportDialogue(QDialog)`
  - `onFileButtonClicked()`
- `xschemSymIimportDialogue(QDialog)`
  - `onFileButtonClicked()`
- `fileInfoDialogue(QDialog)`
- `imageExportDialog(QDialog)` — Dialog for exporting the current editor view as an image file.
  - `init_UI()`
  - `filePath()`
  - `colorMode()`
  - `dpi()`
  - `scale()`
  - `backgroundColor()`
  - `margin()`
  - `jpegQuality()`
  - `transparent()`
  - `exportScope()`
  - `includeGrid()`
  - `antialiasing()`
  - internals: `_onFormatChanged()`, `_onDpiChanged()`, `_onScaleChanged()`, `_onMarginChanged()`, `_onQualityChanged()`, `_onTransparentChanged()`, `_chooseBackgroundColor()`, `_browse()`, `_validateAndAccept()`

## Depends on

- [[revedaEditor/backend/libraryMethods|revedaEditor.backend.libraryMethods]]
- [[revedaEditor/gui/editFunctions|revedaEditor.gui.editFunctions]]

## Used by

- [[revedaEditor/backend/libraryModelView|revedaEditor.backend.libraryModelView]]
- [[revedaEditor/fileio/importVeriloga|revedaEditor.fileio.importVeriloga]]
- [[revedaEditor/gui/editorWindow|revedaEditor.gui.editorWindow]]
- [[revedaEditor/gui/layoutEditor|revedaEditor.gui.layoutEditor]]
- [[revedaEditor/gui/libraryBrowser|revedaEditor.gui.libraryBrowser]]
- [[revedaEditor/gui/revedaMain|revedaEditor.gui.revedaMain]]
- [[revedaEditor/gui/schematicEditor|revedaEditor.gui.schematicEditor]]
- [[revedaEditor/scenes/layoutScene|revedaEditor.scenes.layoutScene]]
- [[revedaEditor/scenes/schematicScene|revedaEditor.scenes.schematicScene]]
