# `revedaEditor/gui/layoutDialogues.py`

**Module:** `revedaEditor.gui.layoutDialogues`

## Purpose

Layout creation/property dialogs: instance placement (incl. arrays), paths, pins, labels, vias, multipart parameters, layer ops.

## Classes

- `layoutInstanceDialogue(QDialog)`
  - `arraySpec()`
- `layoutInstancePropertiesDialogue(layoutInstanceDialogue)`
- `pcellLinkDialogue(QDialog)`
- `createPathDialogue(QDialog)`
- `layoutPathPropertiesDialog(createPathDialogue)`
- `createLayoutPinDialog(QDialog)`
  - `familyFontStyles()`
  - `styleFontSizes()`
- `layoutPinProperties(QDialog)`
- `createLayoutLabelDialog(QDialog)`
  - `familyFontStyles()`
  - `styleFontSizes()`
- `layoutLabelProperties(createLayoutLabelDialog)`
- `createLayoutViaDialog(QDialog)`
  - `singleViaClicked()`
  - `arrayViaClicked()`
  - `singleViaNameChanged()`
  - `arrayViaNameChanged()`
  - `enclosureChanged()`
  - `singleViaWidthChanged()`
  - `singleViaHeightChanged()`
  - `arrayViaWidthChanged()`
  - `arrayViaHeightChanged()`
  - `arrayViaSpacingChanged()`
  - `validateValue()`
- `layoutViaProperties(createLayoutViaDialog)`
- `layoutRectProperties(QDialog)`
- `pointsTableWidget(QTableWidget)`
- `layoutPolygonProperties(QDialog)`
  - `populateTable()`
  - `addRow()`
  - `addEmptyRow()`
  - `handleCellChange()`
  - `deleteRow()`
- `formDictionary` — This code defines a utility class formDictionary that extracts data
  - `extractDictFormLayout()`
- `createMultipartDialogue(QDialog)` — Pick a multipart kind and its parameters before the two-click draw.
  - `selectedSpec()`
  - internals: `_clearFields()`, `_rebuildFields()`
- `makeCellDialogue(QDialog)` — Ask for the library and cell name used by Edit > Make Cell.
  - `libName()`
  - `cellName()`
- `multipartPropertiesDialogue(QDialog)` — Generic key->value editor for a multipart item's `params` dict.
  - `parsedParams()`
- `layerOpDialogue(QDialog)` — Pick a boolean/size operation for the selected shapes.
  - `selectedOp()`
  - `selectedAmount()`
- `drcErrorsDialogue(QDialog)`
  - `closeEvent()`
  - internals: `_clearDRCPolygons()`

## Depends on

- [[revedaEditor/backend/drcModelView|revedaEditor.backend.drcModelView]]
- [[revedaEditor/backend/pdkLoader|revedaEditor.backend.pdkLoader]]
- [[revedaEditor/common/layoutShapes|revedaEditor.common.layoutShapes]]
- [[revedaEditor/gui/editFunctions|revedaEditor.gui.editFunctions]]

## Used by

- [[revedaEditor/backend/libraryModelView|revedaEditor.backend.libraryModelView]]
- [[revedaEditor/gui/layoutEditor|revedaEditor.gui.layoutEditor]]
- [[revedaEditor/scenes/layoutScene|revedaEditor.scenes.layoutScene]]
