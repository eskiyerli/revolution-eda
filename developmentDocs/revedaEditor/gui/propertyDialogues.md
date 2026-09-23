# `revedaEditor/gui/propertyDialogues.py`

**Module:** `revedaEditor.gui.propertyDialogues`

## Purpose

Schematic/symbol property and creation dialogs (instance placement, pins, labels, parameter widgets).

## Classes

- `placeInstanceDialog(QDialog)` — Compact parameter form shown while placing an instance.
  - `paramValues()`
  - internals: `_validateAndAccept()`
- `rectPropertyDialog(QDialog)` — Property dialog for symbol rectangles.
- `circlePropertyDialog(QDialog)`
- `arcPropertyDialog(QDialog)`
- `linePropertyDialog(QDialog)`
- `pointsTableWidget(QTableWidget)`
- `symbolPolygonProperties(QDialog)`
  - `populateTable()`
  - `addRow()`
  - `addEmptyRow()`
  - `handleCellChange()`
  - `deleteRow()`
- `createPinDialog(QDialog)`
- `pinPropertyDialog(createPinDialog)`
- `createSymbolLabelDialog(QDialog)`
- `labelPropertyDialog(createSymbolLabelDialog)`
- `symbolLabelsDialogue(QDialog)` — Dialog for changing symbol labels and attributes. Symbol properties... menu item.
  - `paramDefs()`
  - `symbolAttrsMethod()`
  - `updateAttributeDef()`
  - `symbolLabelsMethod()`
  - internals: `_populateParamsTable()`, `_setParamRow()`, `_paramCellChanged()`
- `instanceProperties(QDialog)`
  - `initUI()`
- `schematicCheckRulesDialogue(QDialog)` — Checkbox dialogue selecting which schematic check rules are applied.
  - `selectedRuleIds()`
  - internals: `_setAllChecked()`
- `netNameDialog(QDialog)`
- `netProperties(QDialog)`
  - `initUI()`
- `createSchematicPinDialog(createPinDialog)`
- `schematicPinPropertiesDialog(createPinDialog)`
- `symbolNameDialog(QDialog)`
  - `initUI()`
- `symbolCreateDialog(QDialog)`
- `noteTextEdit(QDialog)` — Set text properties.
  - `familyFontStyles()`
  - `styleFontSizes()`
- `displayConfigDialog(QDialog)`
- `layoutDisplayConfigDialog(QDialog)`
- `selectConfigDialogue(QDialog)`
- `moveByDialogue(QDialog)`
- `copyOptionsDialogue(QDialog)` — Modeless copy-options form (F3 while a copy is armed): rows×columns array + Delta X/Y pitch; Apply/Ok write `scene.copyOptions` and rearm the ghost.
  - internals: `_unitScale()`, `_displayPitch()`, `_applyOptions()`

## Functions

- `paramValueWidget()` — Build the editor widget for a typed parameter.

## Depends on

- [[revedaEditor/common/labels|revedaEditor.common.labels]]
- [[revedaEditor/common/net|revedaEditor.common.net]]
- [[revedaEditor/common/params|revedaEditor.common.params]]
- [[revedaEditor/common/shapes|revedaEditor.common.shapes]]
- [[revedaEditor/gui/editFunctions|revedaEditor.gui.editFunctions]]

## Used by

- [[revedaEditor/gui/editorWindow|revedaEditor.gui.editorWindow]]
- [[revedaEditor/gui/schematicEditor|revedaEditor.gui.schematicEditor]]
- [[revedaEditor/gui/symbolEditor|revedaEditor.gui.symbolEditor]]
- [[revedaEditor/scenes/editorScene|revedaEditor.scenes.editorScene]]
- [[revedaEditor/scenes/layoutScene|revedaEditor.scenes.layoutScene]]
- [[revedaEditor/scenes/schematicScene|revedaEditor.scenes.schematicScene]]
- [[revedaEditor/scenes/symbolScene|revedaEditor.scenes.symbolScene]]
