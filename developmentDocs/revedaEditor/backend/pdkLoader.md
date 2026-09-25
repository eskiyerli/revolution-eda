# `revedaEditor\backend\pdkLoader.py`

**Module:** `revedaEditor.backend.pdkLoader`

## Purpose

Module in `revedaEditor\backend`.

## Classes

- `_LazyPDKModule` — Proxy that defers PDK module loading until first attribute access.
  - internals: `_resolve()`, `__getattr__()`, `__setattr__()`, `__bool__()`, `__repr__()`
- `pdkConfig`
  - `applyPDKMenus()`
  - internals: `_loadPDKConfig()`

## Functions

- `_get_pdk_path()` — Get and cache PDK path
- `importPDKModule()` — Import a PDK submodule dynamically.
- `lazyPDKModule()` — Return a lazy proxy for a PDK submodule, safe for module-level binding.
- `clearPDKModuleCache()` — Clear the PDK module cache and remove stale PDK modules from sys.modules.
- `getPDKPath()` — Get the resolved PDK path

## Used by

- [[defaultPDK\pcells|defaultPDK.pcells]]
- [[defaultPDK\process|defaultPDK.process]]
- [[reveda|reveda]]
- [[revedaEditor\backend\drcModelView|revedaEditor.backend.drcModelView]]
- [[revedaEditor\common\labels|revedaEditor.common.labels]]
- [[revedaEditor\common\layoutShapes|revedaEditor.common.layoutShapes]]
- [[revedaEditor\common\net|revedaEditor.common.net]]
- [[revedaEditor\common\shapes|revedaEditor.common.shapes]]
- [[revedaEditor\fileio\exportGDS|revedaEditor.fileio.exportGDS]]
- [[revedaEditor\fileio\importGDS|revedaEditor.fileio.importGDS]]
- [[revedaEditor\fileio\importlyrdb|revedaEditor.fileio.importlyrdb]]
- [[revedaEditor\fileio\importXschemSym|revedaEditor.fileio.importXschemSym]]
- [[revedaEditor\fileio\layoutEncoder|revedaEditor.fileio.layoutEncoder]]
- [[revedaEditor\fileio\loadJSON|revedaEditor.fileio.loadJSON]]
- [[revedaEditor\gui\alignItems|revedaEditor.gui.alignItems]]
- [[revedaEditor\gui\editorViews|revedaEditor.gui.editorViews]]
- [[revedaEditor\gui\layoutDialogues|revedaEditor.gui.layoutDialogues]]
- [[revedaEditor\gui\layoutEditor|revedaEditor.gui.layoutEditor]]
- [[revedaEditor\gui\lsw|revedaEditor.gui.lsw]]
- [[revedaEditor\gui\lvsResults|revedaEditor.gui.lvsResults]]
- [[revedaEditor\gui\propertyDialogues|revedaEditor.gui.propertyDialogues]]
- [[revedaEditor\scenes\layoutScene|revedaEditor.scenes.layoutScene]]
- [[revedaEditor\scenes\schematicScene|revedaEditor.scenes.schematicScene]]
- [[revedaEditor\scenes\symbolScene|revedaEditor.scenes.symbolScene]]
- [[revedaEditor\tests\test_file_hardening|revedaEditor.tests.test_file_hardening]]
