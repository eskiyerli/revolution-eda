# `revedaEditor\fileio\schemaValidation.py`

**Module:** `revedaEditor.fileio.schemaValidation`

## Purpose

Schema validation for Revolution EDA JSON design files.

## Classes

- `SchemaCompatibility` — Compatibility decision returned by the preparation helpers.
- `DesignFileValidationError(Exception)` — Raised when a design file fails schema validation.

## Functions

- `_load_schema()` — Load a JSON schema file from the schemas directory.
- `_format_validation_error()` — Convert a jsonschema ValidationError to a human-friendly message.
- `validate_design_data()` — Validate loaded JSON data against the appropriate design file schema.
- `validate_design_file()` — Validate design file data with an expected view type.
- `get_schema_version()` — Extract the schema version from design file data.
- `is_canonical_sdl_source()` — Return whether value is safe canonical SDL correspondence metadata.
- `make_view_header()` — Return the canonical header for a newly saved ordinary cellview.
- `register_schema_migration()` — Register one pure, forward migration step.
- `_prepare_versioned_data()` — Resolve a supported schema version and run its migration chain.
- `prepare_design_data()` — Validate, version-check, and migrate an ordinary cellview array.
- `validate_pcell_definition()` — Validate the lightweight PCell definition file persisted by libraries.
- `prepare_pcell_definition()` — Validate and version-check a PCell definition without changing v1 data.

## Used by

- [[revedaEditor\backend\libBackEnd|revedaEditor.backend.libBackEnd]]
- [[revedaEditor\backend\libraryModelView|revedaEditor.backend.libraryModelView]]
- [[revedaEditor\fileio\importGDS|revedaEditor.fileio.importGDS]]
- [[revedaEditor\fileio\layoutEncoder|revedaEditor.fileio.layoutEncoder]]
- [[revedaEditor\fileio\loadJSON|revedaEditor.fileio.loadJSON]]
- [[revedaEditor\scenes\layoutScene|revedaEditor.scenes.layoutScene]]
- [[revedaEditor\scenes\schematicScene|revedaEditor.scenes.schematicScene]]
- [[revedaEditor\scenes\symbolScene|revedaEditor.scenes.symbolScene]]
- [[revedaEditor\tests\test_schema_validation|revedaEditor.tests.test_schema_validation]]
