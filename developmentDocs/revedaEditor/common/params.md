# `revedaEditor/common/params.py`

**Module:** `revedaEditor.common.params`

## Purpose

Typed instance-parameter model (CDF-lite): `ParamDef` definitions, validation/normalization, default resolution, and schematic-label↔parameter bridging.

## Module docstring

Typed instance-parameter model (CDF-lite).

One semantic model for symbol parameter definitions, consumed by the GUI
(instance properties dialog, place-with-form), the JSON load path, the
record-level diagnostics in `connectivity.diagnostics`, and the symbol
importers. The module is deliberately Qt-free so headless paths
(aiTerminal design ops, importers, batch tooling) share identical
semantics.

Persistence
-----------
Parameter definitions live in the symbol's attribute list as a reserved
attribute `paramDefs` whose definition is a JSON-encoded ordered list::

    {"type": "attr", "nam": "paramDefs",
     "def": '[{"name": "r", "type": "float", "default": "1k", ...}]'}

Older files simply lack the attribute (no parameters); older readers see
an opaque attribute they ignore. Instance values are unchanged: they stay
in `sys.ld` as `labelName: [value, visible]` and are *validated*
against the matching `ParamDef` at load and edit time.

Each `ParamDef` declares:

    name      parameter name; matches instance label `@<name>`
    type      "float" | "int" | "string" | "boolean" | "choice"
    default   literal default, may embed `pPar("name")` sibling refs
    minimum   optional numeric lower bound (quantiphy-parseable)
    maximum   optional numeric upper bound (quantiphy-parseable)
    choices   allowed values for type "choice"
    display   False hides the parameter from the instance edit form
    parse     True: numeric values may use quantiphy suffixes ("1k", "2u")

## Classes

- `ParamDef` — Typed parameter definition declared on a symbol.
  - `toDict()`

## Functions

- `paramDefsFromJson()` — Parse the `paramDefs` attribute payload.
- `paramDefsToJson()` — Serialise paramDefs to the `paramDefs` attribute payload.
- `paramDefsFromSymattrs()` — Extract ParamDefs from a symbol attribute dict (`symattrs`).
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

- [[revedaEditor/fileio/createSymbols|revedaEditor.fileio.createSymbols]]
- [[revedaEditor/fileio/loadJSON|revedaEditor.fileio.loadJSON]]
- [[revedaEditor/gui/propertyDialogues|revedaEditor.gui.propertyDialogues]]
- [[revedaEditor/gui/schematicEditor|revedaEditor.gui.schematicEditor]]
- [[revedaEditor/scenes/schematicScene|revedaEditor.scenes.schematicScene]]
- [[revedaEditor/scenes/symbolScene|revedaEditor.scenes.symbolScene]]
- [[revedaEditor/tests/test_params|revedaEditor.tests.test_params]]
