# `revedaEditor/tests/test_diagnostics.py`

**Module:** `revedaEditor.tests.test_diagnostics`

## Purpose

Headless connectivity-diagnostics tests.

## Module docstring

Tests for connectivity.diagnostics — headless record-level checks
(checkRecords / checkLayoutRecords) and the loadJSON pin locator.

## Functions

- `init_qapp()`
- `test_checkRecords_clean()`
- `test_checkRecords_floating_pin()`
- `test_checkRecords_dangling_end()`
- `test_checkRecords_dangling_suppressed_by_junction()`
- `test_checkRecords_name_conflict_is_error()`
- `test_checkRecords_malformed_and_unresolved()`
- `test_makeSymbolPinLocator()`
- `test_checkRecords_with_locator_resolves_instance_pins()`
- `_m1Index()`
- `_m2Index()`
- `test_checkLayoutRecords_via_bridge_and_label_name()`
- `test_checkLayoutRecords_pin_names_net_and_is_metal()`
- `test_checkLayoutRecords_label_conflict()`

## Depends on

- [[defaultPDK/layoutLayers|defaultPDK.layoutLayers]]
- [[defaultPDK/process|defaultPDK.process]]
- [[revedaEditor/connectivity/__init__|revedaEditor.connectivity.__init__]]
- [[revedaEditor/fileio/loadJSON|revedaEditor.fileio.loadJSON]]
