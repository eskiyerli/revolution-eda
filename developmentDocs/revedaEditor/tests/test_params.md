# `revedaEditor\tests\test_params.py`

**Module:** `revedaEditor.tests.test_params`

## Purpose

Tests for the Qt-free typed parameter model (common/params.py).

## Classes

- `TestParse`
  - `test_empty()`
  - `test_roundtrip()`
  - `test_symattrs()`
  - `test_malformed_json()`
  - `test_non_list()`
  - `test_missing_name_skipped()`
  - `test_unknown_type_becomes_string()`
  - `test_choices_csv()`
  - `test_validate_param_defs()`
- `TestValidation`
  - `test_float_quantiphy()`
  - `test_float_no_parse()`
  - `test_int()`
  - `test_range()`
  - `test_boolean()`
  - `test_choice()`
  - `test_string()`
  - `test_empty_is_valid()`
  - `test_value_with_ppar()`
- `TestPPar`
  - `test_resolve_default()`
  - `test_at_prefixed_sibling()`
  - `test_list_valued_sibling()`
  - `test_unresolved_stays_literal()`
  - `test_chain()`
  - `test_cycle_terminates()`
  - `test_embedded_refs()`
- `TestEffectiveValue`
  - `test_explicit_value_wins()`
  - `test_default_applies()`
  - `test_apply_defaults()`
- `TestInstanceValidation`
  - `test_validate_ld_records()`
  - `test_missing_values_skipped()`
- `TestInferType`
  - `test_infer()`
- `TestInstanceIntegration`
  - `test_paramDefs_property()`
  - `test_paramdefs_empty()`
  - `test_paramdef_default_overrides_nlp()`
  - `test_explicit_value_beats_paramdef_default()`
  - `test_ppar_default_resolves_sibling()`
  - `test_pending_params_applied()`
- `TestDiagnostics`
  - `test_param_value_error()`
  - `test_valid_params_clean()`
  - `test_no_locator_no_param_diags()`
  - `test_locator_metadata_keys_not_treated_as_pins()`
  - internals: `_locator()`
- `TestDialogs`
  - `test_param_value_widget_types()`
  - `test_place_instance_dialog_values()`
  - `test_place_dialog_hidden_sibling_ppar_paramdef_ctor()`
  - `test_place_dialog_rejects_invalid()`
  - `test_instance_dialog_typed_rows()`
  - `test_place_dialog_hidden_sibling_context()`
  - `test_configure_schematic_instance_params()`
  - `test_symbol_labels_dialogue_params_table()`
- `_Stub` — Minimal stand-in for QLineEdit/QComboBox text accessors.
  - `text()`
  - `currentText()`
- `TestBuildInstanceFromDialog`
  - `test_hidden_param_preserved()`
  - `test_invalid_value_falls_back_to_original()`
  - `test_valid_value_normalizes()`
  - internals: `_symattrs()`

## Functions

- `qapp()`
- `defsJson()`
- `_makeInstance()` — A schematicSymbol instance with the given symattrs + NLP labels.
- `_dialogFor()`
- `_valueRow()`
- `_patchInstSymbol()`

## Depends on

- [[revedaEditor\common\params|revedaEditor.common.params]]
