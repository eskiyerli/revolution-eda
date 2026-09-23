# `revedaEditor/gui/lvsResults.py`

**Module:** `revedaEditor.gui.lvsResults`

## Purpose

LVS results dialog presenting the imported LVS database.

## Classes

- `lvsResultsDialogue(QDialog)`
  - `done()`
  - `closeEvent()`
  - `onLayoutHierarchyCellSelected()`
  - `onSchematicHierarchyCellSelected()`
  - `onNetDataSelected()`
  - `onNetSelected()`
  - `onDeviceSelected()`
  - `onCellSelected()`
  - `onCrossrefSelected()`
  - `onMismatchParamRowSelected()`
  - `onMismatchTerminalRowSelected()`
  - `onMismatchNetRowSelected()`
  - `onMissingInLayoutRowSelected()`
  - `onMissingInSchemRowSelected()`
  - `register_schematic_view()`
  - `eventFilter()`
  - `apply_pending_highlights()`
  - `onSchemNetSelected()`
  - `onSchemDeviceSelected()`
  - internals: `_cleanup_highlights()`, `_build_summary_tab()`, `_build_nets_tab()`, `_build_devices_tab()`, `_build_extracted_netlist_tab()`, `_extract_nets_from_schematic()`, `_extract_devices_from_schematic()`, `_build_cells_tab()`, `_build_mismatches_tab()`, `_build_layout_hierarchy_tab()`, `_build_schematic_hierarchy_tab()`, `_populate_layout_hierarchy_tree()` … (+49)

## Depends on

- [[revedaEditor/backend/LVSModelView|revedaEditor.backend.LVSModelView]]
- [[revedaEditor/backend/pdkLoader|revedaEditor.backend.pdkLoader]]
- [[revedaEditor/common/layoutShapes|revedaEditor.common.layoutShapes]]
- [[revedaEditor/common/net|revedaEditor.common.net]]
- [[revedaEditor/common/shapes|revedaEditor.common.shapes]]
- [[revedaEditor/fileio/__init__|revedaEditor.fileio.__init__]]
- [[revedaEditor/fileio/importlvsdb|revedaEditor.fileio.importlvsdb]]
