# `revedaEditor\tests\test_netexpr.py`

**Module:** `revedaEditor.tests.test_netexpr`

## Purpose

Phase 3 tests — net expressions and inherited connections (netSet).

## Classes

- `_MiniSchematicEditor` — Duck-typed schematicEditor: real scene + real loadDesign, no window.
  - `loadSchematic()`

## Functions

- `qapp()`
- `test_parse_netexpr()`
- `test_parse_netexpr_rejects()`
- `test_eval_netexpr_binding_wins()`
- `test_eval_netexpr_default_then_bare_name()`
- `test_parse_netset()`
- `test_format_netset_roundtrip()`
- `test_terminal_binds_and_instance_nets()`
- `test_expr_names_from_records()`
- `test_expr_names_from_records_via_pin_locator()`
- `test_expr_names_conflicting_defaults()`
- `_segs()` — defs: (id, p1, p2, name, strength, expr).
- `test_resolve_expr_default_names_group()` — A wire carrying [@vdd:vdd!] resolves to the default global.
- `test_resolve_expr_netset_override()` — netSet binding beats the expression default.
- `test_resolve_expr_terminal_mode()` — Identity binding (subcircuit definition context) names the net 'vdd'.
- `test_resolve_expr_bare_name_connect_by_name()`
- `test_resolve_malformed_expr_diagnostic()`
- `test_resolve_no_exprs_unchanged()` — No-expression scenes behave exactly as before (auto net<N>).
- `test_resolve_expr_vs_set_conflict()` — An expr resolving to a name different from a SET wire name shorts.
- `test_resolve_expr_on_port()` — Expression on a symbol pin resolves even when the pin is floating.
- `test_resolve_expr_port_overrides_set_global()`
- `test_resolve_symbol_pin_expr_uses_instance_netset()` — A floating pin's [@vdd] resolves via its owning instance's netSet;
- `test_from_records_expr_fields()`
- `test_from_records_netset_override()`
- `test_check_records_expr_diagnostics()`
- `test_schematic_encoder_expr_fields()`
- `test_schematic_encoder_omits_empty_expr()` — No nx/nst keys when expressions are unset — old readers unaffected.
- `test_symbol_encoder_pin_nx()`
- `test_loadjson_decodes_expr_fields()` — nx on scn/scp records and nst on sys records reach live items.
- `test_loadjson_legacy_records_no_expr()` — Records without nx/nst decode with empty expression state.
- `_addNet()`
- `test_scene_collect_net_expr_names()`
- `test_scene_names_nets_with_expr_default()` — [@vdd:vdd!] on a wire resolves to the vdd! global, SET strength.
- `test_scene_names_nets_with_netset()`
- `test_scene_names_nets_terminal_mode()`
- `test_scene_no_exprs_unchanged()` — nameSceneNets output is identical when no expressions are present.
- `test_toggle_resolved_names_visibility()`
- `_writeJson()`
- `_symbolJson()` — Minimal symbol view: pins + instName label + pinOrder/line attrs.
- `_schematicPinRecord()`
- `_wireRecord()`
- `_sysRecord()`
- `exprLibrary()` — Two-level library: top -> mid -> diffpair, vdd bound via netSet.
- `_miniEditorFactory()`
- `test_expr_defs_for_schematic_view()`
- `test_expr_support_instance_nets()`
- `_runNetlister()` — Run a netlister over the exprLibrary top cell; return output text.
- `test_two_level_netset_netlist_xyce()` — Acceptance: vdd! reaches diffpair's implicit terminal through two
- `test_two_level_netset_netlist_spectre()`
- `test_two_level_netset_netlist_vacask()`

## Depends on

- [[revedaEditor\backend\libraryMethods|revedaEditor.backend.libraryMethods]]
- [[revedaEditor\backend\libraryModelView|revedaEditor.backend.libraryModelView]]
- [[revedaEditor\common\labels|revedaEditor.common.labels]]
- [[revedaEditor\common\net|revedaEditor.common.net]]
- [[revedaEditor\common\shapes|revedaEditor.common.shapes]]
- [[revedaEditor\connectivity\__init__|revedaEditor.connectivity.__init__]]
- [[revedaEditor\netlisting\__init__|revedaEditor.netlisting.__init__]]
- [[revedaEditor\netlisting\xyceNetlist|revedaEditor.netlisting.xyceNetlist]]
- [[revedaEditor\tests\sceneTestUtils|revedaEditor.tests.sceneTestUtils]]
