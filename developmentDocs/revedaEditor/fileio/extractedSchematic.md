# `revedaEditor/fileio/extractedSchematic.py`

**Module:** `revedaEditor.fileio.extractedSchematic`

## Purpose

`klayoutSchematicGenerator` — reconstructs a schematic view from an extracted (RCX/LVS) netlist.

## Classes

- `klayoutSchematicGenerator` — Generates a temporary schematic from LVS extracted data.
  - `infer_hierarchical_extraction()`
  - `buildPositionMapping()`
  - `createTempSchematicEditor()`
  - `addDeviceToSchematic()`
  - `createPinNet()`
  - `addDeviceNets()`
  - `addExtractedPins()`
  - `generateSchematic()`
  - internals: `_make_hashable()`, `_parse_source_netlist()`, `_build_hierarchy_node()`, `_findCellItem()`, `_initializeTempSchematicFile()`, `_resolveSymbolView()`, `_getScene()`, `_getMappedLayoutPosition()`, `_getAggregateLayoutPosition()`, `_toScenePlacement()`, `_defaultLabelUnit()`, `_formatExtractedParamValue()` … (+2)

## Depends on

- [[revedaEditor/backend/dataDefinitions|revedaEditor.backend.dataDefinitions]]
- [[revedaEditor/backend/libBackEnd|revedaEditor.backend.libBackEnd]]
- [[revedaEditor/backend/libraryMethods|revedaEditor.backend.libraryMethods]]
- [[revedaEditor/common/net|revedaEditor.common.net]]
- [[revedaEditor/common/shapes|revedaEditor.common.shapes]]
- [[revedaEditor/fileio/__init__|revedaEditor.fileio.__init__]]
