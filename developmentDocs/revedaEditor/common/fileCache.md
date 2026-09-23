# `revedaEditor/common/fileCache.py`

**Module:** `revedaEditor.common.fileCache`

## Purpose

`FileCache` — file-content cache keyed by modification time, used to avoid re-reading unchanged JSON.

## Module docstring

File content caching with modification-time invalidation.

## Classes

- `FileCache` — Singleton file content cache with mtime-based invalidation.
  - `get_json()`
  - `invalidate()`
  - `clear()`
  - `size()`
  - internals: `__new__()`

## Used by

- [[revedaEditor/scenes/schematicScene|revedaEditor.scenes.schematicScene]]
