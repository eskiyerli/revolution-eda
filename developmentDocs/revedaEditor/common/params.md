# `revedaEditor\common\params.py`

**Module:** `revedaEditor.common.params`

## Purpose

Typed instance-parameter model (CDF-lite).

## Classes

- `ParamDef` — Typed parameter definition declared on a symbol.
  - `toDict()`

## Functions

- `paramDefsFromJson()` — Parse the `paramDefs` attribute payload.
- `paramDefsToJson()` — Serialise paramDefs to the `paramDefs` attribute payload.
- `paramDefsFromSymattrs()` — Extract ParamDefs from a symbol attribute dict (`symattrs`).
- `paramDefLabelBindings()` — Match typed parameter definitions to persistent label carriers.
- `validateParamDefs()` — Structural checks on a paramDefs list (duplicates, range sanity).
- `_parseNumber()` — Parse a numeric value, honouring the def's quantiphy flag.
- `_validateScalar()` — Type checks for a single value (no range or pPar handling).
- `validateValue()` — Validate an instance value against its ParamDef.
- `normalizeValue()` — Canonical string form of a valid value (booleans lower-cased).
- `_siblingLookup()` — Find `name` in a label/value mapping, tolerating `@` keys.
- `resolveRefs()` — Substitute `pPar("name")` references with sibling values.
- `resolveDefault()` — The parameter's effective default with pPar references resolved.
- `effectiveValue()` — Value after applying the default when `raw` is empty.
- `applyDefaults()` — Fill empty parameter values with resolved defaults.
- `inferType()` — Best-effort ParamDef type for an imported default value.
- `validateInstanceValues()` — Validate a label value mapping against paramDefs.

## Used by

- [[revedaEditor\fileio\createSymbols|revedaEditor.fileio.createSymbols]]
- [[revedaEditor\fileio\loadJSON|revedaEditor.fileio.loadJSON]]
- [[revedaEditor\gui\propertyDialogues|revedaEditor.gui.propertyDialogues]]
- [[revedaEditor\gui\schematicEditor|revedaEditor.gui.schematicEditor]]
- [[revedaEditor\scenes\schematicScene|revedaEditor.scenes.schematicScene]]
- [[revedaEditor\scenes\symbolScene|revedaEditor.scenes.symbolScene]]
- [[revedaEditor\tests\test_params|revedaEditor.tests.test_params]]
