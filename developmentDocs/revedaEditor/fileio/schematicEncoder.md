# `revedaEditor/fileio/schematicEncoder.py`

**Module:** `revedaEditor.fileio.schematicEncoder`

## Purpose

`schematicEncoder` — scene items → `sys/scn/scp/txt/pin/label/attr/net` JSON records.

## Classes

- `schematicEncoder(json.JSONEncoder)`
  - `default()`
  - internals: `_encodeSchematicSymbol()`, `_encodeSchematicNet()`, `_encodeSchematicPin()`, `_encodeText()`, `_subtract_point()`

## Depends on

- [[revedaEditor/common/net|revedaEditor.common.net]]
- [[revedaEditor/common/shapes|revedaEditor.common.shapes]]

## Used by

- [[revedaEditor/scenes/schematicScene|revedaEditor.scenes.schematicScene]]
