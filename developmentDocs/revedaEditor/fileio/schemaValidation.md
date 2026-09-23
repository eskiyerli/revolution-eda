# `revedaEditor/fileio/schemaValidation.py`

**Module:** `revedaEditor.fileio.schemaValidation`

## Purpose

JSON-schema validation of design files (`schemas/*.schema.json`) with readable error formatting.

## Module docstring

Schema validation for Revolution EDA JSON design files.

Provides JSON Schema definitions and validation utilities for symbol,
schematic, and layout files. Validates files on load to provide clear
error messages instead of cryptic exceptions.

The canonical JSON Schema files are stored alongside this module in the
`schemas/` directory.  They can be referenced from design JSON files
using the standard `$schema` property pointing to the schema `$id`:

  - Symbol:    https://reveda.org/schemas/v1.0/symbol.schema.json
  - Schematic: https://reveda.org/schemas/v1.0/schematic.schema.json
  - Layout:    https://reveda.org/schemas/v1.0/layout.schema.json

Or by relative path to the bundled schema files.

## Classes

- `DesignFileValidationError(Exception)` — Raised when a design file fails schema validation.

## Functions

- `_load_schema()` — Load a JSON schema file from the schemas directory.
- `_format_validation_error()` — Convert a jsonschema ValidationError to a human-friendly message.
- `validate_design_data()` — Validate loaded JSON data against the appropriate design file schema.
- `validate_design_file()` — Validate design file data with an expected view type.
- `get_schema_version()` — Extract the schema version from design file data.

## Used by

- [[revedaEditor/scenes/layoutScene|revedaEditor.scenes.layoutScene]]
- [[revedaEditor/scenes/schematicScene|revedaEditor.scenes.schematicScene]]
- [[revedaEditor/scenes/symbolScene|revedaEditor.scenes.symbolScene]]
- [[revedaEditor/tests/test_schema_validation|revedaEditor.tests.test_schema_validation]]
