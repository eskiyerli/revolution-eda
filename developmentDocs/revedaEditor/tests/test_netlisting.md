# `revedaEditor\tests\test_netlisting.py`

**Module:** `revedaEditor.tests.test_netlisting`

## Purpose

Netlister tests against the real xyceNetlist API.

## Functions

- `qapp()`
- `_writeLibrary()` — Create an on-disk library: reveda.lib marker + cell dirs with view files.
- `libraryModel()` — A real designLibrariesModel over a temp library with top + res cells.
- `_fakeEditor()` — Duck-typed schematicEditor stand-in exposing only what xyceNetlist reads.
- `netlister()`
- `_makeSymbol()` — Real schematicSymbol with real symbolPins and resolved symbolLabels.
- `test_parse_array_notation()`
- `test_expand_pin_names()`
- `_viewItemsOf()`
- `test_switch_list_prefers_schematic()`
- `test_switch_list_stop_view_short_circuits()`
- `test_switch_list_falls_back_to_symbol()`
- `test_determine_netlist_view_uses_config()`
- `test_determine_netlist_view_caches()`
- `test_create_symbol_line_scalar()`
- `test_create_symbol_line_array()`
- `test_create_symbol_line_missing_inst_name()`
- `_addNet()`
- `test_collect_subcircuit_content_flat()` — A resistor wired between two named schematic pins netlists correctly.
- `test_collect_subcircuit_content_ignored_symbol()`

## Depends on

- [[revedaEditor\backend\libBackEnd|revedaEditor.backend.libBackEnd]]
- [[revedaEditor\backend\libraryMethods|revedaEditor.backend.libraryMethods]]
- [[revedaEditor\backend\libraryModelView|revedaEditor.backend.libraryModelView]]
- [[revedaEditor\common\labels|revedaEditor.common.labels]]
- [[revedaEditor\common\net|revedaEditor.common.net]]
- [[revedaEditor\common\shapes|revedaEditor.common.shapes]]
- [[revedaEditor\netlisting\xyceNetlist|revedaEditor.netlisting.xyceNetlist]]
- [[revedaEditor\tests\sceneTestUtils|revedaEditor.tests.sceneTestUtils]]
