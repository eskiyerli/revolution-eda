# `revedaEditor/backend/pdkLoader.py`

**Module:** `revedaEditor.backend.pdkLoader`

## Purpose

PDK loading: `importPDKModule` resolves `<pdk>.<module>` against `REVEDA_PDK_PATH` and applies PDK menu items declared in the PDK's `config.json`.

## Classes

- `pdkConfig`
  - `applyPDKMenus()`
  - internals: `_loadPDKConfig()`

## Functions

- `_get_pdk_path()` — Get and cache PDK path
- `importPDKModule()` — Import a PDK submodule dynamically.
- `clearPDKModuleCache()` — Clear the PDK module cache and remove stale PDK modules from sys.modules.
- `getPDKPath()` — Get the resolved PDK path

## Used by

- [[defaultPDK/pcells|defaultPDK.pcells]]
- [[defaultPDK/process|defaultPDK.process]]
- [[reveda|reveda]]
- [[revedaEditor/backend/drcModelView|revedaEditor.backend.drcModelView]]
- [[revedaEditor/common/labels|revedaEditor.common.labels]]
- [[revedaEditor/common/layoutShapes|revedaEditor.common.layoutShapes]]
- [[revedaEditor/common/net|revedaEditor.common.net]]
- [[revedaEditor/common/shapes|revedaEditor.common.shapes]]
- [[revedaEditor/fileio/exportGDS|revedaEditor.fileio.exportGDS]]
- [[revedaEditor/fileio/importGDS|revedaEditor.fileio.importGDS]]
- [[revedaEditor/fileio/importXschemSym|revedaEditor.fileio.importXschemSym]]
- [[revedaEditor/fileio/importlyrdb|revedaEditor.fileio.importlyrdb]]
- [[revedaEditor/fileio/layoutEncoder|revedaEditor.fileio.layoutEncoder]]
- [[revedaEditor/fileio/loadJSON|revedaEditor.fileio.loadJSON]]
- [[revedaEditor/gui/alignItems|revedaEditor.gui.alignItems]]
- [[revedaEditor/gui/editorViews|revedaEditor.gui.editorViews]]
- [[revedaEditor/gui/layoutDialogues|revedaEditor.gui.layoutDialogues]]
- [[revedaEditor/gui/layoutEditor|revedaEditor.gui.layoutEditor]]
- [[revedaEditor/gui/lsw|revedaEditor.gui.lsw]]
- [[revedaEditor/gui/lvsResults|revedaEditor.gui.lvsResults]]
- [[revedaEditor/scenes/layoutScene|revedaEditor.scenes.layoutScene]]
- [[revedaEditor/scenes/schematicScene|revedaEditor.scenes.schematicScene]]
- [[revedaEditor/scenes/symbolScene|revedaEditor.scenes.symbolScene]]
