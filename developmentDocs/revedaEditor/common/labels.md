# `revedaEditor/common/labels.py`

**Module:** `revedaEditor.common.labels`

## Purpose

Label items (`schematicLabel`, `symbolLabel`) and PyLabel machinery — labels whose text is computed by PDK callback classes and rendered with `quantiphy.Quantity`.

## Classes

- `_LazyModule` — Proxy that defers PDK module loading until first attribute access.
  - internals: `__getattr__()`
- `symbolLabel(QGraphicsSimpleTextItem)` — label: text class definition for symbol drawing.
  - `sceneEvent()`
  - `mousePressEvent()`
  - `itemChange()`
  - `contextMenuEvent()`
  - `start()`
  - `start()`
  - `labelName()`
  - `labelName()`
  - `labelDefinition()`
  - `labelDefinition()`
  - `labelValue()`
  - `labelValue()`
  - `labelText()`
  - `labelText()`
  - `labelType()`
  - `labelType()`
  - `labelAlign()`
  - `labelAlign()`
  - `labelHeight()`
  - `labelHeight()`
  - `labelOrient()`
  - `labelOrient()`
  - `labelUse()`
  - `labelUse()`
  - `labelFont()`
  - `labelFont()`
  - `angle()`
  - `angle()`
  - `labelVisible()`
  - `labelVisible()`
  - `flipTuple()`
  - `flipTuple()`
  - `labelDefs()`
  - `createNLPLabel()`
  - `createPyLabel()`
  - internals: `__repr__()`, `_updateVisibility()`, `_extractDefaultValue()`, `_paramDefDefault()`, `_createPredefinedLabels()`

## Functions

- `_get_schlyr()` — Lazy accessor for schematic layers PDK module (avoids circular import).
- `_get_symlyr()` — Lazy accessor for symbol layers PDK module (avoids circular import).
- `_get_cb()` — Lazy accessor for callbacks PDK module (avoids circular import).

## Depends on

- [[revedaEditor/backend/pdkLoader|revedaEditor.backend.pdkLoader]]

## Used by

- [[revedaEditor/common/shapes|revedaEditor.common.shapes]]
- [[revedaEditor/fileio/importXschemSym|revedaEditor.fileio.importXschemSym]]
- [[revedaEditor/fileio/loadJSON|revedaEditor.fileio.loadJSON]]
- [[revedaEditor/fileio/symbolEncoder|revedaEditor.fileio.symbolEncoder]]
- [[revedaEditor/gui/propertyDialogues|revedaEditor.gui.propertyDialogues]]
- [[revedaEditor/scenes/schematicScene|revedaEditor.scenes.schematicScene]]
- [[revedaEditor/scenes/symbolScene|revedaEditor.scenes.symbolScene]]
- [[revedaEditor/tests/test_labels_nlp|revedaEditor.tests.test_labels_nlp]]
- [[revedaEditor/tests/test_netexpr|revedaEditor.tests.test_netexpr]]
- [[revedaEditor/tests/test_netlisting|revedaEditor.tests.test_netlisting]]
