# `revedaEditor/backend/dataDefinitions.py`

**Module:** `revedaEditor.backend.dataDefinitions`

## Purpose

Shared data types: `edLayer`/`layLayer` dataclasses and the namedtuple records (`viewNameTuple`, `viewItemTuple`, pin/layer defs) exchanged between GUI, scenes and fileio.

## Classes

- `edLayer`
- `layLayer`
  - `filterByGDSLayer()`
- `editModes`
  - `setMode()`
  - `mode()`
- `symbolModes(editModes)`
- `schematicModes(editModes)`
- `layoutModes(editModes)`
- `selectModes`
  - `setMode()`
- `schematicSelectModes(selectModes)`
- `layoutSelectModes(selectModes)`
- `symbolSelectModes(selectModes)`
- `copyOptions` — Session-scoped copy/paste options (rows/columns + X/Y pitch, scene units); zero pitch = fragment bbox size.
- `viewNameTuple(NamedTuple)`
- `cellTuple(NamedTuple)`
- `viewItemTuple(NamedTuple)`
  - `convertToViewNameTuple()`
- `layoutPinTuple(NamedTuple)`
- `layoutLabelTuple(NamedTuple)`
- `rulerTuple(NamedTuple)`
- `viaDefTuple(NamedTuple)`
- `singleViaTuple(NamedTuple)`
- `arrayViaTuple(NamedTuple)`
- `rectCoords(NamedTuple)`
- `layoutPathDefTuple(NamedTuple)`
- `layoutPathTuple(NamedTuple)`

## Depends on

- [[revedaEditor/backend/__init__|revedaEditor.backend.__init__]]

## Used by

- [[defaultPDK/layoutLayers|defaultPDK.layoutLayers]]
- [[defaultPDK/process|defaultPDK.process]]
- [[defaultPDK/schLayers|defaultPDK.schLayers]]
- [[defaultPDK/symLayers|defaultPDK.symLayers]]
- [[revedaEditor/backend/libraryModelView|revedaEditor.backend.libraryModelView]]
- [[revedaEditor/backend/pluginsLoader|revedaEditor.backend.pluginsLoader]]
- [[revedaEditor/common/layoutShapes|revedaEditor.common.layoutShapes]]
- [[revedaEditor/fileio/createSymbols|revedaEditor.fileio.createSymbols]]
- [[revedaEditor/fileio/extractedSchematic|revedaEditor.fileio.extractedSchematic]]
- [[revedaEditor/fileio/importGDS|revedaEditor.fileio.importGDS]]
- [[revedaEditor/fileio/importLayp|revedaEditor.fileio.importLayp]]
- [[revedaEditor/gui/configEditor|revedaEditor.gui.configEditor]]
- [[revedaEditor/gui/editorWindow|revedaEditor.gui.editorWindow]]
- [[revedaEditor/gui/layoutEditor|revedaEditor.gui.layoutEditor]]
- [[revedaEditor/gui/libraryBrowser|revedaEditor.gui.libraryBrowser]]
- [[revedaEditor/gui/revedaMain|revedaEditor.gui.revedaMain]]
- [[revedaEditor/gui/schematicEditor|revedaEditor.gui.schematicEditor]]
- [[revedaEditor/gui/symbolEditor|revedaEditor.gui.symbolEditor]]
- [[revedaEditor/gui/textEditor|revedaEditor.gui.textEditor]]
- [[revedaEditor/netlisting/spectreNetlist|revedaEditor.netlisting.spectreNetlist]]
- [[revedaEditor/netlisting/vacaskNetlist|revedaEditor.netlisting.vacaskNetlist]]
- [[revedaEditor/netlisting/xyceNetlist|revedaEditor.netlisting.xyceNetlist]]
- [[revedaEditor/scenes/editorScene|revedaEditor.scenes.editorScene]]
- [[revedaEditor/scenes/layoutScene|revedaEditor.scenes.layoutScene]]
- [[revedaEditor/scenes/schematicScene|revedaEditor.scenes.schematicScene]]
- [[revedaEditor/scenes/symbolScene|revedaEditor.scenes.symbolScene]]
- [[revedaEditor/tests/test_correspondence|revedaEditor.tests.test_correspondence]]
- [[revedaEditor/tests/test_platform_hardening|revedaEditor.tests.test_platform_hardening]]
