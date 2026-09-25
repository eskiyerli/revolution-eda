# `revedaEditor\tests\test_schematic_checks.py`

**Module:** `revedaEditor.tests.test_schematic_checks`

## Purpose

Module in `revedaEditor\tests`.

## Functions

- `qapp()`
- `scene()`
- `_runViolations()`
- `_violationsOf()`
- `_addNet()`
- `_addPin()`
- `_addSymbol()`
- `test_empty_scene_is_clean()`
- `test_dangling_wire_end()`
- `test_rule_selection_skips_disabled_rules()`
- `test_floating_input_pin()`
- `test_floating_output_pin()`
- `test_connected_pin_not_flagged()`
- `test_pin_on_wire_body_is_connected()`
- `test_shorted_outputs()`
- `test_output_and_input_not_shorted()`
- `test_net_name_conflict()`
- `test_matching_net_names_no_conflict()`
- `test_crossover_without_junction()`
- `test_t_junction_not_a_crossover()`
- `test_overlapping_wires_flagged()`
- `test_parallel_offset_wires_not_flagged()`
- `test_duplicate_instance_names()`
- `test_symbol_overlap()`
- `test_off_grid_net_endpoint()`
- `test_bus_width_mismatch()`
- `test_matching_bus_width_no_violation()`
- `test_delete_errors_survives_scene_clear()`
- `test_check_rules_dialogue_defaults_and_selection()`

## Depends on

- [[revedaEditor\checks\schematic|revedaEditor.checks.schematic]]
- [[revedaEditor\common\net|revedaEditor.common.net]]
- [[revedaEditor\common\shapes|revedaEditor.common.shapes]]
- [[revedaEditor\gui\__init__|revedaEditor.gui.__init__]]
- [[revedaEditor\tests\sceneTestUtils|revedaEditor.tests.sceneTestUtils]]
