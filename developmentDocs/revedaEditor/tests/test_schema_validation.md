# `revedaEditor/tests/test_schema_validation.py`

**Module:** `revedaEditor.tests.test_schema_validation`

## Purpose

JSON schema-validation tests.

## Module docstring

Tests for revedaEditor.fileio.schemaValidation module.

## Classes

- `TestValidateDesignData`
  - `test_valid_symbol()`
  - `test_valid_schematic()`
  - `test_valid_layout()`
  - `test_not_a_list()`
  - `test_empty_list()`
  - `test_single_element()`
  - `test_invalid_view_type()`
  - `test_missing_view_type()`
  - `test_non_dict_header()`
  - `test_invalid_grid_settings_type()`
  - `test_invalid_snap_grid_format()`
  - `test_null_grid_settings_is_valid()`
  - `test_item_missing_type_field()`
  - `test_minimal_valid_file()`
  - `test_legacy_file_without_schema_version()`
- `TestValidateDesignFile`
  - `test_correct_view_type()`
  - `test_wrong_view_type()`
  - `test_invalid_data_fails_before_type_check()`
- `TestStrictValidation`
  - `test_strict_valid_symbol()`
  - `test_strict_valid_schematic()`
  - `test_strict_valid_layout()`
  - `test_strict_valid_layout_path_and_label_native_encoding()`
  - `test_strict_rejects_invalid_layout_path_mode_or_label_height()`
  - `test_strict_rejects_invalid_schematic_pin_direction_or_type()`
  - `test_strict_invalid_item_type()`
- `TestGetSchemaVersion`
  - `test_with_version()`
  - `test_without_version()`
  - `test_invalid_data()`
- `TestDesignFileValidationError`
  - `test_error_attributes()`
  - `test_default_errors_list()`

## Functions

- `valid_symbol_data()`
- `valid_schematic_data()`
- `valid_layout_data()`
- `test_schema_version_is_string()`

## Depends on

- [[revedaEditor/fileio/schemaValidation|revedaEditor.fileio.schemaValidation]]
