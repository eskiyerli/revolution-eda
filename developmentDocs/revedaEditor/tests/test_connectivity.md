# `revedaEditor\tests\test_connectivity.py`

**Module:** `revedaEditor.tests.test_connectivity`

## Purpose

Tests for the unified connectivity engine (revedaEditor.connectivity).

## Functions

- `qapp()`
- `seg()`
- `port()`
- `test_endpoint_coincidence_joins()`
- `test_t_contact_joins()`
- `test_crossing_without_endpoint_does_not_join()`
- `test_disjoint_segments_stay_separate()`
- `test_set_name_propagates()`
- `test_schematic_pin_names_net_inherit()`
- `test_global_pin_names_net_set()`
- `test_auto_naming_is_deterministic()`
- `test_set_name_conflict_flagged()`
- `test_bus_member_name_compatible_with_bus()`
- `test_pin_vs_set_name_conflict()`
- `test_bus_width_mismatch_flagged()`
- `test_conflicting_pin_names_flagged()`
- `test_floating_port_gets_no_group()`
- `test_connect_by_name_signal_key()`
- `test_from_records_basic()`
- `test_from_records_instance_ports_via_pin_locator()`
- `test_from_records_missing_locator_is_diagnostic_not_crash()`
- `test_from_records_malformed_record_is_diagnostic()`
- `_addNet()`
- `_addSchemPin()`
- `_scenePinItems()`
- `test_parity_with_nameSceneNets_simple()` — Engine and legacy naming agree on geometry without T contacts.
- `test_parity_set_name_propagation()`
- `test_parity_t_contact_difference_is_deliberate()` — Endpoint-on-body T contacts join — the adopted check-context
- `test_parity_global_pin()`
- `test_from_records_rotated_instance_pin_positions()` — `ang` on a sys record is the item's Qt rotation (CCW-positive).
- `test_from_records_rotated_instance_connects()` — A wire ending at the rotated pin's true position must join.

## Depends on

- [[revedaEditor\common\net|revedaEditor.common.net]]
- [[revedaEditor\common\shapes|revedaEditor.common.shapes]]
- [[revedaEditor\connectivity\__init__|revedaEditor.connectivity.__init__]]
- [[revedaEditor\connectivity\adapters|revedaEditor.connectivity.adapters]]
- [[revedaEditor\tests\sceneTestUtils|revedaEditor.tests.sceneTestUtils]]
