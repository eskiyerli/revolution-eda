# `revedaEditor\fileio\schematicEncoder.py`

**Module:** `revedaEditor.fileio.schematicEncoder`

## Purpose

Module in `revedaEditor\fileio`.

## Classes

- `schematicEncoder(json.JSONEncoder)`
  - `default()`
  - internals: `_encodeSchematicSymbol()`, `_encodeSchematicGroup()`, `_encodeSchematicNet()`, `_encodeSchematicPin()`, `_encodeText()`, `_subtract_point()`

## Depends on

- [[revedaEditor\common\net|revedaEditor.common.net]]
- [[revedaEditor\common\shapes|revedaEditor.common.shapes]]

## Used by

- [[revedaEditor\scenes\schematicScene|revedaEditor.scenes.schematicScene]]
