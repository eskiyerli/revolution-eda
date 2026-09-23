# `revedaEditor/backend/libBackEnd.py`

**Module:** `revedaEditor.backend.libBackEnd`

## Purpose

Library model items — `libraryItem`/`cellItem`/`viewItem` (QStandardItem subclasses carrying filesystem paths) plus cell/view creation helpers.

## Classes

- `libraryItem(QStandardItem)`
  - `type()`
  - `libraryPath()`
  - `libraryPath()`
  - `libraryName()`
  - internals: `__str__()`, `__repr__()`
- `cellItem(QStandardItem)`
  - `type()`
  - `delete()`
  - `cellName()`
  - `clone()`
  - `refreshCellViews()`
  - internals: `__str__()`, `__repr__()`
- `viewItem(QStandardItem)`
  - `type()`
  - `delete()`
  - `viewType()`
  - `clone()`
  - internals: `__str__()`, `__repr__()`

## Functions

- `textViewFilePath()` — Resolve the file a text-based view refers to.
- `createLibrary()` — Create a library item with the given parameters and add it to the model.
- `createNewLibraryItem()`
- `createCell()`
- `createNewCellItem()`
- `createCellView()` — Create a cell view with the given view name and cell item.
- `createCellviewItem()`
- `copyCell()` — Copy a cell to a new location with a new name.
- `renameCell()` — Function to rename a cell in the parentW with a new name.

## Used by

- [[revedaEditor/backend/libraryMethods|revedaEditor.backend.libraryMethods]]
- [[revedaEditor/backend/libraryModelView|revedaEditor.backend.libraryModelView]]
- [[revedaEditor/fileio/extractedSchematic|revedaEditor.fileio.extractedSchematic]]
- [[revedaEditor/fileio/importGDS|revedaEditor.fileio.importGDS]]
- [[revedaEditor/fileio/importXschemSym|revedaEditor.fileio.importXschemSym]]
- [[revedaEditor/gui/configEditor|revedaEditor.gui.configEditor]]
- [[revedaEditor/gui/editorWindow|revedaEditor.gui.editorWindow]]
- [[revedaEditor/gui/layoutEditor|revedaEditor.gui.layoutEditor]]
- [[revedaEditor/gui/libraryBrowser|revedaEditor.gui.libraryBrowser]]
- [[revedaEditor/gui/schematicEditor|revedaEditor.gui.schematicEditor]]
- [[revedaEditor/gui/symbolEditor|revedaEditor.gui.symbolEditor]]
- [[revedaEditor/netlisting/spectreNetlist|revedaEditor.netlisting.spectreNetlist]]
- [[revedaEditor/netlisting/vacaskNetlist|revedaEditor.netlisting.vacaskNetlist]]
- [[revedaEditor/netlisting/xyceNetlist|revedaEditor.netlisting.xyceNetlist]]
- [[revedaEditor/tests/test_correspondence|revedaEditor.tests.test_correspondence]]
- [[revedaEditor/tests/test_import_gds|revedaEditor.tests.test_import_gds]]
- [[revedaEditor/tests/test_netlisting|revedaEditor.tests.test_netlisting]]
- [[revedaEditor/tests/test_platform_hardening|revedaEditor.tests.test_platform_hardening]]
